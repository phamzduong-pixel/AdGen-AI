from dataclasses import dataclass, field
from enum import Enum


class PlatformId(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    GOOGLE_ADS = "google_ads"
    YOUTUBE = "youtube"
    SHOPEE = "shopee"
    EMAIL = "email"
    LANDING_PAGE = "landing_page"
    SEO = "seo"


@dataclass(frozen=True)
class ContentStructure:
    primary_sections: list[str]
    suggested_length_guide: str
    key_elements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HookGuideline:
    recommended_types: list[str]
    time_or_line_constraint: str
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CtaGuideline:
    primary_actions: list[str]
    tone_requirement: str
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlatformSpecification:
    platform_id: PlatformId
    display_name: str
    primary_objective: str
    audience_behavior: str
    recommended_tones: list[str]
    structure: ContentStructure
    hook_guideline: HookGuideline
    cta_guideline: CtaGuideline
    constraints: list[str]
    best_practices: list[str]
    policy_guidelines: list[str]
