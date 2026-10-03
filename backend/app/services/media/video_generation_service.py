import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.media_job import MediaJob
from app.models.user import User
from app.schemas.media import VideoGenerationRequest
from app.services.file_storage import LocalFileStorage
from app.services.media.providers.factory import build_video_generation_provider
from app.services.media.providers.video_generation import (
    MAX_REFERENCE_IMAGES,
    VideoGenerationInput,
    VideoGenerationProvider,
    VideoGenerationProviderError,
    VideoGenerationProviderUnavailable,
)
from app.services.media.video_service import VideoService


VIDEO_PROVIDER_OUTPUT_TYPES = {"video/mp4", "video/quicktime"}
VALID_JOB_STATUSES = {"queued", "processing", "completed", "failed", "cancelled"}


class VideoGenerationService:
    """Owns provider-backed video jobs without implementing a worker queue."""

    def __init__(
        self,
        provider: VideoGenerationProvider | None = None,
        video_service: VideoService | None = None,
    ):
        self.provider = provider
        self.video_service = video_service or VideoService()
        self.storage = self.video_service.storage
        self.generated_dir = Path(settings.UPLOAD_DIR) / "generated-videos"
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _conversation(db: Session, conversation_id: int, current_user: User) -> Conversation:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuộc trò chuyện không tồn tại hoặc bạn không có quyền truy cập",
            )
        return conversation

    def _provider(self) -> VideoGenerationProvider:
        if self.provider is not None:
            return self.provider
        return build_video_generation_provider()

    def _reference_data(
        self,
        db: Session,
        request: VideoGenerationRequest,
        conversation: Conversation,
        current_user: User,
    ) -> tuple[tuple[bytes, str], ...]:
        if len(request.reference_asset_ids) > MAX_REFERENCE_IMAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Chỉ được dùng tối đa 3 ảnh tham chiếu",
            )
        if not request.reference_asset_ids:
            return ()
        assets = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id.in_(request.reference_asset_ids),
                MediaAsset.user_id == current_user.id,
                MediaAsset.conversation_id == conversation.id,
                MediaAsset.status == "completed",
                MediaAsset.kind == "image",
            )
            .all()
        )
        by_id = {asset.id: asset for asset in assets}
        if len(by_id) != len(request.reference_asset_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Một hoặc nhiều asset tham chiếu không tồn tại hoặc không thuộc cuộc trò chuyện",
            )
        references: list[tuple[bytes, str]] = []
        for asset_id in request.reference_asset_ids:
            asset = by_id[asset_id]
            if not asset.filepath or not asset.content_type:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Asset tham chiếu thiếu file hoặc MIME type",
                )
            try:
                path = self.storage.resolve(asset.filepath)
                data = path.read_bytes()
            except OSError as error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File asset tham chiếu không còn tồn tại",
                ) from error
            if asset.content_type not in {"image/png", "image/jpeg", "image/webp"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="MIME ảnh tham chiếu không được hỗ trợ",
                )
            if len(data) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Asset tham chiếu vượt quá kích thước cho phép",
                )
            references.append((data, asset.content_type))
        return tuple(references)

    async def create_job(
        self,
        *,
        db: Session,
        conversation_id: int,
        request: VideoGenerationRequest,
        current_user: User,
    ) -> MediaJob:
        conversation = self._conversation(db, conversation_id, current_user)
        if request.duration_seconds and request.duration_seconds > settings.MAX_VIDEO_GENERATION_DURATION_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Thời lượng video tạo ra vượt quá giới hạn cho phép",
            )
        references = self._reference_data(db, request, conversation, current_user)
        provider = self._provider()
        job = MediaJob(
            user_id=current_user.id,
            conversation_id=conversation.id,
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            duration_seconds=request.duration_seconds,
            source_asset_ids=request.reference_asset_ids or None,
            provider=provider.provider_id,
            provider_model=provider.model_name,
            status="queued",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            submission = await provider.submit(
                VideoGenerationInput(
                    prompt=request.prompt,
                    aspect_ratio=request.aspect_ratio,
                    duration_seconds=request.duration_seconds,
                    references=references,
                )
            )
            if not submission.provider_job_id or submission.status not in VALID_JOB_STATUSES:
                raise VideoGenerationProviderError("Provider trả về job submission không hợp lệ")
            job.provider_job_id = submission.provider_job_id
            job.status = submission.status
            db.commit()
            db.refresh(job)
            if job.status == "completed":
                await self._complete_job(db, job, provider, request)
        except Exception as error:
            self._mark_failed(db, job, error)
        return job

    async def get_job(self, *, db: Session, job_id: int, current_user: User) -> MediaJob:
        job = (
            db.query(MediaJob)
            .filter(MediaJob.id == job_id, MediaJob.user_id == current_user.id)
            .first()
        )
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media job không tồn tại hoặc bạn không có quyền truy cập",
            )
        if job.status in {"queued", "processing"} and job.provider_job_id:
            await self._refresh_job(db, job)
        return job

    def list_jobs(
        self,
        *,
        db: Session,
        conversation_id: int,
        current_user: User,
        limit: int = 10,
    ) -> list[MediaJob]:
        self._conversation(db, conversation_id, current_user)
        return (
            db.query(MediaJob)
            .filter(
                MediaJob.conversation_id == conversation_id,
                MediaJob.user_id == current_user.id,
            )
            .order_by(MediaJob.created_at.desc(), MediaJob.id.desc())
            .limit(limit)
            .all()
        )
    async def _refresh_job(self, db: Session, job: MediaJob) -> None:
        provider = self._provider()
        try:
            provider_status = await provider.get_status(job.provider_job_id)
            if provider_status.status not in VALID_JOB_STATUSES:
                raise VideoGenerationProviderError("Provider trả về trạng thái job không hợp lệ")
            job.status = provider_status.status
            if provider_status.error_message:
                job.error_message = provider_status.error_message[:2_000]
            db.commit()
            db.refresh(job)
            if job.status == "failed":
                return
            if job.status == "completed":
                request = VideoGenerationRequest(
                    prompt=job.prompt,
                    aspect_ratio=job.aspect_ratio,
                    duration_seconds=job.duration_seconds,
                    reference_asset_ids=job.source_asset_ids or [],
                )
                await self._complete_job(db, job, provider, request)
        except Exception as error:
            self._mark_failed(db, job, error)

    async def _complete_job(
        self,
        db: Session,
        job: MediaJob,
        provider: VideoGenerationProvider,
        request: VideoGenerationRequest,
    ) -> None:
        try:
            generated = await provider.retrieve_result(job.provider_job_id)
            self._validate_provider_output(generated.data, generated.content_type)
            asset = MediaAsset(
                user_id=job.user_id,
                conversation_id=job.conversation_id,
                version_number=1,
                kind="video",
                operation="generate_video",
                status="processing",
                prompt=job.prompt,
                aspect_ratio=job.aspect_ratio,
                provider=job.provider,
                model=job.provider_model,
                content_type=generated.content_type,
                operation_params={
                    "job_id": job.id,
                    "reference_asset_ids": job.source_asset_ids or [],
                },
            )
            db.add(asset)
            db.flush()
            asset.root_asset_id = asset.id
            db.commit()
            db.refresh(asset)
            destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
            try:
                destination.write_bytes(generated.data)
                self.video_service._complete_output(
                    asset,
                    destination,
                    db,
                    request.duration_seconds,
                    expected_aspect_ratio=request.aspect_ratio,
                    storage_prefix="generated-videos",
                )
                job.output_asset_id = asset.id
                job.status = "completed"
                job.error_message = None
                db.commit()
                db.refresh(job)
            except Exception as error:
                self.video_service._cleanup_output(destination)
                asset.status = "failed"
                asset.error_message = str(error)[:2_000]
                db.commit()
                raise
        except Exception as error:
            self._mark_failed(db, job, error)

    @staticmethod
    def _validate_provider_output(data: bytes, content_type: str | None) -> None:
        if content_type not in VIDEO_PROVIDER_OUTPUT_TYPES:
            raise VideoGenerationProviderError("Provider trả về MIME video không được hỗ trợ")
        if not data or len(data) > settings.MAX_VIDEO_SIZE:
            raise VideoGenerationProviderError("Provider trả về video rỗng hoặc vượt kích thước cho phép")
        if len(data) < 8 or data[4:8] != b"ftyp":
            raise VideoGenerationProviderError("Provider trả về container video không hợp lệ")

    @staticmethod
    def _mark_failed(db: Session, job: MediaJob, error: Exception) -> None:
        job.status = "failed"
        job.error_message = str(error)[:2_000]
        db.commit()
        db.refresh(job)


video_generation_service = VideoGenerationService()
