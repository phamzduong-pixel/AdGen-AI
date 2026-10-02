import unittest

import app.api.media as media_api
from app.schemas.media import (
    AspectCropOperation,
    ConversationalEditPlan,
    TextOverlayOperation,
    TrimVideoOperation,
)
from app.models.media_asset import MediaAsset
from app.models.media_request import MediaEditRequest
from app.services.media.video_edit_plan_service import VideoEditPlanService
from tests.test_video_edit_api import VideoEditApiIntegrationTest


class ConversationalVideoEditApiTest(VideoEditApiIntegrationTest):
    def setUp(self):
        super().setUp()
        self.original_plan_service = media_api.video_edit_plan_service
        media_api.video_edit_plan_service = VideoEditPlanService(self.service)

    def tearDown(self):
        media_api.video_edit_plan_service = self.original_plan_service
        super().tearDown()

    def _plan(self, asset_id, instruction, merge_source_asset_ids=None, conversation=None):
        conversation = conversation or self.conversation
        return self.client.post(
            f"/media/conversations/{conversation.id}/videos/{asset_id}/conversational-edit-plan",
            json={
                "instruction": instruction,
                "merge_source_asset_ids": merge_source_asset_ids or [],
            },
        )

    def _execute(self, asset_id, plan, conversation=None, key=None):
        conversation = conversation or self.conversation
        return self.client.post(
            f"/media/conversations/{conversation.id}/videos/{asset_id}/conversational-edits",
            json={"plan": plan, "confirm": True},
            headers={"Idempotency-Key": key} if key else None,
        )

    def test_plan_parses_multiple_operations_in_text_order(self):
        original = self._register(self._upload().id).json()
        response = self._plan(
            original["id"],
            "cat video con 15 giay, chuyen sang khung doc 9:16, them CTA 'Dat hang ngay' o 3 giay cuoi",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["operation"] for item in response.json()["operations"]], ["trim", "aspect_crop", "cta_overlay"])
        self.assertEqual(response.json()["operations"][-1]["start"], 12.0)

    def test_plan_rejects_unsupported_operation_and_invalid_whole_plan(self):
        original = self._register(self._upload().id).json()
        self.assertEqual(self._plan(original["id"], "add a logo in the corner").status_code, 422)
        self.assertEqual(self._plan(original["id"], "cat video con 25 giay").status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 1)

    def test_execute_plan_reuses_video_service_and_creates_version_chain(self):
        original = self._register(self._upload().id).json()
        planned = self._plan(original["id"], "cat video con 15 giay, chuyen sang khung doc 9:16")
        self.assertEqual(planned.status_code, 200)
        plan = {
            "source_asset_id": original["id"],
            "operations": planned.json()["operations"],
        }
        response = self._execute(original["id"], plan)
        self.assertEqual(response.status_code, 201)
        created = response.json()["created_assets"]
        self.assertEqual([asset["operation"] for asset in created], ["trim", "aspect_crop"])
        first, second = [self.db.get(MediaAsset, asset["id"]) for asset in created]
        source = self.db.get(MediaAsset, original["id"])
        self.assertEqual((first.parent_asset_id, first.version_number), (source.id, 2))
        self.assertEqual((second.parent_asset_id, second.version_number), (first.id, 3))
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")

    def test_execute_rejects_plan_source_mismatch_and_cross_conversation_source(self):
        original = self._register(self._upload().id).json()
        plan = {
            "source_asset_id": original["id"],
            "operations": [{"operation": "trim", "start": 0, "end": 10}],
        }
        mismatch = self._execute(original["id"] + 1, plan)
        self.assertEqual(mismatch.status_code, 422)
        cross_conversation = self._plan(original["id"], "trim video con 10 giay", conversation=self.other_conversation)
        self.assertEqual(cross_conversation.status_code, 404)

    def test_merge_plan_requires_owned_sources(self):
        first = self._register(self._upload().id).json()
        second = self._register(self._upload().id).json()
        planned = self._plan(first["id"], "ghep hai video", [second["id"]])
        self.assertEqual(planned.status_code, 200)
        self.assertEqual(planned.json()["operations"][0]["source_asset_ids"], [first["id"], second["id"]])
        self.assertEqual(self._plan(first["id"], "ghep hai video", [99999]).status_code, 404)

    def test_first_operation_failure_returns_failed_without_created_assets(self):
        original = self._register(self._upload().id).json()
        plan = ConversationalEditPlan(
            source_asset_id=original["id"],
            operations=[TrimVideoOperation(operation="trim", start=0, end=10)],
        )
        self.processor.fail_on_operation_call = 1

        response = self._execute(original["id"], plan.model_dump())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["created_assets"], [])
        self.assertEqual(response.json()["failed_operation_index"], 0)
        self.assertEqual(response.json()["failed_operation"], "trim")
        self.assertIn("Asset gốc", response.json()["error"])
        self.assertEqual(self.db.query(MediaAsset).filter(MediaAsset.status == "completed").count(), 1)
        self.assertEqual(self.db.query(MediaAsset).filter(MediaAsset.status == "failed").count(), 1)

    def test_mid_plan_failure_returns_completed_prefix_and_keeps_assets(self):
        original = self._register(self._upload().id).json()
        plan = ConversationalEditPlan(
            source_asset_id=original["id"],
            operations=[
                TrimVideoOperation(operation="trim", start=0, end=15),
                TextOverlayOperation(operation="text_overlay", text="Buy", start=1, end=3),
            ],
        )
        self.processor.fail_on_operation_call = 2

        response = self._execute(original["id"], plan.model_dump())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "partial")
        self.assertEqual(body["failed_operation_index"], 1)
        self.assertEqual(body["failed_operation"], "text_overlay")
        self.assertEqual(len(body["created_assets"]), 1)
        created = self.db.get(MediaAsset, body["created_assets"][0]["id"])
        source = self.db.get(MediaAsset, original["id"])
        failed = self.db.query(MediaAsset).filter(MediaAsset.status == "failed").one()
        self.assertEqual(body["output_asset"]["id"], created.id)
        self.assertEqual((created.parent_asset_id, created.version_number), (source.id, 2))
        self.assertEqual((failed.parent_asset_id, failed.version_number), (created.id, 3))
        self.assertEqual(self.client.get(f"/media/assets/{created.id}/download").status_code, 200)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")
    def test_preflight_rejects_later_operation_before_creating_first_version(self):
        original = self._register(self._upload().id).json()
        plan = ConversationalEditPlan(
            source_asset_id=original["id"],
            operations=[
                TrimVideoOperation(operation="trim", start=0, end=15),
                TextOverlayOperation(operation="cta_overlay", text="Buy", start=14, end=20),
            ],
        )
        response = self._execute(original["id"], plan.model_dump())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 1)


    def test_plan_rejects_missing_physical_source_before_creating_asset(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        self.service.storage.resolve(source.filepath).unlink()

        response = self._plan(original["id"], "cat video con 15 giay")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 1)

    def test_merge_preflight_rejects_missing_physical_source(self):
        first = self._register(self._upload().id).json()
        second = self._register(self._upload().id).json()
        second_asset = self.db.get(MediaAsset, second["id"])
        self.service.storage.resolve(second_asset.filepath).unlink()

        response = self._plan(first["id"], "ghep hai video", [second["id"]])

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 2)

    def test_merge_preflight_rejects_cross_user_source(self):
        self.current_user = self.other
        foreign_file = self._upload(conversation=self.foreign_conversation, user=self.other)
        foreign_asset = self._register(
            foreign_file.id,
            conversation=self.foreign_conversation,
        ).json()
        self.current_user = self.owner
        first = self._register(self._upload().id).json()

        response = self._plan(first["id"], "ghep hai video", [foreign_asset["id"]])

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.query(MediaAsset).count(), 2)

    def test_merge_compatibility_is_rejected_during_preflight(self):
        first = self._register(self._upload().id).json()
        second = self._register(self._upload().id).json()
        second_asset = self.db.get(MediaAsset, second["id"])
        second_path = self.service.storage.resolve(second_asset.filepath)
        self.processor.probe_overrides[str(second_path)] = (640, 360)

        response = self._plan(first["id"], "ghep hai video", [second["id"]])

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.processor.operation_calls, 0)
        self.assertEqual(self.db.query(MediaAsset).count(), 2)

    def test_mixed_supported_and_unsupported_instruction_is_rejected(self):
        original = self._register(self._upload().id).json()

        unsupported = self._plan(
            original["id"],
            "cat video con 15 giay va them animation",
        )
        supported_quoted_text = self._plan(
            original["id"],
            "cat video con 15 giay va them text 'animation'",
        )

        self.assertEqual(unsupported.status_code, 422)
        self.assertEqual(supported_quoted_text.status_code, 200)
        self.assertEqual(
            [item["operation"] for item in supported_quoted_text.json()["operations"]],
            ["trim", "text_overlay"],
        )

    def test_plan_rejects_unparsed_unsupported_clauses(self):
        original = self._register(self._upload().id).json()
        unsupported_instructions = (
            "cat video con 15 giay va them sticker",
            "cat video con 15 giay va them filter",
            "cat video con 15 giay va them logo animation",
        )

        for instruction in unsupported_instructions:
            with self.subTest(instruction=instruction):
                response = self._plan(original["id"], instruction)
                self.assertEqual(response.status_code, 422)

    def test_plan_keeps_unsupported_keywords_inside_quoted_text(self):
        original = self._register(self._upload().id).json()
        response = self._plan(
            original["id"],
            "cat video con 15 giay va them text 'animation filter sticker'",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["operation"] for item in response.json()["operations"]],
            ["trim", "text_overlay"],
        )


    def test_same_key_replay_completed_returns_same_assets_without_processor_retry(self):
        original = self._register(self._upload().id).json()
        plan = {"source_asset_id": original["id"], "operations": [{"operation": "trim", "start": 0, "end": 10}]}

        first = self._execute(original["id"], plan, key="completed-replay")
        second = self._execute(original["id"], plan, key="completed-replay")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "completed")
        self.assertEqual(first.json()["created_assets"], second.json()["created_assets"])
        self.assertEqual(self.processor.operation_calls, 1)
        self.assertEqual(self.db.query(MediaEditRequest).count(), 1)

    def test_same_key_with_different_payload_returns_409_without_processing(self):
        original = self._register(self._upload().id).json()
        first_plan = {"source_asset_id": original["id"], "operations": [{"operation": "trim", "start": 0, "end": 10}]}
        second_plan = {"source_asset_id": original["id"], "operations": [{"operation": "trim", "start": 0, "end": 9}]}

        first = self._execute(original["id"], first_plan, key="payload-conflict")
        conflict = self._execute(original["id"], second_plan, key="payload-conflict")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.processor.operation_calls, 1)
        self.assertEqual(self.db.query(MediaEditRequest).count(), 1)

    def test_same_key_replay_partial_keeps_prefix_without_processor_retry(self):
        original = self._register(self._upload().id).json()
        plan = {
            "source_asset_id": original["id"],
            "operations": [
                {"operation": "trim", "start": 0, "end": 15},
                {"operation": "text_overlay", "text": "Buy", "start": 1, "end": 3},
            ],
        }
        self.processor.fail_on_operation_call = 2

        first = self._execute(original["id"], plan, key="partial-replay")
        calls_after_first = self.processor.operation_calls
        second = self._execute(original["id"], plan, key="partial-replay")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "partial")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "partial")
        self.assertEqual(second.json()["created_assets"], first.json()["created_assets"])
        self.assertEqual(self.processor.operation_calls, calls_after_first)

    def test_different_keys_for_same_payload_are_independent_requests(self):
        original = self._register(self._upload().id).json()
        plan = {"source_asset_id": original["id"], "operations": [{"operation": "trim", "start": 0, "end": 10}]}

        first = self._execute(original["id"], plan, key="independent-one")
        second = self._execute(original["id"], plan, key="independent-two")

        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertNotEqual(first.json()["created_assets"][0]["id"], second.json()["created_assets"][0]["id"])
        self.assertEqual(self.processor.operation_calls, 2)
        self.assertEqual(self.db.query(MediaEditRequest).count(), 2)

    def test_processing_replay_returns_202_without_processor_call(self):
        original = self._register(self._upload().id).json()
        plan = ConversationalEditPlan(
            source_asset_id=original["id"],
            operations=[TrimVideoOperation(operation="trim", start=0, end=10)],
        )
        record = MediaEditRequest(
            user_id=self.owner.id,
            conversation_id=self.conversation.id,
            source_asset_id=original["id"],
            idempotency_key="already-processing",
            payload_hash=self.original_plan_service.execution_payload_hash(
                source_asset_id=original["id"], plan=plan
            ),
            status="processing",
            created_asset_ids=[],
        )
        self.db.add(record)
        self.db.commit()

        response = self._execute(original["id"], plan.model_dump(), key="already-processing")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "processing")
        self.assertEqual(response.json()["created_assets"], [])
        self.assertEqual(self.processor.operation_calls, 0)
if __name__ == "__main__":
    unittest.main()
