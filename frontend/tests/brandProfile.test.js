import assert from "node:assert/strict";
import test from "node:test";

import {
  parseBrandList,
  validateBrandProfile,
} from "../src/utils/brandProfile.js";

test("brand list trims, removes empty values and duplicates", () => {
  assert.deepEqual(parseBrandList("AI, marketing, AI, , sáng tạo"), [
    "AI",
    "marketing",
    "sáng tạo",
  ]);
});

test("brand profile validates required name, URL and HEX colors", () => {
  const errors = validateBrandProfile({
    name: " ",
    website: "javascript:alert(1)",
    primary_color: "purple",
    secondary_color: "#14B8A6",
  });
  assert.ok(errors.name);
  assert.ok(errors.website);
  assert.ok(errors.primary_color);
  assert.equal(errors.secondary_color, undefined);
});

test("valid brand profile has no validation errors", () => {
  assert.deepEqual(
    validateBrandProfile({
      name: "DG Studio",
      website: "https://example.com",
      primary_color: "#4F46E5",
      secondary_color: "",
    }),
    {},
  );
});
