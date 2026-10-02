from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.ad_template import CustomTemplateCreate
from app.schemas.ad_template import CustomTemplateUpdate
from app.schemas.ad_template import TemplateDeleteResponse
from app.schemas.ad_template import TemplateResponse
from app.services.template_service import create_custom_template_service
from app.services.template_service import delete_custom_template_service
from app.services.template_service import favorite_template_service
from app.services.template_service import get_template_service
from app.services.template_service import list_templates_service
from app.services.template_service import unfavorite_template_service
from app.services.template_service import update_custom_template_service


router = APIRouter(prefix="/templates", tags=["Ad Templates"])


@router.get("", response_model=list[TemplateResponse])
def list_templates(
    search: str | None = Query(default=None, max_length=100),
    platform: str | None = Query(default=None, max_length=50),
    category: str | None = Query(default=None, max_length=80),
    scope: Literal["all", "system", "custom"] = "all",
    favorites_only: bool = False,
    popular_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_templates_service(
        db=db,
        current_user=current_user,
        search=search,
        platform=platform,
        category=category,
        scope=scope,
        favorites_only=favorites_only,
        popular_only=popular_only,
    )


@router.get("/favorites", response_model=list[TemplateResponse])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_templates_service(
        db=db,
        current_user=current_user,
        favorites_only=True,
    )


@router.get("/custom", response_model=list[TemplateResponse])
def list_custom_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_templates_service(
        db=db,
        current_user=current_user,
        scope="custom",
    )


@router.post("/custom", response_model=TemplateResponse, status_code=201)
def create_custom_template(
    data: CustomTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_custom_template_service(data, db, current_user)


@router.patch("/custom/{template_id}", response_model=TemplateResponse)
def update_custom_template(
    template_id: int,
    data: CustomTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_custom_template_service(
        template_id,
        data,
        db,
        current_user,
    )


@router.delete(
    "/custom/{template_id}",
    response_model=TemplateDeleteResponse,
)
def delete_custom_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_custom_template_service(template_id, db, current_user)


@router.post("/{template_id}/favorite", response_model=TemplateResponse)
def favorite_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return favorite_template_service(template_id, db, current_user)


@router.delete("/{template_id}/favorite", response_model=TemplateResponse)
def unfavorite_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return unfavorite_template_service(template_id, db, current_user)


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_template_service(template_id, db, current_user)
