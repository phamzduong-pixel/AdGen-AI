"""Local VieNeu-TTS reference-voice provider.

The project backend intentionally does not import the VieNeu SDK.  VieNeu is
installed in a separate CPU/ONNX environment and invoked through the bounded
worker in this package, so the existing Edge TTS environment stays unchanged.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import wave
from pathlib import Path

from app.core.config import settings


class ReferenceVoiceError(RuntimeError):
    """Stable, non-sensitive errors for the reference-voice endpoint."""

    code = "VOICE_REFERENCE_FAILED"
    http_status = 502
    public_message = "Không thể tạo âm thanh bằng giọng tham chiếu."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        self.internal_message = message or self.public_message


class ReferenceVoiceProviderNotConfiguredError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_PROVIDER_NOT_CONFIGURED"
    http_status = 503
    public_message = "Provider giọng tham chiếu chưa được cấu hình."


class ReferenceVoiceProviderTimeoutError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_PROVIDER_TIMEOUT"
    http_status = 504
    public_message = "Tạo âm thanh bằng giọng tham chiếu đã quá thời gian chờ."


class ReferenceVoiceOutputInvalidError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_OUTPUT_INVALID"
    http_status = 502
    public_message = "Provider giọng tham chiếu trả về audio không hợp lệ."


class ReferenceVoiceProviderBusyError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_PROVIDER_BUSY"
    http_status = 429
    public_message = "Provider giọng tham chiếu đang bận. Vui lòng thử lại sau."


class ReferenceVoiceFormatError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_UNSUPPORTED_FORMAT"
    http_status = 415
    public_message = "Định dạng file giọng tham chiếu không được hỗ trợ."


class ReferenceVoiceMimeMismatchError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_MIME_MISMATCH"
    http_status = 415
    public_message = "Loại file giọng tham chiếu không khớp với phần mở rộng."


class ReferenceVoiceTooLargeError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_TOO_LARGE"
    http_status = 413
    public_message = "File giọng tham chiếu vượt quá giới hạn dung lượng."


class ReferenceVoiceTooLongError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_TOO_LONG"
    http_status = 413
    public_message = "File giọng tham chiếu vượt quá giới hạn thời lượng."


class ReferenceVoiceInvalidError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_INVALID"
    http_status = 422
    public_message = "File giọng tham chiếu không hợp lệ hoặc bị hỏng."


class ReferenceVoiceNoAudioError(ReferenceVoiceError):
    code = "VOICE_REFERENCE_NO_AUDIO_STREAM"
    http_status = 422
    public_message = "Video giọng tham chiếu không có luồng âm thanh."


class VieNeuReferenceVoiceProvider:
    provider_id = "vieneu-v3-turbo-local"
    preset_provider_id = "vieneu-v3-turbo"
    preset_voice_prefix = "vieneu-v3-turbo:"
    PRESET_VOICES = (
        {"id": "vieneu-v3-turbo:Ngọc Huyền", "name": "Ngọc Huyền (Nữ · Bắc · Giải trí)", "gender": "female", "language": "vi-VN", "description": "Tự nhiên, giàu năng lượng; hợp nội dung giải trí, review và social video.", "sample_rate": 48000},
        {"id": "vieneu-v3-turbo:Quốc Tuấn", "name": "Quốc Tuấn (Nam · Bắc · Quảng cáo)", "gender": "male", "language": "vi-VN", "description": "Tự nhiên, rõ ràng; hợp quảng cáo sản phẩm và lời kêu gọi hành động.", "sample_rate": 48000},
        {"id": "vieneu-v3-turbo:Hải Đăng", "name": "Hải Đăng (Nam · Bắc · Năng động)", "gender": "male", "language": "vi-VN", "description": "Giọng tự nhiên, linh hoạt; hợp video ngắn, giới thiệu và nội dung trẻ.", "sample_rate": 48000},
        {"id": "vieneu-v3-turbo:Trúc Ly", "name": "Trúc Ly (Nữ · Bắc · Tươi sáng)", "gender": "female", "language": "vi-VN", "description": "Giọng tự nhiên, thân thiện; hợp lifestyle, khuyến mãi và review.", "sample_rate": 48000},
        {"id": "vieneu-v3-turbo:Thiện Minh", "name": "Thiện Minh (Nam · Bắc · Kể chuyện)", "gender": "male", "language": "vi-VN", "description": "Chất kể chuyện mượt, có chiều sâu; hợp brand story và video dài.", "sample_rate": 48000},
        {"id": "vieneu-v3-turbo:Mai Anh", "name": "Mai Anh (Nữ · Bắc · Rõ nét)", "gender": "female", "language": "vi-VN", "description": "Nhịp đọc rõ ràng; hợp giới thiệu sản phẩm và nội dung thông tin.", "sample_rate": 48000},
    )
    _worker_output_max_bytes = 64 * 1024

    def __init__(self) -> None:
        self._slot = asyncio.Semaphore(1)

    @staticmethod
    def _latest_snapshot(cache_dir: Path, repository: str) -> Path | None:
        snapshots = cache_dir / "hub" / repository / "snapshots"
        if not snapshots.is_dir():
            return None
        candidates = [path for path in snapshots.iterdir() if path.is_dir()]
        return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None

    def _resolve_assets(self) -> tuple[Path, Path]:
        python_path = Path(settings.VIENEU_PYTHON)
        cache_dir = Path(settings.VIENEU_CACHE_DIR)
        model_snapshot = self._latest_snapshot(
            cache_dir,
            "models--pnnbao-ump--VieNeu-TTS-v3-Turbo",
        )
        codec_snapshot = self._latest_snapshot(
            cache_dir,
            "models--OpenMOSS-Team--MOSS-Audio-Tokenizer-Nano-ONNX",
        )
        required_model_files = (
            "onnx_update/vieneu_prefill.onnx",
            "onnx_update/vieneu_decode_step.onnx",
            "onnx_update/vieneu_acoustic_cached.onnx",
            "onnx_update/vieneu_backbone_shared.data",
            "onnx_update/vieneu_v3_heads.npz",
            "onnx_update/config.json",
            "onnx_update/tokenizer.json",
            "speaker_encoder.onnx",
            "denoiser.onnx",
        )
        required_codec_files = (
            "moss_audio_tokenizer_decode_full.onnx",
            "moss_audio_tokenizer_decode_shared.data",
            "moss_audio_tokenizer_decode_step.onnx",
            "codec_browser_onnx_meta.json",
            "moss_audio_tokenizer_encode.onnx",
            "moss_audio_tokenizer_encode.data",
        )
        if (
            not python_path.is_file()
            or model_snapshot is None
            or codec_snapshot is None
            or any(not (model_snapshot / file).is_file() for file in required_model_files)
            or any(not (codec_snapshot / file).is_file() for file in required_codec_files)
        ):
            raise ReferenceVoiceProviderNotConfiguredError
        return model_snapshot, codec_snapshot

    def is_configured(self) -> bool:
        try:
            self._resolve_assets()
        except ReferenceVoiceProviderNotConfiguredError:
            return False
        return True

    def is_preset_voice(self, voice_id: str) -> bool:
        return any(voice["id"] == voice_id for voice in self.PRESET_VOICES)

    async def synthesize_preset(self, *, text: str, voice_id: str, output_audio_path: Path) -> tuple[bytes, float]:
        if not self.is_preset_voice(voice_id):
            raise ReferenceVoiceError
        try:
            await asyncio.wait_for(self._slot.acquire(), timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as error:
            raise ReferenceVoiceProviderBusyError from error
        try:
            model_snapshot, codec_snapshot = self._resolve_assets()
            payload = {"text": text, "voice": voice_id.removeprefix(self.preset_voice_prefix), "output_audio": str(output_audio_path), "model_snapshot": str(model_snapshot), "codec_snapshot": str(codec_snapshot)}
            try:
                await asyncio.wait_for(asyncio.to_thread(self._run_worker, payload), timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS)
            except asyncio.TimeoutError as error:
                raise ReferenceVoiceProviderTimeoutError from error
            if not output_audio_path.is_file() or output_audio_path.stat().st_size <= 0 or output_audio_path.stat().st_size > settings.VIENEU_OUTPUT_MAX_SIZE_BYTES:
                raise ReferenceVoiceOutputInvalidError
            try:
                with wave.open(str(output_audio_path), "rb") as audio_file:
                    frame_rate, frame_count = audio_file.getframerate(), audio_file.getnframes()
                    if frame_rate <= 0 or frame_count <= 0:
                        raise ValueError("empty wave")
                    duration = frame_count / frame_rate
                return output_audio_path.read_bytes(), round(duration, 3)
            except (OSError, EOFError, wave.Error, ValueError) as error:
                raise ReferenceVoiceOutputInvalidError from error
        finally:
            self._slot.release()

    async def synthesize(
        self,
        *,
        text: str,
        reference_audio_path: Path,
        output_audio_path: Path,
    ) -> tuple[bytes, float]:
        try:
            await asyncio.wait_for(
                self._slot.acquire(),
                timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as error:
            raise ReferenceVoiceProviderBusyError from error

        try:
            model_snapshot, codec_snapshot = self._resolve_assets()
            payload = {
                "text": text,
                "reference_audio": str(reference_audio_path),
                "output_audio": str(output_audio_path),
                "model_snapshot": str(model_snapshot),
                "codec_snapshot": str(codec_snapshot),
            }
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._run_worker, payload),
                    timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as error:
                raise ReferenceVoiceProviderTimeoutError from error

            if not output_audio_path.is_file() or output_audio_path.stat().st_size <= 0:
                raise ReferenceVoiceOutputInvalidError
            if output_audio_path.stat().st_size > settings.VIENEU_OUTPUT_MAX_SIZE_BYTES:
                raise ReferenceVoiceOutputInvalidError

            try:
                with wave.open(str(output_audio_path), "rb") as audio_file:
                    frame_rate = audio_file.getframerate()
                    frame_count = audio_file.getnframes()
                    if frame_rate <= 0 or frame_count <= 0:
                        raise ValueError("empty wave")
                    duration = frame_count / frame_rate
                audio_bytes = output_audio_path.read_bytes()
            except (OSError, EOFError, wave.Error, ValueError) as error:
                raise ReferenceVoiceOutputInvalidError from error
            return audio_bytes, round(duration, 3)
        finally:
            self._slot.release()

    @classmethod
    def _run_worker(cls, payload: dict[str, str]) -> None:
        worker_path = Path(__file__).with_name("vieneu_worker.py")
        python_path = Path(settings.VIENEU_PYTHON)
        try:
            process = subprocess.Popen(
                [str(python_path), str(worker_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
            )
        except (FileNotFoundError, OSError) as error:
            raise ReferenceVoiceProviderNotConfiguredError from error

        try:
            stdout, _ = process.communicate(
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise ReferenceVoiceProviderTimeoutError from error

        if len(stdout) > cls._worker_output_max_bytes or process.returncode != 0:
            raise ReferenceVoiceError
        try:
            result = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReferenceVoiceError from error
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise ReferenceVoiceError

