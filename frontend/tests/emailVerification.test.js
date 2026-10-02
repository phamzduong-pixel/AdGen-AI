import assert from "node:assert/strict";
import test from "node:test";

import { maskEmail } from "../src/utils/emailVerification.js";

test("email verification masks the local part but keeps the domain", () => {
  assert.equal(maskEmail("phamduong@gmail.com"), "ph*******@gmail.com");
  assert.equal(maskEmail("a@example.com"), "a**@example.com");
});
