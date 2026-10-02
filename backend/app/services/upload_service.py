from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.core.config import settings
from app.services.file_storage import LocalFileStorage
from app.services.file_storage import StorageSizeLimitError


UPLOAD_DIRECTORY = settings.UPLOAD_DIR
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
CHUNK_SIZE = 1024 * 1024
file_storage = LocalFileStorage(UPLOAD_DIRECTORY)
ALLOWED_EXTENSIONS = {
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
}
ALLOWED_MIME_TYPES = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
    ".mp4": {"video/mp4", "application/octet-stream"},
    ".mov": {"video/quicktime", "video/mp4", "application/octet-stream"},
    ".webm": {"video/webm", "application/octet-stream"},
}


def determine_file_type(content_type: str | None, filename: str | None) -> str:
    """Xác định loại tệp: video, image, pdf, hoặc document."""
    ext = Path(filename or "").suffix.lower()
    ct = (content_type or "").lower()
    if ct.startswith("video/") or ext in {".mp4", ".mov", ".webm"}:
        return "video"
    if ct.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"
    if ct == "application/pdf" or ext == ".pdf":
        return "pdf"
    return "document"


def _get_user_conversation(
    db: Session,
    conversation_id: int,
    current_user: User,
) -> Conversation:
    """Return a conversation only when it belongs to the current user."""

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Cuộc trò chuyện không tồn tại "
                "hoặc bạn không có quyền truy cập"
            ),
        )

    return conversation


def _validate_filename(filename: str | None) -> tuple[str, str]:
    """Validate a client filename and return its safe name and extension."""

    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên tệp không hợp lệ",
        )

    # Path.name handles Unix separators; replacing backslashes also handles
    # filenames sent by Windows clients on every operating system.
    safe_name = Path(filename.replace("\\", "/")).name.strip()
    extension = Path(safe_name).suffix.lower()

    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên tệp không hợp lệ",
        )

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tệp '{extension or 'không xác định'}' không được hỗ trợ",
        )

    stem = Path(safe_name).stem
    clean_stem = "".join(
        character
        for character in stem
        if character.isalnum() or character in {" ", "_", "-", "."}
    ).strip(" .")
    if not clean_stem:
        clean_stem = "upload"
    safe_name = f"{clean_stem[:180]}{extension}"

    return safe_name, extension


async def upload_file_service(
    file: UploadFile,
    conversation_id: int,
    db: Session,
    current_user: User,
) -> UploadedFile:
    """Validate, store and persist one uploaded file."""

    conversation = _get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user,
    )
    original_name, extension = _validate_filename(file.filename)
    content_type = (file.content_type or "application/octet-stream").lower()

    if content_type not in ALLOWED_MIME_TYPES[extension]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loại MIME của tệp không khớp với định dạng được hỗ trợ",
        )

    is_video = extension in {".mp4", ".mov", ".webm"} or content_type.startswith("video/")
    effective_max_size = 50 * 1024 * 1024 if is_video else MAX_FILE_SIZE

    stored = None
    try:
        stored = await file_storage.save(
            upload=file,
            extension=extension,
            max_size=effective_max_size,
            chunk_size=CHUNK_SIZE,
        )

        uploaded_file = UploadedFile(
            filename=original_name,
            filepath=stored.location,
            content_type=content_type,
            size=stored.size,
            conversation_id=conversation.id,
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        return uploaded_file
    except StorageSizeLimitError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                "Tệp vượt quá kích thước tối đa "
                f"{effective_max_size / (1024 * 1024):g} MB"
            ),
        ) from error
    except HTTPException:
        db.rollback()
        if stored:
            file_storage.delete(stored.location)
        raise
    except Exception as error:
        db.rollback()
        if stored:
            file_storage.delete(stored.location)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu tệp",
        ) from error
    finally:
        await file.close()


def get_uploaded_files_service(
    conversation_id: int,
    db: Session,
    current_user: User,
) -> list[UploadedFile]:
    """List uploaded files from a conversation owned by the current user."""

    conversation = _get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user,
    )

    return (
        db.query(UploadedFile)
        .filter(UploadedFile.conversation_id == conversation.id)
        .order_by(UploadedFile.id.asc())
        .all()
    )


def get_uploaded_file_service(
    file_id: int,
    db: Session,
    current_user: User,
) -> UploadedFile:
    """Return an uploaded file only when its conversation belongs to the user."""

    uploaded_file = (
        db.query(UploadedFile)
        .join(
            Conversation,
            UploadedFile.conversation_id == Conversation.id,
        )
        .filter(
            UploadedFile.id == file_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )

    if uploaded_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp không tồn tại hoặc bạn không có quyền truy cập",
        )

    return uploaded_file


def delete_uploaded_file_service(
    file_id: int,
    db: Session,
    current_user: User,
) -> dict[str, str]:
    """Delete an uploaded file record and its local file."""

    uploaded_file = get_uploaded_file_service(
        file_id=file_id,
        db=db,
        current_user=current_user,
    )
    referenced_asset = (
        db.query(MediaAsset.id)
        .filter(MediaAsset.source_uploaded_file_id == uploaded_file.id)
        .first()
    )
    if referenced_asset:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể xóa tệp đang được media asset sử dụng",
        )
    try:
        db.delete(uploaded_file)
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể xóa tệp",
        ) from error

    # Delete from disk only after the database transaction succeeds. Restrict
    # deletion to this service's upload directory even if database data is bad.
    try:
        file_storage.delete(uploaded_file.filepath)
    except OSError:
        # The database operation is already complete. A stale local file can be
        # cleaned up later without reporting a failed deletion to the client.
        pass

    return {"message": "Xóa tệp thành công"}


def get_uploaded_file_path(uploaded_file: UploadedFile) -> Path:
    """Resolve a protected local file without allowing path traversal."""

    try:
        return file_storage.resolve(uploaded_file.filepath)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tệp không còn tồn tại trên hệ thống lưu trữ",
        ) from error
