import assert from "node:assert/strict";
import test from "node:test";

import { formatReportDate, reportOverview, requestReportHistory, requestTopicSearch, safeArticleUrl } from "../src/utils/trendReportView.js";

test("does not invent optional metrics or dates for legacy reports", () => {
  assert.deepEqual(reportOverview({}), {
    articleCount: null, publisherCount: null, newestArticleAt: null,
    topicClusters: [], evidences: [],
  });
  assert.equal(formatReportDate(null), "Chưa có dữ liệu");
  assert.equal(formatReportDate("invalid date"), "Chưa có dữ liệu");
  assert.equal(reportOverview({ article_count: 0, publisher_count: 1 }).articleCount, 0);
});

test("treats article publication and collection timestamps as independent fields", () => {
  const [article] = reportOverview({ evidences: [{
    published_at: "2026-01-01T00:00:00Z",
    retrieved_at: "2026-10-14T00:00:00Z",
  }] }).evidences;
  assert.notEqual(formatReportDate(article.published_at), formatReportDate(article.retrieved_at));
});

test("accepts only safe original article links", () => {
  assert.equal(safeArticleUrl("https://thanhnien.vn/example.html"), "https://thanhnien.vn/example.html");
  assert.equal(safeArticleUrl("http://example.org/article"), "http://example.org/article");
  for (const value of ["javascript:alert(1)", "data:text/html,test", "/relative", "https://user:pass@example.org/x", "bad url", null]) {
    assert.equal(safeArticleUrl(value), null);
  }
});

test("search and history actions call their separate APIs", async () => {
  const calls = [];
  const retrieve = async (payload) => { calls.push(["retrieve", payload]); return { report_id: "one" }; };
  const list = async () => { calls.push(["history"]); return [{ report_id: "one" }]; };
  assert.deepEqual(await requestTopicSearch(retrieve, "đồ ăn vặt", "13"), { report_id: "one" });
  assert.deepEqual(await requestReportHistory(list), [{ report_id: "one" }]);
  assert.deepEqual(calls, [
    ["retrieve", { query: "đồ ăn vặt", conversation_id: 13 }],
    ["history"],
  ]);
});
