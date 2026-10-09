import api from "./axios";
import { API_BASE_URL } from "../../constants/api";

export const getAvailableVoices = async () => {
  const response = await api.get("/voiceover/voices");
  return response.data;
};

export const cleanScript = async (rawScript) => {
  const response = await api.post("/voiceover/clean-script", {
    raw_script: rawScript,
  });
  return response.data;
};

export const generateVoiceover = async ({
  text,
  voiceId = "vi-VN-HoaiMyNeural",
  speed = 1.0,
  pitch = 0,
  messageId = null,
}) => {
  const payload = {
    text: String(text || "").trim(),
    voice_id: voiceId || "vi-VN-HoaiMyNeural",
    speed: typeof speed === "number" ? speed : (parseFloat(speed) || 1.0),
    pitch: typeof pitch === "number" ? Math.round(pitch) : 0,
    message_id: messageId != null ? String(messageId) : null,
  };

  const response = await api.post("/voiceover/generate", payload, { timeout: 180_000 });
  const data = response.data;
  if (data.audio_url && !data.audio_url.startsWith("http")) {
    data.audio_url = `${API_BASE_URL}${data.audio_url}`;
  }
  if (data.download_url && !data.download_url.startsWith("http")) {
    data.download_url = `${API_BASE_URL}${data.download_url}`;
  }
  return data;
};

export const generateReferenceVoiceover = async ({
  text,
  referenceAudio,
}) => {
  const formData = new FormData();
  formData.append("text", String(text || "").trim());
  formData.append("file", referenceAudio);

  const response = await api.post("/voiceover/generate-reference", formData, {
    timeout: 1_200_000,
  });
  const data = response.data;
  if (data.audio_url && !data.audio_url.startsWith("http")) {
    data.audio_url = API_BASE_URL + data.audio_url;
  }
  if (data.download_url && !data.download_url.startsWith("http")) {
    data.download_url = API_BASE_URL + data.download_url;
  }
  return data;
};
export const transcribeAudio = async (file, language = "vi-VN") => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language || "vi-VN");

  const response = await api.post("/stt/transcribe", formData, {
    timeout: 600_000,
  });
  return response.data;
};

export const transcribeVideo = async (file, language = "vi-VN") => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language || "vi-VN");

  const response = await api.post("/stt/transcribe-video", formData, {
    timeout: 600_000,
  });
  return response.data;
};

// Audio endpoints require JWT. Always fetch them through the authenticated
// Axios client; never append a token to a media URL.
export const fetchVoiceoverAudio = async (url) => {
  const response = await api.get(url, {
    responseType: "blob",
    timeout: 600_000,
  });
  return response.data;
};

export const convertVoiceFileDirect = async ({ sourceFile, sourceKind, referenceAudio, presetVoiceId = null }) => {
  const formData = new FormData();
  formData.append("file", sourceFile);
  if (referenceAudio) formData.append("reference_file", referenceAudio);
  if (presetVoiceId) formData.append("preset_voice_id", presetVoiceId);
  const endpoint = sourceKind === "video"
    ? "/voice-conversion/convert-reference-video"
    : "/voice-conversion/convert-reference";
  const response = await api.post(endpoint, formData, {
    responseType: "blob",
    timeout: 1_200_000,
  });
  const isVideo = sourceKind === "video";
  const objectUrl = URL.createObjectURL(response.data);
  return {
    audio_url: objectUrl,
    download_url: objectUrl,
    voice_name: "Seed-VC · Giọng tham chiếu",
    duration_seconds: null,
    media_kind: isVideo ? "video" : "audio",
  };
};
