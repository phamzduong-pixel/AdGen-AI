from google import genai
from google.genai import types

from app.core.config import settings
from app.services.media.providers.video_generation import (
    GeneratedVideo,
    MAX_REFERENCE_IMAGES,
    VideoGenerationInput,
    VideoGenerationProvider,
    VideoGenerationProviderError,
    VideoGenerationProviderUnavailable,
    VideoGenerationStatus,
    VideoGenerationSubmission,
)


VEO_ASPECT_RATIOS = {"16:9", "9:16"}
VEO_DURATION_SECONDS = 8


class GeminiVideoProvider(VideoGenerationProvider):
    """Gemini Veo 3.1 long-running video generation adapter."""

    def __init__(self, client=None, model_name: str | None = None):
        if client is None and not settings.GEMINI_API_KEY:
            raise VideoGenerationProviderUnavailable(
                "GEMINI_API_KEY chưa được cấu hình"
            )
        self.client = client or genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = model_name or settings.GEMINI_VIDEO_MODEL
        if not self._model_name:
            raise VideoGenerationProviderUnavailable(
                "GEMINI_VIDEO_MODEL chưa được cấu hình"
            )

    @property
    def provider_id(self) -> str:
        return "gemini-veo"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def submit(
        self, request: VideoGenerationInput
    ) -> VideoGenerationSubmission:
        self._validate_request(request)
        reference_images = [
            types.VideoGenerationReferenceImage(
                image=types.Image(image_bytes=data, mime_type=content_type),
                reference_type=types.VideoGenerationReferenceType.ASSET,
            )
            for data, content_type in request.references
        ]
        config = types.GenerateVideosConfig(
            number_of_videos=1,
            aspect_ratio=request.aspect_ratio,
            duration_seconds=VEO_DURATION_SECONDS,
            reference_images=reference_images or None,
        )
        try:
            operation = self.client.models.generate_videos(
                model=self.model_name,
                prompt=request.prompt,
                config=config,
            )
        except Exception as error:
            raise VideoGenerationProviderError(
                self._safe_provider_error("submit", error)
            ) from error
        operation_id = getattr(operation, "name", None)
        if not operation_id:
            raise VideoGenerationProviderError(
                "Gemini không trả về operation ID cho Veo video"
            )
        return VideoGenerationSubmission(operation_id, self._map_status(operation))

    async def get_status(self, provider_job_id: str) -> VideoGenerationStatus:
        operation = self._operation(provider_job_id)
        try:
            operation = self.client.operations.get(operation)
        except Exception as error:
            raise VideoGenerationProviderError(
                self._safe_provider_error("poll", error)
            ) from error
        status = self._map_status(operation)
        error_message = self._operation_error(operation) if status == "failed" else None
        return VideoGenerationStatus(provider_job_id, status, error_message)

    async def retrieve_result(self, provider_job_id: str) -> GeneratedVideo:
        operation = self._operation(provider_job_id)
        try:
            operation = self.client.operations.get(operation)
        except Exception as error:
            raise VideoGenerationProviderError(
                self._safe_provider_error("retrieve", error)
            ) from error
        if self._map_status(operation) != "completed":
            raise VideoGenerationProviderError(
                "Gemini Veo operation chưa hoàn tất"
            )
        response = getattr(operation, "response", None) or getattr(operation, "result", None)
        generated_videos = getattr(response, "generated_videos", None) if response else None
        if not generated_videos:
            raise VideoGenerationProviderError(
                "Gemini Veo completed nhưng không trả về video"
            )
        video = getattr(generated_videos[0], "video", None)
        if video is None:
            raise VideoGenerationProviderError(
                "Gemini Veo result không có video file"
            )
        try:
            data = self.client.files.download(file=video)
        except Exception as error:
            raise VideoGenerationProviderError(
                self._safe_provider_error("download", error)
            ) from error
        if not isinstance(data, bytes) or not data:
            raise VideoGenerationProviderError(
                "Gemini Veo download trả về dữ liệu không hợp lệ"
            )
        return GeneratedVideo(
            data=data,
            content_type=getattr(video, "mime_type", None) or "video/mp4",
        )

    @staticmethod
    def _safe_provider_error(action: str, error: Exception) -> str:
        status_code = getattr(error, "status_code", None)
        provider_text = str(error).lower()
        if status_code == 429 or "resource_exhausted" in provider_text:
            return "Video AI đang bị giới hạn quota hoặc rate limit (HTTP 429). Hãy kiểm tra quota, usage tier và billing rồi thử lại sau."
        if isinstance(error, TimeoutError):
            return "Provider video không phản hồi kịp thời. Vui lòng thử lại sau."
        messages = {
            "submit": "Không thể gửi yêu cầu tới provider video.",
            "poll": "Không thể cập nhật trạng thái provider video.",
            "retrieve": "Không thể lấy kết quả video từ provider.",
            "download": "Không thể tải kết quả video từ provider.",
        }
        return messages.get(action, "Provider video không thể xử lý yêu cầu.")

    @staticmethod
    def _validate_request(request: VideoGenerationInput) -> None:
        if request.aspect_ratio not in VEO_ASPECT_RATIOS:
            raise VideoGenerationProviderError(
                "Veo 3.1 chỉ hỗ trợ aspect ratio 16:9 hoặc 9:16 ở MVP"
            )
        if request.duration_seconds not in {None, VEO_DURATION_SECONDS}:
            raise VideoGenerationProviderError(
                "Veo 3.1 MVP chỉ hỗ trợ video dài 8 giây"
            )
        if len(request.references) > MAX_REFERENCE_IMAGES:
            raise VideoGenerationProviderError(
                "Veo 3.1 chỉ nhận tối đa 3 ảnh tham chiếu"
            )
        for _, content_type in request.references:
            if content_type not in {"image/png", "image/jpeg", "image/webp"}:
                raise VideoGenerationProviderError(
                    "Ảnh tham chiếu có MIME type không được hỗ trợ"
                )

    @staticmethod
    def _operation(provider_job_id: str):
        if not provider_job_id:
            raise VideoGenerationProviderError("Provider job ID không hợp lệ")
        return types.GenerateVideosOperation(name=provider_job_id)

    @classmethod
    def _map_status(cls, operation) -> str:
        if getattr(operation, "error", None):
            return "failed"
        if not getattr(operation, "done", False):
            return "processing"
        response = getattr(operation, "response", None) or getattr(operation, "result", None)
        if response and getattr(response, "generated_videos", None):
            return "completed"
        return "failed"

    @staticmethod
    def _operation_error(operation) -> str:
        error = getattr(operation, "error", None)
        raw = str(error.get("message") or error) if isinstance(error, dict) else str(error or "")
        lowered = raw.lower()
        if "429" in lowered or "quota" in lowered or "resource_exhausted" in lowered:
            return "Video AI đang bị giới hạn quota hoặc rate limit (HTTP 429). Hãy kiểm tra quota, usage tier và billing rồi thử lại sau."
        return "Provider video generation thất bại. Vui lòng thử lại sau."