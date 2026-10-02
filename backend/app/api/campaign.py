from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.campaign import CampaignContentAdd
from app.schemas.campaign import CampaignCreate
from app.schemas.campaign import CampaignDeleteResponse
from app.schemas.campaign import CampaignDetailResponse
from app.schemas.campaign import CampaignListResponse
from app.schemas.campaign import CampaignStatus
from app.schemas.campaign import CampaignUpdate
from app.services.campaign_service import add_campaign_content_service
from app.services.campaign_service import create_campaign_service
from app.services.campaign_service import delete_campaign_service
from app.services.campaign_service import get_campaign_detail_service
from app.services.campaign_service import list_campaigns_service
from app.services.campaign_service import remove_campaign_content_service
from app.services.campaign_service import set_primary_content_service
from app.services.campaign_service import update_campaign_service


router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("", response_model=CampaignListResponse, status_code=201)
def create_campaign(
    data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_campaign_service(data, db, current_user)


@router.get("", response_model=list[CampaignListResponse])
def list_campaigns(
    query: str | None = Query(default=None, max_length=160),
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
    platform: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_campaigns_service(
        db=db,
        current_user=current_user,
        query=query,
        campaign_status=status_filter,
        platform=platform,
    )


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_campaign_detail_service(campaign_id, db, current_user)


@router.patch("/{campaign_id}", response_model=CampaignListResponse)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_campaign_service(campaign_id, data, db, current_user)


@router.delete("/{campaign_id}", response_model=CampaignDeleteResponse)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_campaign_service(campaign_id, db, current_user)


@router.post(
    "/{campaign_id}/contents",
    response_model=CampaignDetailResponse,
)
def add_campaign_content(
    campaign_id: int,
    data: CampaignContentAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return add_campaign_content_service(
        campaign_id,
        data.saved_content_id,
        db,
        current_user,
    )


@router.delete(
    "/{campaign_id}/contents/{saved_content_id}",
    response_model=CampaignDetailResponse,
)
def remove_campaign_content(
    campaign_id: int,
    saved_content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return remove_campaign_content_service(
        campaign_id,
        saved_content_id,
        db,
        current_user,
    )


@router.patch(
    "/{campaign_id}/contents/{saved_content_id}/primary",
    response_model=CampaignDetailResponse,
)
def set_primary_content(
    campaign_id: int,
    saved_content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return set_primary_content_service(
        campaign_id,
        saved_content_id,
        db,
        current_user,
    )
