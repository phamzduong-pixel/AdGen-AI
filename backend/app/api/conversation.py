from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.user import User

from app.core.security import get_current_user

from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    ConversationPinUpdate,
    ConversationDeleteResponse,
    ConversationBrandUpdate,
)

from app.services.conversation_service import (
    create_conversation,
    get_all_conversations,
    get_conversation,
    update_conversation,
    delete_conversation,
    toggle_pin_conversation,
    update_conversation_brand,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversation"],
)


@router.post(
    "",
    response_model=ConversationResponse,
)
def create(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_conversation(
        db=db,
        user_id=current_user.id,
        title=conversation.title,
        brand_id=conversation.brand_id,
    )


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def read_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_all_conversations(
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def read_one(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )


@router.put(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update(
    conversation_id: int,
    conversation: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        title=conversation.title,
    )


@router.delete(
    "/{conversation_id}",
    response_model=ConversationDeleteResponse,
)
def delete(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )


@router.patch(
    "/{conversation_id}/pin",
    response_model=ConversationResponse,
)
def toggle_pin(
    conversation_id: int,
    pin_data: ConversationPinUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return toggle_pin_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        is_pinned=pin_data.is_pinned,
    )


@router.patch(
    "/{conversation_id}/brand",
    response_model=ConversationResponse,
)
def set_brand(
    conversation_id: int,
    data: ConversationBrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_conversation_brand(
        db,
        conversation_id,
        current_user.id,
        data.brand_id,
    )
