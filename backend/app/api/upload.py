from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.upload_service import (
    delete_uploaded_file_service,
    determine_file_type,
    get_uploaded_file_path,
    get_uploaded_file_service,
    get_uploaded_files_service,
    upload_file_service,
)


router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)


def _serialize_file(uploaded_file: UploadedFile) -> dict[str, int | str | None]:
    """Build a response without exposing the server's local file path."""

    return {
        "id": uploaded_file.id,
        "filename": uploaded_file.filename,
        "conversation_id": uploaded_file.conversation_id,
        "message_id": uploaded_file.message_id,
        "content_type": uploaded_file.content_type,
        "file_type": determine_file_type(uploaded_file.content_type, uploaded_file.filename),
        "size": uploaded_file.size,
        "url": f"/uploads/file/{uploaded_file.id}/download",
    }


@router.post("/{conversation_id}", status_code=201)
async def upload_file(
    conversation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload one file to a conversation owned by the current user."""

    uploaded_file = await upload_file_service(
        file=file,
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )

    return _serialize_file(uploaded_file)


@router.get("/{conversation_id}")
def get_uploaded_files(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List files uploaded to a conversation."""

    uploaded_files = get_uploaded_files_service(
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )

    return [_serialize_file(item) for item in uploaded_files]


@router.get("/file/{file_id}/download")
def download_uploaded_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a file after checking that the current user owns it."""

    uploaded_file = get_uploaded_file_service(
        file_id=file_id,
        db=db,
        current_user=current_user,
    )

    return FileResponse(
        path=get_uploaded_file_path(uploaded_file),
        filename=uploaded_file.filename,
        media_type="application/octet-stream",
    )


@router.delete("/file/{file_id}")
def delete_uploaded_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an uploaded file owned by the current user."""

    return delete_uploaded_file_service(
        file_id=file_id,
        db=db,
        current_user=current_user,
    )
