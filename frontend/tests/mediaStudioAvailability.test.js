import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("../src/components/chat/MediaStudio/MediaStudio.jsx", import.meta.url), "utf8");

test("Media Studio keeps a visible development notice and disables creation actions", () => {
  assert.match(source, /const MEDIA_STUDIO_IN_DEVELOPMENT = true;/);
  assert.match(source, /media-studio__development[\s\S]*?Đang phát triển[\s\S]*?chưa sẵn sàng sử dụng/);
  assert.match(source, /onClick=\{handleGenerateImage\} disabled=\{MEDIA_STUDIO_IN_DEVELOPMENT \|\|/);
  assert.match(source, /onClick=\{handleGenerateVideo\} disabled=\{MEDIA_STUDIO_IN_DEVELOPMENT \|\|/);
  assert.match(source, /onClick=\{onExecute\} disabled=\{isUnavailable \|\| isBusy/);
  assert.match(source, /onClick=\{onPlan\} disabled=\{isUnavailable \|\|/);
  assert.match(source, /if \(MEDIA_STUDIO_IN_DEVELOPMENT \|\| !prompt\.trim\(\) \|\| isBusy\) return;/);
  assert.match(source, /if \(MEDIA_STUDIO_IN_DEVELOPMENT \|\| !videoGenerationPrompt\.trim\(\) \|\| isBusy\) return;/);
});
