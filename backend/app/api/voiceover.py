import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse

from app.schemas.voiceover import (
    VoiceOption,
    CleanScriptRequest,
    CleanScriptResponse,
    VoiceoverGenerateRequest,
    VoiceoverGenerateResponse,
)
from app.services.voiceover.voiceover_service import voiceover_service
from app.core.config import settings

router = APIRouter(prefix="/voiceover", tags=["voiceover"])

AUDIO_DIR = Path(settings.UPLOAD_DIR) / "audio"

@router.get("/voices", response_model=List[VoiceOption])
async def list_available_voices():
    """
    Returns available TTS voice options (Vietnamese, English, male, female).
    """
    try:
        return await voiceover_service.get_available_voices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lấy danh sách giọng đọc: {str(e)}")

@router.post("/clean-script", response_model=CleanScriptResponse)
async def clean_script(request: CleanScriptRequest):
    """
    Extracts pure spoken dialogue from advertising scripts by stripping out
    bracket tags, stage directions, visual descriptors, and actor prefixes.
    """
    try:
        return voiceover_service.clean_script(request.raw_script)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý kịch bản: {str(e)}")

@router.post("/generate", response_model=VoiceoverGenerateResponse)
async def generate_voiceover(request: VoiceoverGenerateRequest):
    """
    On-demand voiceover generation.
    Synthesizes speech from dialogue, writes MP3 file, and returns playback metadata.
    """
    try:
        return await voiceover_service.generate_voiceover(request, clean_first=False)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo voiceover: {str(e)}")

@router.api_route("/audio/{filename}", methods=["GET", "HEAD"])
async def get_audio_file(filename: str, download: bool = Query(False)):
    """
    Streams or downloads the generated MP3 audio file.
    Supports HTTP Range requests for instant browser seekbar scrubbing.
    """
    # Sanitize filename
    safe_filename = Path(filename).name
    if not safe_filename.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Định dạng file không hợp lệ.")

    file_path = AUDIO_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file âm thanh.")

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{safe_filename}"'

    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        headers=headers
    )