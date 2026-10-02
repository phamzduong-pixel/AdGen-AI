import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.media import ImageGenerateRequest
from app.services.file_storage import LocalFileStorage
from app.services.media.providers import ImageGenerationProvider
from app.services.media.providers.gemini_provider import ImageProviderError, classify_image_provider_error
from app.services.media.providers.factory import build_image_generation_provider
from app.services.media.versioning import create_versioned_asset


logger = logging.getLogger(__name__)


GENERATED_IMAGE_FORMATS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _validate_generated_image(data: bytes, content_type: str | None) -> str:
    """Return a safe extension only for supported, recognisable image bytes."""

    mime_type = (content_type or "").strip().lower()
    extension = GENERATED_IMAGE_FORMATS.get(mime_type)
    if not extension:
        raise ValueError("Provider trả về định dạng ảnh không được hỗ trợ")
    if not data:
        raise ValueError("Provider trả về ảnh rỗng")
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise ValueError("Ảnh tạo ra vượt quá kích thước cho phép")

    signatures_match = {
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not signatures_match[mime_type]:
        raise ValueError("Dữ liệu ảnh không khớp với định dạng được khai báo")
    return extension


def _validate_reference_image(data: bytes, content_type: str | None) -> None:
    try:
        _validate_generated_image(data, content_type)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference image is invalid",
        ) from error


class MediaService:
    def __init__(self, provider: ImageGenerationProvider | None = None):
        self.provider = provider or build_image_generation_provider()
        self.storage = LocalFileStorage(settings.UPLOAD_DIR)
        self.generated_dir = Path(settings.UPLOAD_DIR) / "generated-images"
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _conversation(
        db: Session, conversation_id: int, current_user: User
    ) -> Conversation:
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

    def _reference_image(
        self,
        db: Session,
        request: ImageGenerateRequest,
        conversation: Conversation,
        current_user: User,
    ) -> tuple[bytes | None, str | None, int | None, int | None]:
        if request.reference_file_id:
            source = (
                db.query(UploadedFile)
                .filter(
                    UploadedFile.id == request.reference_file_id,
                    UploadedFile.conversation_id == conversation.id,
                )
                .first()
            )
            if not source or not (source.content_type or "").startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ảnh tham chiếu không hợp lệ hoặc không thuộc cuộc trò chuyện",
                )
            try:
                path = self.storage.resolve(source.filepath)
                data = path.read_bytes()
                _validate_reference_image(data, source.content_type)
                return data, source.content_type, source.id, None
            except FileNotFoundError as error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ảnh tham chiếu không còn tồn tại",
                ) from error
            except OSError as error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference image is unavailable",
                ) from error
        if request.source_asset_id:
            source_asset = (
                db.query(MediaAsset)
                .filter(
                    MediaAsset.id == request.source_asset_id,
                    MediaAsset.user_id == current_user.id,
                    MediaAsset.conversation_id == conversation.id,
                    MediaAsset.kind == "image",
                    MediaAsset.status == "completed",
                )
                .first()
            )
            if not source_asset or not source_asset.filepath:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asset ảnh nguồn không tồn tại hoặc không thuộc cuộc trò chuyện",
                )
            try:
                path = self.storage.resolve(source_asset.filepath)
                data = path.read_bytes()
                _validate_reference_image(data, source_asset.content_type)
                return data, source_asset.content_type, None, source_asset.id
            except FileNotFoundError as error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asset ảnh nguồn không còn tồn tại",
                ) from error
            except OSError as error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reference image is unavailable",
                ) from error
        return None, None, None, None

    async def generate_image(
        self,
        *,
        db: Session,
        conversation_id: int,
        request: ImageGenerateRequest,
        current_user: User,
    ) -> MediaAsset:
        conversation = self._conversation(db, conversation_id, current_user)
        reference, reference_type, source_file_id, parent_id = self._reference_image(
            db, request, conversation, current_user
        )
        operation = "edit" if reference is not None else "generate"
        source_asset = db.get(MediaAsset, parent_id) if parent_id else None
        if source_asset:
            asset = create_versioned_asset(
                db,
                source_asset,
                lambda root_id, version_number: MediaAsset(
                    user_id=current_user.id,
                    conversation_id=conversation.id,
                    parent_asset_id=source_asset.id,
                    root_asset_id=root_id,
                    source_uploaded_file_id=source_file_id,
                    version_number=version_number,
                    kind="image",
                    operation=operation,
                    status="processing",
                    prompt=request.prompt,
                    aspect_ratio=request.aspect_ratio,
                    provider=self.provider.provider_id,
                    model=self.provider.model_name,
                ),
            )
        else:
            asset = MediaAsset(
                user_id=current_user.id,
                conversation_id=conversation.id,
                parent_asset_id=None,
                source_uploaded_file_id=source_file_id,
                version_number=1,
                kind="image",
                operation=operation,
                status="processing",
                prompt=request.prompt,
                aspect_ratio=request.aspect_ratio,
                provider=self.provider.provider_id,
                model=self.provider.model_name,
            )
            db.add(asset)
            db.flush()
            asset.root_asset_id = asset.id
            db.commit()
            db.refresh(asset)
        generated_path: Path | None = None
        try:
            generated = await asyncio.wait_for(
                self.provider.generate(
                    prompt=request.prompt,
                    aspect_ratio=request.aspect_ratio,
                    reference_image=reference,
                    reference_content_type=reference_type,
                ),
                timeout=settings.IMAGE_GENERATION_TIMEOUT_SECONDS,
            )
            extension = _validate_generated_image(
                generated.data, generated.content_type
            )
            filename = f"{uuid.uuid4().hex}{extension}"
            relative_path = Path("generated-images") / filename
            absolute_path = settings.UPLOAD_DIR / relative_path
            generated_path = absolute_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_path.write_bytes(generated.data)

            asset.filename = filename
            asset.filepath = relative_path.as_posix()
            asset.content_type = generated.content_type
            asset.size = len(generated.data)
            asset.status = "completed"
            db.commit()
            db.refresh(asset)
            return asset
        except asyncio.TimeoutError as error:
            self._cleanup_generated_file(generated_path, asset)
            failure = ImageProviderError("PROVIDER_TIMEOUT", provider_status=504)
            safe_status, failure_message, client_message, error_code = self._classify_provider_error(failure)
            self._mark_failed(db, asset, failure_message)
            raise HTTPException(
                status_code=safe_status,
                detail={"code": error_code, "message": client_message},
            ) from error
        except HTTPException as error:
            self._cleanup_generated_file(generated_path, asset)
            safe_status, failure_message, client_message, error_code = self._classify_provider_error(error)
            self._mark_failed(db, asset, failure_message)
            raise HTTPException(
                status_code=safe_status,
                detail={"code": error_code, "message": client_message},
            ) from error
        except ValueError as error:
            self._cleanup_generated_file(generated_path, asset)
            failure = ImageProviderError("PROVIDER_ERROR")
            safe_status, _, _, error_code = self._classify_provider_error(failure)
            self._mark_failed(db, asset, "Image provider returned invalid image")
            raise HTTPException(
                status_code=safe_status,
                detail={"code": error_code, "message": "Image provider returned invalid image"},
            ) from error
        except OSError as error:
            self._cleanup_generated_file(generated_path, asset)
            failure = ImageProviderError("PROVIDER_ERROR")
            safe_status, _, client_message, error_code = self._classify_provider_error(failure)
            self._mark_failed(db, asset, "Image storage failed")
            raise HTTPException(
                status_code=safe_status,
                detail={"code": error_code, "message": client_message},
            ) from error
        except Exception as error:
            self._cleanup_generated_file(generated_path, asset)
            safe_status, failure_message, client_message, error_code = self._classify_provider_error(error)
            self._mark_failed(db, asset, failure_message)
            logger.warning(
                "Image provider request failed: type=%s status=%s code=%s",
                type(error).__name__,
                safe_status,
                error_code,
            )
            raise HTTPException(
                status_code=safe_status,
                detail={"code": error_code, "message": client_message},
            ) from error
    @staticmethod
    def _classify_provider_error(error: Exception) -> tuple[int, str, str, str]:
        """Map provider failures to stable codes and safe HTTP/client messages."""

        failure = classify_image_provider_error(error)
        code = failure.code
        provider_status = failure.provider_status
        status_by_code = {
            "RESOURCE_EXHAUSTED": status.HTTP_429_TOO_MANY_REQUESTS,
            "INVALID_ARGUMENT": status.HTTP_400_BAD_REQUEST,
            "PROVIDER_TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
        }
        safe_status = status_by_code.get(code, status.HTTP_502_BAD_GATEWAY)
        if code == "PROVIDER_ERROR" and provider_status == 429:
            safe_status = status.HTTP_429_TOO_MANY_REQUESTS

        internal_messages = {
            "RESOURCE_EXHAUSTED": "Image provider quota exceeded",
            "INVALID_ARGUMENT": "Image provider rejected the request",
            "MODEL_NOT_FOUND": "Image provider model was not found",
            "PERMISSION_DENIED": "Image provider permission denied",
            "UNAUTHENTICATED": "Image provider authentication failed",
            "PROVIDER_TIMEOUT": "Image provider timeout",
            "IMAGE_OUTPUT_MISSING": "Image provider returned no image",
            "PROVIDER_ERROR": "Image provider failed",
        }
        client_messages = {
            "RESOURCE_EXHAUSTED": "Image generation is temporarily limited by verified provider quota or rate limit",
            "INVALID_ARGUMENT": "Image generation request or parameters are invalid",
            "MODEL_NOT_FOUND": "The configured image model is unavailable or not recognized by the provider",
            "PERMISSION_DENIED": "The image provider denied access to this request",
            "UNAUTHENTICATED": "The image provider API key could not be authenticated",
            "PROVIDER_TIMEOUT": "Image provider timed out",
            "IMAGE_OUTPUT_MISSING": "Image provider did not return a valid image",
            "PROVIDER_ERROR": "Unable to generate image",
        }
        if code == "PROVIDER_ERROR" and provider_status == 429:
            client_messages[code] = "Image generation is temporarily limited by provider request or resource capacity"
        return safe_status, internal_messages[code], client_messages[code], code
    @staticmethod
    def _cleanup_generated_file(path: Path | None, asset: MediaAsset) -> None:
        if path is None or asset.status == "completed":
            return
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.warning("Unable to clean up failed generated image file")

    @staticmethod
    def _mark_failed(db: Session, asset: MediaAsset, message: str) -> None:
        if asset.status == "completed":
            return
        asset.status = "failed"
        asset.error_message = message
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to persist failed image asset state")
    def list_assets(
        self, *, db: Session, conversation_id: int, current_user: User
    ) -> list[MediaAsset]:
        conversation = self._conversation(db, conversation_id, current_user)
        return (
            db.query(MediaAsset)
            .filter(
                MediaAsset.conversation_id == conversation.id,
                MediaAsset.user_id == current_user.id,
            )
            .order_by(MediaAsset.created_at.asc(), MediaAsset.id.asc())
            .all()
        )

    def get_asset(
        self, *, db: Session, asset_id: int, current_user: User
    ) -> MediaAsset:
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == asset_id, MediaAsset.user_id == current_user.id)
            .first()
        )
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset không tồn tại hoặc bạn không có quyền truy cập",
            )
        return asset

    def get_asset_path(self, asset: MediaAsset) -> Path:
        if asset.status != "completed" or not asset.filepath:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset chưa có file kết quả",
            )
        try:
            return self.storage.resolve(asset.filepath)
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File media không còn tồn tại trên hệ thống lưu trữ",
            ) from error


    def delete_image_asset(
        self,
        *,
        db: Session,
        conversation_id: int,
        asset_id: int,
        current_user: User,
    ) -> None:
        """Delete an owned image asset without breaking an existing lineage."""

        self._conversation(db, conversation_id, current_user)
        asset = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == asset_id,
                MediaAsset.user_id == current_user.id,
                MediaAsset.conversation_id == conversation_id,
                MediaAsset.kind == "image",
            )
            .first()
        )
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image does not exist or is not accessible",
            )

        child_exists = (
            db.query(MediaAsset.id)
            .filter(MediaAsset.parent_asset_id == asset.id)
            .first()
            is not None
        )
        if child_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an image that is the source of another version",
            )

        stored_path = None
        if asset.filepath:
            try:
                stored_path = self.storage.resolve(asset.filepath)
            except FileNotFoundError:
                stored_path = None

        db.delete(asset)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        if stored_path and stored_path.is_file():
            try:
                stored_path.unlink()
            except OSError:
                logger.warning("Unable to remove deleted media asset file")

media_service = MediaService()
