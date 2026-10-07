import assert from "node:assert/strict";
import test from "node:test";

import { actionPresentation, metricEntries, snapshotTone } from "../src/utils/stage4Workflow.js";

test("maps backend trust actions without upgrading blocked or ask-user states", () => {
  assert.equal(actionPresentation("allow").canCreate, true);
  assert.equal(actionPresentation("soften").canCreate, true);
  assert.equal(actionPresentation("ask_user").canCreate, false);
  assert.equal(actionPresentation("block").canCreate, false);
});

test("renders only supplied metric keys and preserves empty payload", () => {
  assert.deepEqual(metricEntries({ clicks: 4, ctr: 0.2 }), [["clicks", 4], ["ctr", 0.2]]);
  assert.deepEqual(metricEntries({}), []);
  assert.deepEqual(metricEntries(null), []);
});

test("keeps success, empty and error snapshots distinct", () => {
  assert.equal(snapshotTone("success"), "success");
  assert.equal(snapshotTone("empty"), "empty");
  assert.equal(snapshotTone("error"), "error");
});
