export const SUPPORTED_VIDEO_EXTENSIONS = Object.freeze([
  ".mp4",
  ".mov",
  ".webm",
]);

export const VIDEO_MAX_SIZE_BYTES = 50 * 1024 * 1024;

const VIDEO_MIME_TYPES = {
  ".mp4": ["video/mp4"],
  ".mov": ["video/quicktime", "video/mp4"],
  ".webm": ["video/webm"],
};

const VIDEO_ERROR_MESSAGES = {
  NO_FILE: "Vui lòng chọn một file video.",
  EMPTY_FILE: "File video đang trống.",
  UNSUPPORTED_EXTENSION: "Định dạng video không được hỗ trợ.",
  MIME_MISMATCH: "Loại file video không khớp với phần mở rộng.",
  FILE_TOO_LARGE: "File video vượt quá giới hạn 50 MB.",
};

export const formatVideoSize = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const getVideoExtension = (filename = "") => {
  const lastDot = filename.lastIndexOf(".");
  return lastDot >= 0 ? filename.slice(lastDot).toLowerCase() : "";
};

export const validateVideoFile = (
  file,
  maxSizeBytes = VIDEO_MAX_SIZE_BYTES,
) => {
  if (!file) {
    return { code: "NO_FILE", message: VIDEO_ERROR_MESSAGES.NO_FILE };
  }

  const extension = getVideoExtension(file.name);
  if (!SUPPORTED_VIDEO_EXTENSIONS.includes(extension)) {
    return {
      code: "UNSUPPORTED_EXTENSION",
      message: VIDEO_ERROR_MESSAGES.UNSUPPORTED_EXTENSION,
    };
  }

  if (!Number.isFinite(file.size) || file.size <= 0) {
    return { code: "EMPTY_FILE", message: VIDEO_ERROR_MESSAGES.EMPTY_FILE };
  }

  if (file.size > maxSizeBytes) {
    return {
      code: "FILE_TOO_LARGE",
      message: `${VIDEO_ERROR_MESSAGES.FILE_TOO_LARGE} (${formatVideoSize(maxSizeBytes)}).`,
    };
  }

  const allowedMimeTypes = VIDEO_MIME_TYPES[extension] || [];
  if (file.type && !allowedMimeTypes.includes(file.type.toLowerCase())) {
    return {
      code: "MIME_MISMATCH",
      message: VIDEO_ERROR_MESSAGES.MIME_MISMATCH,
    };
  }

  return null;
};
