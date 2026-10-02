import test from "node:test";
import assert from "node:assert/strict";

import {
  getVideoJobErrorMessage,
  isVideoJobPending,
  pollVideoJob,
} from "../src/utils/mediaJob.js";

test("polls processing job until completed without creating another job", async () => {
  const updates = [];
  const requests = [];
  const result = await pollVideoJob({
    initialJob: { id: 7, status: "processing" },
    fetchJob: async (id) => {
      requests.push(id);
      return { id, status: "completed", output_asset_id: 41 };
    },
    onUpdate: (job) => updates.push(job.status),
    wait: async () => {},
  });

  assert.deepEqual(requests, [7]);
  assert.deepEqual(updates, ["processing", "completed"]);
  assert.equal(result.output_asset_id, 41);
});

test("maps provider quota error to a friendly message", () => {
  const message = getVideoJobErrorMessage({
    status: "failed",
    error_message: "Gemini submit failed (429 RESOURCE_EXHAUSTED)",
  });
  assert.match(message, /quota|rate limit/i);
  assert.doesNotMatch(message, /RESOURCE_EXHAUSTED/);
});

test("polling stops when the UI is unmounted", async () => {
  let calls = 0;
  let cancelled = false;
  const result = await pollVideoJob({
    initialJob: { id: 9, status: "processing" },
    fetchJob: async () => {
      calls += 1;
      return { id: 9, status: "processing" };
    },
    wait: async () => { cancelled = true; },
    isCancelled: () => cancelled,
  });

  assert.equal(calls, 0);
  assert.equal(result.status, "processing");
  assert.equal(isVideoJobPending(result), true);
});
