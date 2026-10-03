"""Safe conversational planning and execution for technical video edits."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.media_asset import MediaAsset
from app.models.media_request import MediaEditRequest
from app.models.user import User
from app.schemas.media import (
    AspectCropOperation,
    AudioOperation,
    ConversationalEditPlan,
    ConversationalEditPlanRequest,
    MergeVideoOperation,
    SubtitleOperation,
    TextOverlayOperation,
    TrimVideoOperation,
    VideoEditRequest,
)
from app.services.media.video_service import VideoService, video_service


MAX_CONVERSATIONAL_OPERATIONS = 8
logger = logging.getLogger(__name__)


class ConversationalEditExecutionError(Exception):
    def __init__(self, *, created_assets: list[MediaAsset], failed_operation_index: int, failed_operation: str):
        self.created_assets = created_assets
        self.failed_operation_index = failed_operation_index
        self.failed_operation = failed_operation
        super().__init__(f"Conversational video operation failed: {failed_operation}")

def _plain(value: str) -> str:
    value = value.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def _number(value: str) -> float:
    return float(value.replace(",", "."))


def _position(text: str) -> str:
    if re.search(r"\b(top|tren|dau)\b", text):
        return "top"
    if re.search(r"\b(center|giua|middle)\b", text):
        return "center"
    return "bottom"


def _timing(text: str, start_at: int, duration: float) -> tuple[float, float]:
    window = text[start_at:start_at + 140]
    last = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:giay|s|seconds?)\s*(?:cuoi|last)\b", window)
    if last:
        amount = _number(last.group(1))
        return max(0.0, duration - amount), duration
    explicit = re.search(
        r"(?:tu|from)\s+(\d+(?:[.,]\d+)?)\s*(?:giay|s)?\s*(?:den|to)\s+(\d+(?:[.,]\d+)?)",
        window,
    )
    if explicit:
        return _number(explicit.group(1)), _number(explicit.group(2))
    end = min(duration, 3.0)
    return max(0.0, duration - end), duration


class VideoEditPlanService:
    """Parse natural language into an allowlisted plan, then reuse VideoService."""

    def __init__(self, video_service_instance: VideoService | None = None):
        self.video_service = video_service_instance or video_service

    @staticmethod
    def _unsupported_instruction(instruction: str) -> bool:
        # Ignore quoted text content: "add text 'logo sale'" is still a
        # supported text overlay, while "add a logo" is not.
        unquoted = re.sub(r"""(['"]).*?\1""", " ", instruction)
        direct_operation = re.search(
            r"\b(?:rotate|xoay|speed|thumbnail)\b",
            unquoted,
        )
        unsupported_terms = (
            r"(?:logo|watermark|animation|animated|music|nhac|"
            r"rotate|xoay|speed|thumbnail|hook|sticker|filter|"
            r"effect|effects|transition|chuyen canh)"
        )
        operation_request = re.search(
            rf"\b(?:add|them|chen|insert|replace|thay|doi|change|remove|"
            rf"xoa|create|tao)\b.{{0,40}}\b{unsupported_terms}\b",
            unquoted,
        )
        if direct_operation or operation_request:
            return True

        action = r"(?:add|them|chen|insert|replace|thay|doi|change|remove|xoa|create|tao)"
        supported_action = (
            r"(?:\b(?:add|them|chen)\s+(?:text|cta|call to action|subtitle|phu de)\b|"
            r"\b(?:replace|thay|doi|change)\b[^,.;]*\b(?:16:9|9:16|1:1|4:5|"
            r"aspect|crop|ty le|ratio|volume|am luong)\b)"
        )
        clauses = re.split(r"[,;]|\b(?:and|va|và|then|roi|rồi|sau do|sau đó)\b", unquoted)
        for clause in clauses:
            if re.search(rf"\b{action}\b", clause) and not re.search(supported_action, clause):
                return True
        return False
    def parse_instruction(
        self,
        *,
        source_asset_id: int,
        request: ConversationalEditPlanRequest,
        duration: float,
    ) -> ConversationalEditPlan:
        instruction = _plain(request.instruction)
        if self._unsupported_instruction(instruction):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="The requested video operation is not supported")

        parsed: list[tuple[int, VideoEditRequest]] = []

        trim_match = re.search(
            r"\b(?:cat|trim)\b(?:\s+\w+){0,6}\s+(\d+(?:[.,]\d+)?)\s*(?:giay|s|seconds?)\s+(dau|first|cuoi|last)\b",
            instruction,
        )
        range_match = re.search(
            r"\b(?:cat|trim)\b.*?\b(?:tu|from)\s+(\d+(?:[.,]\d+)?)\s*(?:giay|s)?\s*(?:den|to)\s+(\d+(?:[.,]\d+)?)",
            instruction,
        )
        remain_match = re.search(
            r"\b(?:cat|trim)\b.*?\b(?:con|to)\s+(\d+(?:[.,]\d+)?)\s*(?:giay|s|seconds?)\b",
            instruction,
        )
        if trim_match:
            amount = _number(trim_match.group(1))
            if trim_match.group(2) in {"dau", "first"}:
                start, end = amount, duration
            else:
                start, end = 0.0, max(0.0, duration - amount)
            parsed.append((trim_match.start(), TrimVideoOperation(operation="trim", start=start, end=end)))
        elif range_match:
            parsed.append((range_match.start(), TrimVideoOperation(operation="trim", start=_number(range_match.group(1)), end=_number(range_match.group(2)))))
        elif remain_match:
            parsed.append((remain_match.start(), TrimVideoOperation(operation="trim", start=0.0, end=_number(remain_match.group(1)))))
        elif re.search(r"\b(?:cat|trim)\b", instruction):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Trim requires a valid time range")

        aspect_match = re.search(r"\b(16:9|9:16|1:1|4:5)\b", instruction)
        if aspect_match and re.search(r"\b(?:ty le|aspect|crop|doc|ngang|vertical|portrait|tiktok|story)\b", instruction):
            parsed.append((aspect_match.start(), AspectCropOperation(operation="aspect_crop", aspect_ratio=aspect_match.group(1))))

        cta_match = re.search(r"\b(?:cta|call to action)\b\s*[:\-]?\s*(['\"])(.*?)\1", instruction)
        if cta_match:
            timing_duration = duration
            prior_trim = next((operation for position, operation in parsed if position < cta_match.start() and isinstance(operation, TrimVideoOperation)), None)
            if prior_trim:
                timing_duration = prior_trim.end - prior_trim.start
            start, end = _timing(instruction, cta_match.end(), timing_duration)
            text_start, text_end = cta_match.span(2)
            cta_text = request.instruction[text_start:text_end]
            parsed.append((cta_match.start(), TextOverlayOperation(
                operation="cta_overlay",
                text=cta_text,
                start=start,
                end=end,
                position=_position(instruction),
            )))
        elif re.search(r"\b(?:cta|call to action)\b", instruction):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="CTA requires quoted text")

        text_match = re.search(r"\b(?:them text|add text|text overlay)\b\s*[:\-]?\s*(['\"])(.*?)\1", instruction)
        if text_match:
            timing_duration = duration
            prior_trim = next((operation for position, operation in parsed if position < text_match.start() and isinstance(operation, TrimVideoOperation)), None)
            if prior_trim:
                timing_duration = prior_trim.end - prior_trim.start
            start, end = _timing(instruction, text_match.end(), timing_duration)
            text_start, text_end = text_match.span(2)
            overlay_text = request.instruction[text_start:text_end]
            parsed.append((text_match.start(), TextOverlayOperation(
                operation="text_overlay",
                text=overlay_text,
                start=start,
                end=end,
                position=_position(instruction),
            )))
        elif re.search(r"\b(?:them text|add text|text overlay)\b", instruction):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Text overlay requires quoted text")

        subtitle_pattern = re.compile(
            r"\b(?:subtitle|phu de)\b\s*[:\-]?\s*(['\"])(.*?)\1\s*(?:tu|from)\s*(\d+(?:[.,]\d+)?)\s*(?:giay|s)?\s*(?:den|to)\s*(\d+(?:[.,]\d+)?)",
        )
        subtitle_matches = list(subtitle_pattern.finditer(instruction))
        if subtitle_matches:
            entries = []
            for match in subtitle_matches:
                text_start, text_end = match.span(2)
                entries.append({
                    "text": request.instruction[text_start:text_end],
                    "start": _number(match.group(3)),
                    "end": _number(match.group(4)),
                })
            parsed.append((subtitle_matches[0].start(), SubtitleOperation(operation="subtitle", entries=entries, position=_position(instruction))))
        elif re.search(r"\b(?:subtitle|phu de)\b", instruction):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Subtitle requires quoted text and timing")

        if re.search(r"\b(?:tat tieng|mute|muted)\b", instruction):
            match = re.search(r"\b(?:tat tieng|mute|muted)\b", instruction)
            parsed.append((match.start(), AudioOperation(operation="mute")))
        else:
            volume_match = re.search(r"\b(?:am luong|volume)\b\s*(?:[a-z]+\s*)?(\d+(?:[.,]\d+)?)\s*(%|x)?", instruction)
            if volume_match:
                value = _number(volume_match.group(1))
                if volume_match.group(2) == "%":
                    value /= 100
                parsed.append((volume_match.start(), AudioOperation(operation="volume", volume=value)))

        if re.search(r"\b(?:ghep|merge|join)\b", instruction):
            match = re.search(r"\b(?:ghep|merge|join)\b", instruction)
            source_ids = [source_asset_id, *request.merge_source_asset_ids]
            if len(set(source_ids)) < 2:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Merge requires at least two valid source assets")
            parsed.append((match.start(), MergeVideoOperation(operation="merge", source_asset_ids=list(dict.fromkeys(source_ids)))))

        if not parsed:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No supported video operation was found")
        parsed.sort(key=lambda item: item[0])
        if len(parsed) > MAX_CONVERSATIONAL_OPERATIONS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Too many video operations in one request")
        return ConversationalEditPlan(source_asset_id=source_asset_id, operations=[operation for _, operation in parsed])

    def _get_source(self, db: Session, conversation_id: int, source_asset_id: int, current_user: User) -> MediaAsset:
        return self.video_service._get_source(db, conversation_id, source_asset_id, current_user)

    def _preflight_source(
        self,
        *,
        db: Session,
        conversation_id: int,
        asset_id: int,
        current_user: User,
    ) -> tuple[MediaAsset, object]:
        source = self._get_source(db, conversation_id, asset_id, current_user)
        # Probe through the existing storage/processor abstraction so a
        # missing, unreadable, invalid or incomplete physical source is
        # rejected before any processing asset is created.
        metadata = self.video_service._probe_source(source)
        if source.duration_seconds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Source video has no duration metadata",
            )
        if abs(float(source.duration_seconds) - metadata.duration_seconds) > 0.25:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Source video metadata is not consistent",
            )
        return source, metadata

    def validate_plan(
        self,
        *,
        db: Session,
        conversation_id: int,
        plan: ConversationalEditPlan,
        current_user: User,
    ) -> MediaAsset:
        source, source_metadata = self._preflight_source(
            db=db,
            conversation_id=conversation_id,
            asset_id=plan.source_asset_id,
            current_user=current_user,
        )
        duration = source.duration_seconds
        for index, operation in enumerate(plan.operations):
            if isinstance(operation, TrimVideoOperation):
                if operation.end > duration:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Trim timing exceeds the current video duration")
                duration = operation.end - operation.start
            elif isinstance(operation, TextOverlayOperation):
                if operation.end > duration:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Overlay timing exceeds the current video duration")
            elif isinstance(operation, SubtitleOperation):
                if any(entry.end > duration for entry in operation.entries):
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Subtitle timing exceeds the current video duration")
            elif isinstance(operation, MergeVideoOperation):
                if index != 0:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Merge must be the first operation in a plan")
                if plan.source_asset_id not in operation.source_asset_ids:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Merge must include the route source asset")
                preflight_sources = [
                    self._preflight_source(
                        db=db,
                        conversation_id=conversation_id,
                        asset_id=asset_id,
                        current_user=current_user,
                    )
                    for asset_id in operation.source_asset_ids
                ]
                sources = [item[0] for item in preflight_sources]
                metadata = [item[1] for item in preflight_sources]
                compatibility = {
                    (
                        item.width,
                        item.height,
                        item.has_audio,
                        item.video_codec,
                        item.audio_codec,
                    )
                    for item in metadata
                }
                if len(compatibility) != 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Merge sources are not compatible",
                    )
                durations = [item.duration_seconds for item in metadata]
                duration = sum(durations)
                if duration > settings.MAX_VIDEO_DURATION_SECONDS:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Merged video exceeds the duration limit",
                    )
        return source

    @staticmethod
    def execution_payload_hash(*, source_asset_id: int, plan: ConversationalEditPlan) -> str:
        payload = {
            "source_asset_id": source_asset_id,
            "plan": plan.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def register_execution_request(
        self,
        *,
        db: Session,
        user_id: int,
        conversation_id: int,
        source_asset_id: int,
        plan: ConversationalEditPlan,
        idempotency_key: str,
    ) -> tuple[MediaEditRequest, bool]:
        payload_hash = self.execution_payload_hash(source_asset_id=source_asset_id, plan=plan)
        existing = (
            db.query(MediaEditRequest)
            .filter(
                MediaEditRequest.user_id == user_id,
                MediaEditRequest.conversation_id == conversation_id,
                MediaEditRequest.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing:
            if existing.payload_hash != payload_hash:
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            return existing, False

        record = MediaEditRequest(
            user_id=user_id,
            conversation_id=conversation_id,
            source_asset_id=source_asset_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            status="processing",
            created_asset_ids=[],
        )
        db.add(record)
        try:
            db.commit()
            db.refresh(record)
            return record, True
        except IntegrityError as error:
            db.rollback()
            if "uq_media_edit_requests_scope_key" not in str(error).lower():
                raise
            existing = (
                db.query(MediaEditRequest)
                .filter(
                    MediaEditRequest.user_id == user_id,
                    MediaEditRequest.conversation_id == conversation_id,
                    MediaEditRequest.idempotency_key == idempotency_key,
                )
                .first()
            )
            if not existing:
                raise
            if existing.payload_hash != payload_hash:
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác") from error
            return existing, False

    @staticmethod
    def request_assets(db: Session, request: MediaEditRequest) -> list[MediaAsset]:
        asset_ids = request.created_asset_ids or []
        if not asset_ids:
            return []
        assets = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id.in_(asset_ids),
                MediaAsset.user_id == request.user_id,
                MediaAsset.conversation_id == request.conversation_id,
            )
            .all()
        )
        by_id = {asset.id: asset for asset in assets}
        return [by_id[asset_id] for asset_id in asset_ids if asset_id in by_id]

    def persist_request_result(
        self,
        *,
        db: Session,
        request: MediaEditRequest,
        status_value: str,
        created_assets: list[MediaAsset],
        failed_operation_index: int | None = None,
        failed_operation: str | None = None,
        error_message: str | None = None,
    ) -> MediaEditRequest:
        request.status = status_value
        request.created_asset_ids = [asset.id for asset in created_assets]
        request.output_asset_id = created_assets[-1].id if created_assets else None
        request.failed_operation_index = failed_operation_index
        request.failed_operation = failed_operation
        request.error_message = error_message[:2_000] if error_message else None
        try:
            db.commit()
            db.refresh(request)
            return request
        except Exception as error:
            db.rollback()
            logger.error("Unable to persist conversational request result (%s)", type(error).__name__)
            try:
                persisted = db.get(MediaEditRequest, request.id)
                if persisted:
                    persisted.status = "recovery_required"
                    persisted.created_asset_ids = [asset.id for asset in created_assets]
                    persisted.output_asset_id = created_assets[-1].id if created_assets else None
                    persisted.error_message = "Request result needs recovery review"
                    db.commit()
                    db.refresh(persisted)
                    return persisted
            except Exception as recovery_error:
                db.rollback()
                logger.error("Unable to persist conversational request recovery state (%s)", type(recovery_error).__name__)
            raise HTTPException(status_code=503, detail="Kết quả chỉnh sửa cần được kiểm tra lại") from error

    def mark_request_failed(
        self,
        *,
        db: Session,
        request: MediaEditRequest,
        message: str = "Không thể thực thi kế hoạch chỉnh sửa video",
    ) -> MediaEditRequest:
        request.status = "failed"
        request.created_asset_ids = request.created_asset_ids or []
        request.error_message = message[:2_000]
        try:
            db.commit()
            db.refresh(request)
        except Exception as error:
            db.rollback()
            logger.error("Unable to persist conversational request failure (%s)", type(error).__name__)
        return request
    def execute_plan(
        self,
        *,
        db: Session,
        conversation_id: int,
        plan: ConversationalEditPlan,
        current_user: User,
    ) -> list[MediaAsset]:
        self.validate_plan(db=db, conversation_id=conversation_id, plan=plan, current_user=current_user)
        current_id = plan.source_asset_id
        created: list[MediaAsset] = []
        for index, operation in enumerate(plan.operations):
            kwargs = {
                "db": db,
                "conversation_id": conversation_id,
                "source_asset_id": current_id,
                "operation": operation,
                "current_user": current_user,
            }
            try:
                if isinstance(operation, TrimVideoOperation):
                    asset = self.video_service.trim(**kwargs)
                elif isinstance(operation, AspectCropOperation):
                    asset = self.video_service.aspect_crop(**kwargs)
                elif isinstance(operation, TextOverlayOperation):
                    asset = self.video_service.text_overlay(**kwargs)
                elif isinstance(operation, SubtitleOperation):
                    asset = self.video_service.subtitles(**kwargs)
                elif isinstance(operation, AudioOperation):
                    asset = self.video_service.audio(**kwargs)
                elif isinstance(operation, MergeVideoOperation):
                    asset = self.video_service.merge(**kwargs)
                else:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported video operation")
            except Exception as error:
                raise ConversationalEditExecutionError(
                    created_assets=created,
                    failed_operation_index=index,
                    failed_operation=operation.operation,
                ) from error
            created.append(asset)
            current_id = asset.id
        return created


video_edit_plan_service = VideoEditPlanService()
