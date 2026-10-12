import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  FiX,
  FiPlay,
  FiVolume2,
  FiCheck,
  FiAlertCircle,
  FiSmile,
  FiSliders,
  FiEdit3,
  FiLoader,
  FiMic,
  FiVideo,
  FiUploadCloud,
  FiTrash2,
} from "react-icons/fi";
import {
  getAvailableVoices,
  cleanScript,
  generateVoiceover,
  generateReferenceVoiceover,
  transcribeAudio,
  transcribeVideo,
  convertVoiceFileDirect,
} from "../../../services/api/voiceoverApi";
import { getUserErrorMessage } from "../../../utils/apiError";

import {
  formatVoiceFileSize,
  validateVoiceFile,
  VOICE_FILE_ACCEPT,
} from "./fileInput";
import AudioPlayer from "./AudioPlayer";
import "./VoiceoverModal.css";

// Seed-VC uses reference-audio preset IDs, while the voice list uses TTS IDs.
// Keep this mapping local to the audio/video conversion flow; text mode keeps
// using the selected TTS voice ID unchanged.
const VOICE_CONVERSION_PRESET_BY_ID = Object.freeze({
  "vi-VN-HoaiMyNeural": "ngoc-huyen",
  "vieneu-v3-turbo:Ngọc Huyền": "ngoc-huyen",
});

const getVoiceConversionPresetId = (voiceId) =>
  VOICE_CONVERSION_PRESET_BY_ID[String(voiceId || "")] || null;

const getTranscriptionErrorMessage = (error) => {
  const code = error?.response?.data?.detail?.code;
  // Axios client timeout (no response received)
  if (
    !error?.response &&
    (error?.code === "ECONNABORTED" ||
      (error?.message &&
        typeof error.message === "string" &&
        error.message.toLowerCase().includes("timeout")))
  ) {
    return "Nhận dạng lời thoại mất quá nhiều thời gian. Vui lòng thử lại với file ngắn hơn.";
  }
  if (code === "STT_PROVIDER_NOT_CONFIGURED") {
      return "Tính năng nhận dạng lời thoại hiện chưa sẵn sàng. Vui lòng thử lại sau.";
  }
  if (code === "STT_PROVIDER_TIMEOUT") {
    return "Nhận dạng lời thoại đã quá thời gian chờ. Vui lòng thử lại sau.";
  }
  if (code === "VIDEO_NO_AUDIO_STREAM") {
    return "Video không có luồng âm thanh để nhận dạng lời thoại.";
  }
  const videoErrors = {
    VIDEO_INVALID: "File video không hợp lệ hoặc bị hỏng.",
    VIDEO_EMPTY: "File video đang trống.",
    VIDEO_UNSUPPORTED_FORMAT: "Định dạng video không được hỗ trợ.",
    VIDEO_MIME_MISMATCH: "Loại file video không khớp với phần mở rộng.",
    VIDEO_SIGNATURE_INVALID: "Chữ ký container của video không hợp lệ.",
    VIDEO_NO_VIDEO_STREAM: "Không tìm thấy luồng video trong file.",
    VIDEO_DURATION_INVALID: "Không đọc được thời lượng video.",
    VIDEO_DURATION_TOO_LONG: "Thời lượng video vượt quá giới hạn cho phép.",
    VIDEO_TOO_LARGE: "File video vượt quá giới hạn 50 MB.",
    VIDEO_AUDIO_EXTRACTION_FAILED: "Không thể trích xuất âm thanh từ video.",
    VIDEO_AUDIO_EXTRACTION_TIMEOUT:
      "Trích xuất âm thanh từ video mất quá nhiều thời gian.",
    VIDEO_EXTRACTED_AUDIO_INVALID: "Âm thanh trích xuất từ video không hợp lệ.",
    FFMPEG_NOT_CONFIGURED: "Máy chủ chưa sẵn sàng để xử lý video.",
    FFPROBE_NOT_CONFIGURED: "Máy chủ chưa sẵn sàng để kiểm tra video.",
    FFPROBE_TIMEOUT: "Kiểm tra video mất quá nhiều thời gian.",
    FFPROBE_FAILED: "Không thể kiểm tra thông tin video.",
  };
  if (videoErrors[code]) return videoErrors[code];
  if (
    code?.startsWith("VIDEO_") ||
    code?.startsWith("FFMPEG_") ||
    code?.startsWith("FFPROBE_")
  ) {
    return (
      error?.response?.data?.detail?.message ||
      "Video không thể xử lý. Vui lòng kiểm tra lại file."
    );
  }
  const transcriptionErrors = {
    STT_AUDIO_TOO_LARGE: "File âm thanh vượt quá giới hạn 10 MB.",
    STT_AUDIO_TOO_LONG:
      "Thời lượng âm thanh vượt quá giới hạn cho phép. Vui lòng dùng file ngắn hơn.",
    STT_UNSUPPORTED_AUDIO_FORMAT: "Định dạng âm thanh không được hỗ trợ.",
    STT_UNSUPPORTED_AUDIO_MIME: "Loại file âm thanh không khớp với phần mở rộng.",
    STT_UNSUPPORTED_AUDIO_CODEC:
      "Định dạng âm thanh chưa được hỗ trợ. Vui lòng chuyển file sang định dạng phù hợp.",
    STT_EMPTY_AUDIO: "File âm thanh đang trống.",
    STT_INVALID_AUDIO: "File âm thanh không hợp lệ hoặc bị hỏng.",
    STT_AUDIO_PROBE_NOT_CONFIGURED: "Máy chủ chưa có công cụ kiểm tra âm thanh.",
    STT_AUDIO_PROBE_TIMEOUT:
      "Kiểm tra âm thanh mất quá nhiều thời gian. Vui lòng thử file ngắn hơn.",
    STT_AUDIO_CONVERSION_FAILED: "Không thể chuyển đổi âm thanh để nhận dạng.",
    STT_AUDIO_CONVERSION_NOT_CONFIGURED:
      "Máy chủ chưa sẵn sàng để chuyển đổi âm thanh.",
    STT_AUDIO_CONVERSION_TIMEOUT:
      "Chuyển đổi âm thanh mất quá nhiều thời gian. Vui lòng thử file ngắn hơn.",
    STT_EMPTY_TRANSCRIPT: "Không nhận dạng được lời thoại trong file này.",
    STT_INVALID_LANGUAGE: "Mã ngôn ngữ không hợp lệ.",
    STT_PROVIDER_AUTHENTICATION_FAILED:
      "Dịch vụ nhận dạng lời thoại chưa sẵn sàng. Vui lòng thử lại sau.",
    STT_PROVIDER_RATE_LIMITED:
      "Dịch vụ nhận dạng lời thoại đang bận. Vui lòng thử lại sau.",
    STT_PROVIDER_QUOTA_EXCEEDED: "Dịch vụ nhận dạng lời thoại đã tạm hết lượt sử dụng. Vui lòng thử lại sau.",
    STT_PROVIDER_INVALID_RESPONSE:
      "Dịch vụ nhận dạng lời thoại trả về kết quả không hợp lệ.",
    STT_PROVIDER_ERROR: "Dịch vụ nhận dạng lời thoại gặp lỗi. Vui lòng thử lại sau.",
  };
  if (transcriptionErrors[code]) return transcriptionErrors[code];
  if (code?.startsWith("STT_")) {
    return (
      error?.response?.data?.detail?.message || "File âm thanh không hợp lệ."
    );
  }
  return getUserErrorMessage(
    error,
    "Không thể nhận dạng lời thoại lúc này. Vui lòng kiểm tra kết nối và thử lại.",
  );
};

const getReferenceVoiceErrorMessage = (error) => {
  const code = error?.response?.data?.detail?.code;
  const messages = {
    VOICE_REFERENCE_PROVIDER_NOT_CONFIGURED:
      "Tính năng dùng giọng từ file hiện chưa sẵn sàng. Vui lòng thử lại sau.",
    VOICE_REFERENCE_PROVIDER_TIMEOUT:
      "Tạo giọng từ file mất nhiều thời gian. Vui lòng thử lại sau.",
    VOICE_REFERENCE_PROVIDER_BUSY:
      "Tính năng đang bận. Vui lòng thử lại sau.",
    VOICE_REFERENCE_UNSUPPORTED_FORMAT:
      "Định dạng file mẫu giọng không được hỗ trợ.",
    VOICE_REFERENCE_MIME_MISMATCH:
      "Loại file không khớp với phần mở rộng.",
    VOICE_REFERENCE_TOO_LARGE:
      "Âm thanh tối đa 10 MB; video tối đa 50 MB.",
    VOICE_REFERENCE_TOO_LONG:
      "File mẫu giọng vượt quá thời lượng cho phép.",
    VOICE_REFERENCE_INVALID: "File mẫu giọng không hợp lệ hoặc bị hỏng.",
    VOICE_REFERENCE_OUTPUT_INVALID:
      "Không tạo được file âm thanh. Vui lòng thử lại.",
    VOICE_REFERENCE_NO_AUDIO_STREAM:
      "Video không có phần âm thanh để dùng làm mẫu giọng.",
  };
  return (
    messages[code] ||
    getUserErrorMessage(
      error,
      "Không thể tạo giọng đọc từ file. Vui lòng thử lại.",
    )
  );
};

const getVoiceConversionErrorMessage = (error) => {
  const code = error?.response?.data?.detail?.code;
  const messages = {
    VC_PROVIDER_NOT_CONFIGURED:
      "Tính năng chuyển giọng trực tiếp hiện chưa sẵn sàng. Vui lòng thử lại sau.",
    VC_PROVIDER_TIMEOUT:
      "Mô hình chuyển giọng mất quá thời gian xử lý. Thời lượng file không phải nguyên nhân; vui lòng thử lại khi hệ thống đang rảnh.",
    VC_REFERENCE_REQUIRED:
      "Vui lòng chọn mẫu giọng đích trước khi chuyển giọng trực tiếp.",
    VC_REFERENCE_NOT_FOUND:
      "Mẫu giọng đích chưa được cài đặt. Vui lòng chọn Ngọc Huyền hoặc tải file mẫu giọng.",
    VC_OUTPUT_INVALID: "Seed-VC không tạo được file âm thanh hợp lệ. Vui lòng thử lại.",
    VC_VIDEO_PROCESSING_TIMEOUT:
      "Chuyển giọng cho video mất quá nhiều thời gian. Vui lòng thử file ngắn hơn.",
    VC_VIDEO_TOOL_NOT_CONFIGURED:
      "Máy chủ chưa sẵn sàng để xử lý chuyển giọng cho video.",
  };
  return (
    messages[code] ||
    getUserErrorMessage(
      error,
      "Không thể chuyển âm thanh sang giọng đích lúc này. Vui lòng thử lại.",
    )
  );
};

const getVoiceoverErrorMessage = (error) => {
  const code = error?.response?.data?.detail?.code;
  if (code === 'VOICEOVER_PROVIDER_TIMEOUT') {
    return '\u0044\u1ecbch v\u1ee5 gi\u1ecdng \u0111\u1ecdc \u0111ang ph\u1ea3n h\u1ed3i ch\u1eadm. H\u00e3y th\u1eed l\u1ea1i sau \u00edt ph\u00fat.';
  }
  if (
    !error?.response &&
    (error?.code === 'ECONNABORTED' ||
      String(error?.message || '').toLowerCase().includes('timeout'))
  ) {
    return '\u0054\u1ea1o gi\u1ecdng \u0111\u1ecdc \u0111ang m\u1ea5t nhi\u1ec1u th\u1eddi gian. Vui l\u00f2ng gi\u1eef c\u1eeda s\u1ed5 n\u00e0y m\u1edf v\u00e0 th\u1eed l\u1ea1i.';
  }
  return getUserErrorMessage(
    error,
    '\u004b\u0068\u00f4ng th\u1ec3 sinh audio l\u00fac n\u00e0y. Vui l\u00f2ng ki\u1ec3m tra l\u1ea1i n\u1ed9i dung v\u00e0 th\u1eed l\u1ea1i.',
  );
};

export default function VoiceoverModal({
  isOpen,
  onClose,
  initialText = "",
  messageId = null,
  onGenerated = null,
}) {
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState("vi-VN-HoaiMyNeural");
  const [speed, setSpeed] = useState(1.0);
  const [emotionCue, setEmotionCue] = useState('none');
  const [textToRead, setTextToRead] = useState("");
  const [originalScript, setOriginalScript] = useState("");
  const [cleanedScript, setCleanedScript] = useState("");
  const [activeTextVersion, setActiveTextVersion] = useState("cleaned");
  const [isCleaning, setIsCleaning] = useState(false);

  const [extractionMeta, setExtractionMeta] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [audioResult, setAudioResult] = useState(null);
  const [activeMode, setActiveMode] = useState("text");
  const [selectedSourceFile, setSelectedSourceFile] = useState(null);
  const [selectedSourceKind, setSelectedSourceKind] = useState(null);
  const [sourceObjectUrl, setSourceObjectUrl] = useState(null);
  const [fileTranscript, setFileTranscript] = useState("");
  const [fileTranscriptBaseline, setFileTranscriptBaseline] = useState("");
  const [pendingTranscript, setPendingTranscript] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isFileDragging, setIsFileDragging] = useState(false);
  const [voiceSource, setVoiceSource] = useState("builtin");
  const [referenceAudio, setReferenceAudio] = useState(null);
  const [referenceAudioKind, setReferenceAudioKind] = useState(null);
  const [referenceAudioObjectUrl, setReferenceAudioObjectUrl] = useState(null);
  const sourceObjectUrlRef = useRef(null);
  const sourceInputRef = useRef(null);
  const sourceVersionRef = useRef(0);
  const transcriptionRequestRef = useRef(0);
  const transcriptionInFlightRef = useRef(null);
  const generationRequestRef = useRef(0);
  const referenceAudioObjectUrlRef = useRef(null);
  const referenceAudioInputRef = useRef(null);
  const editorTextAreaRef = useRef(null);

  const invalidateGeneratedAudio = () => {
    generationRequestRef.current += 1;
    setAudioResult(null);
    setIsGenerating(false);
  };

  useEffect(() => {
    generationRequestRef.current += 1;
    if (!isOpen) {
      sourceVersionRef.current += 1;
      transcriptionRequestRef.current += 1;
      transcriptionInFlightRef.current = null;
      if (sourceObjectUrlRef.current) {
        URL.revokeObjectURL(sourceObjectUrlRef.current);
        sourceObjectUrlRef.current = null;
      }
      if (referenceAudioObjectUrlRef.current) {
        URL.revokeObjectURL(referenceAudioObjectUrlRef.current);
        referenceAudioObjectUrlRef.current = null;
      }
      const closeResetId = window.setTimeout(() => {
        setSelectedSourceFile(null);
        setSelectedSourceKind(null);
        setSourceObjectUrl(null);
        setFileTranscript("");
        setFileTranscriptBaseline("");
        setPendingTranscript(null);
        setIsTranscribing(false);
        setEmotionCue('none');
        setVoiceSource("builtin");
        setReferenceAudio(null);
        setReferenceAudioObjectUrl(null);
      }, 0);
      return () => window.clearTimeout(closeResetId);
    }

    const safeInitial = typeof initialText === "string" ? initialText : "";
    const resetId = window.setTimeout(() => {
      setError(null);
      setAudioResult(null);
      setExtractionMeta(null);
      setOriginalScript(safeInitial);
      setCleanedScript("");
      setTextToRead("");
      setActiveTextVersion("cleaned");
      setActiveMode("text");
      setFileTranscript("");
      setFileTranscriptBaseline("");
      setPendingTranscript(null);
      setSelectedSourceFile(null);
      setSelectedSourceKind(null);
      setEmotionCue('none');
      setSourceObjectUrl(null);
      setVoiceSource("builtin");
      setReferenceAudio(null);
      setReferenceAudioObjectUrl(null);
    }, 0);

    // Fetch voices
    getAvailableVoices()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setVoices(data);
        }
      })
      .catch((err) => {
        console.warn("Could not load voices, using fallback default:", err);
      });

    // Auto extract pure spoken dialogue from the script
    if (safeInitial.trim()) {
      window.setTimeout(() => setIsCleaning(true), 0);
      cleanScript(safeInitial)
        .then((res) => {
          if (res) {
            if (res.status === "no_dialogue") {
              window.setTimeout(() => setTextToRead(""), 0);
              setCleanedScript("");
              setExtractionMeta({
                status: "no_dialogue",
                warning:
                  res.warning_message ||
                  "Không tìm thấy cấu trúc lời thoại rõ ràng (VO / Lời thoại). Vui lòng nhập lời thoại cần đọc vào ô bên dưới.",
                count: 0,
              });
            } else {
              const cleaned = res.cleaned_script || "";
              setCleanedScript(cleaned);
              setTextToRead(cleaned);
              setActiveTextVersion("cleaned");
              setExtractionMeta({
                status: res.status || "success",
                warning: res.warning_message,
                count: res.dialogue_blocks_count || 1,
              });
            }
          }
        })
        .catch((err) => {
          console.warn("Auto script extraction failed, keeping raw:", err);
          setCleanedScript(safeInitial);
          setTextToRead(safeInitial);
        })
        .finally(() => {
          setIsCleaning(false);
        });
    } else {
      window.setTimeout(() => setTextToRead(""), 0);
      window.setTimeout(() => setCleanedScript(""), 0);
    }
    return () => window.clearTimeout(resetId);
  }, [isOpen, initialText]);

  useEffect(
    () => () => {
      if (sourceObjectUrlRef.current) {
        URL.revokeObjectURL(sourceObjectUrlRef.current);
        sourceObjectUrlRef.current = null;
      }
      if (referenceAudioObjectUrlRef.current) {
        URL.revokeObjectURL(referenceAudioObjectUrlRef.current);
        referenceAudioObjectUrlRef.current = null;
      }
    },
    [],
  );

  const replaceSelectedSource = (file) => {
    sourceVersionRef.current += 1;
    transcriptionRequestRef.current += 1;
    transcriptionInFlightRef.current = null;
    if (sourceObjectUrlRef.current) {
      URL.revokeObjectURL(sourceObjectUrlRef.current);
      sourceObjectUrlRef.current = null;
    }
    setSelectedSourceFile(null);
    setSelectedSourceKind(null);
    setSourceObjectUrl(null);
    setFileTranscript("");
    setFileTranscriptBaseline("");
    setPendingTranscript(null);
    setIsTranscribing(false);
    invalidateGeneratedAudio();

    if (!file) {
      if (sourceInputRef.current) sourceInputRef.current.value = "";
      return;
    }

    const { kind, error: validationError } = validateVoiceFile(file);
    if (validationError) {
      setError(validationError.message);
      if (sourceInputRef.current) sourceInputRef.current.value = "";
      return;
    }

    const nextObjectUrl = URL.createObjectURL(file);
    sourceObjectUrlRef.current = nextObjectUrl;
    setSelectedSourceFile(file);
    setSelectedSourceKind(kind);
    setSourceObjectUrl(nextObjectUrl);
    setError(null);
  };

  const handleSourceFileChange = (event) => {
    replaceSelectedSource(event.target.files?.[0] || null);
  };

  const handleSourceDrop = (event) => {
    event.preventDefault();
    setIsFileDragging(false);
    replaceSelectedSource(event.dataTransfer.files?.[0] || null);
  };

  const replaceReferenceAudio = (file) => {
    invalidateGeneratedAudio();
    if (referenceAudioObjectUrlRef.current) {
      URL.revokeObjectURL(referenceAudioObjectUrlRef.current);
      referenceAudioObjectUrlRef.current = null;
    }
    setReferenceAudio(null);
    setReferenceAudioKind(null);
    setReferenceAudioObjectUrl(null);

    if (!file) {
      if (referenceAudioInputRef.current)
        referenceAudioInputRef.current.value = "";
      return;
    }

    const { kind, error: validationError } = validateVoiceFile(file);
    if (validationError) {
      setError(validationError.message);
      if (referenceAudioInputRef.current)
        referenceAudioInputRef.current.value = "";
      return;
    }

    const nextObjectUrl = URL.createObjectURL(file);
    referenceAudioObjectUrlRef.current = nextObjectUrl;
    setReferenceAudio(file);
    setReferenceAudioKind(kind);
    setReferenceAudioObjectUrl(nextObjectUrl);
    setError(null);
  };

  const handleReferenceAudioFileChange = (event) => {
    replaceReferenceAudio(event.target.files?.[0] || null);
  };

  const applyTranscript = (transcript, { invalidateResult = true } = {}) => {
    if (invalidateResult) invalidateGeneratedAudio();
    setFileTranscript(transcript);
    setFileTranscriptBaseline(transcript);
    setPendingTranscript(null);
    setError(null);
  };

  const transcribeSelectedSource = async ({ confirmEditedTranscript }) => {
    if (transcriptionInFlightRef.current) {
      setError("Nhận dạng lời thoại đang chạy. Vui lòng chờ hoàn tất.");
      return null;
    }

    if (!selectedSourceFile || !selectedSourceKind) {
      setError("Vui lòng chọn file giọng nói trước khi nhận dạng lời thoại.");
      return null;
    }

    const sourceVersion = sourceVersionRef.current;
    const requestId = transcriptionRequestRef.current + 1;
    transcriptionRequestRef.current = requestId;
    transcriptionInFlightRef.current = { sourceVersion, requestId };
    const currentTranscript = fileTranscript;
    const currentBaseline = fileTranscriptBaseline;

    try {
      setIsTranscribing(true);
      setError(null);
      const result =
        selectedSourceKind === "video"
          ? await transcribeVideo(selectedSourceFile, "vi-VN")
          : await transcribeAudio(selectedSourceFile, "vi-VN");
      if (
        sourceVersion !== sourceVersionRef.current ||
        requestId !== transcriptionRequestRef.current
      ) {
        return null;
      }

      const transcript = String(result?.transcript || "").trim();
      if (!transcript) {
        setError("Không nhận dạng được lời thoại. Vui lòng thử file khác.");
        return null;
      }

      const hasEditedTranscript =
        currentTranscript.trim() !== "" &&
        currentTranscript.trim() !== currentBaseline.trim();
      if (confirmEditedTranscript && hasEditedTranscript) {
        setPendingTranscript(transcript);
        return null;
      }

      applyTranscript(transcript, { invalidateResult: false });
      return transcript;
    } catch (err) {
      if (
        sourceVersion === sourceVersionRef.current &&
        requestId === transcriptionRequestRef.current
      ) {
        console.error("Transcription failed:", err);
        setError(getTranscriptionErrorMessage(err));
      }
      return null;
    } finally {
      if (
        sourceVersion === sourceVersionRef.current &&
        requestId === transcriptionRequestRef.current
      ) {
        setIsTranscribing(false);
      }
      if (
        transcriptionInFlightRef.current?.sourceVersion === sourceVersion &&
        transcriptionInFlightRef.current?.requestId === requestId
      ) {
        transcriptionInFlightRef.current = null;
      }
    }
  };

  const handleTranscribe = async () => {
    invalidateGeneratedAudio();
    await transcribeSelectedSource({ confirmEditedTranscript: true });
  };

  const handleTranscriptChange = (event) => {
    invalidateGeneratedAudio();
    transcriptionRequestRef.current += 1;
    setFileTranscript(event.target.value);
  };

  const changeActiveMode = (mode) => {
    sourceVersionRef.current += 1;
    transcriptionRequestRef.current += 1;
    transcriptionInFlightRef.current = null;
    setIsTranscribing(false);
    setActiveMode(mode);
    invalidateGeneratedAudio();
    setError(null);
    setPendingTranscript(null);
  };

  const changeVoiceSource = (source) => {
    invalidateGeneratedAudio();
    setVoiceSource(source);
  };

  const handleVoiceChange = (event) => {
    invalidateGeneratedAudio();
    const nextVoice = event.target.value;
    setSelectedVoice(nextVoice);
    if (!nextVoice.startsWith('vieneu-v3-turbo:')) {
      setEmotionCue('none');
    }
  };

  const handleSpeedChange = (event) => {
    invalidateGeneratedAudio();
    setSpeed(parseFloat(event.target.value));
  };

  const handleEmotionCueChange = (event) => {
    invalidateGeneratedAudio();
    setEmotionCue(event.target.value);
  };

  const handleModeKeyDown = (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const contentModes = ["text", "file"];
    const currentIndex = contentModes.indexOf(activeMode);
    let nextIndex = currentIndex;
    if (event.key === "ArrowLeft") nextIndex = Math.max(0, currentIndex - 1);
    if (event.key === "ArrowRight")
      nextIndex = Math.min(contentModes.length - 1, currentIndex + 1);
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = contentModes.length - 1;
    changeActiveMode(contentModes[nextIndex]);
  };

  const isVieNeuVoice = selectedVoice.startsWith('vieneu-v3-turbo:');
  const isDirectVoiceConversion =
    activeMode === 'file' && !fileTranscript.trim();
  const emotionCueAvailable =
    !isDirectVoiceConversion &&
    (voiceSource === 'reference' || isVieNeuVoice);

  if (!isOpen) return null;

  const handleClose = () => {
    invalidateGeneratedAudio();
    onClose();
  };

  const handleGenerate = async () => {
    if (transcriptionInFlightRef.current) {
      setError("Nhận dạng lời thoại đang chạy. Vui lòng chờ hoàn tất.");
      return;
    }

    if (activeMode === "file" && !selectedSourceFile) {
      setError("Vui lòng chọn file giọng nói trước khi tạo giọng đọc.");
      return;
    }
    if (voiceSource === "reference" && !referenceAudio) {
      setError("Vui lòng chọn file mẫu giọng trước khi tạo giọng đọc.");
      return;
    }

    const directPresetVoiceId =
      isDirectVoiceConversion && voiceSource === "builtin"
        ? getVoiceConversionPresetId(selectedVoice)
        : null;
    if (isDirectVoiceConversion && voiceSource === "builtin" && !directPresetVoiceId) {
      setError(
        "Chuyển giọng trực tiếp hiện có mẫu Ngọc Huyền. Vui lòng chọn Ngọc Huyền hoặc dùng giọng từ file của tôi.",
      );
      return;
    }

    invalidateGeneratedAudio();
    const requestId = generationRequestRef.current;
    try {
      setIsGenerating(true);
      setError(null);

      let text =
        activeMode === "text" ? textToRead.trim() : fileTranscript.trim();
      let result;
      if (isDirectVoiceConversion) {
        result = await convertVoiceFileDirect({
          sourceFile: selectedSourceFile,
          sourceKind: selectedSourceKind,
          referenceAudio: voiceSource === "reference" ? referenceAudio : null,
          presetVoiceId: directPresetVoiceId,
          messageId,
        });
      } else if (voiceSource === "reference") {
        result = await generateReferenceVoiceover({
          text,
          referenceAudio,
          emotionCue,
          messageId,
        });
      } else {
        result = await generateVoiceover({
          text,
          voiceId: selectedVoice,
          speed,
          emotionCue: emotionCueAvailable ? emotionCue : 'none',
          messageId,
        });
      }
      if (requestId !== generationRequestRef.current) return;

      setAudioResult(result);
      if (onGenerated) {
        onGenerated(result);
      }
    } catch (err) {
      if (requestId !== generationRequestRef.current) return;
      console.error("Generate voiceover failed:", err);
      setError(
        isDirectVoiceConversion
          ? getVoiceConversionErrorMessage(err)
          : voiceSource === "reference"
          ? getReferenceVoiceErrorMessage(err)
          : getVoiceoverErrorMessage(
              err,
              "Không thể sinh audio lúc này. Vui lòng kiểm tra lại nội dung và thử lại.",
            ),
      );
    } finally {
      if (requestId === generationRequestRef.current) setIsGenerating(false);
    }
  };
  const handleTextChange = (event) => {
    invalidateGeneratedAudio();
    const nextText = event.target.value;
    setTextToRead(nextText);
    if (activeTextVersion === "original") {
      setOriginalScript(nextText);
    } else {
      setCleanedScript(nextText);
    }
  };

  const handleTextVersionToggle = () => {
    invalidateGeneratedAudio();
    if (activeTextVersion === "cleaned") {
      setActiveTextVersion("original");
      setTextToRead(originalScript);
      return;
    }
    setActiveTextVersion("cleaned");
    setTextToRead(cleanedScript);
  };

  const isFileMode = activeMode === "file";
  const sourceInputId = "voice-studio-file-input";
  const editorText = activeMode === "text" ? textToRead : fileTranscript;
  const canGenerate =
    activeMode === "text"
      ? Boolean(editorText.trim())
      : Boolean(selectedSourceFile);
  const generateButtonLabel =
    voiceSource === "reference"
      ? referenceAudio
        ? "Tạo giọng đọc từ file của tôi"
        : "Chọn file mẫu giọng"
      : activeMode !== "text"
        ? selectedSourceFile
          ? "Tạo giọng đọc từ file"
          : "Chọn âm thanh / video"
        : "Tạo giọng đọc";
  const modalContent = (
    <div className="adgen-modal-overlay" onClick={handleClose}>
      <div
        className="adgen-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="adgen-modal-header">
          <div className="adgen-modal-title">
            <div className="adgen-modal-icon" aria-hidden="true">
              <FiMic />
            </div>
            <div>
              <h3>AdGen Voice Studio</h3>
              <p>Chuyển kịch bản quảng cáo thành giọng đọc chuyên nghiệp</p>
            </div>
          </div>
          <button
            type="button"
            className="adgen-modal-close"
            onClick={handleClose}
            aria-label="Đóng"
          >
            <FiX />
          </button>
        </div>

        {/* Body */}
        <div className="adgen-modal-body">
          <section
            className="adgen-source-section"
            aria-labelledby="voice-studio-content-source"
          >
            <div className="adgen-source-section__header">
              <div>
                <p className="adgen-eyebrow">Nguồn nội dung</p>
                <h4 id="voice-studio-content-source">
                  Chọn nội dung sẽ được đọc
                </h4>
              </div>
              <span className="adgen-source-section__hint">
                Có thể chọn riêng nội dung và giọng đọc
              </span>
            </div>
            <div
              className="adgen-mode-tabs"
              role="tablist"
              aria-label="Nguồn nội dung Voice Studio"
            >
              <button
                type="button"
                role="tab"
                aria-selected={activeMode === "text"}
                className={
                  "adgen-mode-tab " +
                  (activeMode === "text" ? "adgen-mode-tab--active" : "")
                }
                onClick={() => changeActiveMode("text")}
                onKeyDown={handleModeKeyDown}
              >
                Văn bản quảng cáo
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeMode === "file"}
                className={
                  "adgen-mode-tab " +
                  (activeMode === "file" ? "adgen-mode-tab--active" : "")
                }
                onClick={() => changeActiveMode("file")}
                onKeyDown={handleModeKeyDown}
              >
                Âm thanh / video
              </button>
            </div>
          </section>

          {error && (
            <div className="adgen-alert adgen-alert--error">
              <FiAlertCircle />
              <span>
                {typeof error === "string"
                  ? error
                  : error?.message || String(error)}
              </span>
            </div>
          )}

          {isFileMode && (
            <div className="adgen-audio-input-section adgen-file-input-section">
              <div
                className={
                  "adgen-audio-dropzone " +
                  (selectedSourceFile
                    ? "adgen-audio-dropzone--has-file "
                    : "") +
                  (isFileDragging ? "adgen-audio-dropzone--dragging" : "")
                }
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsFileDragging(true);
                }}
                onDragLeave={() => setIsFileDragging(false)}
                onDrop={handleSourceDrop}
              >
                {selectedSourceFile ? (
                  <div className="adgen-audio-dropzone__selected">
                    <span className="adgen-audio-dropzone__selected-badge">
                      <FiCheck aria-hidden="true" /> File đã chọn
                    </span>
                    <div className="adgen-selected-audio">
                      <div className="adgen-selected-audio__meta">
                        {selectedSourceKind === "video" ? (
                          <FiVideo aria-hidden="true" />
                        ) : (
                          <FiMic aria-hidden="true" />
                        )}
                        <div>
                          <strong>{selectedSourceFile.name}</strong>
                          <span>
                            {formatVoiceFileSize(
                              selectedSourceFile,
                              selectedSourceKind,
                            )}
                          </span>
                        </div>
                      </div>
                      <div className="adgen-selected-audio__actions adgen-file-actions">
                        <button
                          type="button"
                          className="adgen-btn-link adgen-file-action adgen-file-action--replace"
                          onClick={() => sourceInputRef.current?.click()}
                          disabled={isTranscribing || isGenerating}
                          aria-label="Thay file nguồn"
                        >
                          <FiUploadCloud /> Thay file
                        </button>
                        <button
                          type="button"
                          className="adgen-btn-link adgen-btn-link--danger adgen-file-action adgen-file-action--remove"
                          onClick={() => replaceSelectedSource(null)}
                          disabled={isTranscribing || isGenerating}
                          aria-label="Xóa file nguồn"
                        >
                          <FiTrash2 /> Xóa file
                        </button>
                      </div>
                      {sourceObjectUrl &&
                        (selectedSourceKind === "video" ? (
                          <video
                            className="adgen-source-video-player"
                            controls
                            preload="metadata"
                            src={sourceObjectUrl}
                          >
                            Trình duyệt không hỗ trợ phát video.
                          </video>
                        ) : (
                          <audio
                            className="adgen-source-audio-player"
                            controls
                            preload="metadata"
                            src={sourceObjectUrl}
                          >
                            Trình duyệt không hỗ trợ phát audio.
                          </audio>
                        ))}
                    </div>
                  </div>
                ) : (
                  <>
                    <FiUploadCloud aria-hidden="true" />
                    <strong>Thêm âm thanh hoặc video để nhận dạng lời thoại</strong>
                    <span>
                      Hỗ trợ FLAC, M4A, MP3, OGG, WAV, MP4, MOV, WEBM — audio tối đa
                      10 MB / 5 phút; video tối đa 50 MB / 5 phút
                    </span>
                    <label
                      className="adgen-btn adgen-btn--secondary adgen-audio-file-label"
                      htmlFor={sourceInputId}
                    >
                      <FiUploadCloud /> Chọn âm thanh / video
                    </label>
                  </>
                )}
                <input
                  ref={sourceInputRef}
                  id={sourceInputId}
                  className="adgen-visually-hidden"
                  type="file"
                  accept={VOICE_FILE_ACCEPT}
                  onChange={handleSourceFileChange}
                />
              </div>

              {pendingTranscript && (
                <div className="adgen-transcript-confirm">
                  <span>
                    Đã có nội dung lời thoại đã chỉnh sửa. Bạn có muốn thay bằng
kết quả nhận dạng mới không?
                  </span>
                  <div>
                    <button
                      type="button"
                      className="adgen-btn-link"
                      onClick={() => applyTranscript(pendingTranscript)}
                    >
Dùng lời thoại mới
                    </button>
                    <button
                      type="button"
                      className="adgen-btn-link"
                      onClick={() => setPendingTranscript(null)}
                    >
                      Giữ nội dung hiện tại
                    </button>
                  </div>
                </div>
              )}

              <button
                type="button"
                className="adgen-btn adgen-btn--primary adgen-transcribe-btn"
                onClick={handleTranscribe}
                disabled={!selectedSourceFile || isTranscribing || isGenerating}
              >
                {isTranscribing ? (
                  <>
                    <FiLoader className="adgen-spinner" /> Đang nhận dạng lời
                    thoại...
                  </>
                ) : (
                  <>
                    <FiMic /> Nhận dạng lời thoại
                  </>
                )}
              </button>
              <p className="adgen-audio-flow-note">
                File sẽ được chuyển trực tiếp sang giọng đích, giữ nội dung và
                nhịp nói. Không cần nhận dạng lời thoại để tạo; nút nhận dạng
                chỉ dùng để xem hoặc chỉnh lời thoại tham khảo.
              </p>
            </div>
          )}
          {/* Extraction status notices */}
          {activeMode === "text" && extractionMeta?.status === "success" && (
            <div className="adgen-cleaner-notice">
              <span className="adgen-cleaner-badge">
<FiCheck /> Đã tìm thấy {extractionMeta.count} đoạn lời thoại
trong các phân cảnh (đã bỏ qua chỉ dẫn hình ảnh, camera và hiệu ứng)
              </span>
              <button
                type="button"
                className="adgen-btn-link"
                onClick={handleTextVersionToggle}
                title="Khôi phục toàn bộ văn bản gốc"
              >
                {activeTextVersion === "cleaned"
                  ? "Xem văn bản gốc"
                  : "Quay lại văn bản đã lọc"}
              </button>
            </div>
          )}

          {activeMode === "text" &&
            extractionMeta?.status === "no_dialogue" && (
              <div className="adgen-alert adgen-alert--warning">
                <FiAlertCircle />
                <div style={{ flex: 1 }}>
                  <span>{extractionMeta.warning}</span>
                  <button
                    type="button"
                    className="adgen-btn-link adgen-btn-link--block"
                    onClick={handleTextVersionToggle}
                  >
                    {activeTextVersion === "cleaned"
                      ? "Xem văn bản gốc"
                      : "Quay lại văn bản đã lọc"}
                  </button>
                </div>
              </div>
            )}

          {activeMode === "text" && extractionMeta?.status === "uncertain" && (
            <div className="adgen-alert adgen-alert--warning">
              <FiAlertCircle />
              <span>
                {extractionMeta.warning ||
                  "Hệ thống đã chọn các đoạn có khả năng là lời thoại. Vui lòng kiểm tra trước khi tạo audio."}
              </span>
            </div>
          )}

          {/* Text dialogue editor */}
          <div className="adgen-form-group">
            {activeMode === "text" ? (
              <span className="adgen-text-version">
                {activeTextVersion === "cleaned"
                  ? "Đang xem văn bản đã lọc"
                  : "Đang xem văn bản gốc"}
              </span>
            ) : (
              <span className="adgen-text-version">
                {fileTranscriptBaseline && editorText !== fileTranscriptBaseline
                  ? "Lời thoại đã được chỉnh sửa"
                  : "Lời thoại có thể chỉnh sửa"}
              </span>
            )}{" "}
            <label className="adgen-label">
              <FiEdit3 />
              {activeMode !== "text"
                ? "Lời thoại nhận dạng (Bạn có thể chỉnh sửa):"
                : "Lời thoại sẽ được đọc (Bạn có thể chỉnh sửa tự do):"}
            </label>
            <div className="adgen-textarea-wrap">
              <textarea
                className="adgen-textarea"
                ref={editorTextAreaRef}
                rows={5}
                value={editorText}
                onChange={
                  activeMode === "text"
                    ? handleTextChange
                    : handleTranscriptChange
                }
                placeholder="Nhập hoặc dán lời thoại quảng cáo cần đọc vào đây..."
                disabled={isCleaning || isGenerating || isTranscribing}
              />
              <span className="adgen-char-count">
                {editorText.length} / 10000 ký tự
              </span>
            </div>
          </div>

          <section
            className="adgen-source-section adgen-voice-source-section"
            aria-labelledby="voice-studio-voice-source"
          >
            <div className="adgen-source-section__header">
              <div>
                <p className="adgen-eyebrow">Cách chọn giọng đọc</p>
                <h4 id="voice-studio-voice-source">
Bạn muốn dùng giọng nào?
                </h4>
              </div>
              <span className="adgen-source-section__hint">
                Không đổi nội dung đã chọn
              </span>
            </div>

            <div
              className="adgen-voice-source-tabs"
              role="tablist"
              aria-label="Chọn cách dùng giọng đọc"
            >
              <button
                type="button"
                role="tab"
                aria-selected={voiceSource === "builtin"}
                className={
                  "adgen-voice-source-tab " +
                  (voiceSource === "builtin"
                    ? "adgen-voice-source-tab--active"
                    : "")
                }
                onClick={() => changeVoiceSource("builtin")}
              >
                Dùng giọng có sẵn
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={voiceSource === "reference"}
                className={
                  "adgen-voice-source-tab " +
                  (voiceSource === "reference"
                    ? "adgen-voice-source-tab--active"
                    : "")
                }
                onClick={() => changeVoiceSource("reference")}
              >
Dùng giọng từ file của tôi
              </button>
            </div>

            {voiceSource === "builtin" ? (
              <div className="adgen-voice-source-panel">
<strong>Giọng đọc có sẵn</strong>
<span>
  {isDirectVoiceConversion
    ? "Chọn mẫu giọng chuyển đổi trực tiếp trong danh sách bên dưới."
    : "Chọn một giọng đọc phù hợp trong danh sách bên dưới."}
</span>
              </div>
            ) : (
              <div className="adgen-reference-voice-panel">
                <div className="adgen-reference-voice-panel__header">
                  <div>
<strong>Giọng đọc từ file của bạn</strong>
                    <span>
                      {isDirectVoiceConversion
                        ? "File mẫu xác định giọng đích; nội dung lấy trực tiếp từ file nguồn."
                        : "File này chỉ làm mẫu giọng; nội dung được đọc lấy từ phần văn bản bên trên."}
                    </span>
                  </div>
                  <span className="adgen-status-badge">Sẵn sàng</span>
                </div>
                <p className="adgen-reference-voice-panel__note">
                  {isDirectVoiceConversion
                    ? "Hệ thống sẽ chuyển trực tiếp âm thanh hoặc phần âm thanh của video sang giọng trong file mẫu, giữ nội dung và nhịp nói. File chỉ dùng cho lần tạo này và không được lưu lại."
                    : "Hệ thống sẽ dùng giọng trong âm thanh hoặc phần âm thanh của video để đọc nội dung. Video cần có âm thanh, tối đa 50 MB và 60 giây. File chỉ dùng cho lần tạo này và không được lưu lại."}
                </p>
                <label
                  className="adgen-btn adgen-btn--secondary adgen-reference-audio-label"
                  htmlFor="voice-studio-reference-audio-input"
                >
<FiUploadCloud /> Tải file âm thanh hoặc video lên
                </label>
                <input
                  ref={referenceAudioInputRef}
                  id="voice-studio-reference-audio-input"
                  className="adgen-visually-hidden"
                  type="file"
                  accept={VOICE_FILE_ACCEPT}
                  onChange={handleReferenceAudioFileChange}
                  disabled={isGenerating}
                />

                {referenceAudio && (
                  <div className="adgen-reference-audio">
                    <div className="adgen-reference-audio__meta">
                      {referenceAudioKind === "video" ? (
                        <FiVideo aria-hidden="true" />
                      ) : (
                        <FiMic aria-hidden="true" />
                      )}
                      <div>
                        <strong>{referenceAudio.name}</strong>
                        <span>
                          {formatVoiceFileSize(
                            referenceAudio,
                            referenceAudioKind,
                          )}
                        </span>
                      </div>
                    </div>
                    <div className="adgen-selected-audio__actions adgen-file-actions">
                      <button
                        type="button"
                        className="adgen-btn-link adgen-file-action adgen-file-action--replace"
                        onClick={() => referenceAudioInputRef.current?.click()}
                        disabled={isGenerating}
                        aria-label="Thay file mẫu giọng"
                      >
                        <FiUploadCloud /> Thay file
                      </button>
                      <button
                        type="button"
                        className="adgen-btn-link adgen-btn-link--danger adgen-file-action adgen-file-action--remove"
                        onClick={() => replaceReferenceAudio(null)}
                        disabled={isGenerating}
                        aria-label="Xóa file mẫu giọng"
                      >
                        <FiTrash2 /> Xóa file
                      </button>
                    </div>
                    {referenceAudioObjectUrl &&
                      (referenceAudioKind === "video" ? (
                        <video
                          className="adgen-source-video-player"
                          controls
                          preload="metadata"
                          src={referenceAudioObjectUrl}
                        >
                          Trình duyệt không hỗ trợ phát video.
                        </video>
                      ) : (
                        <audio
                          className="adgen-source-audio-player"
                          controls
                          preload="metadata"
                          src={referenceAudioObjectUrl}
                        >
                          Trình duyệt không hỗ trợ phát audio.
                        </audio>
                      ))}
                  </div>
                )}
              </div>
            )}
          </section>
          {/* Voice settings */}
          {voiceSource === "builtin" && (
            <div className="adgen-settings-grid">
              {/* Voice Select */}
              <div className="adgen-form-group">
                <label className="adgen-label">
                  <FiVolume2 /> Chọn giọng đọc:
                </label>
                <select
                  className="adgen-select"
                  value={selectedVoice}
                  onChange={handleVoiceChange}
                  disabled={isGenerating}
                >
                  {voices.length > 0 ? (
                    voices.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.language})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="vi-VN-HoaiMyNeural">
                        Hoài My (Nữ - Tự nhiên, truyền cảm)
                      </option>
                      <option value="vi-VN-NamMinhNeural">
                        Nam Minh (Nam - Trầm ấm, dứt khoát)
                      </option>
                    </>
                  )}
                </select>
              </div>

              {/* Speed Slider */}
              <div className="adgen-form-group">
                <label className="adgen-label">
                  <FiSliders /> Tốc độ đọc: <strong>{speed}x</strong>
                </label>
                <div className="adgen-slider-wrap">
                  <span className="adgen-slider-label">0.8x</span>
                  <input
                    type="range"
                    min="0.8"
                    max="1.5"
                    step="0.1"
                    value={speed}
                    onChange={handleSpeedChange}
                    disabled={isGenerating || isDirectVoiceConversion}
                    className="adgen-slider"
                  />
                  <span className="adgen-slider-label">1.5x</span>
                </div>
              </div>
            </div>
          )}

          <div className='adgen-emotion-control'>
            <div className='adgen-form-group'>
              <label className='adgen-label' htmlFor='voice-studio-emotion-cue'>
                <FiSmile /> {'C\u00e1ch th\u1ec3 hi\u1ec7n khi \u0111\u1ecdc:'}
              </label>
              <select
                id='voice-studio-emotion-cue'
                className='adgen-select'
                value={emotionCue}
                onChange={handleEmotionCueChange}
                disabled={isGenerating || !emotionCueAvailable}
              >
                <option value='none'>{'T\u1ef1 nhi\u00ean'}</option>
                <option value='laugh'>{'C\u01b0\u1eddi nh\u1eb9'}</option>
                <option value='sigh'>{'Th\u1edf d\u00e0i'}</option>
                <option value='clear_throat'>{'H\u1eafng gi\u1ecdng'}</option>
              </select>
              <span className='adgen-field-help'>
                {emotionCueAvailable
? 'Ch\u1ecdn m\u1ed9t s\u1eafc th\u00e1i \u0111\u1ec3 gi\u1ecdng \u0111\u1ecdc t\u1ef1 nhi\u00ean v\u00e0 ph\u00f9 h\u1ee3p h\u01a1n v\u1edbi n\u1ed9i dung.'
                  : isDirectVoiceConversion
? '\u0110\u1ed5i gi\u1ecdng tr\u1ef1c ti\u1ebfp s\u1ebd gi\u1eef c\u00e1ch th\u1ec3 hi\u1ec7n c\u1ee7a file \u00e2m thanh g\u1ed1c.'
: 'T\u00f9y ch\u1ecdn n\u00e0y ch\u1ec9 d\u00f9ng \u0111\u01b0\u1ee3c v\u1edbi nh\u1eefng gi\u1ecdng c\u00f3 h\u1ed7 tr\u1ee3 bi\u1ec3u c\u1ea3m.'}
              </span>
            </div>
          </div>

          {/* Audio result preview if generated */}
          {audioResult && (
            <div className="adgen-result-section">
              <label className="adgen-label">
                <FiCheck /> File âm thanh đã tạo:
              </label>
              <AudioPlayer
                src={audioResult.audio_url}
                voiceName={audioResult.voice_name}
                duration={audioResult.duration_seconds}
                downloadUrl={audioResult.download_url}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="adgen-modal-footer">
          <button
            type="button"
            className="adgen-btn adgen-btn--secondary"
            onClick={handleClose}
          >
            Đóng
          </button>
          <button
            type="button"
            className="adgen-btn adgen-btn--primary"
            onClick={handleGenerate}
            disabled={
              isGenerating ||
              isCleaning ||
              isTranscribing ||
              !canGenerate ||
              (voiceSource === "reference" && !referenceAudio)
            }
          >
            {isGenerating ? (
              <>
                <FiLoader className="adgen-spinner" /> Đang tạo âm thanh...
              </>
            ) : (
              <>
                <FiPlay /> {generateButtonLabel}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
