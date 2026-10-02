from datetime import datetime

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.content_activity import ContentActivity
from app.models.saved_content import SavedContent
from app.models.user import User
from app.schemas.campaign import ContentStatistics


ALLOWED_CLIENT_ACTIONS = {"copy", "export", "regenerate"}


def get_owned_saved_content(
    saved_content_id: int,
    db: Session,
    current_user: User,
) -> SavedContent:
    saved_content = (
        db.query(SavedContent)
        .filter(
            SavedContent.id == saved_content_id,
            SavedContent.user_id == current_user.id,
        )
        .first()
    )
    if saved_content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Nội dung đã lưu không tồn tại hoặc bạn không có quyền truy cập"
            ),
        )
    return saved_content


def record_content_activity(
    *,
    db: Session,
    user_id: int,
    action_type: str,
    saved_content_id: int | None = None,
    platform: str | None = None,
    score: float | None = None,
    quantity: int = 1,
    commit: bool = True,
) -> ContentActivity:
    activity = ContentActivity(
        user_id=user_id,
        saved_content_id=saved_content_id,
        action_type=action_type,
        platform=platform,
        score=score,
        quantity=max(1, quantity),
    )
    db.add(activity)
    if commit:
        db.commit()
        db.refresh(activity)
    return activity


def record_saved_content_activity_service(
    *,
    saved_content_id: int,
    action_type: str,
    db: Session,
    current_user: User,
) -> dict:
    if action_type not in ALLOWED_CLIENT_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loại hoạt động không hợp lệ",
        )
    saved_content = get_owned_saved_content(
        saved_content_id=saved_content_id,
        db=db,
        current_user=current_user,
    )
    record_content_activity(
        db=db,
        user_id=current_user.id,
        saved_content_id=saved_content.id,
        action_type=action_type,
        platform=saved_content.platform,
    )
    return {
        "message": "Đã ghi nhận hoạt động nội dung",
        "saved_content_id": saved_content.id,
        "action_type": action_type,
    }


def get_content_statistics(
    db: Session,
    saved_content_id: int,
) -> ContentStatistics:
    counts = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (ContentActivity.action_type == "copy", ContentActivity.quantity),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (ContentActivity.action_type == "export", ContentActivity.quantity),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ContentActivity.action_type.in_(
                                ("regenerate", "variants_generated")
                            ),
                            ContentActivity.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            ContentActivity.action_type == "evaluation",
                            ContentActivity.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.max(
                case(
                    (
                        ContentActivity.action_type == "evaluation",
                        ContentActivity.score,
                    )
                )
            ),
            func.max(ContentActivity.created_at),
        )
        .filter(ContentActivity.saved_content_id == saved_content_id)
        .one()
    )
    latest_evaluation = (
        db.query(ContentActivity)
        .filter(
            ContentActivity.saved_content_id == saved_content_id,
            ContentActivity.action_type == "evaluation",
            ContentActivity.score.is_not(None),
        )
        .order_by(ContentActivity.created_at.desc(), ContentActivity.id.desc())
        .first()
    )
    return ContentStatistics(
        copy_count=int(counts[0]),
        export_count=int(counts[1]),
        regenerate_count=int(counts[2]),
        evaluation_count=int(counts[3]),
        highest_score=counts[4],
        latest_score=latest_evaluation.score if latest_evaluation else None,
        last_used_at=counts[5],
    )
