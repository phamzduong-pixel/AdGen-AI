from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.message import MessageCreate
from app.schemas.message import MessageUpdate
from app.services.message_service import create_message_service
from app.services.message_service import edit_message_stream_service
from app.services.message_service import get_messages_service
from app.services.message_service import stream_message_service
from app.services.message_service import update_message_service
from app.services.message_service import clear_conversation_messages_service


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


@router.delete("/conversation/{conversation_id}")
def clear_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return clear_conversation_messages_service(
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )


@router.post("")
def create_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gửi tin nhắn và nhận phản hồi AI hoàn chỉnh.
    """

    return create_message_service(
        message=message,
        db=db,
        current_user=current_user,
    )


@router.get("/{conversation_id}")
def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lấy toàn bộ tin nhắn của một cuộc trò chuyện.
    """

    return get_messages_service(
        conversation_id=conversation_id,
        db=db,
        current_user=current_user,
    )


@router.put("/{message_id}")
def update_message(
    message_id: int,
    message: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chỉnh sửa nội dung tin nhắn người dùng.
    Endpoint này chỉ cập nhật dữ liệu, chưa tạo lại phản hồi AI.
    """

    return update_message_service(
        message_id=message_id,
        message_data=message,
        db=db,
        current_user=current_user,
    )


@router.post("/stream")
def stream_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gửi tin nhắn và stream phản hồi AI.
    """

    generator = stream_message_service(
        message=message,
        db=db,
        current_user=current_user,
    )

    return StreamingResponse(
        generator,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.put("/{message_id}/stream")
def edit_message_stream(
    message_id: int,
    message: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Chỉnh sửa tin nhắn, xóa các tin nhắn phía sau
    và stream lại phản hồi AI.
    """

    generator = edit_message_stream_service(
        message_id=message_id,
        message_data=message,
        db=db,
        current_user=current_user,
    )

    return StreamingResponse(
        generator,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
