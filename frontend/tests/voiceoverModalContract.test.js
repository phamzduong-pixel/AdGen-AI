import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const testsDirectory = path.dirname(fileURLToPath(import.meta.url));
const modalPath = path.join(testsDirectory, "..", "src", "components", "chat", "VoiceoverModal", "VoiceoverModal.jsx");
const apiPath = path.join(testsDirectory, "..", "src", "services", "api", "voiceoverApi.js");

test("Voice Studio keeps text mode and exposes one unified voice-file mode", () => {
  const source = fs.readFileSync(modalPath, "utf8");

  assert.match(source, /adgen-mode-tabs/);
  assert.match(source, /role="tab"/);
  assert.match(source, /Tạo Voiceover/);
  assert.match(source, /Tạo giọng đọc từ file/);
  assert.match(source, /File giọng nói/);
  assert.doesNotMatch(source, /activeMode === "audio"/);
  assert.doesNotMatch(source, /activeMode === "video"/);
  assert.match(source, /sourceObjectUrlRef/);
  assert.match(source, /URL\.revokeObjectURL/);
});

test("Voice Studio sends multipart audio to the existing STT endpoint", () => {
  const apiSource = fs.readFileSync(apiPath, "utf8");
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(apiSource, /FormData/);
  assert.match(apiSource, /formData\.append\("file", file\)/);
  assert.match(apiSource, /formData\.append\("language", language/);
  assert.match(apiSource, /api\.post\("\/stt\/transcribe", formData/);
  assert.match(modalSource, /transcribeAudio\(selectedSourceFile, "vi-VN"\)/);
});

test("Voice Studio allows local STT enough time for a five-minute file", () => {
  const apiSource = fs.readFileSync(apiPath, "utf8");

  assert.match(apiSource, /api\.post\("\/stt\/transcribe", formData, \{\s*timeout: 600_000,/);
  assert.match(apiSource, /api\.post\("\/stt\/transcribe-video", formData, \{\s*timeout: 600_000,/);
});

test("Voice Studio keeps content and voice sources independent", () => {
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(modalSource, /Nguồn nội dung/);
  assert.match(modalSource, /Văn bản quảng cáo/);
  assert.match(modalSource, /File giọng nói/);
  assert.match(modalSource, /Nguồn giọng đọc/);
  assert.match(modalSource, /Giọng có sẵn/);
  assert.match(modalSource, /Giọng tham chiếu của tôi/);
  assert.match(modalSource, /generateReferenceVoiceover/);
  assert.match(modalSource, /Sẵn sàng/);
  assert.match(modalSource, /referenceAudioObjectUrlRef/);
  assert.match(modalSource, /referenceAudioInputRef/);
  assert.match(modalSource, /referenceAudio/);
  assert.doesNotMatch(modalSource, /voice-conversion\/convert/);
});

test("Voice Studio keeps reference audio separate from content source files", () => {
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(modalSource, /id=\{sourceInputId\}/);
  assert.match(modalSource, /id="voice-studio-reference-audio-input"/);
  assert.match(modalSource, /replaceSelectedSource/);
  assert.match(modalSource, /replaceReferenceAudio/);
  assert.match(modalSource, /URL\.revokeObjectURL\(referenceAudioObjectUrlRef\.current\)/);
});

test("Voice Studio keeps transcription and audio generation as separate actions", () => {
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(modalSource, /convertVoiceFileDirect\(\{/);
  assert.doesNotMatch(modalSource, /await transcribeSelectedSource\(\{ confirmEditedTranscript: false \}\)/);
  assert.match(modalSource, /transcriptionInFlightRef/);
  assert.match(modalSource, /Boolean\(selectedSourceFile\)/);
});
test("Voice Studio invalidates stale generated audio when inputs or modal state change", () => {
  const modalSource = fs.readFileSync(modalPath, "utf8");

  assert.match(modalSource, /generationRequestRef = useRef\(0\)/);
  assert.match(modalSource, /const invalidateGeneratedAudio = \(\) =>/);
  assert.match(modalSource, /if \(requestId !== generationRequestRef\.current\) return;/);
  assert.match(modalSource, /onClick=\{handleClose\}/);
  assert.match(modalSource, /onChange=\{handleVoiceChange\}/);
  assert.match(modalSource, /onChange=\{handleSpeedChange\}/);
  assert.match(modalSource, /changeVoiceSource\("reference"\)/);
});
