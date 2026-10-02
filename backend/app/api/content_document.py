from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.content_document import (
    ContentDeleteResponse,
    ContentDocumentCreate,
    ContentDocumentResponse,
    ContentDocumentUpdate,
    ContentRestoreResponse,
    ContentRewriteRequest,
    ContentRewriteResponse,
    ContentVersionCreate,
    ContentVersionCreateResponse,
    ContentVersionResponse,
)
from app.services.content_document_service import (
    campaign_documents,
    create_document,
    create_version,
    delete_document,
    get_owned_document,
    get_owned_version,
    list_versions,
    restore_version,
    rewrite_document,
    serialize_document,
    update_document,
)


router = APIRouter(prefix="/contents", tags=["Content Editor"])


@router.post("", response_model=ContentDocumentResponse, status_code=201)
def create(
    data: ContentDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_document(data, db, current_user)


@router.get("/{content_id}", response_model=ContentDocumentResponse)
def get_one(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return serialize_document(get_owned_document(content_id, db, current_user))


@router.patch("/{content_id}", response_model=ContentDocumentResponse)
def update(
    content_id: int,
    data: ContentDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_document(content_id, data, db, current_user)


@router.delete("/{content_id}", response_model=ContentDeleteResponse)
def delete(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_document(content_id, db, current_user)


@router.get(
    "/{content_id}/versions",
    response_model=list[ContentVersionResponse],
)
def versions(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_versions(content_id, db, current_user)


@router.post(
    "/{content_id}/versions",
    response_model=ContentVersionCreateResponse,
)
def save_version(
    content_id: int,
    data: ContentVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_version(content_id, data, db, current_user)


@router.get(
    "/{content_id}/versions/{version_id}",
    response_model=ContentVersionResponse,
)
def get_version(
    content_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_owned_version(content_id, version_id, db, current_user)


@router.post(
    "/{content_id}/versions/{version_id}/restore",
    response_model=ContentRestoreResponse,
)
def restore(
    content_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return restore_version(content_id, version_id, db, current_user)


@router.post(
    "/{content_id}/ai-rewrite",
    response_model=ContentRewriteResponse,
)
def ai_rewrite(
    content_id: int,
    data: ContentRewriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rewrite_document(content_id, data, db, current_user)


@router.get(
    "/{content_id}/campaign-contents",
    response_model=list[ContentDocumentResponse],
)
def list_campaign_documents(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return campaign_documents(content_id, db, current_user)
