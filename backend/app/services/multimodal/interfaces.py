from abc import ABC, abstractmethod
from app.services.multimodal.models import (
    MediaAsset,
    MultimodalPayload,
    MultimodalTaskType,
)


class IMediaAnalyzer(ABC):
    """Interface phân tích dữ liệu đa phương thức (Ảnh, Video, Âm thanh)."""

    @abstractmethod
    def analyze_asset(self, asset: MediaAsset) -> dict:
        """Trích xuất thuộc tính hình ảnh/video/âm thanh (màu sắc, text OCR, thời lượng, cảnh quay)."""
        pass


class IMultimodalProcessor(ABC):
    """Interface xử lý luồng công việc đa phương thức."""

    @abstractmethod
    def can_handle(self, task_type: MultimodalTaskType) -> bool:
        """Kiểm tra processor có hỗ trợ tác vụ đa phương thức này hay không."""
        pass

    @abstractmethod
    def prepare_parts(self, payload: MultimodalPayload) -> list[dict]:
        """Chuyển đổi các media assets thành các parts tương thích với AI Core SDK."""
        pass
