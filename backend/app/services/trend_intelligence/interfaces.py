from abc import ABC, abstractmethod
from app.services.trend_intelligence.models import (
    TrendItem,
    TrendQuery,
    ValidatedTrend,
)


class ITrendCollector(ABC):
    """
    Interface thu thập xu hướng từ các nguồn dữ liệu bên ngoài
    (Ví dụ: Google Trends API, TikTok Creative Center API, Shopee Hot Searches, RSS Feed).
    """

    @abstractmethod
    def collect_trends(self, query: TrendQuery) -> list[TrendItem]:
        """Thu thập danh sách TrendItem từ nguồn dữ liệu."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Kiểm tra nguồn dữ liệu có sẵn sàng kết nối không (API Key, Network, Token)."""
        pass


class ITrendValidator(ABC):
    """
    Interface thẩm định xu hướng: Kiểm tra tính xác thực, độ tươi mới (freshness),
    độ tin cậy của nguồn và loại bỏ tin giả / số liệu ảo.
    """

    @abstractmethod
    def validate(self, item: TrendItem, query: TrendQuery) -> ValidatedTrend:
        """Kiểm tra và đánh giá độ tin cậy của một TrendItem."""
        pass


class ITrendNormalizer(ABC):
    """
    Interface chuẩn hóa dữ liệu xu hướng:
    - Loại bỏ mã HTML / khoảng trắng thừa
    - Chuẩn hóa từ khóa / hashtags
    - Định dạng mốc thời gian ISO UTC
    - Gắn category và platform tags đồng nhất
    """

    @abstractmethod
    def normalize(self, validated_trend: ValidatedTrend) -> ValidatedTrend:
        """Chuẩn hóa cấu trúc nội dung và metadata của ValidatedTrend."""
        pass


class ITrendCache(ABC):
    """
    Interface lưu trữ / cache xu hướng để tối ưu tốc độ và giảm gọi API ngoài lặp lại.
    """

    @abstractmethod
    def get(self, cache_key: str) -> list[ValidatedTrend] | None:
        """Lấy danh sách xu hướng đã thẩm định từ bộ nhớ cache."""
        pass

    @abstractmethod
    def set(self, cache_key: str, trends: list[ValidatedTrend], ttl_seconds: int = 3600) -> None:
        """Lưu danh sách xu hướng vào cache với thời gian sống TTL."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Xóa toàn bộ cache."""
        pass
