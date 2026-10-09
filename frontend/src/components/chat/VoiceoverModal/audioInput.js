export const SUPPORTED_AUDIO_EXTENSIONS = Object.freeze([
  '.flac',
  '.m4a',
  '.mp3',
  '.ogg',
  '.wav',
  '.webm',
]);

export const DEFAULT_AUDIO_MAX_SIZE_BYTES = 10 * 1024 * 1024;

const configuredMaxSize = Number(import.meta.env?.VITE_STT_AUDIO_MAX_SIZE_BYTES);
export const AUDIO_MAX_SIZE_BYTES =
  Number.isFinite(configuredMaxSize) && configuredMaxSize > 0
    ? configuredMaxSize
    : DEFAULT_AUDIO_MAX_SIZE_BYTES;

const AUDIO_ERROR_MESSAGES = {
  NO_FILE: 'Vui l\u00f2ng ch\u1ecdn m\u1ed9t file audio.',
  EMPTY_FILE: 'File audio \u0111ang tr\u1ed1ng.',
  UNSUPPORTED_EXTENSION: '\u0110\u1ecbnh d\u1ea1ng audio kh\u00f4ng \u0111\u01b0\u1ee3c h\u1ed7 tr\u1ee3.',
  FILE_TOO_LARGE: 'File audio v\u01b0\u1ee3t qu\u00e1 gi\u1edbi h\u1ea1n cho ph\u00e9p.',
};

export const formatAudioSize = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const getAudioExtension = (filename = '') => {
  const lastDot = filename.lastIndexOf('.');
  return lastDot >= 0 ? filename.slice(lastDot).toLowerCase() : '';
};

export const validateAudioFile = (
  file,
  maxSizeBytes = AUDIO_MAX_SIZE_BYTES,
) => {
  if (!file) {
    return { code: 'NO_FILE', message: AUDIO_ERROR_MESSAGES.NO_FILE };
  }

  const extension = getAudioExtension(file.name);
  if (!SUPPORTED_AUDIO_EXTENSIONS.includes(extension)) {
    return {
      code: 'UNSUPPORTED_EXTENSION',
      message: AUDIO_ERROR_MESSAGES.UNSUPPORTED_EXTENSION,
    };
  }

  if (!Number.isFinite(file.size) || file.size <= 0) {
    return { code: 'EMPTY_FILE', message: AUDIO_ERROR_MESSAGES.EMPTY_FILE };
  }

  if (file.size > maxSizeBytes) {
    return {
      code: 'FILE_TOO_LARGE',
      message: `${AUDIO_ERROR_MESSAGES.FILE_TOO_LARGE} (${formatAudioSize(maxSizeBytes)}).`,
    };
  }

  return null;
};
