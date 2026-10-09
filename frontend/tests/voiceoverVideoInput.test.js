import test from "node:test";
import assert from "node:assert/strict";

import {
  VIDEO_MAX_SIZE_BYTES,
  formatVideoSize,
  getVideoExtension,
  validateVideoFile,
} from "../src/components/chat/VoiceoverModal/videoInput.js";

test("accepts the supported video extensions case-insensitively", () => {
  assert.equal(getVideoExtension("sample.MP4"), ".mp4");
  assert.equal(validateVideoFile({ name: "sample.MP4", size: 1024, type: "video/mp4" }), null);
  assert.equal(validateVideoFile({ name: "sample.MOV", size: 1024, type: "video/quicktime" }), null);
  assert.equal(validateVideoFile({ name: "sample.WEBM", size: 1024, type: "video/webm" }), null);
  assert.equal(validateVideoFile({ name: "sample.avi", size: 1024, type: "video/avi" })?.code, "UNSUPPORTED_EXTENSION");
});

test("rejects empty, oversized, and MIME-mismatched video files", () => {
  assert.equal(validateVideoFile(null)?.code, "NO_FILE");
  assert.equal(validateVideoFile({ name: "empty.mp4", size: 0, type: "video/mp4" })?.code, "EMPTY_FILE");
  assert.equal(
    validateVideoFile({ name: "large.mp4", size: VIDEO_MAX_SIZE_BYTES + 1, type: "video/mp4" })?.code,
    "FILE_TOO_LARGE",
  );
  assert.equal(validateVideoFile({ name: "spoofed.mp4", size: 1024, type: "text/plain" })?.code, "MIME_MISMATCH");
});

test("formats the displayed video size", () => {
  assert.equal(formatVideoSize(0), "0 B");
  assert.equal(formatVideoSize(1024), "1.0 KB");
  assert.equal(formatVideoSize(50 * 1024 * 1024), "50.0 MB");
});
