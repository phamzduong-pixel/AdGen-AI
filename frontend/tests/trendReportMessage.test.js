import assert from "node:assert/strict";
import test from "node:test";

import { presentTrendMessage } from "../src/utils/trendReportMessage.js";

test("describes an unconfigured collector as missing RSS sources", () => {
  assert.equal(
    presentTrendMessage("No retrieval collectors are configured"),
    "Chưa cấu hình nguồn RSS, nên chưa thể tìm bài báo mới cho chủ đề này.",
  );
});

test("keeps generic external errors neutral about trends", () => {
  assert.equal(
    presentTrendMessage("External service failed"),
    "Nguồn dữ liệu bên ngoài không trả về thông tin có thể sử dụng. Vui lòng thử lại hoặc kiểm tra cấu hình nguồn.",
  );
});

test("presents monitoring alerts without claiming a social trend", () => {
  assert.equal(
    presentTrendMessage("Trend snack food detected."),
    "Đã ghi nhận tín hiệu theo dõi: snack food.",
  );
});
