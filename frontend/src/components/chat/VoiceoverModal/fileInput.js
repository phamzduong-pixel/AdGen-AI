import {
  AUDIO_MAX_SIZE_BYTES,
  formatAudioSize,
  getAudioExtension,
  validateAudioFile,
} from "./audioInput.js";
import {
  VIDEO_MAX_SIZE_BYTES,
  formatVideoSize,
  getVideoExtension,
  validateVideoFile,
} from "./videoInput.js";

export const VOICE_FILE_ACCEPT = ".flac,.m4a,.mp3,.ogg,.wav,.mp4,.mov,.webm,audio/*,video/mp4,video/quicktime,video/webm";

const AMBIGUOUS_WEBM_ERROR = Object.freeze({
  code: "AMBIGUOUS_MEDIA_TYPE",
  message: "Không xác định được WEBM là audio hay video. Vui lòng chọn file có MIME hợp lệ.",
});

export const getVoiceFileKind = (file) => {
  const extension = getAudioExtension(file?.name) || getVideoExtension(file?.name);
  if ([".flac", ".m4a", ".mp3", ".ogg", ".wav"].includes(extension)) return "audio";
  if ([".mp4", ".mov"].includes(extension)) return "video";
  if (extension !== ".webm") return null;

  const mimeType = String(file?.type || "").toLowerCase();
  if (mimeType === "audio/webm") return "audio";
  if (mimeType === "video/webm") return "video";
  return null;
};

export const validateVoiceFile = (file) => {
  const extension = getAudioExtension(file?.name) || getVideoExtension(file?.name);
  const kind = getVoiceFileKind(file);
  if (extension === ".webm" && !kind) {
    return { kind: null, error: AMBIGUOUS_WEBM_ERROR };
  }
  if (kind === "audio") return { kind, error: validateAudioFile(file) };
  if (kind === "video") return { kind, error: validateVideoFile(file) };

  return {
    kind: null,
    error: {
      code: "UNSUPPORTED_MEDIA_TYPE",
      message: "Định dạng file không được hỗ trợ.",
    },
  };
};

export const formatVoiceFileSize = (file, kind) =>
  kind === "video" ? formatVideoSize(file?.size) : formatAudioSize(file?.size);

export { AUDIO_MAX_SIZE_BYTES, VIDEO_MAX_SIZE_BYTES };
