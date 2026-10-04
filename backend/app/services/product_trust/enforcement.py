"""Deterministic output controls for assessed product claims.

This module deliberately enforces only claims that can be located exactly in
model output.  It does not infer semantic equivalence or product truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.services.product_trust.models import ClaimAssessment, ProductClaim, RecommendedAction


ACTION_PRIORITY = {
    RecommendedAction.ALLOW.value: 0,
    RecommendedAction.SOFTEN.value: 1,
    RecommendedAction.ASK_USER.value: 2,
    RecommendedAction.BLOCK.value: 3,
}
SAFE_SOFTENED_TEXT = "thông tin này cần được kiểm tra thêm"
ASK_USER_RESPONSE = (
    "Để tạo nội dung quảng cáo đáng tin cậy, vui lòng cung cấp nguồn hoặc tài liệu "
    "kiểm chứng cho thông tin công dụng, chứng nhận hoặc kết quả sản phẩm bạn muốn nêu."
)


class ProductTrustPolicyError(RuntimeError):
    """Raised before a blocked claim is released to a caller."""


@dataclass(frozen=True)
class ProductTrustEnforcementResult:
    content: str
    action: RecommendedAction
    matched_claim_ids: tuple[str, ...] = ()
    softened_claim_ids: tuple[str, ...] = ()


def _action_value(value: RecommendedAction | str) -> RecommendedAction:
    return value if isinstance(value, RecommendedAction) else RecommendedAction(value)


def _claim_pattern(claim_text: str) -> re.Pattern[str]:
    # Treat whitespace formatting as insignificant, but require all supplied words.
    escaped = re.escape(claim_text.strip())
    return re.compile(escaped.replace(r"\ ", r"\s+"), re.IGNORECASE)


def _matching_pairs(
    content: str,
    pairs: Iterable[tuple[ProductClaim, ClaimAssessment]],
) -> list[tuple[ProductClaim, ClaimAssessment]]:
    return [
        (claim, assessment)
        for claim, assessment in pairs
        if claim.claim_id == assessment.claim_id and _claim_pattern(claim.claim_text).search(content)
    ]


def enforce_product_trust(
    content: str,
    pairs: Iterable[tuple[ProductClaim, ClaimAssessment]] | None,
) -> ProductTrustEnforcementResult:
    """Apply the strongest action among explicitly matched assessed claims.

    ``block`` rejects before output is released; ``ask_user`` replaces the
    generated response with a neutral clarification request; ``soften`` only
    replaces the exact matched claim.  Claims that cannot be matched exactly
    are intentionally left untouched rather than guessed at.
    """
    normalized_pairs = tuple(pairs or ())
    matches = _matching_pairs(content, normalized_pairs)
    if not matches:
        return ProductTrustEnforcementResult(content=content, action=RecommendedAction.ALLOW)

    strongest = max(
        (_action_value(assessment.recommended_action) for _, assessment in matches),
        key=lambda action: ACTION_PRIORITY[action.value],
    )
    matched_ids = tuple(claim.claim_id for claim, _ in matches)
    if strongest is RecommendedAction.BLOCK:
        raise ProductTrustPolicyError(
            "Product Trust blocked assessed claim(s): " + ", ".join(matched_ids)
        )
    if strongest is RecommendedAction.ASK_USER:
        return ProductTrustEnforcementResult(
            content=ASK_USER_RESPONSE,
            action=strongest,
            matched_claim_ids=matched_ids,
        )

    softened_ids: list[str] = []
    updated = content
    for claim, assessment in matches:
        if _action_value(assessment.recommended_action) is RecommendedAction.SOFTEN:
            updated, replacements = _claim_pattern(claim.claim_text).subn(
                SAFE_SOFTENED_TEXT, updated
            )
            if replacements:
                softened_ids.append(claim.claim_id)
    return ProductTrustEnforcementResult(
        content=updated,
        action=strongest,
        matched_claim_ids=matched_ids,
        softened_claim_ids=tuple(softened_ids),
    )
