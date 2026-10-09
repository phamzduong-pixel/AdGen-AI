import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testsDirectory = path.dirname(fileURLToPath(import.meta.url));
const modalPath = path.join(testsDirectory, "..", "src", "components", "chat", "VoiceoverModal", "VoiceoverModal.jsx");
const apiPath = path.join(testsDirectory, "..", "src", "services", "api", "voiceoverApi.js");

test("Voice Studio exposes text and unified voice-file content sources", () => {
  const source = fs.readFileSync(modalPath, "utf8");

  assert.match(source, /Văn bản quảng cáo/);
  assert.match(source, /File giọng nói/);
  assert.match(source, /contentModes = \["text", "file"\]/);
  assert.match(source, /id=\{sourceInputId\}/);
  assert.match(source, /VOICE_FILE_ACCEPT/);
});

test("video transcription reuses the authenticated multipart STT contract", () => {
  const apiSource = fs.readFileSync(apiPath, "utf8");
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(apiSource, /export const transcribeVideo/);
  assert.match(apiSource, /api\.post\("\/stt\/transcribe-video", formData/);
  assert.match(apiSource, /formData\.append\("file", file\)/);
  assert.match(apiSource, /formData\.append\("language", language/);
  assert.match(modalSource, /transcribeVideo\(selectedSourceFile, "vi-VN"\)/);
  assert.match(modalSource, /selectedSourceKind === "video"/);
  assert.match(modalSource, /onDrop=\{handleSourceDrop\}/);
});

test("unified source state supports preview cleanup and edited-transcript confirmation", () => {
  const source = fs.readFileSync(modalPath, "utf8");

  assert.match(source, /sourceObjectUrlRef/);
  assert.match(source, /URL\.revokeObjectURL\(sourceObjectUrlRef\.current\)/);
  assert.match(source, /setPendingTranscript\(transcript\)/);
  assert.match(source, /applyTranscript\(pendingTranscript\)/);
  assert.doesNotMatch(source, /voice-conversion\/convert/);
});