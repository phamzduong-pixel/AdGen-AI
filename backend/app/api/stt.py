from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.stt import TranscriptionResponse
from app.services.stt.models import STTError
from app.services.stt.service import stt_service


router = APIRouter(prefix="/stt", tags=["speech-to-text"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    _current_user: User = Depends(get_current_user),
):
    """Transcribe one authenticated audio upload without persisting it."""

    try:
        result = await stt_service.transcribe_upload(file, language=language)
    except STTError as error:
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
