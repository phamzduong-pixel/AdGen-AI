from datetime import datetime, timezone, timedelta
import re
import threading

from app.services.trend_intelligence.interfaces import (
    ITrendCollector,
    ITrendValidator,
    ITrendNormalizer,
    ITrendCache,
)
from app.services.trend_intelligence.models import (
    TrendCategory,
    TrendItem,
    TrendQuery,
    TrendSourceType,
    ValidatedTrend,
)


class StandardTrendValidator(ITrendValidator):
    """
    Bộ thẩm định xu hướng tiêu chuẩn:
    - Kiểm tra nguồn dữ liệu (Official report, Market data, Platform Analytics được chấm điểm cao).
    - Kiểm tra độ tươi mới (so với max_age_days).
    - Ngăn chặn tin đồn / thông tin thiếu căn cứ.
    """

    def validate(self, item: TrendItem, query: TrendQuery) -> ValidatedTrend:
        now = datetime.now(timezone.utc)
        item_time = item.published_at
        if item_time.tzinfo is None:
            item_time = item_time.replace(tzinfo=timezone.utc)

        age_days = (now - item_time).total_seconds() / 86400.0

        if age_days > query.max_age_days:
            return ValidatedTrend(
                item=item,
                is_valid=False,
                credibility_score=0.2,
                validation_notes=f"Dữ liệu đã cũ ({age_days:.1f} ngày trước, giới hạn: {query.max_age_days} ngày)",
            )

        base_scores = {
            TrendSourceType.OFFICIAL_REPORT: 0.95,
            TrendSourceType.MANUAL_VERIFIED: 0.90,
            TrendSourceType.PLATFORM_ANALYTICS: 0.85,
            TrendSourceType.MARKET_DATA: 0.80,
            TrendSourceType.NEWS_FEED: 0.70,
        }
        score = base_scores.get(item.source_type, 0.6)

        # Trừ điểm nếu thiếu mô tả hoặc nguồn
        if not item.source_name or not item.description:
            score -= 0.3

        is_valid = score >= query.min_credibility
        notes = (
            "Đã xác thực nguồn tin cậy"
            if is_valid
            else f"Độ tin cậy ({score:.2f}) chưa đạt mức yêu cầu ({query.min_credibility})"
        )

        return ValidatedTrend(
            item=item,
            is_valid=is_valid,
            credibility_score=score,
            validation_notes=notes,
        )


class StandardTrendNormalizer(ITrendNormalizer):
    """
    Bộ chuẩn hóa dữ liệu xu hướng:
    - Loại bỏ mã HTML / ký tự rác / khoảng trắng thừa
    - Chuẩn hóa keywords và hashtags
    - Đảm bảo datetime có timezone UTC
    - Chuẩn hóa chữ thường/hoa trên platform tags
    """

    def normalize(self, validated_trend: ValidatedTrend) -> ValidatedTrend:
        item = validated_trend.item

        # 1. Clean HTML & Whitespace
        clean_headline = re.sub(r"<[^>]+>", "", item.headline).strip()
        clean_headline = re.sub(r"\s+", " ", clean_headline)

        clean_desc = re.sub(r"<[^>]+>", "", item.description).strip()
        clean_desc = re.sub(r"\s+", " ", clean_desc)

        clean_topic = re.sub(r"\s+", " ", item.topic).strip()

        # 2. Normalize Keywords & Hashtags
        clean_keywords = [
            re.sub(r"^[#\s]+", "", kw).strip().lower()
            for kw in item.keywords
            if kw and kw.strip()
        ]
        clean_keywords = list(dict.fromkeys(clean_keywords))

        # 3. Normalize Platform tags
        clean_platforms = [p.strip().lower() for p in item.target_platforms if p and p.strip()]
        clean_platforms = list(dict.fromkeys(clean_platforms))

        # 4. Normalize Datetime to UTC
        pub_at = item.published_at
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)
        else:
            pub_at = pub_at.astimezone(timezone.utc)

        normalized_item = TrendItem(
            topic=clean_topic,
            headline=clean_headline,
            description=clean_desc,
            source_name=item.source_name.strip(),
            source_type=item.source_type,
            category=item.category,
            published_at=pub_at,
            source_url=item.source_url.strip() if item.source_url else None,
            target_platforms=clean_platforms,
            keywords=clean_keywords,
            metadata=item.metadata,
        )

        return ValidatedTrend(
            item=normalized_item,
            is_valid=validated_trend.is_valid,
            credibility_score=validated_trend.credibility_score,
            validation_notes=validated_trend.validation_notes,
            validated_at=validated_trend.validated_at,
        )


class InMemoryTrendCache(ITrendCache):
    """Bộ nhớ đệm xu hướng trong RAM có TTL."""

    def __init__(self):
        self._cache: dict[str, tuple[list[ValidatedTrend], datetime]] = {}
        self._lock = threading.Lock()

    def get(self, cache_key: str) -> list[ValidatedTrend] | None:
        with self._lock:
            record = self._cache.get(cache_key)
            if not record:
                return None
            data, expires_at = record
            if datetime.now(timezone.utc) > expires_at:
                del self._cache[cache_key]
                return None
            return data

    def set(self, cache_key: str, trends: list[ValidatedTrend], ttl_seconds: int = 3600) -> None:
        with self._lock:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            self._cache[cache_key] = (trends, expires_at)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class VerifiedTrendRegistryCollector(ITrendCollector):
    """
    Collector nguồn dữ liệu xu hướng đã qua kiểm duyệt / xác minh.
    Cho phép hệ thống cập nhật các trend đã kiểm chứng từ các báo cáo thị trường chính thống.
    """

    def __init__(self):
        self._verified_trends: list[TrendItem] = []
        self._lock = threading.Lock()

    def register_verified_trend(self, item: TrendItem) -> None:
        with self._lock:
            self._verified_trends.append(item)

    def is_available(self) -> bool:
        return True

    def collect_trends(self, query: TrendQuery) -> list[TrendItem]:
        with self._lock:
            results = []
            q_str = query.query.lower() if query.query else None
            p_str = query.platform.lower() if query.platform else None

            for item in self._verified_trends:
                if query.category and item.category != query.category:
                    continue
                if p_str and item.target_platforms:
                    if p_str not in [p.lower() for p in item.target_platforms]:
                        continue
                if q_str:
                    matched = (
                        q_str in item.topic.lower()
                        or q_str in item.headline.lower()
                        or q_str in item.description.lower()
                        or any(q_str in kw.lower() for kw in item.keywords)
                    )
                    if not matched:
                        continue
                results.append(item)
            return results[: query.max_results]


class TrendIntelligenceService:
    """
    Dịch vụ Trend Intelligence:
    Triển khai luồng kiến trúc hoàn chỉnh:
    External Sources -> Retrieve/Collect -> Validate -> Normalize -> Store/Cache -> Retrieve Relevant Info -> Prompt Engine -> AI Model
    """

    def __init__(
        self,
        collectors: list[ITrendCollector] | None = None,
        validator: ITrendValidator | None = None,
        normalizer: ITrendNormalizer | None = None,
        cache: ITrendCache | None = None,
    ):
        self.verified_collector = VerifiedTrendRegistryCollector()
        self.collectors: list[ITrendCollector] = collectors or [self.verified_collector]
        self.validator: ITrendValidator = validator or StandardTrendValidator()
        self.normalizer: ITrendNormalizer = normalizer or StandardTrendNormalizer()
        self.cache: ITrendCache = cache or InMemoryTrendCache()

    def add_collector(self, collector: ITrendCollector) -> None:
        self.collectors.append(collector)

    def add_verified_trend(self, item: TrendItem) -> None:
        self.verified_collector.register_verified_trend(item)

    def retrieve_trends(self, query: TrendQuery) -> list[ValidatedTrend]:
        """
        Thực thi trọn vẹn quy trình 6 bước:
        1. Kiểm tra Cache
        2. Nếu miss, Retrieve/Collect từ các Collectors sẵn sàng
        3. Validate tính xác thực và độ tin cậy
        4. Normalize chuẩn hóa dữ liệu
        5. Store / Cache
        6. Trả về Relevant Validated Trends
        """
        cache_key = f"trends:{query.category}:{query.platform}:{query.query}:{query.min_credibility}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        raw_items: list[TrendItem] = []
        for collector in self.collectors:
            if collector.is_available():
                try:
                    items = collector.collect_trends(query)
                    raw_items.extend(items)
                except Exception:
                    # Tránh làm gián đoạn hệ thống nếu 1 collector gặp sự cố
                    pass

        # Bước 3 & Bước 4: Validate và Normalize
        normalized_trends: list[ValidatedTrend] = []
        for item in raw_items:
            val = self.validator.validate(item, query)
            if val.is_valid:
                norm = self.normalizer.normalize(val)
                normalized_trends.append(norm)

        # Sắp xếp theo điểm tin cậy và ngày xuất bản
        normalized_trends.sort(
            key=lambda x: (x.credibility_score, x.item.published_at),
            reverse=True,
        )
        final_results = normalized_trends[: query.max_results]

        # Bước 5: Store/Cache
        self.cache.set(cache_key, final_results, ttl_seconds=1800)
        return final_results

    def format_trend_context(
        self,
        query: str | None = None,
        category: TrendCategory | None = None,
        platform: str | None = None,
    ) -> str:
        """
        Định dạng ngữ cảnh xu hướng thực tế để đưa vào Prompt Engine.
        QUAN TRỌNG: Nếu không có dữ liệu xu hướng thực tế, thông báo rõ ràng
        và cấm AI bịa đặt xu hướng.
        """
        trend_query = TrendQuery(
            query=query,
            category=category,
            platform=platform,
            max_results=3,
        )
        trends = self.retrieve_trends(trend_query)

        if not trends:
            return (
                "### THÔNG TIN XU HƯỚNG HIỆN TẠI (TREND INTELLIGENCE)\n"
                "Hiện không có dữ liệu xu hướng được xác thực cho chủ đề này.\n"
                "QUY TẮC BẮT BUỘC: Không tự bịa đặt số liệu thống kê, tên xu hướng hoặc trích dẫn nguồn không có thật."
            )

        items_formatted = []
        for idx, t in enumerate(trends, start=1):
            item = t.item
            items_formatted.append(
                f"{idx}. **{item.headline}**\n"
                f"   - Chủ đề: {item.topic} | Nguồn: {item.source_name} ({item.source_type.value})\n"
                f"   - Nội dung tóm tắt: {item.description}\n"
                f"   - Độ tin cậy thẩm định: {int(t.credibility_score * 100)}%"
            )

        return (
            "### THÔNG TIN XU HƯỚNG ĐÃ XÁC THỰC (VERIFIED TRENDS)\n"
            "Chỉ sử dụng các xu hướng có căn cứ dưới đây khi phù hợp với ngữ cảnh sản phẩm:\n"
            + "\n".join(items_formatted)
            + "\n*Lưu ý: Tuyệt đối không tự suy diễn thêm các số liệu chưa được cung cấp.*"
        )


trend_intelligence_service = TrendIntelligenceService()
