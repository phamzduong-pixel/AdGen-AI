import { useCallback, useEffect, useRef, useState } from "react";
import {
  FiArrowUp,
  FiLoader,
  FiMic,
  FiMicOff,
  FiPaperclip,
  FiSliders,
  FiSquare,
} from "react-icons/fi";

import PromptSelector from "../PromptSelector";
import BrandSelector from "../../brand/BrandSelector";
import AdBriefForm from "../AdBriefForm";
import AttachmentPreview from "./AttachmentPreview";
import "./ChatInput.css";
import useToast from "../../ui/Toast/useToast";
import Modal from "../../ui/Modal/Modal";
import { buildTemplateBrief } from "../../../utils/adTemplate";

function ChatInput({
  conversationId,
  onSend,
  promptType = "facebook",
  onPromptTypeChange,
  disabled = false,
  isStreaming = false,
  onStop,
  templateRequest,
  onTemplateHandled,
  brands = [],
  brandId = null,
  onBrandChange,
}) {
  const toast = useToast();
  const draftKey = conversationId
    ? `chat-draft-${conversationId}`
    : "chat-draft-new";
  const [text, setText] = useState(() => localStorage.getItem(draftKey) || "");
  const [attachments, setAttachments] = useState([]);
  const [attachmentError, setAttachmentError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [adBrief, setAdBrief] = useState(null);
  const [hasAdBriefDraft, setHasAdBriefDraft] = useState(false);
  const [isAdBriefOpen, setIsAdBriefOpen] = useState(false);
  const [adBriefFormVersion, setAdBriefFormVersion] = useState(0);
  const [templateDecision, setTemplateDecision] = useState(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const processedTemplateRequestRef = useRef(null);

  const autoResize = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, []);

  const speechRecognitionRef = useRef(null);
  const speechBaseTextRef = useRef("");
  const [isListening, setIsListening] = useState(false);
  const speechSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  useEffect(() => {
    if (!speechSupported) return undefined;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "vi-VN";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let index = 0; index < event.results.length; index += 1) {
        const transcript = event.results[index][0]?.transcript || "";
        if (event.results[index].isFinal) finalTranscript += transcript;
        else interimTranscript += transcript;
      }

      const nextText = [
        speechBaseTextRef.current,
        finalTranscript,
        interimTranscript,
      ]
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

      setText(nextText);
      requestAnimationFrame(autoResize);
    };
    recognition.onerror = (event) => {
      setIsListening(false);
      if (!["aborted", "no-speech"].includes(event.error)) {
        toast.error(
          event.error === "not-allowed"
            ? "Vui lòng cấp quyền sử dụng micro cho trình duyệt."
            : "Không thể nhận diện giọng nói. Vui lòng thử lại."
        );
      }
    };
    recognition.onend = () => setIsListening(false);
    speechRecognitionRef.current = recognition;

    return () => {
      recognition.onend = null;
      recognition.abort();
      speechRecognitionRef.current = null;
    };
  }, [autoResize, speechSupported, toast]);

  const toggleSpeechRecognition = () => {
    if (!speechSupported) {
      toast.error("Trình duyệt này chưa hỗ trợ nhập bằng giọng nói.");
      return;
    }

    const recognition = speechRecognitionRef.current;
    if (!recognition) return;

    if (isListening) {
      recognition.stop();
      return;
    }

    speechBaseTextRef.current = text.trim();
    try {
      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  useEffect(() => {
    if (text) localStorage.setItem(draftKey, text);
    else localStorage.removeItem(draftKey);
  }, [draftKey, text]);

  const applyTemplate = useCallback(
    (template, replaceText) => {
      onPromptTypeChange?.(template.platform);
      setAdBrief(buildTemplateBrief(template));
      setHasAdBriefDraft(true);
      setAdBriefFormVersion((current) => current + 1);
      setIsAdBriefOpen(true);
      if (replaceText) {
        setText(template.prompt_template || "");
        requestAnimationFrame(autoResize);
      }
      setTemplateDecision(null);
      onTemplateHandled?.();
      requestAnimationFrame(() => textareaRef.current?.focus());
    },
    [autoResize, onPromptTypeChange, onTemplateHandled],
  );

  useEffect(() => {
    if (
      !templateRequest?.template ||
      processedTemplateRequestRef.current === templateRequest.id
    ) {
      return;
    }
    processedTemplateRequestRef.current = templateRequest.id;
    if (text.trim()) {
      // Apply one external navigation request to the local composer state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTemplateDecision(templateRequest.template);
      return;
    }
    applyTemplate(templateRequest.template, true);
  }, [applyTemplate, templateRequest, text]);

  const handleFilesSelected = (event) => {
    const selectedFiles = Array.from(event.target.files || []);
    event.target.value = "";
    setAttachmentError("");
    const availableSlots = 5 - attachments.length;

    if (selectedFiles.length > availableSlots) {
      setAttachmentError("Chỉ được đính kèm tối đa 5 tệp.");
    }

    const allowedExtensions = /\.(png|jpe?g|webp|pdf|docx|txt|mp4|mov|webm)$/i;
    const validFiles = selectedFiles.slice(0, availableSlots).filter((file) => {
      if (!allowedExtensions.test(file.name)) {
        setAttachmentError(`Định dạng “${file.name}” không được hỗ trợ.`);
        return false;
      }
      const isVideo = /\.(mp4|mov|webm)$/i.test(file.name) || file.type.startsWith("video/");
      const maxSize = isVideo ? 50 * 1024 * 1024 : 10 * 1024 * 1024;
      if (file.size > maxSize) {
        setAttachmentError(
          `Tệp “${file.name}” vượt quá giới hạn ${isVideo ? "50 MB" : "10 MB"}.`
        );
        return false;
      }
      return true;
    });

    setAttachments((current) => [
      ...current,
      ...validFiles.map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
        file,
        previewUrl:
          file.type.startsWith("image/") || file.type.startsWith("video/")
            ? URL.createObjectURL(file)
            : "",
      })),
    ]);
  };

  const removeAttachment = (id) => {
    setAttachments((current) => {
      const removed = current.find((item) => item.id === id);
      if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl);
      return current.filter((item) => item.id !== id);
    });
  };

  const handleSend = async () => {
    const content =
      text.trim() || (attachments.length ? "Đã gửi tệp đính kèm." : "");
    if (!content || disabled || isSending) return;
    if ((adBrief?.platform || promptType) === "other" && !adBrief?.platform_name?.trim()) {
      toast.error("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung.");
      return;
    }

    const payload = {
      content,
      promptType: adBrief?.platform || promptType,
      platformName: adBrief?.platform_name || "",
      attachments: attachments.map((item) => item.file),
      adBrief,
      brandId,
    };

    // Clean up attachment preview object URLs
    attachments.forEach((item) => {
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    });

    // Reset input states immediately so the composer is cleared while AI is generating
    setText("");
    setAttachments([]);
    setAdBrief(null);
    setHasAdBriefDraft(false);
    setIsAdBriefOpen(false);
    setAdBriefFormVersion((current) => current + 1);
    localStorage.removeItem(draftKey);
    localStorage.removeItem("chat-draft-new");
    setAttachmentError("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setIsSending(true);

    try {
      const sent = await onSend?.(payload);
      if (sent === false) {
        throw new Error("Không thể gửi tin nhắn hoặc tải tệp đính kèm.");
      }
    } catch (error) {
      const message = error.message || "Không thể gửi tin nhắn.";
      setAttachmentError(message);
      toast.error(message);
    } finally {
      setIsSending(false);
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
        }
      });
    }
  };

  return (
    <div className="chat-composer-wrapper">
      <div className="chat-composer">
        <AdBriefForm
          key={adBriefFormVersion}
          open={isAdBriefOpen}
          value={adBrief}
          onApply={setAdBrief}
          onDraftChange={setHasAdBriefDraft}
          onClear={() => {
            setAdBrief(null);
            setHasAdBriefDraft(false);
            setAdBriefFormVersion((current) => current + 1);
          }}
          onClose={() => setIsAdBriefOpen(false)}
          disabled={disabled || isSending}
        />
        <AttachmentPreview files={attachments} onRemove={removeAttachment} />
        {attachmentError && (
          <div className="chat-composer__attachment-error" role="alert">
            {attachmentError}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="chat-composer__textarea"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            requestAnimationFrame(autoResize);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSend();
            }
          }}
          placeholder="Nhập yêu cầu tạo nội dung..."
          rows={1}
          disabled={disabled || isSending}
        />

        <div className="chat-composer__toolbar">
          <div className="chat-composer__left">
            <button
              type="button"
              className="chat-composer__icon-button"
              disabled={disabled || isSending || attachments.length >= 5}
              title="Đính kèm tệp"
              aria-label="Đính kèm tệp"
              onClick={() => fileInputRef.current?.click()}
            >
              <FiPaperclip />
            </button>
            <input
              ref={fileInputRef}
              className="chat-composer__file-input"
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.txt,.mp4,.mov,.webm,video/mp4,video/quicktime,video/webm"
              onChange={handleFilesSelected}
            />

            <button
              type="button"
              className={`chat-composer__icon-button chat-composer__brief-button ${
                adBrief || hasAdBriefDraft ? "is-active" : ""
              }`}
              data-ad-brief-trigger
              disabled={disabled || isSending}
              title="Thông tin quảng cáo"
              aria-label="Thông tin quảng cáo"
              aria-expanded={isAdBriefOpen}
              onClick={() => setIsAdBriefOpen((current) => !current)}
            >
              <FiSliders />
              {(adBrief || hasAdBriefDraft) && (
                <span
                  className="chat-composer__brief-status"
                  aria-label="Đã áp dụng thông tin quảng cáo"
                />
              )}
            </button>

            <PromptSelector
              value={promptType}
              platformName={adBrief?.platform_name || ""}
              onPlatformNameChange={(value) => setAdBrief((current) => ({
                ...(current || {}),
                platform: "other",
                platform_name: value,
              }))}
              onChange={(value) => {
                onPromptTypeChange?.(value);
                setAdBrief((current) => value === "other"
                  ? { ...(current || {}), platform: value, platform_name: current?.platform_name || "" }
                  : current?.platform === "other" ? null : current);
              }}
              disabled={disabled || isSending}
              compact
            />

            <BrandSelector
              brands={brands}
              value={brandId}
              onChange={onBrandChange}
              disabled={disabled || isSending}
              compact
            />
          </div>

          <div className="chat-composer__right">
            <button
              type="button"
              className={`chat-composer__icon-button chat-composer__mic-button ${
                isListening ? "is-listening" : ""
              }`}
              onClick={toggleSpeechRecognition}
              disabled={disabled || isSending || isStreaming}
              title={
                isListening
                  ? "Dừng nhập bằng giọng nói"
                  : speechSupported
                    ? "Nhập bằng giọng nói"
                    : "Trình duyệt chưa hỗ trợ nhập bằng giọng nói"
              }
              aria-label={
                isListening
                  ? "Dừng nhập bằng giọng nói"
                  : "Nhập bằng giọng nói"
              }
              aria-pressed={isListening}
            >
              {isListening ? <FiMicOff /> : <FiMic />}
            </button>

            <button
              type="button"
              className={`chat-composer__send-button ${
              isStreaming ? "chat-composer__send-button--stop" : ""
            }`}
            onClick={isStreaming ? onStop : handleSend}
            disabled={
              isStreaming
                ? false
                : disabled ||
                  isSending ||
                  (!text.trim() && !attachments.length)
            }
            title={isStreaming ? "Dừng tạo nội dung" : "Gửi tin nhắn"}
            aria-label={isStreaming ? "Dừng tạo nội dung" : "Gửi tin nhắn"}
          >
            {isStreaming ? (
              <FiSquare />
            ) : isSending ? (
              <FiLoader className="chat-composer__spinner" />
            ) : (
              <FiArrowUp />
            )}
            </button>
          </div>
        </div>
      </div>

      <p className="chat-composer__hint">
        AI có thể mắc lỗi. Tệp DOCX chỉ được lưu và chưa được AI đọc nội dung.
      </p>

      <Modal
        open={Boolean(templateDecision)}
        title="Áp dụng mẫu quảng cáo?"
        onClose={() => {
          setTemplateDecision(null);
          onTemplateHandled?.();
        }}
        footer={
          <div className="chat-composer__template-actions">
            <button
              type="button"
              onClick={() => {
                setTemplateDecision(null);
                onTemplateHandled?.();
              }}
            >
              Hủy
            </button>
            <button
              type="button"
              onClick={() => applyTemplate(templateDecision, false)}
            >
              Giữ nội dung hiện tại
            </button>
            <button
              type="button"
              className="is-primary"
              onClick={() => applyTemplate(templateDecision, true)}
            >
              Thay thế nội dung
            </button>
          </div>
        }
      >
        <p className="chat-composer__template-copy">
          Ô chat đang có nội dung chưa gửi. Bạn muốn giữ nội dung hiện tại và
          chỉ áp dụng cài đặt của mẫu, hay thay thế bằng gợi ý “
          {templateDecision?.title}”?
        </p>
      </Modal>
    </div>
  );
}

export default ChatInput;
