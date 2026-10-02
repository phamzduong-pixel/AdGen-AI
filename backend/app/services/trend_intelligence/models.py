from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TrendCategory(str, Enum):
    MARKETING = "marketing"
    ECOMMERCE = "ecommerce"
    CONSUMER_TECH = "consumer_tech"
    FASHION_BEAUTY = "fashion_beauty"
    FOOD_BEVERAGE = "food_beverage"
    LIFESTYLE = "lifestyle"
    GENERAL = "general"


class TrendSourceType(str, Enum):
    OFFICIAL_REPORT = "official_report"
    MARKET_DATA = "market_data"
    PLATFORM_ANALYTICS = "platform_analytics"
    NEWS_FEED = "news_feed"
    MANUAL_VERIFIED = "manual_verified"


@dataclass(frozen=True)
class TrendItem:
    topic: str
    headline: str
    description: str
    source_name: str
    source_type: TrendSourceType
    category: TrendCategory
    published_at: datetime
    source_url: str | None = None
    target_platforms: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ValidatedTrend:
    item: TrendItem
    is_valid: bool
    credibility_score: float  # 0.0 to 1.0
    validation_notes: str
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TrendQuery:
    query: str | None = None
    category: TrendCategory | None = None
    platform: str | None = None
    max_results: int = 5
    min_credibility: float = 0.7
    max_age_days: int = 30
