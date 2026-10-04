"""Intent Gate for deciding whether a request needs external retrieval.

This module deliberately only decides intent. It does not make network calls,
select providers, or claim that external information has been verified.
"""

from dataclasses import dataclass
from enum import Enum
import re


class ExternalRetrievalDecision(str, Enum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"


@dataclass(frozen=True)
class RetrievalIntent:
    """Result of classifying a user request for external information needs."""

    decision: ExternalRetrievalDecision
    reason_codes: tuple[str, ...] = ()
    matched_signals: tuple[str, ...] = ()

    @property
    def should_retrieve(self) -> bool:
        return self.decision is ExternalRetrievalDecision.REQUIRED


class ExternalRetrievalIntentGate:
    """Classify retrieval intent without treating platform names as triggers."""

    _SIGNAL_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
        (
            "explicit_lookup",
            (
                ("tìm kiếm", r"\btìm\s+kiếm\b"),
                ("tra cứu", r"\btra\s+cứu\b"),
                ("tìm xu hướng", r"\btìm\s+(?:xu\s+hướng|trend(?:s)?)\b"),
                ("tìm trend", r"\btìm\s+trend(?:s)?\b"),
                ("tìm thông tin", r"\btìm\s+(?:thông\s+tin|hiểu\s+thêm)\b"),
                ("search", r"\b(?:search|look\s+up|research)\b"),
            ),
        ),
        (
            "source_request",
            (
                ("dẫn nguồn", r"\bdẫn\s+nguồn\b"),
                ("trích nguồn", r"\btrích\s+(?:nguồn|dẫn)\b"),
                ("nguồn tham khảo", r"\bnguồn\s+tham\s+khảo\b"),
                ("nguồn đáng tin", r"\bnguồn\s+(?:đáng\s+tin|chính\s+thức)\b"),
                ("citation", r"\b(?:citation|cite|evidence)\b"),
            ),
        ),
        (
            "verification_request",
            (
                ("kiểm chứng", r"\bkiểm\s+chứng\b"),
                ("xác minh", r"\bxác\s+minh\b"),
                ("kiểm tra thông tin", r"\bkiểm\s+tra\s+(?:thông\s+tin|công\s+dụng|nguồn\s+gốc|chứng\s+nhận)\b"),
                ("được chứng minh", r"\bđược\s+chứng\s+minh\b"),
            ),
        ),
        (
            "trend_request",
            (
                ("xu hướng", r"\bxu\s+hướng\b"),
                ("trend", r"\btrend(?:s)?\b"),
                ("đang hot", r"\bđang\s+hot\b"),
                ("đang nổi", r"\bđang\s+nổi\b"),
                ("viral", r"\bviral\b"),
            ),
        ),
        (
            "market_analysis",
            (
                ("phân tích thị trường", r"\bphân\s+tích\s+thị\s+trường\b"),
                ("nghiên cứu thị trường", r"\bnghiên\s+cứu\s+thị\s+trường\b"),
                ("nhu cầu thị trường", r"\bnhu\s+cầu\s+thị\s+trường\b"),
            ),
        ),
        (
            "analysis_action",
            (
                ("phân tích", r"\bphân\s+tích\b"),
                ("nghiên cứu", r"\bnghiên\s+cứu\b"),
            ),
        ),
        (
            "freshness_request",
            (
                ("mới nhất", r"\bmới\s+nhất\b"),
                ("hiện nay", r"\bhiện\s+nay\b"),
                ("hiện tại", r"\bhiện\s+tại\b"),
                ("tháng này", r"\btháng\s+này\b"),
                ("gần đây", r"\bgần\s+đây\b"),
                ("cập nhật", r"\bcập\s+nhật\b"),
            ),
        ),
    )

    @classmethod
    def _normalize(cls, user_text: str | None) -> str:
        return re.sub(r"\s+", " ", (user_text or "").strip().lower())

    @classmethod
    def decide(cls, user_text: str | None) -> RetrievalIntent:
        text = cls._normalize(user_text)
        if not text:
            return RetrievalIntent(ExternalRetrievalDecision.NOT_REQUIRED)

        matched_groups: list[str] = []
        matched_signals: list[str] = []
        for group, patterns in cls._SIGNAL_GROUPS:
            group_matches = [
                label for label, pattern in patterns if re.search(pattern, text, re.IGNORECASE)
            ]
            if group_matches:
                matched_groups.append(group)
                matched_signals.extend(group_matches)

        retrieval_groups = {
            "explicit_lookup",
            "source_request",
            "verification_request",
            "market_analysis",
        }
        matched_group_set = set(matched_groups)
        trend_requires_current_data = (
            "trend_request" in matched_group_set
            and (
                "freshness_request" in matched_group_set
                or "market_analysis" in matched_group_set
                or "analysis_action" in matched_group_set
            )
        )
        should_retrieve = bool(matched_group_set & retrieval_groups) or trend_requires_current_data
        decision = (
            ExternalRetrievalDecision.REQUIRED
            if should_retrieve
            else ExternalRetrievalDecision.NOT_REQUIRED
        )

        return RetrievalIntent(
            decision=decision,
            reason_codes=tuple(matched_groups),
            matched_signals=tuple(dict.fromkeys(matched_signals)),
        )


external_retrieval_intent_gate = ExternalRetrievalIntentGate()
