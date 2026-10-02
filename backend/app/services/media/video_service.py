"""Business flow for safe, deterministic editing of uploaded videos."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.media_asset import MediaAsset
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.media import AspectCropOperation, AudioOperation, MergeVideoOperation, SubtitleOperation, TextOverlayOperation, TrimVideoOperation
from app.services.file_storage import LocalFileStorage
from app.services.media.video_processor import (
    FFmpegVideoProcessor,
    VideoMetadata,
    VideoProcessorError,
)
from app.services.media.versioning import create_versioned_asset
logger = logging.getLogger(__name__)
DURATION_TOLERANCE_SECONDS = 0.25



VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


VIDEO_SIGNATURES = {
    "video/mp4": "mp4",
    "video/quicktime": "mp4",
    "video/webm": "webm",
}

class VideoService:
    def __init__(self, processor: FFmpegVideoProcessor | None = None):
        self.storage = LocalFileStorage(settings.UPLOAD_DIR)
        self.generated_dir = Path(settings.UPLOAD_DIR) / "edited-videos"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.processor = processor or FFmpegVideoProcessor(
            settings.FFMPEG_BINARY,
            settings.FFPROBE_BINARY,
            settings.VIDEO_PROCESS_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _validate_source_container(path: Path, content_type: str) -> None:
        try:
            with path.open("rb") as source_file:
                header = source_file.read(32)
        except OSError as error:
            raise VideoProcessorError("Không thể đọc video nguồn") from error
        if content_type in {"video/mp4", "video/quicktime"}:
            valid = len(header) >= 8 and header[4:8] == b"ftyp"
        else:
            valid = header.startswith(b"\x1a\x45\xdf\xa3")
        if not valid:
            raise VideoProcessorError("Container video nguồn không hợp lệ")

    def _probe_source(self, source: MediaAsset) -> VideoMetadata:
        try:
            path = self.storage.resolve(source.filepath)
            self._validate_source_container(path, source.content_type)
            metadata = self.processor.probe(path)
            self._validate_metadata(metadata)
            return metadata
        except Exception as error:
            raise HTTPException(status_code=422, detail="Không thể đọc metadata video nguồn") from error
    @staticmethod
    def _owned_upload(
        db: Session, conversation_id: int, file_id: int, current_user: User
    ) -> UploadedFile:
        source = (
            db.query(UploadedFile)
            .join(UploadedFile.conversation)
            .filter(
                UploadedFile.id == file_id,
                UploadedFile.conversation_id == conversation_id,
                UploadedFile.conversation.has(user_id=current_user.id),
            )
            .first()
        )
        if not source:
            raise HTTPException(status_code=404, detail="Video nguồn không tồn tại hoặc không thuộc cuộc trò chuyện")
        if (source.content_type or "").lower() not in VIDEO_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Tệp nguồn không phải video được hỗ trợ")
        if source.size > settings.MAX_VIDEO_SIZE:
            raise HTTPException(status_code=413, detail="Video nguồn vượt quá kích thước cho phép")
        return source

    def register_uploaded_video(
        self, *, db: Session, conversation_id: int, source_file_id: int, current_user: User
    ) -> MediaAsset:
        source = self._owned_upload(db, conversation_id, source_file_id, current_user)
        existing = (
            db.query(MediaAsset)
            .filter(MediaAsset.source_uploaded_file_id == source.id, MediaAsset.kind == "video")
            .first()
        )
        if existing:
            return existing
        try:
            path = self.storage.resolve(source.filepath)
            self._validate_source_container(path, source.content_type)
            metadata = self.processor.probe(path)
            self._validate_metadata(metadata)
        except Exception as error:
            raise HTTPException(status_code=422, detail="Không thể dùng video nguồn lúc này") from error
        asset = MediaAsset(
            user_id=current_user.id, conversation_id=conversation_id,
            source_uploaded_file_id=source.id, version_number=1, kind="video",
            operation="upload", status="completed", prompt="Video tải lên",
            filename=source.filename, filepath=source.filepath,
            content_type=source.content_type, size=source.size,
            operation_params={}, duration_seconds=metadata.duration_seconds,
            width=metadata.width, height=metadata.height,
        )
        db.add(asset)
        db.flush()
        asset.root_asset_id = asset.id
        db.commit()
        db.refresh(asset)
        return asset

    def trim(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: TrimVideoOperation, current_user: User,
    ) -> MediaAsset:
        source = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == source_asset_id, MediaAsset.user_id == current_user.id,
                MediaAsset.conversation_id == conversation_id, MediaAsset.kind == "video",
                MediaAsset.status == "completed",
            ).first()
        )
        if not source or not source.filepath:
            raise HTTPException(status_code=404, detail="Video asset nguồn không tồn tại hoặc không thuộc cuộc trò chuyện")
        if source.size > settings.MAX_VIDEO_SIZE:
            raise HTTPException(status_code=413, detail="Video nguồn vượt quá kích thước cho phép")
        if source.duration_seconds is None:
            raise HTTPException(status_code=422, detail="Video nguồn thiếu metadata thời lượng")
        if operation.end > source.duration_seconds:
            raise HTTPException(status_code=422, detail="Mốc kết thúc vượt quá thời lượng video nguồn")

        asset = self._new_edit_asset(db, source, "trim", operation.model_dump())

        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            source_path = self.storage.resolve(source.filepath)
            source_metadata = self._probe_source(source)
            self.processor.trim(source_path, destination, operation.start, operation.end)
            self._complete_output(asset, destination, db, expected_duration=operation.end - operation.start, expected_audio=source_metadata.has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể xử lý video lúc này") from error

    def text_overlay(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: TextOverlayOperation, current_user: User,
    ) -> MediaAsset:
        source = self._get_source(db, conversation_id, source_asset_id, current_user)
        if source.duration_seconds is None or operation.end > source.duration_seconds:
            raise HTTPException(status_code=422, detail="Timing overlay vượt quá thời lượng video")
        asset = self._new_edit_asset(db, source, operation.operation, operation.model_dump())
        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            source_path = self.storage.resolve(source.filepath)
            source_metadata = self._probe_source(source)
            self.processor.text_overlay(source_path, destination, operation.text, operation.start,
                                         operation.end, operation.position, operation.font_size,
                                         operation.text_color, operation.background)
            self._complete_output(asset, destination, db, expected_duration=source.duration_seconds, expected_audio=source_metadata.has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể xử lý video lúc này") from error
    def merge(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: MergeVideoOperation, current_user: User,
    ) -> MediaAsset:
        if source_asset_id not in operation.source_asset_ids:
            raise HTTPException(status_code=422, detail="Source route không nằm trong danh sách merge")
        sources = [self._get_source(db, conversation_id, asset_id, current_user) for asset_id in operation.source_asset_ids]
        source_metadata = [self._probe_source(source) for source in sources]
        compatibility = {
            (metadata.width, metadata.height, metadata.has_audio, metadata.video_codec, metadata.audio_codec)
            for metadata in source_metadata
        }
        if len(compatibility) != 1:
            raise HTTPException(status_code=422, detail="Các video merge không tương thích về dimensions/audio/codec")
        if any(source.duration_seconds is None for source in sources):
            raise HTTPException(status_code=422, detail="Video merge thiếu metadata thời lượng")
        if sum(source.duration_seconds for source in sources) > settings.MAX_VIDEO_DURATION_SECONDS:
            raise HTTPException(status_code=422, detail="Tổng thời lượng video merge vượt giới hạn")
        asset = self._new_edit_asset(db, sources[0], "merge", operation.model_dump())
        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            paths = [self.storage.resolve(source.filepath) for source in sources]
            self.processor.merge(paths, destination)
            self._complete_output(asset, destination, db, expected_duration=sum(source.duration_seconds for source in sources), expected_audio=source_metadata[0].has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể ghép video lúc này") from error
    def audio(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: AudioOperation, current_user: User,
    ) -> MediaAsset:
        source = self._get_source(db, conversation_id, source_asset_id, current_user)
        asset = self._new_edit_asset(db, source, operation.operation, operation.model_dump())
        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            source_path = self.storage.resolve(source.filepath)
            source_metadata = self._probe_source(source)
            self.processor.volume(source_path, destination, operation.volume, operation.operation == "mute")
            self._complete_output(asset, destination, db, expected_duration=source.duration_seconds, expected_audio=source_metadata.has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể xử lý audio video lúc này") from error
    def subtitles(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: SubtitleOperation, current_user: User,
    ) -> MediaAsset:
        source = self._get_source(db, conversation_id, source_asset_id, current_user)
        if source.duration_seconds is None or any(entry.end > source.duration_seconds for entry in operation.entries):
            raise HTTPException(status_code=422, detail="Timing subtitle vượt quá thời lượng video")
        asset = self._new_edit_asset(db, source, "subtitle", operation.model_dump())
        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            source_path = self.storage.resolve(source.filepath)
            source_metadata = self._probe_source(source)
            self.processor.subtitles(source_path, destination, [entry.model_dump() for entry in operation.entries], operation.position)
            self._complete_output(asset, destination, db, expected_duration=source.duration_seconds, expected_audio=source_metadata.has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể xử lý video lúc này") from error
    def aspect_crop(
        self, *, db: Session, conversation_id: int, source_asset_id: int,
        operation: AspectCropOperation, current_user: User,
    ) -> MediaAsset:
        source = self._get_source(db, conversation_id, source_asset_id, current_user)
        dimensions = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}
        width, height = dimensions[operation.aspect_ratio]
        asset = self._new_edit_asset(db, source, "aspect_crop", operation.model_dump())
        destination = self.generated_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            source_path = self.storage.resolve(source.filepath)
            source_metadata = self._probe_source(source)
            self.processor.aspect_crop(source_path, destination, width, height)
            self._complete_output(asset, destination, db, source.duration_seconds, expected_dimensions=(width, height), expected_audio=source_metadata.has_audio)
            return asset
        except Exception as error:
            self._cleanup_output(destination)
            self._mark_failed(db, asset, f"Video {asset.operation} failed")
            raise HTTPException(status_code=502, detail="Không thể xử lý video lúc này") from error

    @staticmethod
    def _mark_failed(db: Session, asset: MediaAsset, message: str) -> None:
        if asset.status == "completed":
            return
        asset.status = "failed"
        asset.error_message = message
        try:
            db.commit()
        except Exception as error:
            db.rollback()
            logger.error(
                "Unable to persist failed video asset state (%s)",
                type(error).__name__,
            )

    @staticmethod
    def _cleanup_output(destination: Path) -> None:
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass

    def _get_source(self, db: Session, conversation_id: int, source_asset_id: int, current_user: User) -> MediaAsset:
        source = db.query(MediaAsset).filter(
            MediaAsset.id == source_asset_id, MediaAsset.user_id == current_user.id,
            MediaAsset.conversation_id == conversation_id, MediaAsset.kind == "video",
            MediaAsset.status == "completed",
        ).first()
        if not source or not source.filepath:
            raise HTTPException(status_code=404, detail="Video asset nguồn không tồn tại hoặc không thuộc cuộc trò chuyện")
        if source.size > settings.MAX_VIDEO_SIZE:
            raise HTTPException(status_code=413, detail="Video nguồn vượt quá kích thước cho phép")
        return source

    def _new_edit_asset(self, db: Session, source: MediaAsset, operation: str, params: dict) -> MediaAsset:
        return create_versioned_asset(
            db,
            source,
            lambda root_id, version_number: MediaAsset(
                user_id=source.user_id,
                conversation_id=source.conversation_id,
                parent_asset_id=source.id,
                root_asset_id=root_id,
                version_number=version_number,
                kind="video",
                operation=operation,
                status="processing",
                prompt=operation,
                operation_params=params,
                content_type="video/mp4",
            ),
        )

    def _complete_output(
        self, asset: MediaAsset, destination: Path, db: Session,
        expected_duration: float | None, expected_dimensions: tuple[int, int] | None = None,
        expected_audio: bool | None = None,
        expected_aspect_ratio: str | None = None,
        storage_prefix: str = "edited-videos",
    ) -> None:
        if not destination.is_file() or destination.stat().st_size == 0:
            raise VideoProcessorError("FFmpeg không tạo file video hợp lệ")
        if destination.stat().st_size > settings.MAX_VIDEO_SIZE:
            raise VideoProcessorError("Video kết quả vượt quá kích thước cho phép")
        header = destination.read_bytes()[:16]
        if len(header) < 8 or header[4:8] != b"ftyp":
            raise VideoProcessorError("File kết quả không phải MP4 hợp lệ")
        metadata = self.processor.probe(destination)
        self._validate_metadata(metadata)
        if expected_dimensions and (metadata.width, metadata.height) != expected_dimensions:
            raise VideoProcessorError("Kích thước video kết quả không đúng operation")
        if expected_audio is not None and metadata.has_audio != expected_audio:
            raise VideoProcessorError("Audio stream video kết quả không đúng operation")
        if expected_aspect_ratio:
            target = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:5": 4 / 5, "3:2": 3 / 2, "2:3": 2 / 3}.get(expected_aspect_ratio)
            actual = metadata.width / metadata.height if metadata.height else 0
            if target is None or actual <= 0 or abs(actual - target) / target > 0.02:
                raise VideoProcessorError("Tỷ lệ khung hình video kết quả không đúng yêu cầu")
        asset.filename = destination.name
        asset.filepath = (Path(storage_prefix) / destination.name).as_posix()
        asset.size = destination.stat().st_size
        if expected_duration is not None and abs(metadata.duration_seconds - expected_duration) > DURATION_TOLERANCE_SECONDS:
            raise VideoProcessorError("Duration video kết quả không đúng operation")
        asset.duration_seconds = metadata.duration_seconds
        asset.width, asset.height = metadata.width, metadata.height
        asset.status = "completed"
        db.commit()
        db.refresh(asset)
    @staticmethod
    def _validate_metadata(metadata: VideoMetadata) -> None:
        if metadata.width <= 0 or metadata.height <= 0:
            raise VideoProcessorError("Video thiếu kích thước hợp lệ")
        if metadata.duration_seconds <= 0:
            raise VideoProcessorError("Video thiếu thời lượng hợp lệ")
        if metadata.duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            raise VideoProcessorError("Video vượt quá thời lượng cho phép")


video_service = VideoService()
