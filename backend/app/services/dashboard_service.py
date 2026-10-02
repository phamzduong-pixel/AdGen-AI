from datetime import date
from datetime import datetime
from datetime import timedelta

from app.core.datetime_utils import utc_now

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.content_activity import ContentActivity
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User
from app.schemas.dashboard import DailyActivity
from app.schemas.dashboard import DashboardActivity
from app.schemas.dashboard import DashboardPlatformUsage
from app.schemas.dashboard import DashboardSummary
from app.schemas.dashboard import PlatformUsage


def _generated_content_query(db: Session, user_id: int):
    return (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == user_id,
            Message.role == "assistant",
        )
    )


def get_dashboard_summary_service(
    db: Session,
    current_user: User,
) -> DashboardSummary:
    now = utc_now()
    total_conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == current_user.id)
        .scalar()
    )
    generated = _generated_content_query(db, current_user.id)
    total_generated = generated.with_entities(func.count(Message.id)).scalar()
    saved_count = (
        db.query(func.count(SavedContent.id))
        .filter(SavedContent.user_id == current_user.id)
        .scalar()
    )
    evaluation_count = (
        db.query(func.coalesce(func.sum(ContentActivity.quantity), 0))
        .filter(
            ContentActivity.user_id == current_user.id,
            ContentActivity.action_type == "evaluation",
        )
        .scalar()
    )
    variant_count = (
        db.query(func.coalesce(func.sum(ContentActivity.quantity), 0))
        .filter(
            ContentActivity.user_id == current_user.id,
            ContentActivity.action_type == "variants_generated",
        )
        .scalar()
    )
    top_platform_row = (
        db.query(Message.prompt_type, func.count(Message.id).label("total"))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == current_user.id,
            Message.role == "user",
            Message.prompt_type.is_not(None),
        )
        .group_by(Message.prompt_type)
        .order_by(func.count(Message.id).desc())
        .first()
    )
    last_7 = generated.filter(
        Message.created_at >= now - timedelta(days=7)
    ).with_entities(func.count(Message.id)).scalar()
    last_30 = generated.filter(
        Message.created_at >= now - timedelta(days=30)
    ).with_entities(func.count(Message.id)).scalar()
    return DashboardSummary(
        total_conversations=int(total_conversations or 0),
        total_generated_contents=int(total_generated or 0),
        total_saved_contents=int(saved_count or 0),
        total_evaluations=int(evaluation_count or 0),
        total_variants=int(variant_count or 0),
        top_platform=top_platform_row[0] if top_platform_row else None,
        contents_last_7_days=int(last_7 or 0),
        contents_last_30_days=int(last_30 or 0),
    )


def get_dashboard_activity_service(
    db: Session,
    current_user: User,
) -> DashboardActivity:
    start_date = date.today() - timedelta(days=29)
    rows = (
        _generated_content_query(db, current_user.id)
        .with_entities(
            func.date(Message.created_at).label("activity_date"),
            func.count(Message.id),
        )
        .filter(Message.created_at >= datetime.combine(start_date, datetime.min.time()))
        .group_by(func.date(Message.created_at))
        .all()
    )
    values = {str(day): int(count) for day, count in rows}
    return DashboardActivity(
        days=[
            DailyActivity(
                date=start_date + timedelta(days=offset),
                count=values.get(str(start_date + timedelta(days=offset)), 0),
            )
            for offset in range(30)
        ]
    )


def get_platform_usage_service(
    db: Session,
    current_user: User,
) -> DashboardPlatformUsage:
    usage_rows = (
        db.query(Message.prompt_type, func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == current_user.id,
            Message.role == "user",
            Message.prompt_type.is_not(None),
        )
        .group_by(Message.prompt_type)
        .all()
    )
    score_rows = (
        db.query(ContentActivity.platform, func.avg(ContentActivity.score))
        .filter(
            ContentActivity.user_id == current_user.id,
            ContentActivity.action_type == "evaluation",
            ContentActivity.platform.is_not(None),
            ContentActivity.score.is_not(None),
        )
        .group_by(ContentActivity.platform)
        .all()
    )
    averages = {platform: round(float(score), 1) for platform, score in score_rows}
    total = sum(int(count) for _, count in usage_rows)
    return DashboardPlatformUsage(
        platforms=[
            PlatformUsage(
                platform=platform,
                count=int(count),
                percentage=round((int(count) / total * 100), 1) if total else 0,
                average_score=averages.get(platform),
            )
            for platform, count in sorted(
                usage_rows,
                key=lambda item: item[1],
                reverse=True,
            )
        ]
    )
