from dataclasses import dataclass, field
from enum import Enum


class CampaignObjectiveType(str, Enum):
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"
    TRAFFIC = "traffic"
    MESSAGES = "messages"
    LEAD_GENERATION = "lead_generation"
    CONVERSION = "conversion"
    RETENTION = "retention"
    EVENT_PROMOTION = "event_promotion"


@dataclass
class ProductProfile:
    name: str
    category: str | None = None
    description: str | None = None
    key_features: list[str] = field(default_factory=list)
    key_benefits: list[str] = field(default_factory=list)
    usp: str | None = None
    price: str | None = None
    offer: str | None = None
    warranty: str | None = None
    technical_specs: dict[str, str] = field(default_factory=dict)
    forbidden_claims: list[str] = field(default_factory=list)


@dataclass
class AudienceProfile:
    persona_name: str | None = None
    pain_points: list[str] = field(default_factory=list)
    desires: list[str] = field(default_factory=list)
    demographics: str | None = None
    common_objections: list[str] = field(default_factory=list)


@dataclass
class ProductAwareContext:
    product: ProductProfile
    platform: str
    audience: AudienceProfile | None = None
    objective: CampaignObjectiveType = CampaignObjectiveType.CONVERSION
    brand_name: str | None = None
    brand_voice: str | None = None
    custom_notes: str | None = None
