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

  assert.equal(getProviderStatusPresentation({ provider_status: "partial", evidences: [{}, {}] }).tone, "warning");
  assert.equal(cards.find((card) => card.source === "healthy").tone, "success");
  assert.equal(cards.find((card) => card.source === "failed").tone, "failure");
});

test("maps CP-10A RSS result states without guessing legacy empty reasons", () => {
  const states = [
    ["no_valid_entries", "Nguồn chưa có bài viết hợp lệ"],
    ["no_topic_matches", "Có bài viết nhưng không khớp chủ đề"],
    ["success", "Đã tìm thấy bài phù hợp"],
    ["timeout", "Nguồn hết thời gian chờ"],
    ["invalid_response", "Không thể đọc dữ liệu nguồn"],
    ["unknown", "Chưa xác định được nguyên nhân"],
  ];
  for (const [result_state, label] of states) {
    const status = result_state === "no_valid_entries" || result_state === "no_topic_matches" || result_state === "unknown" ? "empty" : result_state;
    const [card] = buildSourceStatusCards({ source_statuses: [{ source: "Báo Thanh Niên", status, result_state }] });
    assert.equal(card.label, label);
    assert.equal(card.source, "Báo Thanh Niên");
  }
  const [legacy] = buildSourceStatusCards({ source_statuses: [{ source: "Old RSS", status: "empty" }] });
  assert.equal(legacy.resultState, "unknown");
  assert.equal(legacy.label, "Chưa xác định được nguyên nhân");
  assert.equal(legacy.entriesChecked, null);
});

test("keeps measured counts separate from persisted evidence count", () => {
  const [card] = buildSourceStatusCards({ source_statuses: [{
    source: "RSS", status: "success", result_state: "success",
    entries_checked: 8, valid_entries: 6, matched_entries: 3, evidence_count: 2,
  }] });
  assert.equal(card.entriesChecked, 8);
  assert.equal(card.validEntries, 6);
  assert.equal(card.matchedEntries, 3);
  assert.equal(card.evidenceCount, 2);
});

test("renders mixed all-source failure status as a provider failure", () => {
  assert.equal(
    getProviderStatusPresentation({ provider_status: "failed", evidences: [] }).tone,
    "failure",
  );
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
    { tone: "empty", label: "Chưa có kết quả RSS phù hợp" },
  );
  assert.deepEqual(
    getSourceStatusPresentation({ status: "not_configured", evidenceCount: 0 }),
    { tone: "empty", label: "Chưa cấu hình" },
  );
});
