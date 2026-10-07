"""Brave Web Search adapter for CP-2.

The adapter only requests Brave's search endpoint. It never follows result URLs,
does not persist evidence, and does not mark a result verified.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceNormalizer,
    EvidenceSourceType,
    EvidenceValidator,
)
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus


class BraveSearchProvider:
    """Translate Brave Web Search snippets into unverified Evidence records."""

    endpoint = "https://api.search.brave.com/res/v1/web/search"
    provider_name = "brave_search"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        max_results: int | None = None,
        max_excerpt_chars: int | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self.api_key = (api_key if api_key is not None else settings.BRAVE_SEARCH_API_KEY).strip()
        self.timeout_seconds = timeout_seconds or settings.EXTERNAL_RETRIEVAL_TIMEOUT_SECONDS
        self.max_results = max_results or settings.EXTERNAL_RETRIEVAL_MAX_RESULTS
        self.max_excerpt_chars = (
            max_excerpt_chars or settings.EXTERNAL_RETRIEVAL_MAX_EXCERPT_CHARS
        )
        self.max_retries = max_retries if max_retries is not None else settings.EXTERNAL_RETRIEVAL_MAX_RETRIES
        self.transport = transport
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def search(self, query: str, *, limit: int | None = None) -> SearchProviderResult:
        safe_query = " ".join((query or "").split())
        if not safe_query or len(safe_query) > 512:
            return SearchProviderResult(
                status=SearchProviderStatus.INVALID_REQUEST,
                message="Search query must contain 1 to 512 characters.",
            )
        if not self.api_key:
            return SearchProviderResult(
                status=SearchProviderStatus.NOT_CONFIGURED,
                message="Chưa cấu hình nguồn tìm kiếm dữ liệu xu hướng bên ngoài.",
            )

        result_limit = self._result_limit(limit)
        response_result = self._request(safe_query, result_limit)
        if isinstance(response_result, SearchProviderResult):
            return response_result

        try:
            payload = response_result.json()
        except ValueError:
            return SearchProviderResult(
                status=SearchProviderStatus.INVALID_RESPONSE,
                message="Search provider returned invalid JSON.",
            )

        if not isinstance(payload, dict):
            return SearchProviderResult(
                status=SearchProviderStatus.INVALID_RESPONSE,
                message="Search provider returned an invalid response structure.",
            )
        web = payload.get("web")
        if not isinstance(web, dict) or not isinstance(web.get("results"), list):
            return SearchProviderResult(
                status=SearchProviderStatus.INVALID_RESPONSE,
                message="Search provider returned an invalid result structure.",
            )

        raw_results = web["results"]
        if not raw_results:
            return SearchProviderResult(
                status=SearchProviderStatus.EMPTY,
                message="No search results were returned.",
                metadata={"provider": self.provider_name, "requested_limit": result_limit},
            )

        evidences, duplicates_removed, malformed_results = self._to_evidence(
            raw_results[:result_limit],
            query=safe_query,
        )
        metadata = {
            "provider": self.provider_name,
            "requested_limit": result_limit,
            "duplicates_removed": duplicates_removed,
            "malformed_results": malformed_results,
        }
        if evidences:
            return SearchProviderResult(
                status=SearchProviderStatus.SUCCESS,
                evidences=tuple(evidences),
                metadata=metadata,
            )
        return SearchProviderResult(
            status=SearchProviderStatus.INVALID_RESPONSE,
            message="Search provider returned no usable evidence.",
            metadata=metadata,
        )

    def _request(self, query: str, limit: int) -> httpx.Response | SearchProviderResult:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": limit}
        attempts = max(0, self.max_retries) + 1

        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                    response = client.get(self.endpoint, params=params, headers=headers)
            except httpx.TimeoutException:
                if attempt + 1 < attempts:
                    continue
                return SearchProviderResult(
                    status=SearchProviderStatus.TIMEOUT,
                    message="External search timed out.",
                )
            except httpx.TransportError:
                if attempt + 1 < attempts:
                    continue
                return SearchProviderResult(
                    status=SearchProviderStatus.NETWORK_ERROR,
                    message="Nguồn tìm kiếm dữ liệu xu hướng đang tạm thời không khả dụng.",
                )

            if response.status_code == 429:
                return SearchProviderResult(
                    status=SearchProviderStatus.QUOTA_EXCEEDED,
                    message="External search quota is unavailable.",
                    metadata={"http_status": response.status_code},
                )
            if response.status_code in {401, 403}:
                return SearchProviderResult(
                    status=SearchProviderStatus.AUTHENTICATION_ERROR,
                    message="External search authentication failed.",
                    metadata={"http_status": response.status_code},
                )
            if response.status_code >= 500 and attempt + 1 < attempts:
                continue
            if response.is_error:
                return SearchProviderResult(
                    status=SearchProviderStatus.HTTP_ERROR,
                    message="External search provider returned an error.",
                    metadata={"http_status": response.status_code},
                )
            return response

        return SearchProviderResult(
            status=SearchProviderStatus.NETWORK_ERROR,
            message="Nguồn tìm kiếm dữ liệu xu hướng đang tạm thời không khả dụng.",
        )

    def _result_limit(self, requested_limit: int | None) -> int:
        if not isinstance(requested_limit, int) or isinstance(requested_limit, bool):
            return self.max_results
        return max(1, min(requested_limit, self.max_results))

    def _to_evidence(
        self,
        raw_results: list[Any],
        *,
        query: str,
    ) -> tuple[list[Evidence], int, int]:
        normalizer = EvidenceNormalizer()
        validator = EvidenceValidator()
        evidences: list[Evidence] = []
        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()
        seen_urls: set[str] = set()
        duplicates_removed = 0
        malformed_results = 0
        retrieved_at = self.clock()

        for rank, raw_result in enumerate(raw_results, start=1):
            if not isinstance(raw_result, dict):
                malformed_results += 1
                continue
            title = raw_result.get("title")
            url = raw_result.get("url")
            excerpt = raw_result.get("description")
            if not all(isinstance(value, str) and value.strip() for value in (title, url, excerpt)):
                malformed_results += 1
                continue

            evidence_id = self._evidence_id(url, title)
            candidate = Evidence(
                evidence_id=evidence_id,
                title=title[:300],
                source_url=url,
                publisher=self._publisher(raw_result, url),
                retrieved_at=retrieved_at,
                excerpt=excerpt[: self.max_excerpt_chars],
                source_type=EvidenceSourceType.SEARCH_RESULT,
                metadata={
                    "provider": self.provider_name,
                    "retrieval_query": query,
                    "provider_rank": rank,
                },
            )
            normalized = normalizer.normalize(candidate)
            if not normalized.is_valid or normalized.evidence is None:
                malformed_results += 1
                continue
            validation = validator.validate(normalized.evidence, now=retrieved_at)
            if not validation.is_valid:
                malformed_results += 1
                continue

            evidence = normalized.evidence
            if (
                evidence.evidence_id in seen_ids
                or evidence.content_hash in seen_hashes
                or evidence.source_url in seen_urls
            ):
                duplicates_removed += 1
                continue
            seen_ids.add(evidence.evidence_id)
            seen_hashes.add(evidence.content_hash or "")
            seen_urls.add(evidence.source_url)
            evidences.append(evidence)

        return evidences, duplicates_removed, malformed_results

    @staticmethod
    def _evidence_id(url: str, title: str) -> str:
        fingerprint = f"{url}\n{title}".encode("utf-8")
        return f"brave:{sha256(fingerprint).hexdigest()[:24]}"

    @staticmethod
    def _publisher(raw_result: dict[str, Any], url: str) -> str:
        profile = raw_result.get("profile")
        if isinstance(profile, dict):
            long_name = profile.get("long_name")
            if isinstance(long_name, str) and long_name.strip():
                return long_name.strip()
        return urlsplit(url).hostname or "unknown publisher"
