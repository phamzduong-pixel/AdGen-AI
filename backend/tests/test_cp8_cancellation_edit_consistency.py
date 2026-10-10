"""CP-8 regression tests for disconnect cleanup and edit stream consistency."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import StreamingResponse

import app.models  # noqa: F401
from app.api import message as message_api
from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageUpdate
from app.services import ai_service, message_service
from app.services.output_validator.models import ValidationResult


class NoRetrieval:
    def retrieve(self, *_args, **_kwargs):
        return SimpleNamespace(was_requested=False, provider_result=None)


class CancellationAndEditConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.user = User(
            username="cp8-owner",
            email="cp8-owner@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    def conversation_with_turn(self):
        conversation = Conversation(title="CP-8", user_id=self.user.id)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="old user request",
            prompt_type="facebook",
        )
        old_assistant = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="old assistant response",
            prompt_type="facebook",
        )
        self.db.add_all([user_message, old_assistant])
        self.db.commit()
        self.db.refresh(user_message)
        return conversation, user_message

    def messages_for(self, conversation):
        self.db.expire_all()
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id)
            .all()
        )

    def test_asgi_disconnect_closes_local_source_before_next_chunk(self):
        state = {"closed": False, "second_chunk_requested": False}

        def source():
            try:
                yield "first"
                state["second_chunk_requested"] = True
                yield "second"
            finally:
                state["closed"] = True

        async def exercise():
            disconnect_ready = asyncio.Event()
            request_seen = False
            sent = []

            async def receive():
                nonlocal request_seen
                if not request_seen:
                    request_seen = True
                    return {"type": "http.request", "body": b"", "more_body": False}
                await disconnect_ready.wait()
                return {"type": "http.disconnect"}

            async def send(event):
                sent.append(event)
                if event["type"] == "http.response.body" and event.get("body") == b"first":
                    disconnect_ready.set()

            scope = {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.4"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/messages/stream",
                "raw_path": b"/messages/stream",
                "query_string": b"",
                "headers": [],
                "client": ("testclient", 1234),
                "server": ("testserver", 80),
            }
            request = Request(scope, receive=receive)
            response = StreamingResponse(message_api._stream_with_disconnect(request, source()))
            await response(scope, receive, send)
            return sent

        sent = asyncio.run(exercise())

        self.assertIn(
            {"type": "http.response.body", "body": b"first", "more_body": True},
            sent,
        )
        self.assertTrue(state["closed"])
        self.assertFalse(state["second_chunk_requested"])

    def test_ai_generator_close_closes_local_provider_stream_without_logging_final(self):
        state = {"closed": False}

        class ProviderStream:
            def __iter__(self):
                return self

            def __next__(self):
                if getattr(self, "sent", False):
                    raise StopIteration
                self.sent = True
                return SimpleNamespace(text="PARTIAL RAW")

            def close(self):
                state["closed"] = True

        provider_stream = ProviderStream()
        models = SimpleNamespace(
            generate_content_stream=lambda **_kwargs: provider_stream,
        )
        valid = ValidationResult(
            is_valid=True,
            sanitized_content="CANONICAL FINAL",
            issues=[],
        )

        with patch.object(ai_service, "client", SimpleNamespace(models=models)), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=valid,
        ), patch.object(ai_service.learning_dataset_service, "log_generation") as writer:
            generator = ai_service.stream_ai([{"role": "user", "content": "cancel"}])
            self.assertEqual(next(generator), "PARTIAL RAW")
            generator.close()

        self.assertTrue(state["closed"])
        writer.assert_not_called()

    def test_edit_cancellation_keeps_existing_assistant(self):
        conversation, user_message = self.conversation_with_turn()

        def partial_stream(**_kwargs):
            yield "PARTIAL RAW"
            yield " UNREAD"

        with patch.object(message_service, "external_retrieval_service", NoRetrieval()), patch.object(
            message_service,
            "stream_ai",
            side_effect=partial_stream,
        ):
            generator = message_service.edit_message_stream_service(
                user_message.id,
                MessageUpdate(content="new user request", prompt_type="facebook"),
                self.db,
                self.user,
            )
            self.assertEqual(next(generator), "PARTIAL RAW")
            generator.close()

        messages = self.messages_for(conversation)
        self.assertEqual(
            [(item.role, item.content) for item in messages],
            [("user", "new user request"), ("assistant", "old assistant response")],
        )

    def test_edit_provider_error_keeps_existing_assistant(self):
        conversation, user_message = self.conversation_with_turn()

        def failing_stream(**_kwargs):
            yield "PARTIAL RAW"
            raise RuntimeError("fake provider failure")

        with patch.object(message_service, "external_retrieval_service", NoRetrieval()), patch.object(
            message_service,
            "stream_ai",
            side_effect=failing_stream,
        ):
            output = list(
                message_service.edit_message_stream_service(
                    user_message.id,
                    MessageUpdate(content="new user request", prompt_type="facebook"),
                    self.db,
                    self.user,
                )
            )

        self.assertEqual(output, ["PARTIAL RAW", "\n[ADGEN_STREAM_ERROR]\n"])
        messages = self.messages_for(conversation)
        self.assertEqual(
            [(item.role, item.content) for item in messages],
            [("user", "new user request"), ("assistant", "old assistant response")],
        )

    def test_completed_edit_replaces_successors_once_with_canonical_content(self):
        conversation, user_message = self.conversation_with_turn()
        captured = {}

        def successful_stream(**kwargs):
            captured["history"] = kwargs["history"]
            yield "RAW STREAM"
            kwargs["on_final_content"]("CANONICAL FINAL")

        with patch.object(message_service, "external_retrieval_service", NoRetrieval()), patch.object(
            message_service,
            "stream_ai",
            side_effect=successful_stream,
        ):
            output = list(
                message_service.edit_message_stream_service(
                    user_message.id,
                    MessageUpdate(content="new user request", prompt_type="facebook"),
                    self.db,
                    self.user,
                )
            )

        self.assertEqual(output, ["RAW STREAM"])
        self.assertEqual(captured["history"], [{"role": "user", "content": "new user request", "prompt_type": "facebook"}])
        messages = self.messages_for(conversation)
        self.assertEqual(
            [(item.role, item.content) for item in messages],
            [("user", "new user request"), ("assistant", "CANONICAL FINAL")],
        )


if __name__ == "__main__":
    unittest.main()
