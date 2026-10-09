import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  FiX,
  FiPlay,
  FiVolume2,
  FiCheck,
  FiAlertCircle,
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
    return "Provider nhận dạng lời thoại chưa được cấu hình trên máy chủ.";
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
    VIDEO_AUDIO_EXTRACTION_FAILED: "Không thể trích xuất audio từ video.",
    VIDEO_AUDIO_EXTRACTION_TIMEOUT:
      "Trích xuất audio từ video mất quá nhiều thời gian.",
    VIDEO_EXTRACTED_AUDIO_INVALID: "Audio trích xuất từ video không hợp lệ.",
    FFMPEG_NOT_CONFIGURED: "Máy chủ chưa có FFmpeg để xử lý video.",
    FFPROBE_NOT_CONFIGURED: "Máy chủ chưa có FFprobe để kiểm tra video.",
    FFPROBE_TIMEOUT: "Kiểm tra video mất quá nhiều thời gian.",
    FFPROBE_FAILED: "Không thể kiểm tra metadata của video.",
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
    STT_AUDIO_TOO_LARGE: "File audio vượt quá giới hạn 10 MB.",
    STT_AUDIO_TOO_LONG:
      "Thời lượng audio vượt quá giới hạn cho phép. Vui lòng dùng file ngắn hơn.",
    STT_UNSUPPORTED_AUDIO_FORMAT: "Định dạng audio không được hỗ trợ.",
    STT_UNSUPPORTED_AUDIO_MIME: "Loại file audio không khớp với phần mở rộng.",
    STT_UNSUPPORTED_AUDIO_CODEC:
      "Codec audio chưa được hỗ trợ. Vui lòng chuyển file sang định dạng phù hợp.",
    STT_EMPTY_AUDIO: "File audio đang trống.",
    STT_INVALID_AUDIO: "File audio không hợp lệ hoặc bị hỏng.",
    STT_AUDIO_PROBE_NOT_CONFIGURED: "Máy chủ chưa có công cụ kiểm tra audio.",
    STT_AUDIO_PROBE_TIMEOUT:
      "Kiểm tra audio mất quá nhiều thời gian. Vui lòng thử file ngắn hơn.",
    STT_AUDIO_CONVERSION_FAILED: "Không thể chuyển đổi audio để nhận dạng.",
    STT_AUDIO_CONVERSION_NOT_CONFIGURED:
      "Máy chủ chưa có công cụ chuyển đổi audio.",
    STT_AUDIO_CONVERSION_TIMEOUT:
      "Chuyển đổi audio mất quá nhiều thời gian. Vui lòng thử file ngắn hơn.",
    STT_EMPTY_TRANSCRIPT: "Không nhận dạng được lời thoại trong file này.",
    STT_INVALID_LANGUAGE: "Mã ngôn ngữ không hợp lệ.",
    STT_PROVIDER_AUTHENTICATION_FAILED:
      "Provider nhận dạng lời thoại chưa xác thực được.",
    STT_PROVIDER_RATE_LIMITED:
      "Provider nhận dạng lời thoại đang quá tải. Vui lòng thử lại sau.",
    STT_PROVIDER_QUOTA_EXCEEDED: "Provider nhận dạng lời thoại đã hết hạn mức.",
    STT_PROVIDER_INVALID_RESPONSE:
      "Provider nhận dạng lời thoại trả về phản hồi không hợp lệ.",
    STT_PROVIDER_ERROR: "Provider nhận dạng lời thoại gặp lỗi.",
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
      "Provider giọng tham chiếu chưa được cấu hình trên máy chủ.",
    VOICE_REFERENCE_PROVIDER_TIMEOUT:
      "Tạo giọng tham chiếu mất quá nhiều thời gian. Vui lòng thử lại sau.",
    VOICE_REFERENCE_PROVIDER_BUSY:
      "Provider giọng tham chiếu đang bận. Vui lòng thử lại sau.",
    VOICE_REFERENCE_UNSUPPORTED_FORMAT:
      "Định dạng file giọng tham chiếu không được hỗ trợ.",
    VOICE_REFERENCE_MIME_MISMATCH:
      "Loại file giọng tham chiếu không khớp với phần mở rộng.",
    VOICE_REFERENCE_TOO_LARGE:
      "File audio tham chiếu tối đa 10 MB; video tham chiếu tối đa 50 MB.",
    VOICE_REFERENCE_TOO_LONG:
      "File giọng tham chiếu vượt quá giới hạn thời lượng cho phép.",
    VOICE_REFERENCE_INVALID: "File giọng tham chiếu không hợp lệ hoặc bị hỏng.",
    VOICE_REFERENCE_OUTPUT_INVALID:
      "Provider không tạo được audio đầu ra hợp lệ.",
    VOICE_REFERENCE_NO_AUDIO_STREAM:
      "Video giọng tham chiếu không có luồng âm thanh.",
  };
  return (
    messages[code] ||
    getUserErrorMessage(
      error,
      "Không thể tạo giọng đọc bằng file tham chiếu. Vui lòng thử lại.",
    )
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
        setError("Provider không trả về transcript. Vui lòng thử file khác.");
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
    setSelectedVoice(event.target.value);
  };

  const handleSpeedChange = (event) => {
    invalidateGeneratedAudio();
    setSpeed(parseFloat(event.target.value));
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
      setError("Vui lòng chọn file giọng tham chiếu trước khi tạo audio.");
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
      if (activeMode === "file" && !text) {
        result = await convertVoiceFileDirect({
          sourceFile: selectedSourceFile,
          sourceKind: selectedSourceKind,
          referenceAudio: voiceSource === "reference" ? referenceAudio : null,
          presetVoiceId: voiceSource === "builtin" ? selectedVoice : null,
        });
      } else if (voiceSource === "reference") {
        result = await generateReferenceVoiceover({
          text,
          referenceAudio,
        });
      } else {
        result = await generateVoiceover({
          text,
          voiceId: selectedVoice,
          speed,
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
        voiceSource === "reference"
          ? getReferenceVoiceErrorMessage(err)
          : getUserErrorMessage(
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
        ? "Tạo giọng đọc bằng giọng tham chiếu"
        : "Chọn file giọng tham chiếu"
      : activeMode !== "text"
        ? selectedSourceFile
          ? "Tạo giọng đọc từ file"
          : "Chọn file giọng nói"
        : "Tạo Voiceover";
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
                Độc lập với nguồn giọng
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
                File giọng nói
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
                  (isFileDragging ? "adgen-audio-dropzone--dragging" : "")
                }
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsFileDragging(true);
                }}
                onDragLeave={() => setIsFileDragging(false)}
                onDrop={handleSourceDrop}
              >
                <FiUploadCloud aria-hidden="true" />
                <strong>Thêm file giọng nói để nhận dạng lời thoại</strong>
                <span>
                  Hỗ trợ FLAC, M4A, MP3, OGG, WAV, MP4, MOV, WEBM — audio tối đa
                  10 MB / 5 phút; video tối đa 50 MB / 5 phút
                </span>
                <label
                  className="adgen-btn adgen-btn--secondary adgen-audio-file-label"
                  htmlFor={sourceInputId}
                >
                  <FiUploadCloud /> Chọn file giọng nói
                </label>
                <input
                  ref={sourceInputRef}
                  id={sourceInputId}
                  className="adgen-visually-hidden"
                  type="file"
                  accept={VOICE_FILE_ACCEPT}
                  onChange={handleSourceFileChange}
                />
              </div>

              {selectedSourceFile && (
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
                  <div className="adgen-selected-audio__actions">
                    <button
                      type="button"
                      className="adgen-btn-link"
                      onClick={() => sourceInputRef.current?.click()}
                      disabled={isTranscribing || isGenerating}
                    >
                      Thay file
                    </button>
                    <button
                      type="button"
                      className="adgen-btn-link adgen-btn-link--danger"
                      onClick={() => replaceSelectedSource(null)}
                      disabled={isTranscribing || isGenerating}
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
              )}

              {pendingTranscript && (
                <div className="adgen-transcript-confirm">
                  <span>
                    Đã có nội dung lời thoại đã chỉnh sửa. Bạn có muốn thay bằng
                    transcript mới không?
                  </span>
                  <div>
                    <button
                      type="button"
                      className="adgen-btn-link"
                      onClick={() => applyTranscript(pendingTranscript)}
                    >
                      Dùng transcript mới
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
                File được định tuyến theo loại media, rồi được backend kiểm tra
                trước khi nhận dạng. Transcript có thể chỉnh sửa trước khi tạo
                giọng đọc.
              </p>
            </div>
          )}
          {/* Extraction status notices */}
          {activeMode === "text" && extractionMeta?.status === "success" && (
            <div className="adgen-cleaner-notice">
              <span className="adgen-cleaner-badge">
                <FiCheck /> Đã trích xuất {extractionMeta.count} đoạn lời thoại
                từ các phân cảnh (đã loại bỏ chỉ dẫn hình ảnh, camera, hiệu ứng)
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
                  ? "Transcript đã được chỉnh sửa"
                  : "Transcript có thể chỉnh sửa"}
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
                <p className="adgen-eyebrow">Nguồn giọng đọc</p>
                <h4 id="voice-studio-voice-source">
                  Chọn giọng sẽ được sử dụng
                </h4>
              </div>
              <span className="adgen-source-section__hint">
                Không đổi nội dung đã chọn
              </span>
            </div>

            <div
              className="adgen-voice-source-tabs"
              role="tablist"
              aria-label="Nguồn giọng đọc"
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
                Giọng có sẵn
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
                Giọng tham chiếu của tôi
              </button>
            </div>

            {voiceSource === "builtin" ? (
              <div className="adgen-voice-source-panel">
                <strong>Giọng TTS có sẵn</strong>
                <span>Tiếp tục dùng selector giọng và Edge TTS hiện tại.</span>
              </div>
            ) : (
              <div className="adgen-reference-voice-panel">
                <div className="adgen-reference-voice-panel__header">
                  <div>
                    <strong>File giọng tham chiếu</strong>
                    <span>
                      File audio hoặc video chỉ là nguồn giọng, không phải nội
                      dung cần đọc.
                    </span>
                  </div>
                  <span className="adgen-status-badge">Sẵn sàng</span>
                </div>
                <p className="adgen-reference-voice-panel__note">
                  VieNeu-TTS local sẽ lấy giọng từ audio hoặc track âm thanh
                  trong video. Video phải có audio, tối đa 50 MB và 60 giây;
                  file không được lưu lại sau request.
                </p>
                <label
                  className="adgen-btn adgen-btn--secondary adgen-reference-audio-label"
                  htmlFor="voice-studio-reference-audio-input"
                >
                  <FiUploadCloud /> Chọn audio hoặc video tham chiếu
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
                    <div className="adgen-selected-audio__actions">
                      <button
                        type="button"
                        className="adgen-btn-link"
                        onClick={() => referenceAudioInputRef.current?.click()}
                        disabled={isGenerating}
                      >
                        Thay file
                      </button>
                      <button
                        type="button"
                        className="adgen-btn-link adgen-btn-link--danger"
                        onClick={() => replaceReferenceAudio(null)}
                        disabled={isGenerating}
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
          {/* Settings Grid */}
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
                    disabled={isGenerating}
                    className="adgen-slider"
                  />
                  <span className="adgen-slider-label">1.5x</span>
                </div>
              </div>
            </div>
          )}

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
