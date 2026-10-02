from __future__ import annotations

import re

SUPPORTED_PLATFORM_TYPES = (
    "facebook",
    "tiktok",
    "instagram",
    "shopee",
    "google_ads",
    "other",
)

SUPPORTED_PLATFORM_LABELS = {
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "shopee": "Shopee",
    "google_ads": "Google Ads",
    "other": "Khác",
}

# Kept only so previously stored conversations/templates can still be opened.
LEGACY_PLATFORM_TYPES = (
    "youtube",
    "email",
    "landing_page",
    "seo",
    "slogan",
    "rewrite",
    "summarize",
)

CUSTOM_PLATFORM_MIN_LENGTH = 2
CUSTOM_PLATFORM_MAX_LENGTH = 80


def normalize_custom_platform_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized or None


def is_current_platform(value: str | None) -> bool:
    return bool(value and value.strip().lower() in SUPPORTED_PLATFORM_TYPES)


def is_legacy_platform(value: str | None) -> bool:
    return bool(value and value.strip().lower() in LEGACY_PLATFORM_TYPES)


def platform_label(platform: str | None, custom_name: str | None = None) -> str:
    normalized = (platform or "").strip().lower()
    if normalized == "other":
        return custom_name or SUPPORTED_PLATFORM_LABELS["other"]
    return SUPPORTED_PLATFORM_LABELS.get(normalized, platform or "Nội dung chung")
