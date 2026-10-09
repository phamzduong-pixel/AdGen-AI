from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.security import get_current_user
from app.models.user import User
from app.services.voice_conversion.models import VoiceConversionError
from app.services.voice_conversion.service import voice_conversion_service
from app.services.voice_conversion.reference_service import seed_vc_reference_service
from app.services.voice_conversion.media_service import seed_vc_media_service


router = APIRouter(prefix="/voice-conversion", tags=["voice-conversion"])


@router.post("/convert")
async def convert_voice(
    file: UploadFile = File(...),
    target_voice_id: str | None = Form(default=None),
    language: str | None = Form(default=None),
    output_format: str = Form(default="mp3"),
    remove_background_noise: bool = Form(default=False),
    _current_user: User = Depends(get_current_user),
):
    """Convert uploaded audio directly to a target voice without persistence."""

    try:
        result = await voice_conversion_service.convert_upload(
            file,
            target_voice_id=target_voice_id,
            language=language,
            output_format=output_format,
            remove_background_noise=remove_background_noise,
        )
    except VoiceConversionError as error:
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error

    extension = result.file_extension.lstrip(".") or "audio"
    headers = {
        "Content-Disposition": f'inline; filename="voice-converted.{extension}"',
        "X-VC-Provider": result.provider_id,
        "X-VC-Output-Format": extension,
    }
    if result.duration_seconds is not None:
        headers["X-VC-Duration-Seconds"] = str(result.duration_seconds)
    return Response(
        content=result.audio_bytes,
        media_type=result.content_type,
        headers=headers,
    )


@router.post("/convert-reference")
async def convert_voice_with_reference(
    file: UploadFile = File(...),
    reference_file: UploadFile | None = File(default=None),
    preset_voice_id: str | None = Form(default=None),
    _current_user: User = Depends(get_current_user),
):
    """Seed-VC audio-to-audio conversion; source timing and delivery are retained."""
    try:
        result = await seed_vc_reference_service.convert_upload(
            file,
            reference_upload=reference_file,
            preset_voice_id=preset_voice_id,
        )
    except VoiceConversionError as error:
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error

    return Response(
        content=result.audio_bytes,
        media_type=result.content_type,
        headers={
            "Content-Disposition": 'inline; filename="voice-converted.wav"',
            "X-VC-Provider": result.provider_id,
            "X-VC-Output-Format": "wav",
        },
    )

@router.post("/convert-reference-video")
async def convert_video_with_reference(
    file: UploadFile = File(...),
    reference_file: UploadFile | None = File(default=None),
    preset_voice_id: str | None = Form(default=None),
    _current_user: User = Depends(get_current_user),
):
    """Convert a video's spoken voice and return the remuxed video."""
    try:
        video_bytes, content_type, extension = await seed_vc_media_service.convert_video_upload(
            file,
            reference_upload=reference_file,
            preset_voice_id=preset_voice_id,
        )
    except VoiceConversionError as error:
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error
    return Response(
        content=video_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="voice-converted{extension}"',
            "X-VC-Provider": "seed-vc-cpu",
        },
    )
