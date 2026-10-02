from fastapi import HTTPException
from fastapi import status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.platforms import is_current_platform
from app.core.platforms import is_legacy_platform
from app.core.platforms import normalize_custom_platform_name
from app.core.platforms import SUPPORTED_PLATFORM_TYPES
from app.data.system_templates import SYSTEM_AD_TEMPLATES
from app.models.ad_template import AdTemplate
from app.models.ad_template import TemplateFavorite
from app.models.saved_content import SavedContent
from app.models.user import User
from app.schemas.ad_template import CustomTemplateCreate
from app.schemas.ad_template import CustomTemplateUpdate
from app.schemas.ad_template import TemplateResponse


def seed_system_templates(db: Session) -> None:
    existing = {
        item.system_key: item
        for item in db.query(AdTemplate)
        .filter(AdTemplate.is_system.is_(True))
        .all()
        if item.system_key
    }
    for definition in SYSTEM_AD_TEMPLATES:
        template = existing.get(definition["system_key"])
        if template is None:
            template = AdTemplate(
                user_id=None,
                is_system=True,
                **definition,
            )
            db.add(template)
            continue
        for field, value in definition.items():
            setattr(template, field, value)
        template.user_id = None
        template.is_system = True
    db.commit()


def _accessible_template_query(db: Session, current_user: User):
    return db.query(AdTemplate).filter(
        or_(
            AdTemplate.is_system.is_(True),
            AdTemplate.user_id == current_user.id,
        )
    )


def _get_accessible_template(
    template_id: int,
    db: Session,
    current_user: User,
) -> AdTemplate:
    template = (
        _accessible_template_query(db, current_user)
        .filter(AdTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mẫu không tồn tại hoặc bạn không có quyền truy cập",
        )
    return template


def _favorite_ids(db: Session, current_user: User) -> set[int]:
    return {
        row[0]
        for row in db.query(TemplateFavorite.template_id)
        .filter(TemplateFavorite.user_id == current_user.id)
        .all()
    }


def _serialize(
    template: AdTemplate,
    favorite_ids: set[int],
    current_user: User,
) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        title=template.title,
        description=template.description,
        platform=template.platform,
        platform_name=template.platform_name,
        category=template.category,
        prompt_template=template.prompt_template,
        default_tone=template.default_tone,
        default_length=template.default_length,
        suggested_cta=template.suggested_cta,
        is_system=template.is_system,
        is_popular=template.is_popular,
        is_favorite=template.id in favorite_ids,
        is_owner=template.user_id == current_user.id,
        created_at=template.created_at,
    )


def list_templates_service(
    db: Session,
    current_user: User,
    search: str | None = None,
    platform: str | None = None,
    category: str | None = None,
    scope: str = "all",
    favorites_only: bool = False,
    popular_only: bool = False,
) -> list[TemplateResponse]:
    query = _accessible_template_query(db, current_user)
    # Legacy system templates remain stored for compatibility, but are not offered in new quick-start/template lists.
    query = query.filter(
        or_(
            AdTemplate.is_system.is_(False),
            AdTemplate.platform.in_(SUPPORTED_PLATFORM_TYPES),
        )
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AdTemplate.title.ilike(term),
                AdTemplate.description.ilike(term),
            )
        )
    if platform:
        query = query.filter(AdTemplate.platform == platform)
    if category:
        query = query.filter(AdTemplate.category == category)
    if scope == "system":
        query = query.filter(AdTemplate.is_system.is_(True))
    elif scope == "custom":
        query = query.filter(
            AdTemplate.is_system.is_(False),
            AdTemplate.user_id == current_user.id,
        )
    if popular_only:
        query = query.filter(AdTemplate.is_popular.is_(True))

    favorite_ids = _favorite_ids(db, current_user)
    templates = query.order_by(
        AdTemplate.is_popular.desc(),
        AdTemplate.created_at.desc(),
        AdTemplate.id.desc(),
    ).all()
    if favorites_only:
        templates = [item for item in templates if item.id in favorite_ids]
    return [_serialize(item, favorite_ids, current_user) for item in templates]


def get_template_service(
    template_id: int,
    db: Session,
    current_user: User,
) -> TemplateResponse:
    template = _get_accessible_template(template_id, db, current_user)
    return _serialize(template, _favorite_ids(db, current_user), current_user)


def favorite_template_service(
    template_id: int,
    db: Session,
    current_user: User,
) -> TemplateResponse:
    template = _get_accessible_template(template_id, db, current_user)
    existing = (
        db.query(TemplateFavorite)
        .filter(
            TemplateFavorite.user_id == current_user.id,
            TemplateFavorite.template_id == template.id,
        )
        .first()
    )
    if existing is None:
        db.add(
            TemplateFavorite(
                user_id=current_user.id,
                template_id=template.id,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return _serialize(template, _favorite_ids(db, current_user), current_user)


def unfavorite_template_service(
    template_id: int,
    db: Session,
    current_user: User,
) -> TemplateResponse:
    template = _get_accessible_template(template_id, db, current_user)
    favorite = (
        db.query(TemplateFavorite)
        .filter(
            TemplateFavorite.user_id == current_user.id,
            TemplateFavorite.template_id == template.id,
        )
        .first()
    )
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return _serialize(template, _favorite_ids(db, current_user), current_user)


def create_custom_template_service(
    data: CustomTemplateCreate,
    db: Session,
    current_user: User,
) -> TemplateResponse:
    values = data.model_dump(
        exclude={"source_template_id", "source_saved_content_id"},
    )
    source_template = None
    if data.source_template_id:
        source_template = _get_accessible_template(
            data.source_template_id,
            db,
            current_user,
        )
    if source_template:
        source_values = {
            field: getattr(source_template, field)
            for field in (
                "description",
                "platform",
                "platform_name",
                "category",
                "prompt_template",
                "default_tone",
                "default_length",
                "suggested_cta",
            )
        }
        explicit_values = data.model_dump(
            exclude={
                "source_template_id",
                "source_saved_content_id",
            },
            exclude_unset=True,
        )
        source_values.update(
            {
                field: value
                for field, value in explicit_values.items()
                if value not in {None, ""}
            }
        )
        values = source_values
    elif data.source_saved_content_id:
        saved_content = (
            db.query(SavedContent)
            .filter(
                SavedContent.id == data.source_saved_content_id,
                SavedContent.user_id == current_user.id,
            )
            .first()
        )
        if saved_content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nội dung đã lưu không tồn tại hoặc không thuộc về bạn",
            )
        values["prompt_template"] = saved_content.content
        if saved_content.platform:
            values["platform"] = saved_content.platform
        if saved_content.platform_name:
            values["platform_name"] = saved_content.platform_name

    platform = (values.get("platform") or "facebook").strip().lower()
    if not is_current_platform(platform) and not (
        (data.source_template_id or data.source_saved_content_id)
        and is_legacy_platform(platform)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nền tảng mẫu không được hỗ trợ cho lựa chọn mới.",
        )
    platform_name = normalize_custom_platform_name(values.get("platform_name"))
    if platform == "other" and not platform_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung.",
        )
    values["platform"] = platform
    values["platform_name"] = platform_name
    prompt_template = (values.get("prompt_template") or "").strip()
    if not prompt_template:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nội dung mẫu không được để trống",
        )
    values["prompt_template"] = prompt_template
    template = AdTemplate(
        user_id=current_user.id,
        is_system=False,
        is_popular=False,
        **values,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize(template, _favorite_ids(db, current_user), current_user)


def update_custom_template_service(
    template_id: int,
    data: CustomTemplateUpdate,
    db: Session,
    current_user: User,
) -> TemplateResponse:
    template = (
        db.query(AdTemplate)
        .filter(
            AdTemplate.id == template_id,
            AdTemplate.user_id == current_user.id,
            AdTemplate.is_system.is_(False),
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mẫu cá nhân không tồn tại hoặc bạn không có quyền chỉnh sửa",
        )
    values = data.model_dump(exclude_unset=True)
    if "platform" in values or "platform_name" in values:
        platform = (values.get("platform", template.platform) or "").strip().lower()
        if not is_current_platform(platform):
            raise HTTPException(status_code=422, detail="Nền tảng mẫu không được hỗ trợ cho lựa chọn mới.")
        platform_name = normalize_custom_platform_name(
            values.get("platform_name", template.platform_name)
        )
        if platform == "other" and not platform_name:
            raise HTTPException(status_code=422, detail="Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung.")
        values["platform"] = platform
        values["platform_name"] = platform_name
    for field, value in values.items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return _serialize(template, _favorite_ids(db, current_user), current_user)


def delete_custom_template_service(
    template_id: int,
    db: Session,
    current_user: User,
) -> dict:
    template = (
        db.query(AdTemplate)
        .filter(
            AdTemplate.id == template_id,
            AdTemplate.user_id == current_user.id,
            AdTemplate.is_system.is_(False),
        )
        .first()
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mẫu cá nhân không tồn tại hoặc bạn không có quyền xóa",
        )
    db.delete(template)
    db.commit()
    return {"message": "Đã xóa mẫu cá nhân", "id": template_id}
