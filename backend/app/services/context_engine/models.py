from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FollowUpIntentType(str, Enum):
    SHORTEN = "shorten"
    EXPAND = "expand"
    CHANGE_TONE = "change_tone"
    ADD_CTA = "add_cta"
    REWRITE = "rewrite"
    MULTI_VARIATION = "multi_variation"
    SWITCH_PLATFORM = "switch_platform"
    FIX_CONTENT = "fix_content"
    GENERAL_REFINEMENT = "general_refinement"
    GENERATE_VOICEOVER = "generate_voiceover"
    NEW_REQUEST = "new_request"


@dataclass
class ExtractedProductContext:
    product_name: str | None = None
    description: str | None = None
    target_audience: str | None = None
    price: str | None = None
    offer: str | None = None
    usp: str | None = None
    key_features: list[str] = field(default_factory=list)
    platform: str | None = None
    raw_brief: dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.product_name or self.description or self.raw_brief)


@dataclass
class FollowUpContext:
    intent: FollowUpIntentType
    target_platform: str | None = None
    target_tone: str | None = None
    variation_count: int | None = None
    specific_instruction: str = ""
    extracted_product: ExtractedProductContext = field(default_factory=ExtractedProductContext)
    last_assistant_content: str | None = None
