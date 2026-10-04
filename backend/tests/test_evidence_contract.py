"""Unit tests for the CP-1 Evidence Contract."""

import unittest
from datetime import datetime, timezone, timedelta

from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceDeduplicator,
    EvidenceIssueCode,
    EvidenceNormalizer,
    EvidenceSourceType,
    EvidenceVerificationStatus,
    EvidenceValidator,
)


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = EvidenceNormalizer()
        self.validator = EvidenceValidator()
        self.now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    def make_evidence(self, **overrides):
        values = {
            "evidence_id": "ev-001",
            "title": "Market report",
            "source_url": "https://Example.com:443/report#section",
            "publisher": "Example Research",
            "retrieved_at": "2026-10-05T12:00:00Z",
            "excerpt": "  Product demand increased.\n  This is the source excerpt. ",
            "source_type": EvidenceSourceType.MARKET_DATA,
        }
        values.update(overrides)
        return Evidence(**values)

    def normalize(self, evidence):
        result = self.normalizer.normalize(evidence)
        self.assertTrue(result.evidence is not None, result.issues)
        return result.evidence

    def test_valid_evidence_is_normalized_and_remains_unverified(self):
        evidence = self.normalize(self.make_evidence())
        result = self.validator.validate(evidence, now=self.now)

        self.assertTrue(result.is_valid)
        self.assertEqual(evidence.source_url, "https://example.com/report")
        self.assertEqual(evidence.retrieved_at.tzinfo, timezone.utc)
        self.assertEqual(len(evidence.content_hash), 64)
        self.assertEqual(
            evidence.verification_status,
            EvidenceVerificationStatus.UNVERIFIED,
        )
        self.assertIsNone(evidence.confidence)

    def test_missing_required_url_is_rejected(self):
        result = self.normalizer.normalize(self.make_evidence(source_url=""))

        self.assertFalse(result.is_valid)
        self.assertIsNone(result.evidence)
        self.assertIn(
            EvidenceIssueCode.MISSING_REQUIRED_FIELD,
            {issue.code for issue in result.issues},
        )

    def test_missing_required_metadata_is_rejected(self):
        for field_name in ("title", "publisher", "excerpt", "retrieved_at", "source_type"):
            with self.subTest(field=field_name):
                result = self.normalizer.normalize(self.make_evidence(**{field_name: None}))
                self.assertFalse(result.is_valid)
                self.assertIn(
                    EvidenceIssueCode.MISSING_REQUIRED_FIELD,
                    {issue.code for issue in result.issues},
                )

    def test_unknown_published_at_is_allowed(self):
        evidence = self.normalize(self.make_evidence(published_at=None))
        result = self.validator.validate(evidence, now=self.now)

        self.assertTrue(result.is_valid)
        self.assertIsNone(evidence.published_at)
        self.assertIsNone(result.stale_by_days)

    def test_invalid_datetime_is_rejected(self):
        result = self.normalizer.normalize(
            self.make_evidence(retrieved_at="not-a-date")
        )

        self.assertFalse(result.is_valid)
        self.assertIn(
            EvidenceIssueCode.INVALID_DATETIME,
            {issue.code for issue in result.issues},
        )

    def test_unsupported_or_malformed_url_is_rejected(self):
        for url in ("ftp://example.com/file", "javascript:alert(1)", "/relative/path"):
            with self.subTest(url=url):
                result = self.normalizer.normalize(self.make_evidence(source_url=url))
                self.assertFalse(result.is_valid)
                self.assertTrue(
                    {issue.code for issue in result.issues}
                    & {
                        EvidenceIssueCode.INVALID_URL,
                        EvidenceIssueCode.UNSUPPORTED_URL_SCHEME,
                    }
                )

    def test_same_normalized_excerpt_is_detected_as_duplicate(self):
        first = self.normalize(self.make_evidence())
        second = self.normalize(
            self.make_evidence(
                evidence_id="ev-002",
                source_url="https://another.example/source",
                excerpt="Product demand increased. This is the source excerpt.",
            )
        )

        groups = EvidenceDeduplicator.duplicate_groups([first, second])

        self.assertEqual(len(groups), 1)
        self.assertEqual({item.evidence_id for item in groups[0]}, {"ev-001", "ev-002"})

    def test_same_evidence_id_is_detected_even_with_different_content(self):
        first = self.normalize(self.make_evidence())
        second = self.normalize(
            self.make_evidence(
                source_url="https://another.example/source",
                excerpt="A different excerpt with the same record identifier.",
            )
        )

        groups = EvidenceDeduplicator.duplicate_groups([first, second])

        self.assertEqual(len(groups), 1)
        self.assertEqual({item.evidence_id for item in groups[0]}, {"ev-001"})

    def test_old_evidence_is_marked_stale_without_being_deleted(self):
        evidence = self.normalize(
            self.make_evidence(published_at="2026-08-01T12:00:00Z")
        )
        result = self.validator.validate(evidence, now=self.now, max_age_days=30)

        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_stale)
        self.assertEqual(result.status, EvidenceVerificationStatus.STALE)
        self.assertTrue(any(not issue.fatal for issue in result.issues))
        self.assertEqual(evidence.evidence_id, "ev-001")

    def test_verified_status_requires_explicit_basis(self):
        evidence = self.normalize(
            self.make_evidence(
                verification_status=EvidenceVerificationStatus.VERIFIED,
            )
        )
        result = self.validator.validate(evidence, now=self.now)

        self.assertFalse(result.is_valid)
        self.assertIn(
            EvidenceIssueCode.VERIFIED_REQUIRES_BASIS,
            {issue.code for issue in result.issues},
        )

    def test_confidence_requires_basis_and_valid_range(self):
        without_basis = self.normalize(self.make_evidence(confidence=0.8))
        missing_basis_result = self.validator.validate(without_basis, now=self.now)
        self.assertFalse(missing_basis_result.is_valid)
        self.assertIn(
            EvidenceIssueCode.CONFIDENCE_REQUIRES_BASIS,
            {issue.code for issue in missing_basis_result.issues},
        )

        with_basis = self.normalize(
            self.make_evidence(
                confidence=0.8,
                metadata={"confidence_basis": "Two independent reports"},
            )
        )
        valid_result = self.validator.validate(with_basis, now=self.now)
        self.assertTrue(valid_result.is_valid)

        out_of_range = self.normalize(self.make_evidence(confidence=1.1))
        invalid_result = self.validator.validate(out_of_range, now=self.now)
        self.assertFalse(invalid_result.is_valid)
        self.assertIn(
            EvidenceIssueCode.INVALID_CONFIDENCE,
            {issue.code for issue in invalid_result.issues},
        )

    def test_supplied_hash_must_match_normalized_excerpt(self):
        result = self.normalizer.normalize(self.make_evidence(content_hash="0" * 64))

        self.assertFalse(result.is_valid)
        self.assertIn(
            EvidenceIssueCode.CONTENT_HASH_MISMATCH,
            {issue.code for issue in result.issues},
        )


if __name__ == "__main__":
    unittest.main()
