import { useEffect, useRef, useState } from "react";
import { FiCheck, FiCopy, FiEdit2, FiX } from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import "./MessageBubble.css";
import MessageAttachments from "./MessageAttachments";
import MessageActions from "../MessageActions";
import AudioPlayer from "../VoiceoverModal/AudioPlayer";

function MessageBubble({
  role = "assistant",
  content = "",
  time = "",
  isStreaming = false,
  onEdit,
  onCopy,
  isCopied = false,
  attachments = [],
  onAction,
  onToggleSave,
  onEvaluate,
  onGenerateVariants,
  onCopied,
  onCheckBrand,
  onOpenEditor,
  onVoiceover,
  audioData = null,
  isSaved = false,
  savePending = false,
  actionsDisabled = false,
}) {
  const isUser = role === "user";

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(content);
  const [isSaving, setIsSaving] = useState(false);

  const textareaRef = useRef(null);

  useEffect(() => {
    if (!isEditing) return;

    const textarea = textareaRef.current;

    if (!textarea) return;

    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }, [isEditing]);

  const handleCopy = async () => {
    if (onCopy) {
      await onCopy(content);
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
    } catch (error) {
      console.error("Không thể sao chép tin nhắn:", error);
    }
  };

  const handleStartEdit = () => {
    setEditText(content);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setEditText(content);
    setIsEditing(false);
  };

  const handleEditChange = (event) => {
    setEditText(event.target.value);

    const textarea = event.target;

    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  };

  const handleSaveEdit = async () => {
    const normalizedContent = editText.trim();

    if (
      !normalizedContent ||
      normalizedContent === content.trim() ||
      isSaving
    ) {
      if (normalizedContent === content.trim()) {
        setIsEditing(false);
      }

      return;
    }

    try {
      setIsSaving(true);

      await onEdit?.(normalizedContent);

      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      handleCancelEdit();
      return;
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSaveEdit();
    }
  };

  return (
    <article
      className={`message ${isUser ? "message--user" : "message--assistant"}`}
    >
      <div className="message__container">
        {isUser && isEditing ? (
          <div className="message-edit">
            <textarea
              ref={textareaRef}
              className="message-edit__textarea"
              value={editText}
              onChange={handleEditChange}
              onKeyDown={handleEditKeyDown}
              disabled={isSaving}
              rows={1}
            />

            <div className="message-edit__actions">
              <span className="message-edit__hint">
                Enter để lưu · Shift + Enter để xuống dòng
              </span>

              <button
                type="button"
                className="message-edit__button"
                onClick={handleCancelEdit}
                disabled={isSaving}
                title="Hủy chỉnh sửa"
                aria-label="Hủy chỉnh sửa"
              >
                <FiX />
              </button>

              <button
                type="button"
                className="message-edit__button message-edit__button--save"
                onClick={handleSaveEdit}
                disabled={isSaving || !editText.trim()}
                title="Lưu chỉnh sửa"
                aria-label="Lưu chỉnh sửa"
              >
                <FiCheck />
              </button>
            </div>
          </div>
        ) : (
          <>
            <MessageAttachments attachments={attachments} />
            <div className="message__content">
              {isUser ? (
                <p className="message__plain-text">{content}</p>
              ) : (
                <div className="message__markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                </div>
              )}

              {isStreaming && (
                <span
                  className="message__cursor"
                  aria-label="AI đang trả lời"
                />
              )}

              {audioData && (
                <AudioPlayer
                  src={audioData.audio_url}
                  voiceName={audioData.voice_name}
                  duration={audioData.duration_seconds}
                  downloadUrl={audioData.download_url}
                />
              )}
            </div>

            <div className="message__footer">
              {time && <time className="message__time">{time}</time>}

              {isUser ? (
                <div className="message__actions">
                {onEdit && (
                  <button
                    type="button"
                    className="message__action-button"
                    onClick={handleStartEdit}
                    title="Chỉnh sửa tin nhắn"
                    aria-label="Chỉnh sửa tin nhắn"
                  >
                    <FiEdit2 />
                  </button>
                )}

                <button
                  type="button"
                  className="message__action-button"
                  onClick={handleCopy}
                  title={isCopied ? "Đã sao chép" : "Sao chép"}
                  aria-label={isCopied ? "Đã sao chép" : "Sao chép"}
                >
                  {isCopied ? <FiCheck /> : <FiCopy />}
                </button>
                </div>
              ) : (
                <MessageActions
                  content={content}
                  onAction={onAction}
                  onToggleSave={onToggleSave}
                  onEvaluate={onEvaluate}
                  onGenerateVariants={onGenerateVariants}
                  onCopied={onCopied}
                  onCheckBrand={onCheckBrand}
                  onOpenEditor={onOpenEditor}
                  onVoiceover={onVoiceover}
                  isSaved={isSaved}
                  savePending={savePending}
                  disabled={actionsDisabled || isStreaming}
                />
              )}
            </div>
          </>
        )}
      </div>
    </article>
  );
}

export default MessageBubble;