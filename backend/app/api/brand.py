from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.brand import (
    BrandAssetResponse,
    BrandContentCheckRequest,
    BrandContentCheckResponse,
    BrandCreate,
    BrandDeleteResponse,
    BrandResponse,
    BrandStatisticsResponse,
    BrandUpdate,
)
from app.services.brand_service import (
    brand_asset_storage,
    brand_statistics,
    check_brand_content,
    create_brand,
    delete_brand,
    delete_brand_asset,
    get_owned_asset,
    get_owned_brand,
    list_brands,
    serialize_brand,
    set_default_brand,
    update_brand,
    upload_brand_asset,
)


router = APIRouter(prefix="/brands", tags=["Brands"])


@router.post("", response_model=BrandResponse, status_code=201)
def create(
    data: BrandCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_brand(data, db, current_user)


@router.get("", response_model=list[BrandResponse])
def list_all(
    query: str | None = Query(default=None, max_length=160),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_brands(db, current_user, query)


@router.get("/{brand_id}", response_model=BrandResponse)
def get_one(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return serialize_brand(get_owned_brand(brand_id, db, current_user))


@router.patch("/{brand_id}", response_model=BrandResponse)
def update(
    brand_id: int,
    data: BrandUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_brand(brand_id, data, db, current_user)


@router.delete("/{brand_id}", response_model=BrandDeleteResponse)
def delete(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_brand(brand_id, db, current_user)


@router.patch("/{brand_id}/default", response_model=BrandResponse)
def make_default(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return set_default_brand(brand_id, db, current_user)


@router.post(
    "/{brand_id}/check-content",
    response_model=BrandContentCheckResponse,
)
def check_content(
    brand_id: int,
    data: BrandContentCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return check_brand_content(brand_id, data, db, current_user)


@router.get(
    "/{brand_id}/statistics",
    response_model=BrandStatisticsResponse,
)
def statistics(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return brand_statistics(brand_id, db, current_user)


@router.post(
    "/{brand_id}/assets",
    response_model=BrandAssetResponse,
    status_code=201,
)
async def upload_asset(
    brand_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await upload_brand_asset(brand_id, file, db, current_user)
    return {
        "id": asset.id,
        "brand_id": asset.brand_id,
        "file_name": asset.file_name,
        "file_type": asset.file_type,
        "file_url": f"/brands/{brand_id}/assets/{asset.id}/download",
        "size": asset.size,
        "created_at": asset.created_at,
    }


@router.get("/{brand_id}/assets/{asset_id}/download")
def download_asset(
    brand_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = get_owned_asset(brand_id, asset_id, db, current_user)
    path = brand_asset_storage.resolve(asset.file_url)
    return FileResponse(path, media_type=asset.file_type, filename=asset.file_name)


@router.delete("/{brand_id}/assets/{asset_id}")
def delete_asset(
    brand_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_brand_asset(brand_id, asset_id, db, current_user)
