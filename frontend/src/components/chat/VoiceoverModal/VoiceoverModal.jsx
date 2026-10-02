import React, { useState, useEffect } from "react";
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
} from "react-icons/fi";
import {
  getAvailableVoices,
  cleanScript,
  generateVoiceover,
} from "../../../services/api/voiceoverApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import AudioPlayer from "./AudioPlayer";
import "./VoiceoverModal.css";

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
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleanedStats, setCleanedStats] = useState(null);
  const [extractionMeta, setExtractionMeta] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [audioResult, setAudioResult] = useState(null);

  useEffect(() => {
    if (!isOpen) return;

    setError(null);
    setAudioResult(null);
    setExtractionMeta(null);
    const safeInitial = typeof initialText === "string" ? initialText : "";
    setOriginalScript(safeInitial);

    // Fetch voices
    getAvailableVoices()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setVoices(data);
          if (!selectedVoice) setSelectedVoice(data[0].id);
        }
      })
      .catch((err) => {
        console.warn("Could not load voices, using fallback default:", err);
      });

    // Auto extract pure spoken dialogue from the script
    if (safeInitial.trim()) {
      setIsCleaning(true);
      cleanScript(safeInitial)
        .then((res) => {
          if (res) {
            if (res.status === "no_dialogue") {
              setTextToRead("");
              setExtractionMeta({
                status: "no_dialogue",
                warning: res.warning_message || "Không tìm thấy cấu trúc lời thoại rõ ràng (VO / Lời thoại). Vui lòng nhập lời thoại cần đọc vào ô bên dưới.",
                count: 0,
              });
            } else {
              setTextToRead(res.cleaned_script || "");
              setExtractionMeta({
                status: res.status || "success",
                warning: res.warning_message,
                count: res.dialogue_blocks_count || 1,
              });
              setCleanedStats({
                removed: res.dialogue_blocks_count || 1,
                savedChars: Math.max(0, (res.original_length || 0) - (res.cleaned_length || 0)),
              });
            }
          }
        })
        .catch((err) => {
          console.warn("Auto script extraction failed, keeping raw:", err);
          setTextToRead(safeInitial);
        })
        .finally(() => {
          setIsCleaning(false);
        });
    } else {
      setTextToRead("");
    }
  }, [isOpen, initialText]);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    const trimmed = (textToRead || "").trim();
    if (!trimmed) {
      setError("Vui lòng nhập hoặc giữ lại nội dung lời thoại để tạo audio.");
      return;
    }

    try {
      setIsGenerating(true);
      setError(null);

      const result = await generateVoiceover({
        text: trimmed,
        voiceId: selectedVoice,
        speed,
        messageId,
      });

      setAudioResult(result);
      if (onGenerated) {
        onGenerated(result);
      }
    } catch (err) {
      console.error("Generate voiceover failed:", err);
      const safeErrorMessage = getUserErrorMessage(
        err,
        "Không thể sinh audio lúc này. Vui lòng kiểm tra lại nội dung và thử lại."
      );
      setError(safeErrorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRestoreOriginal = () => {
    setTextToRead(originalScript);
    setCleanedStats(null);
  };

  const modalContent = (
    <div className="adgen-modal-overlay" onClick={onClose}>
      <div
        className="adgen-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="adgen-modal-header">
          <div className="adgen-modal-title">
            <div className="adgen-modal-icon">🎙️</div>
            <div>
              <h3>AdGen Voice Studio</h3>
              <p>Chuyển kịch bản quảng cáo thành giọng đọc chuyên nghiệp</p>
            </div>
          </div>
          <button
            type="button"
            className="adgen-modal-close"
            onClick={onClose}
            aria-label="Đóng"
          >
            <FiX />
          </button>
        </div>

        {/* Body */}
        <div className="adgen-modal-body">
          {error && (
            <div className="adgen-alert adgen-alert--error">
              <FiAlertCircle />
              <span>{typeof error === "string" ? error : (error?.message || String(error))}</span>
            </div>
          )}

          {/* Extraction status notices */}
          {extractionMeta?.status === "success" && (
            <div className="adgen-cleaner-notice">
              <span className="adgen-cleaner-badge">
                <FiCheck /> Đã trích xuất {extractionMeta.count} đoạn lời thoại từ các phân cảnh (đã loại bỏ chỉ dẫn hình ảnh, camera, hiệu ứng)
              </span>
              <button
                type="button"
                className="adgen-btn-link"
                onClick={handleRestoreOriginal}
                title="Khôi phục toàn bộ văn bản gốc"
              >
                Xem văn bản gốc
              </button>
            </div>
          )}

          {extractionMeta?.status === "no_dialogue" && (
            <div className="adgen-alert adgen-alert--warning" style={{ background: "rgba(245, 158, 11, 0.15)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "#fbbf24" }}>
              <FiAlertCircle />
              <div style={{ flex: 1 }}>
                <span>{extractionMeta.warning}</span>
                <button
                  type="button"
                  className="adgen-btn-link"
                  style={{ display: "block", marginTop: "4px", color: "#60a5fa" }}
                  onClick={handleRestoreOriginal}
                >
                  Dán toàn bộ văn bản gốc vào ô
                </button>
              </div>
            </div>
          )}

          {extractionMeta?.status === "uncertain" && (
            <div className="adgen-cleaner-notice" style={{ background: "rgba(59, 130, 246, 0.12)", borderColor: "rgba(59, 130, 246, 0.3)", color: "#93c5fd" }}>
              <span className="adgen-cleaner-badge">
                <FiAlertCircle /> {extractionMeta.warning}
              </span>
            </div>
          )}

          {/* Text dialogue editor */}
          <div className="adgen-form-group">
            <label className="adgen-label">
              <FiEdit3 /> Lời thoại sẽ được đọc (Bạn có thể chỉnh sửa tự do):
            </label>
            <div className="adgen-textarea-wrap">
              <textarea
                className="adgen-textarea"
                rows={5}
                value={textToRead}
                onChange={(e) => setTextToRead(e.target.value)}
                placeholder="Nhập hoặc dán lời thoại quảng cáo cần đọc vào đây..."
                disabled={isCleaning || isGenerating}
              />
              <span className="adgen-char-count">
                {(textToRead || "").length} / 10000 ký tự
              </span>
            </div>
          </div>

          {/* Settings Grid */}
          <div className="adgen-settings-grid">
            {/* Voice Select */}
            <div className="adgen-form-group">
              <label className="adgen-label">
                <FiVolume2 /> Chọn giọng đọc:
              </label>
              <select
                className="adgen-select"
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
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
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  disabled={isGenerating}
                  className="adgen-slider"
                />
                <span className="adgen-slider-label">1.5x</span>
              </div>
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
            onClick={onClose}
          >
            Đóng
          </button>
          <button
            type="button"
            className="adgen-btn adgen-btn--primary"
            onClick={handleGenerate}
            disabled={isGenerating || isCleaning || !(textToRead || "").trim()}
          >
            {isGenerating ? (
              <>
                <FiLoader className="adgen-spinner" /> Đang tạo âm thanh...
              </>
            ) : (
              <>
                <FiPlay /> Tạo Voiceover
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}