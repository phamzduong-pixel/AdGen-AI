import assert from "node:assert/strict";
import test from "node:test";

import {
  isNearBottom,
  SCROLL_FOLLOW_THRESHOLD,
} from "../src/utils/messageListScroll.js";

const makeContainer = (scrollTop) => ({
  scrollHeight: 1800,
  clientHeight: 600,
  scrollTop,
});

test("considers the reader to be following when within the bottom threshold", () => {
  assert.equal(SCROLL_FOLLOW_THRESHOLD, 80);
  assert.equal(isNearBottom(makeContainer(1120)), true);
  assert.equal(isNearBottom(makeContainer(1119)), false);
});

test("does not follow when the reader is viewing the middle or top of history", () => {
  assert.equal(isNearBottom(makeContainer(600)), false);
  assert.equal(isNearBottom(makeContainer(0)), false);
});

test("treats a non-scrollable message list as being at the bottom", () => {
  assert.equal(
    isNearBottom({ scrollHeight: 500, clientHeight: 600, scrollTop: 0 }),
    true,
  );
  assert.equal(isNearBottom(null), false);
});
