import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSourceStatusCards,
  getProviderStatusPresentation,
  getSourceStatusPresentation,
} from "../src/utils/trendReportSourceStatus.js";

test("builds source/platform cards from API data with cache and dedup details", () => {
  const report = {
    source_statuses: [
      {
        source: "api-source-a",
        platform: "platform-a",
        status: "success",
        evidence_count: 2,
        from_cache: true,
        deduplicated_evidence_ids: ["duplicate-a"],
      },
      {
        source: "api-source-b",
        platform: "platform-b",
        status: "timeout",
        message: "Injected provider timeout",
        evidence_count: 0,
      },
    ],
  };

  const cards = buildSourceStatusCards(report);

  assert.deepEqual(cards.map((card) => [card.source, card.platform]), [
    ["api-source-a", "platform-a"],
    ["api-source-b", "platform-b"],
  ]);
  assert.equal(cards[0].tone, "success");
  assert.equal(cards[0].fromCache, true);
  assert.deepEqual(cards[0].deduplicatedEvidenceIds, ["duplicate-a"]);
  assert.equal(cards[1].tone, "failure");
  assert.equal(cards[1].message, "Injected provider timeout");
});

test("keeps successful sources visible when provider status is partial", () => {
  const cards = buildSourceStatusCards({
    provider_status: "partial",
    evidences: [{ evidence_id: "fresh" }],
    source_statuses: [
      { source: "healthy", platform: "healthy", status: "success", evidence_count: 1 },
      { source: "failed", platform: "failed", status: "network_error", evidence_count: 0 },
    ],
  });

  assert.equal(getProviderStatusPresentation({ provider_status: "partial", evidences: [{}, {}] }).tone, "failure");
  assert.equal(cards.find((card) => card.source === "healthy").tone, "success");
  assert.equal(cards.find((card) => card.source === "failed").tone, "failure");
});

test("renders stale and conflicting evidence as distinct statuses", () => {
  assert.deepEqual(
    getSourceStatusPresentation({ status: "stale", evidenceCount: 1 }),
    { tone: "stale", label: "Dữ liệu đã cũ" },
  );
  assert.deepEqual(
    getSourceStatusPresentation({ status: "conflicting", evidenceCount: 1 }),
    { tone: "conflicting", label: "Bằng chứng mâu thuẫn" },
  );
  assert.deepEqual(
    getSourceStatusPresentation({ status: "partial", evidenceCount: 1 }),
    { tone: "warning", label: "Bằng chứng một phần" },
  );
});

test("renders empty and not-configured responses without inventing sources", () => {
  assert.deepEqual(buildSourceStatusCards({ source_statuses: [] }), []);
  assert.deepEqual(
    getProviderStatusPresentation({ provider_status: "success", evidences: [] }),
    { tone: "empty", label: "Không có bằng chứng" },
  );
  assert.deepEqual(
    getSourceStatusPresentation({ status: "not_configured", evidenceCount: 0 }),
    { tone: "empty", label: "Chưa cấu hình" },
  );
});
