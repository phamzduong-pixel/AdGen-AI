"""Regression tests for CP-3 citation validation during streaming."""

import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.services import ai_service
from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.services.output_validator.models import ValidationResult
from tests.dataset_writer_isolation import block_ai_writer


def evidence_result():
    evidence = Evidence(
        evidence_id="stream-source",
        title="Source",
        source_url="https://example.com/source",
        publisher="Example",
        retrieved_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        excerpt="Reference excerpt.",
        source_type=EvidenceSourceType.SEARCH_RESULT,
    )
    return SearchProviderResult(
        status=SearchProviderStatus.SUCCESS,
        evidences=(evidence,),
    )


class FakeModels:
    def __init__(self, chunks):
        self.chunks = chunks

    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text=chunk) for chunk in self.chunks]


class StreamingCitationValidationTests(unittest.TestCase):
    def stream(self, chunks):
        text = "".join(chunks)
        valid = ValidationResult(is_valid=True, sanitized_content=text, issues=[])
        return patch.object(
            ai_service,
            "client",
            types.SimpleNamespace(models=FakeModels(chunks)),
        ), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=valid,
        )

    @block_ai_writer
    def test_valid_citation_split_across_chunks_is_preserved(self):
        client_patch, validation_patch = self.stream(["Trend signal [S", "1] remains unverified."])

        with client_patch, validation_patch:
            output = "".join(
                ai_service.stream_ai(
                    [{"role": "user", "content": "Research current trend"}],
                    external_retrieval_requested=True,
                    external_retrieval_result=evidence_result(),
                )
            )

        self.assertEqual(output, "Trend signal [S1] remains unverified.")

    def test_invalid_citation_is_not_yielded_before_stream_fails(self):
        client_patch, validation_patch = self.stream(["Unsupported claim [S9] rest"])

        with client_patch, validation_patch:
            generator = ai_service.stream_ai(
                [{"role": "user", "content": "Research current trend"}],
                external_retrieval_requested=True,
                external_retrieval_result=evidence_result(),
            )
            yielded = []
            with self.assertRaisesRegex(RuntimeError, "citation IDs"):
                while True:
                    yielded.append(next(generator))

        self.assertEqual(yielded, [])


if __name__ == "__main__":
    unittest.main()
