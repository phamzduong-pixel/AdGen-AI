import test from "node:test";
import assert from "node:assert/strict";

import {
  buildConversationalEditRequest,
  createIdempotencyKey,
  reuseIdempotencyKey,
  getConversationalOperationNames,
  getConversationalExecutionOutcome,
} from "../src/utils/conversationalEdit.js";

test("builds a safe conversational edit request", () => {
  assert.deepEqual(
    buildConversationalEditRequest("  trim video  ", [3, 3, 0, -1, 4.5, 7]),
    { instruction: "trim video", merge_source_asset_ids: [3, 7] },
  );
});

test("maps only structured plan operation names for the UI", () => {
  assert.deepEqual(
    getConversationalOperationNames({ operations: [{ operation: "trim" }, { operation: "cta_overlay" }] }),
    ["trim", "cta_overlay"],
  );
  assert.deepEqual(getConversationalOperationNames(null), []);
});

test("maps partial execution to the latest recoverable asset", () => {
  assert.deepEqual(
    getConversationalExecutionOutcome({
      status: "partial",
      failed_operation: "text_overlay",
      error: "Operation failed; previous versions were kept.",
      created_assets: [{ id: 11 }, { id: 12 }],
    }),
    {
      status: "partial",
      latestAssetId: 12,
      createdAssetCount: 2,
      createdAssets: [{ id: 11 }, { id: 12 }],
      failedOperation: "text_overlay",
      failedOperationIndex: null,
      message: "Operation failed; previous versions were kept.",
    },
  );
});

test("keeps the source selected when the first operation fails", () => {
  assert.deepEqual(
    getConversationalExecutionOutcome({ status: "failed", created_assets: [] }),
    {
      status: "failed",
      latestAssetId: null,
      createdAssetCount: 0,
      createdAssets: [],
      failedOperation: null,
      failedOperationIndex: null,
      message: "Không thể hoàn thành kế hoạch chỉnh sửa video.",
    },
  );
});
test("maps the failed operation index and preserves completed assets", () => {
  const createdAssets = [{ id: 21, status: "completed" }, { id: 22, status: "failed" }];
  assert.deepEqual(
    getConversationalExecutionOutcome({
      status: "partial",
      failed_operation: "text_overlay",
      failed_operation_index: 1,
      error: "partial recovery",
      created_assets: createdAssets,
    }),
    {
      status: "partial",
      latestAssetId: 21,
      createdAssetCount: 2,
      createdAssets,
      failedOperation: "text_overlay",
      failedOperationIndex: 1,
      message: "partial recovery",
    },
  );
});
test("reuses an idempotency key for the same execution and creates a new one when requested", () => {
  const first = createIdempotencyKey();
  assert.equal(typeof first, "string");
  assert.ok(first.length > 0);
  assert.equal(reuseIdempotencyKey(first), first);
  const next = reuseIdempotencyKey(null);
  assert.notEqual(next, first);
  assert.ok(next.length > 0);
});

test("keeps processing status recoverable without selecting a failed asset", () => {
  assert.deepEqual(
    getConversationalExecutionOutcome({
      status: "processing",
      created_assets: [{ id: 31, status: "failed" }],
    }),
    {
      status: "processing",
      latestAssetId: null,
      createdAssetCount: 1,
      createdAssets: [{ id: 31, status: "failed" }],
      failedOperation: null,
      failedOperationIndex: null,
      message: "Yêu cầu vẫn đang được xử lý.",
    },
  );
});