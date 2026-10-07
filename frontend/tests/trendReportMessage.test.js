import assert from "node:assert/strict";
import test from "node:test";

import { presentTrendMessage, presentTrustRationale } from "../src/utils/trendReportMessage.js";

test("translates persisted Trend Radar retrieval caveats into user-facing Vietnamese", () => {
  assert.equal(
    presentTrendMessage("No retrieval collectors are configured; insufficient evidence/data."),
    "Chưa cấu hình nguồn thu thập dữ liệu xu hướng, nên hệ thống chưa thể thu thập dữ liệu mới cho chủ đề này.",
  );
  assert.equal(
    presentTrendMessage("External retrieval was not usable (status: not_configured). No fresh source-backed fact or statistic is available."),
    "Không thể sử dụng nguồn dữ liệu xu hướng bên ngoài. Hiện chưa có dữ liệu mới từ nguồn đáng tin cậy để hiển thị.",
  );
});

test("translates trust rationales without changing the trust action or status", () => {
  assert.equal(
    presentTrustRationale("only stale evidence was explicitly related to this claim"),
    "Chỉ có bằng chứng đã cũ liên quan đến claim này.",
  );
  assert.equal(presentTrustRationale("Thông điệp đã Việt hóa."), "Thông điệp đã Việt hóa.");
});
