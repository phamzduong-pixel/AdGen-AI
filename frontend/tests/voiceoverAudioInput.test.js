import test from "node:test";
import assert from "node:assert/strict";

import {
  AUDIO_MAX_SIZE_BYTES,
  DEFAULT_AUDIO_MAX_SIZE_BYTES,
  formatAudioSize,
  getAudioExtension,
  validateAudioFile,
} from "../src/components/chat/VoiceoverModal/audioInput.js";

test("accepts supported audio extensions case-insensitively", () => {
  assert.equal(getAudioExtension("sample.WAV"), ".wav");
  assert.equal(validateAudioFile({ name: "sample.WAV", size: 1024 }), null);
  assert.equal(validateAudioFile({ name: "sample.txt", size: 1024 })?.code, "UNSUPPORTED_EXTENSION");
});

test("rejects missing, empty, and oversized audio files", () => {
  assert.equal(validateAudioFile(null)?.code, "NO_FILE");
  assert.equal(validateAudioFile({ name: "empty.mp3", size: 0 })?.code, "EMPTY_FILE");
  assert.equal(
    validateAudioFile({ name: "large.mp3", size: DEFAULT_AUDIO_MAX_SIZE_BYTES + 1 })?.code,
    "FILE_TOO_LARGE",
  );
  assert.equal(AUDIO_MAX_SIZE_BYTES, DEFAULT_AUDIO_MAX_SIZE_BYTES);
});

test("formats the displayed audio size", () => {
  assert.equal(formatAudioSize(0), "0 B");
  assert.equal(formatAudioSize(1024), "1.0 KB");
  assert.equal(formatAudioSize(10 * 1024 * 1024), "10.0 MB");
});
