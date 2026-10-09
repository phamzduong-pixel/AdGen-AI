from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.stt import TranscriptionResponse
from app.services.stt.models import STTError
from app.services.voice_studio.video_input import VideoInputError
from app.services.voice_studio.video_to_stt import (
    VideoToSTTError,
    video_to_stt_service,
)


router = APIRouter(prefix="/stt", tags=["speech-to-text"])


@router.post("/transcribe-video", response_model=TranscriptionResponse)
async def transcribe_video(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    _current_user: User = Depends(get_current_user),
):
    """Validate one video, extract its audio, and delegate to existing STT."""

    try:
        result = await video_to_stt_service.transcribe_upload(
            file,
            language=language,
        )
    except (VideoInputError, VideoToSTTError, STTError) as error:
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error

    return TranscriptionResponse(
        transcript=result.transcript,
        language=result.language,
        provider=result.provider,
        metadata=result.metadata,
    )
