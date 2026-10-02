from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import FileResponse
import uuid
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.models.media_asset import MediaAsset
from app.models.user import User
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.media import (
    ConversationalEditExecuteRequest,
    ConversationalEditExecutionResponse,
    ConversationalEditPlanRequest,
    ConversationalEditPlanResponse,
    ImageGenerateRequest,
    MediaAssetResponse,
    MediaJobResponse,
    VideoEditRequest,
    VideoGenerationRequest,
    VideoSourceRequest,
)
from app.services.media.media_service import media_service
from app.services.media.video_service import video_service
from app.services.media.video_edit_plan_service import ConversationalEditExecutionError, video_edit_plan_service
from app.services.media.video_generation_service import video_generation_service


router = APIRouter(prefix="/media", tags=["Media"])


def _serialize_asset(asset: MediaAsset) -> MediaAssetResponse:
    return MediaAssetResponse(
        id=asset.id,
        conversation_id=asset.conversation_id,
        parent_asset_id=asset.parent_asset_id,
        source_uploaded_file_id=asset.source_uploaded_file_id,
        version_number=asset.version_number,
        kind=asset.kind,
        operation=asset.operation,
        status=asset.status,
        prompt=asset.prompt,
        aspect_ratio=asset.aspect_ratio,
        provider=asset.provider,
        model=asset.model,
        filename=asset.filename,
        content_type=asset.content_type,
        size=asset.size,
        error_message=asset.error_message,
        operation_params=asset.operation_params,
        duration_seconds=asset.duration_seconds,
        width=asset.width,
        height=asset.height,
        created_at=asset.created_at,
        url=f"/media/assets/{asset.id}/download",
        download_url=f"/media/assets/{asset.id}/download?download=true",
    )



def _serialize_execution_record(db: Session, request_record, source_asset_id: int) -> ConversationalEditExecutionResponse:
    assets = video_edit_plan_service.request_assets(db, request_record)
    output_asset = assets[-1] if assets else None
    return ConversationalEditExecutionResponse(
        status=request_record.status,
        source_asset_id=source_asset_id,
        output_asset=_serialize_asset(output_asset) if output_asset else None,
        created_assets=[_serialize_asset(asset) for asset in assets],
        failed_operation_index=request_record.failed_operation_index,
        failed_operation=request_record.failed_operation,
        error=request_record.error_message,
    )
@router.post(
    "/conversations/{conversation_id}/images",
    response_model=MediaAssetResponse,
    status_code=201,
)
async def generate_image(
    conversation_id: int,
    request: ImageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = await media_service.generate_image(
        db=db,
        conversation_id=conversation_id,
        request=request,
        current_user=current_user,
    )
    return _serialize_asset(asset)


@router.post(
    "/conversations/{conversation_id}/videos/from-upload",
    response_model=MediaAssetResponse,
    status_code=201,
)
def register_video_upload(
    conversation_id: int,
    request: VideoSourceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _serialize_asset(video_service.register_uploaded_video(
        db=db, conversation_id=conversation_id, source_file_id=request.source_file_id,
        current_user=current_user,
    ))


@router.post(
    "/conversations/{conversation_id}/videos/{source_asset_id}/edits",
    response_model=MediaAssetResponse,
    status_code=201,
)
def edit_video(
    conversation_id: int,
    source_asset_id: int,
    request: VideoEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.operation == "trim":
        asset = video_service.trim(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    elif request.operation == "merge":
        asset = video_service.merge(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    elif request.operation in {"volume", "mute"}:
        asset = video_service.audio(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    elif request.operation == "subtitle":
        asset = video_service.subtitles(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    elif request.operation == "aspect_crop":
        asset = video_service.aspect_crop(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    else:
        asset = video_service.text_overlay(
            db=db, conversation_id=conversation_id, source_asset_id=source_asset_id,
            operation=request, current_user=current_user,
        )
    return _serialize_asset(asset)


@router.post(
    "/conversations/{conversation_id}/videos/{source_asset_id}/conversational-edit-plan",
    response_model=ConversationalEditPlanResponse,
)
def create_conversational_edit_plan(
    conversation_id: int,
    source_asset_id: int,
    request: ConversationalEditPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = video_edit_plan_service._get_source(db, conversation_id, source_asset_id, current_user)
    try:
        plan = video_edit_plan_service.parse_instruction(
            source_asset_id=source_asset_id,
            request=request,
            duration=source.duration_seconds or 0,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="The conversational edit plan is invalid") from error
    video_edit_plan_service.validate_plan(
        db=db,
        conversation_id=conversation_id,
        plan=plan,
        current_user=current_user,
    )
    return ConversationalEditPlanResponse(
        source_asset_id=source_asset_id,
        instruction=request.instruction,
        operations=plan.operations,
        summary=[operation.operation for operation in plan.operations],
    )


@router.post(
    "/conversations/{conversation_id}/videos/{source_asset_id}/conversational-edits",
    response_model=ConversationalEditExecutionResponse,
    status_code=201,
)
def execute_conversational_edit_plan(
    conversation_id: int,
    source_asset_id: int,
    request: ConversationalEditExecuteRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not request.confirm:
        raise HTTPException(status_code=400, detail="The edit plan must be confirmed before execution")
    if request.plan.source_asset_id != source_asset_id:
        raise HTTPException(status_code=422, detail="Plan source asset does not match the route")

    request_key = (idempotency_key or uuid.uuid4().hex).strip()
    if not request_key or len(request_key) > 200:
        raise HTTPException(status_code=422, detail="Idempotency key is invalid")
    response.headers["Idempotency-Key"] = request_key

    request_record, is_new = video_edit_plan_service.register_execution_request(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation_id,
        source_asset_id=source_asset_id,
        plan=request.plan,
        idempotency_key=request_key,
    )
    if not is_new:
        response.status_code = 202 if request_record.status == "processing" else 200
        return _serialize_execution_record(db, request_record, source_asset_id)

    try:
        created_assets = video_edit_plan_service.execute_plan(
            db=db,
            conversation_id=conversation_id,
            plan=request.plan,
            current_user=current_user,
        )
    except ConversationalEditExecutionError as error:
        partial = bool(error.created_assets)
        safe_message = (
            f"Operation '{error.failed_operation}' th\u1ea5t b\u1ea1i. "
            "C\u00e1c version \u0111\u00e3 t\u1ea1o tr\u01b0\u1edbc \u0111\u00f3 v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef l\u1ea1i."
            if partial
            else "Kh\u00f4ng th\u1ec3 th\u1ef1c thi k\u1ebf ho\u1ea1ch. Asset g\u1ed1c v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef nguy\u00ean."
        )
        request_record = video_edit_plan_service.persist_request_result(
            db=db,
            request=request_record,
            status_value="partial" if partial else "failed",
            created_assets=error.created_assets,
            failed_operation_index=error.failed_operation_index,
            failed_operation=error.failed_operation,
            error_message=safe_message,
        )
        response.status_code = 200
        return _serialize_execution_record(db, request_record, source_asset_id)
    except HTTPException:
        video_edit_plan_service.mark_request_failed(db=db, request=request_record)
        raise
    except Exception as error:
        video_edit_plan_service.mark_request_failed(db=db, request=request_record)
        raise HTTPException(status_code=502, detail="Kh\u00f4ng th\u1ec3 th\u1ef1c thi k\u1ebf ho\u1ea1ch an to\u00e0n") from error

    request_record = video_edit_plan_service.persist_request_result(
        db=db,
        request=request_record,
        status_value="completed",
        created_assets=created_assets,
    )
    response.status_code = 201
    return _serialize_execution_record(db, request_record, source_asset_id)

@router.get(
    "/conversations/{conversation_id}/assets",
    response_model=list[MediaAssetResponse],
)
def list_media_assets(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        _serialize_asset(asset)
        for asset in media_service.list_assets(
            db=db, conversation_id=conversation_id, current_user=current_user
        )
    ]


@router.delete(
    "/conversations/{conversation_id}/assets/{asset_id}",
    status_code=204,
)
def delete_media_image(
    conversation_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media_service.delete_image_asset(
        db=db,
        conversation_id=conversation_id,
        asset_id=asset_id,
        current_user=current_user,
    )
    return Response(status_code=204)
@router.get("/assets/{asset_id}/download")
def download_media_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = media_service.get_asset(db=db, asset_id=asset_id, current_user=current_user)
    return FileResponse(
        path=media_service.get_asset_path(asset),
        filename=asset.filename,
        media_type=asset.content_type or "application/octet-stream",
    )

def _serialize_job(db: Session, job) -> MediaJobResponse:
    output_asset = db.get(MediaAsset, job.output_asset_id) if job.output_asset_id else None
    return MediaJobResponse(
        id=job.id,
        conversation_id=job.conversation_id,
        prompt=job.prompt,
        aspect_ratio=job.aspect_ratio,
        duration_seconds=job.duration_seconds,
        source_asset_ids=job.source_asset_ids,
        provider=job.provider,
        provider_model=job.provider_model,
        provider_job_id=job.provider_job_id,
        status=job.status,
        error_message=job.error_message,
        output_asset_id=job.output_asset_id,
        output_asset=_serialize_asset(output_asset) if output_asset else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

@router.post(
    "/conversations/{conversation_id}/video-jobs",
    response_model=MediaJobResponse,
    status_code=202,
)
async def create_video_generation_job(
    conversation_id: int,
    request: VideoGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await video_generation_service.create_job(
        db=db,
        conversation_id=conversation_id,
        request=request,
        current_user=current_user,
    )
    return _serialize_job(db, job)

@router.get(
    "/conversations/{conversation_id}/video-jobs",
    response_model=list[MediaJobResponse],
)
def list_video_generation_jobs(
    conversation_id: int,
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs = video_generation_service.list_jobs(
        db=db,
        conversation_id=conversation_id,
        current_user=current_user,
        limit=limit,
    )
    return [_serialize_job(db, job) for job in jobs]

@router.get(
    "/jobs/{job_id}",
    response_model=MediaJobResponse,
)
async def get_video_generation_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await video_generation_service.get_job(
        db=db, job_id=job_id, current_user=current_user
    )
    return _serialize_job(db, job)
