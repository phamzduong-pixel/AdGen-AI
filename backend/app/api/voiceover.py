import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.schemas.voiceover import (
    VoiceOption,
    CleanScriptRequest,
    CleanScriptResponse,
    VoiceoverGenerateRequest,
    VoiceoverGenerateResponse,
)
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.voiceover.voiceover_service import (
    VoiceoverProviderTimeoutError,
    voiceover_service,
)
from app.services.voiceover.providers.vieneu_reference_provider import ReferenceVoiceError
from app.core.config import settings
from app.core.security import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.models.voiceover_audio import VoiceoverAudio
from app.services.voiceover.audio_persistence import (
    VoiceoverMessageLinkError,
    persist_latest_voiceover_record,
    resolve_owned_message_id,
)

router = APIRouter(prefix="/voiceover", tags=["voiceover"])

AUDIO_DIR = Path(settings.UPLOAD_DIR) / "audio"


@router.get("/voices", response_model=List[VoiceOption])
async def list_available_voices():
    """Return available TTS voice options."""
    try:
        return await voiceover_service.get_available_voices()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Không thể lấy danh sách giọng đọc.",
        ) from error


@router.post("/clean-script", response_model=CleanScriptResponse)
async def clean_script(request: CleanScriptRequest):
    """Extract spoken dialogue from an advertising script."""
    try:
        return voiceover_service.clean_script(request.raw_script)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Không thể xử lý kịch bản.",
        ) from error


@router.post("/generate", response_model=VoiceoverGenerateResponse)
async def generate_voiceover(
    request: VoiceoverGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate an audio file and persist its owner before returning its URL."""
    try:
        linked_message_id = resolve_owned_message_id(
            request.message_id,
            db=db,
            current_user=current_user,
        )
    except VoiceoverMessageLinkError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    if request.message_id is not None:
        try:
            linked_message_id = int(request.message_id)
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail="message_id không hợp lệ.") from error
        linked_message = (
            db.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Message.id == linked_message_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )
        if linked_message is None:
            raise HTTPException(status_code=404, detail="Tin nhắn không tồn tại hoặc không thuộc tài khoản.")

    try:
        response = await voiceover_service.generate_voiceover(request, clean_first=False)
        record = VoiceoverAudio(
            audio_id=response.audio_id,
            filename=f"{response.audio_id}.mp3",
            user_id=current_user.id,
            message_id=linked_message_id,
            file_size_bytes=response.file_size_bytes,
            duration_seconds=response.duration_seconds,
            voice_id=response.voice_id,
        )
        persist_latest_voiceover_record(db=db, audio_dir=AUDIO_DIR, record=record)
        return response
    except VoiceoverProviderTimeoutError as error:
        db.rollback()
        raise HTTPException(
            status_code=504,
            detail={'code': error.code, 'message': error.public_message},
        ) from error
    except ReferenceVoiceError as error:
        db.rollback()
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Nội dung voiceover không hợp lệ.",
        ) from error
    except Exception as error:
        db.rollback()
        # Do not leave an unowned generated file if metadata persistence fails.
        audio_path = AUDIO_DIR / f"{getattr(locals().get('response', None), 'audio_id', '')}.mp3"
        if audio_path.name != ".mp3":
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail="Lỗi tạo voiceover hoặc lưu quyền sở hữu audio.") from error


@router.post("/generate-reference", response_model=VoiceoverGenerateResponse)
async def generate_reference_voiceover(
    text: str = Form(...),
    file: UploadFile = File(...),
    emotion_cue: str = Form(default='none'),
    message_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate speech from text with a user-provided reference voice."""

    try:
        linked_message_id = resolve_owned_message_id(message_id, db=db, current_user=current_user)
    except VoiceoverMessageLinkError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    try:
        response = await voiceover_service.generate_reference_voiceover(
            text=text,
            reference_audio=file,
            emotion_cue=emotion_cue,
        )
        record = VoiceoverAudio(
            audio_id=response.audio_id,
            filename=f"{response.audio_id}.mp3",
            user_id=current_user.id,
            message_id=linked_message_id,
            file_size_bytes=response.file_size_bytes,
            duration_seconds=response.duration_seconds,
            voice_id=response.voice_id,
        )
        persist_latest_voiceover_record(db=db, audio_dir=AUDIO_DIR, record=record)
        return response
    except ReferenceVoiceError as error:
        db.rollback()
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Nội dung voiceover không hợp lệ.",
        ) from error
    except Exception as error:
        db.rollback()
        audio_path = AUDIO_DIR / f"{getattr(locals().get('response', None), 'audio_id', '')}.mp3"
        if audio_path.name != ".mp3":
            try:
                audio_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail="Lỗi tạo voiceover hoặc lưu quyền sở hữu audio.",
        ) from error

@router.get("/audio/{filename}")
async def get_audio_file(
    filename: str,
    download: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream/download only audio owned by the authenticated user.

    Legacy files without a ``VoiceoverAudio`` row are intentionally denied;
    ownership is never inferred from a shared filesystem directory.
    """
    safe_filename = Path(filename).name
    if safe_filename != filename or Path(safe_filename).suffix.lower() not in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}:
        raise HTTPException(status_code=400, detail="Định dạng file không hợp lệ.")

    record = (
        db.query(VoiceoverAudio)
        .filter(
            VoiceoverAudio.filename == safe_filename,
            VoiceoverAudio.user_id == current_user.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy audio hoặc bạn không có quyền truy cập.")

    file_path = AUDIO_DIR / safe_filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh.")

    disposition = "attachment" if download else "inline"
    headers = {"Content-Disposition": f'{disposition}; filename="{safe_filename}"'}
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }
    return FileResponse(
        path=str(file_path),
        media_type=media_types[Path(safe_filename).suffix.lower()],
        headers=headers,
    )

@router.head("/audio/{filename}", include_in_schema=False)
async def head_audio_file(
    filename: str,
    download: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the same ownership-checked headers as GET without an OpenAPI duplicate."""
    return await get_audio_file(filename, download, db, current_user)


@router.get("/messages")
async def list_message_voiceovers(
    message_ids: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the latest persisted voiceover for each requested message."""

    normalized_ids = []
    for raw_id in message_ids.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            message_id = int(raw_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="message_ids không hợp lệ.") from error
        if message_id > 0 and message_id not in normalized_ids:
            normalized_ids.append(message_id)

    if not normalized_ids:
        return []

    records = (
        db.query(VoiceoverAudio)
        .filter(
            VoiceoverAudio.user_id == current_user.id,
            VoiceoverAudio.message_id.in_(normalized_ids),
        )
        .order_by(VoiceoverAudio.created_at.desc())
        .all()
    )
    latest_by_message = {}
    for record in records:
        key = str(record.message_id)
        if key in latest_by_message:
            continue
        latest_by_message[key] = {
            "audio_id": record.audio_id,
            "audio_url": f"/voiceover/audio/{record.filename}",
            "download_url": f"/voiceover/audio/{record.filename}?download=true",
            "duration_seconds": record.duration_seconds,
            "file_size_bytes": record.file_size_bytes,
            "voice_id": record.voice_id,
            "voice_name": record.voice_id,
            "message_id": record.message_id,
        }
    return list(latest_by_message.values())
