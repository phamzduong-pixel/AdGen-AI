import test from "node:test";
import assert from "node:assert/strict";

import {
  getVoiceFileKind,
  validateVoiceFile,
  VOICE_FILE_ACCEPT,
} from "../src/components/chat/VoiceoverModal/fileInput.js";

test("routes unambiguous audio and video formats to their existing STT pipelines", () => {
  assert.equal(getVoiceFileKind({ name: "voice.mp3", size: 1024, type: "audio/mpeg" }), "audio");
  assert.equal(getVoiceFileKind({ name: "clip.MOV", size: 1024, type: "video/quicktime" }), "video");
  assert.equal(validateVoiceFile({ name: "voice.mp3", size: 1024, type: "audio/mpeg" }).error, null);
  assert.equal(validateVoiceFile({ name: "clip.mp4", size: 1024, type: "video/mp4" }).error, null);
});

test("routes WEBM by MIME hint and refuses ambiguous WEBM instead of guessing", () => {
  assert.equal(getVoiceFileKind({ name: "voice.webm", size: 1024, type: "audio/webm" }), "audio");
  assert.equal(getVoiceFileKind({ name: "clip.webm", size: 1024, type: "video/webm" }), "video");
  assert.equal(
    validateVoiceFile({ name: "unknown.webm", size: 1024, type: "" }).error?.code,
    "AMBIGUOUS_MEDIA_TYPE",
  );
});

test("keeps the existing audio/video size validation and exposes both sets of accepted formats", () => {
  assert.equal(validateVoiceFile({ name: "large.mp3", size: 10 * 1024 * 1024 + 1, type: "audio/mpeg" }).error?.code, "FILE_TOO_LARGE");
  assert.equal(validateVoiceFile({ name: "large.mp4", size: 50 * 1024 * 1024 + 1, type: "video/mp4" }).error?.code, "FILE_TOO_LARGE");
  assert.match(VOICE_FILE_ACCEPT, /\.mp3/);
  assert.match(VOICE_FILE_ACCEPT, /\.mp4/);
  assert.match(VOICE_FILE_ACCEPT, /\.webm/);
});
