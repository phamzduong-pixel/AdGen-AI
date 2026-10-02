from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.saved_content import SavedContentCreate
from app.schemas.saved_content import SavedContentDeleteResponse
from app.schemas.saved_content import SavedContentResponse
from app.schemas.content_activity import ContentActivityCreate
from app.schemas.content_activity import ContentActivityResponse
from app.services.saved_content_service import delete_saved_content_service
from app.services.saved_content_service import list_saved_contents_service
from app.services.saved_content_service import save_content_service
from app.services.saved_content_service import unsave_message_service
from app.services.content_activity_service import record_saved_content_activity_service


router = APIRouter(
    prefix="/saved-contents",
    tags=["Saved Content"],
)


@router.post(
    "/{saved_content_id}/activities",
    response_model=ContentActivityResponse,
)
def record_activity(
    saved_content_id: int,
    data: ContentActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return record_saved_content_activity_service(
        saved_content_id=saved_content_id,
        action_type=data.action_type,
        db=db,
        current_user=current_user,
    )


@router.get("", response_model=list[SavedContentResponse])
def list_saved_contents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_saved_contents_service(db=db, current_user=current_user)


@router.post("", response_model=SavedContentResponse)
def save_content(
    data: SavedContentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return save_content_service(data=data, db=db, current_user=current_user)


@router.delete(
    "/message/{message_id}",
    response_model=SavedContentDeleteResponse,
)
def unsave_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return unsave_message_service(
        message_id=message_id,
        db=db,
        current_user=current_user,
    )


@router.delete(
    "/{saved_content_id}",
    response_model=SavedContentDeleteResponse,
)
def delete_saved_content(
    saved_content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_saved_content_service(
        saved_content_id=saved_content_id,
        db=db,
        current_user=current_user,
    )
