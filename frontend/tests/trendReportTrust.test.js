import test from "node:test";
import assert from "node:assert/strict";
import { trustPresentation, trustWarning } from "../src/utils/trendReportTrust.js";

test("renders explicit trust labels and actions", () => {
  const claim = trustPresentation({ status: "contradicted", recommended_action: "block", risk_level: "high" });
  assert.equal(claim.label, "Mâu thuẫn");
  assert.equal(claim.tone, "block");
  assert.equal(claim.action, "block");
});

test("distinguishes caution, ask_user and block warnings", () => {
  assert.equal(trustPresentation({ status: "insufficient_evidence", recommended_action: "ask_user" }).tone, "caution");
  assert.equal(trustWarning({ requires_review: true }).tone, "caution");
  assert.equal(trustWarning({ blocking_claim_ids: ["claim-1"] }).tone, "block");
});
