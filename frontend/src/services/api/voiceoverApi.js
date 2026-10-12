import api from "./axios";
import { API_BASE_URL } from "../../constants/api";

const VIE_NEU_GENERATION_TIMEOUT_MS = 1_200_000;
const DEFAULT_VOICEOVER_TIMEOUT_MS = 120_000;

const isVieNeuPreset = (voiceId) =>
  String(voiceId || '').startsWith('vieneu-v3-turbo:');

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
  emotionCue = 'none',
  pitch = 0,
  messageId = null,
}) => {
  const payload = {
    emotion_cue: emotionCue || 'none',
    text: String(text || "").trim(),
    voice_id: voiceId || "vi-VN-HoaiMyNeural",
    speed: typeof speed === "number" ? speed : (parseFloat(speed) || 1.0),
    pitch: typeof pitch === "number" ? Math.round(pitch) : 0,
    message_id: messageId != null ? String(messageId) : null,
  };

  const response = await api.post("/voiceover/generate", payload, {
    timeout: isVieNeuPreset(voiceId)
      ? VIE_NEU_GENERATION_TIMEOUT_MS
      : DEFAULT_VOICEOVER_TIMEOUT_MS,
  });
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
  emotionCue = 'none',
  messageId = null,
}) => {
  const formData = new FormData();
  formData.append('emotion_cue', emotionCue || 'none');
  formData.append("text", String(text || "").trim());
  formData.append("file", referenceAudio);
  if (messageId != null) formData.append("message_id", String(messageId));

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

export const getVoiceoversForMessages = async (messageIds = []) => {
  const ids = messageIds.map((id) => String(id)).filter(Boolean);
  if (!ids.length) return [];
  const response = await api.get("/voiceover/messages", {
    params: { message_ids: ids.join(",") },
  });
  return (Array.isArray(response.data) ? response.data : []).map((data) => {
    if (data.audio_url && !data.audio_url.startsWith("http")) {
      data.audio_url = API_BASE_URL + data.audio_url;
    }
    if (data.download_url && !data.download_url.startsWith("http")) {
      data.download_url = API_BASE_URL + data.download_url;
    }
    return data;
  });
};

export const convertVoiceFileDirect = async ({ sourceFile, sourceKind, referenceAudio, presetVoiceId = null, messageId = null }) => {
  const formData = new FormData();
  formData.append("file", sourceFile);
  if (referenceAudio) formData.append("reference_file", referenceAudio);
  if (presetVoiceId) formData.append("preset_voice_id", presetVoiceId);
  if (messageId != null && sourceKind !== "video") formData.append("message_id", String(messageId));
  const endpoint = sourceKind === "video"
    ? "/voice-conversion/convert-reference-video"
    : "/voice-conversion/convert-reference";
  let response;
  const hasPersistentAudio = messageId != null && sourceKind !== "video";
  try {
    response = await api.post(endpoint, formData, {
      responseType: hasPersistentAudio ? "json" : "blob",
      timeout: 1_200_000,
    });
  } catch (error) {
    // Axios exposes error responses as Blob because this request returns media.
    // Decode the JSON error so Voice Studio can show the actual VC reason.
    if (typeof Blob !== "undefined" && error?.response?.data instanceof Blob) {
      try {
        const payload = await error.response.data.text();
        error.response.data = JSON.parse(payload);
      } catch {
        // Keep the original error when the server did not return JSON.
      }
    }
    throw error;
  }
  const isVideo = sourceKind === "video";
  if (hasPersistentAudio) {
    const data = response.data;
    if (data.audio_url && !data.audio_url.startsWith("http")) {
      data.audio_url = API_BASE_URL + data.audio_url;
    }
    if (data.download_url && !data.download_url.startsWith("http")) {
      data.download_url = API_BASE_URL + data.download_url;
    }
    return { ...data, media_kind: "audio" };
  }
  const objectUrl = URL.createObjectURL(response.data);
  return {
    audio_url: objectUrl,
    download_url: objectUrl,
    voice_name:
      presetVoiceId === "ngoc-huyen"
        ? "Ngọc Huyền · Chuyển giọng trực tiếp"
        : "Seed-VC · Giọng tham chiếu",
    duration_seconds: null,
    media_kind: isVideo ? "video" : "audio",
  };
};
