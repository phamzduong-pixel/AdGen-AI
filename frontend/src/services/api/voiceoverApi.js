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

  const response = await api.post(
    "/voiceover/generate",
    payload,
    { timeout: 60_000 }
  );

  const data = response.data;
  // Ensure absolute audio URL for HTML5 Audio element
  if (data.audio_url && !data.audio_url.startsWith("http")) {
    data.audio_url = `${API_BASE_URL}${data.audio_url}`;
  }
  if (data.download_url && !data.download_url.startsWith("http")) {
    data.download_url = `${API_BASE_URL}${data.download_url}`;
  }
  return data;
};