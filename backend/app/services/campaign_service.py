from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.campaign import Campaign
from app.models.campaign import CampaignContent
from app.models.saved_content import SavedContent
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.trend_report import TrendReport
from app.schemas.campaign import CampaignCreate
from app.schemas.campaign import CampaignDetailResponse
from app.schemas.campaign import CampaignListResponse
from app.schemas.campaign import CampaignUpdate
from app.schemas.campaign import CampaignContentResponse
from app.schemas.saved_content import SavedContentResponse
from app.services.content_activity_service import get_content_statistics
from app.services.content_activity_service import get_owned_saved_content


def get_owned_campaign(
    campaign_id: int,
    db: Session,
    current_user: User,
) -> Campaign:
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
        .first()
    )
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chiến dịch không tồn tại hoặc bạn không có quyền truy cập",
        )
    return campaign


def _campaign_base(campaign: Campaign, contents_count: int) -> dict:
    return {
        "id": campaign.id,
        "user_id": campaign.user_id,
        "name": campaign.name,
        "description": campaign.description,
        "notes": campaign.notes,
        "product_name": campaign.product_name,
        "target_audience": campaign.target_audience,
        "objective": campaign.objective,
        "platform": campaign.platform,
        "platform_name": campaign.platform_name,
        "status": campaign.status,
        "brand_id": campaign.brand_id,
        "trend_report_id": campaign.trend_report_id,
        "advertising_brief_id": campaign.advertising_brief_id,
        "brand_name": campaign.brand.name if campaign.brand else None,
        "contents_count": contents_count,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }


def create_campaign_service(
    data: CampaignCreate,
    db: Session,
    current_user: User,
) -> CampaignListResponse:
    values = data.model_dump()
    brand_id = values.get("brand_id")
    if brand_id is not None and not db.query(BrandProfile).filter(
        BrandProfile.id == brand_id,
        BrandProfile.user_id == current_user.id,
    ).first():
        raise HTTPException(status_code=404, detail="Thương hiệu không tồn tại.")
    trend_report_id = values.get("trend_report_id")
    if trend_report_id is not None and not db.query(TrendReport).filter(
        TrendReport.id == trend_report_id,
        TrendReport.user_id == current_user.id,
    ).first():
        raise HTTPException(status_code=404, detail="Trend Report không tồn tại.")
    campaign = Campaign(user_id=current_user.id, **values)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return CampaignListResponse(**_campaign_base(campaign, 0))


def list_campaigns_service(
    *,
    db: Session,
    current_user: User,
    query: str | None = None,
    campaign_status: str | None = None,
    platform: str | None = None,
) -> list[CampaignListResponse]:
    contents_count = (
        db.query(
            CampaignContent.campaign_id,
            func.count(CampaignContent.id).label("contents_count"),
        )
        .group_by(CampaignContent.campaign_id)
        .subquery()
    )
    campaigns_query = (
        db.query(Campaign, func.coalesce(contents_count.c.contents_count, 0))
        .outerjoin(contents_count, contents_count.c.campaign_id == Campaign.id)
        .filter(Campaign.user_id == current_user.id)
    )
    if query:
        campaigns_query = campaigns_query.filter(
            Campaign.name.ilike(f"%{query.strip()}%")
        )
    if campaign_status:
        campaigns_query = campaigns_query.filter(Campaign.status == campaign_status)
    if platform:
        campaigns_query = campaigns_query.filter(Campaign.platform == platform)

    rows = campaigns_query.order_by(Campaign.updated_at.desc()).all()
    return [
        CampaignListResponse(**_campaign_base(campaign, int(count)))
        for campaign, count in rows
    ]


def get_campaign_detail_service(
    campaign_id: int,
    db: Session,
    current_user: User,
) -> CampaignDetailResponse:
    campaign = (
        db.query(Campaign)
        .options(joinedload(Campaign.content_links).joinedload(CampaignContent.saved_content))
        .filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
        .first()
    )
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chiến dịch không tồn tại hoặc bạn không có quyền truy cập",
        )
    links = sorted(campaign.content_links, key=lambda item: item.added_at, reverse=True)
    contents = [
        CampaignContentResponse(
            id=link.id,
            is_primary=link.is_primary,
            added_at=link.added_at,
            saved_content=SavedContentResponse.model_validate(link.saved_content),
            statistics=get_content_statistics(db, link.saved_content_id),
        )
        for link in links
    ]
    return CampaignDetailResponse(
        **_campaign_base(campaign, len(contents)),
        contents=contents,
    )


def update_campaign_service(
    campaign_id: int,
    data: CampaignUpdate,
    db: Session,
    current_user: User,
) -> CampaignListResponse:
    campaign = get_owned_campaign(campaign_id, db, current_user)
    values = data.model_dump(exclude_unset=True)
    if "brand_id" in values and values["brand_id"] is not None:
        if not db.query(BrandProfile).filter(
            BrandProfile.id == values["brand_id"],
            BrandProfile.user_id == current_user.id,
        ).first():
            raise HTTPException(status_code=404, detail="Thương hiệu không tồn tại.")
    for field, value in values.items():
        setattr(campaign, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(campaign)
    count = (
        db.query(func.count(CampaignContent.id))
        .filter(CampaignContent.campaign_id == campaign.id)
        .scalar()
    )
    return CampaignListResponse(**_campaign_base(campaign, int(count or 0)))


def delete_campaign_service(
    campaign_id: int,
    db: Session,
    current_user: User,
) -> dict:
    campaign = get_owned_campaign(campaign_id, db, current_user)
    db.delete(campaign)
    db.commit()
    return {"message": "Đã xóa chiến dịch", "campaign_id": campaign_id}


def add_campaign_content_service(
    campaign_id: int,
    saved_content_id: int,
    db: Session,
    current_user: User,
) -> CampaignDetailResponse:
    campaign = get_owned_campaign(campaign_id, db, current_user)
    saved_content = get_owned_saved_content(saved_content_id, db, current_user)
    existing = (
        db.query(CampaignContent)
        .filter(
            CampaignContent.campaign_id == campaign.id,
            CampaignContent.saved_content_id == saved_content.id,
        )
        .first()
    )
    if existing is None:
        db.add(
            CampaignContent(
                campaign_id=campaign.id,
                saved_content_id=saved_content.id,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return get_campaign_detail_service(campaign_id, db, current_user)


def remove_campaign_content_service(
    campaign_id: int,
    saved_content_id: int,
    db: Session,
    current_user: User,
) -> CampaignDetailResponse:
    campaign = get_owned_campaign(campaign_id, db, current_user)
    link = (
        db.query(CampaignContent)
        .join(SavedContent, CampaignContent.saved_content_id == SavedContent.id)
        .filter(
            CampaignContent.campaign_id == campaign.id,
            CampaignContent.saved_content_id == saved_content_id,
            SavedContent.user_id == current_user.id,
        )
        .first()
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nội dung không tồn tại trong chiến dịch",
        )
    db.delete(link)
    db.commit()
    return get_campaign_detail_service(campaign_id, db, current_user)


def set_primary_content_service(
    campaign_id: int,
    saved_content_id: int,
    db: Session,
    current_user: User,
) -> CampaignDetailResponse:
    campaign = get_owned_campaign(campaign_id, db, current_user)
    target = (
        db.query(CampaignContent)
        .filter(
            CampaignContent.campaign_id == campaign.id,
            CampaignContent.saved_content_id == saved_content_id,
        )
        .first()
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nội dung không tồn tại trong chiến dịch",
        )
    (
        db.query(CampaignContent)
        .filter(CampaignContent.campaign_id == campaign.id)
        .update({CampaignContent.is_primary: False}, synchronize_session=False)
    )
    target.is_primary = True
    db.commit()
    return get_campaign_detail_service(campaign_id, db, current_user)
