import { useCallback, useEffect, useRef, useState } from "react";

import {
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi,
  getConversations,
  renameConversation as renameConversationApi,
  togglePinConversation as togglePinConversationApi,
  updateConversationBrand as updateConversationBrandApi,
} from "../services/api/conversationApi";

import {
  clearConversationMessages as clearConversationMessagesApi,
  editMessageStream,
  getMessages,
  sendMessageStream,
} from "../services/api/chatApi";
import { uploadFiles } from "../services/api/uploadApi";
import useToast from "../components/ui/Toast/useToast";
import { getUserErrorMessage } from "../utils/apiError";
import { getPreferences } from "../utils/settingsStorage";

const formatTime = (dateValue = null) => {
  let date = new Date();

  if (dateValue) {
    const normalizedDateValue =
      typeof dateValue === "string" &&
      !dateValue.endsWith("Z") &&
      !dateValue.includes("+")
        ? `${dateValue}Z`
        : dateValue;

    date = new Date(normalizedDateValue);
  }

  if (Number.isNaN(date.getTime())) {
    date = new Date();
  }

  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
};

const normalizeMessage = (message) => ({
  ...message,
  time: formatTime(message.created_at ?? message.time),
});

const MESSAGE_ACTION_PROMPTS = {
  shorter:
    "Hãy viết lại câu trả lời AI ngay trước đó ngắn gọn và súc tích hơn. Giữ nguyên thông tin quan trọng, cấu trúc Markdown và không nhắc lại yêu cầu này.",
  longer:
    "Hãy phát triển câu trả lời AI ngay trước đó chi tiết và đầy đủ hơn. Bổ sung giá trị thực tế, giữ đúng dữ kiện và cấu trúc Markdown.",
  professional:
    "Hãy tạo một phiên bản mới của câu trả lời AI ngay trước đó với giọng văn chuyên nghiệp, rõ ràng và đáng tin cậy hơn.",
  friendly:
    "Hãy tạo một phiên bản mới của câu trả lời AI ngay trước đó với giọng văn thân thiện, tự nhiên và gần gũi hơn.",
  alternative:
    "Hãy tạo một phương án hoàn toàn khác cho câu trả lời AI ngay trước đó. Giữ nguyên mục tiêu và dữ kiện, nhưng thay đổi hook, cách diễn đạt và hướng triển khai.",
  improve:
    "Hãy tạo một bản cải thiện của câu trả lời AI ngay trước đó. Giữ nguyên dữ kiện gốc, làm rõ lợi ích, tăng sức thuyết phục, cải thiện CTA và trình bày chuyên nghiệp hơn.",
};

function useChat() {
  const toast = useToast();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);

  const [messages, setMessages] = useState([]);

  const [isTyping, setIsTyping] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const [error, setError] = useState("");

  const abortControllerRef = useRef(null);

  const sortConversations = (items) =>
    [...items].sort((left, right) => {
      if (Boolean(left.is_pinned) !== Boolean(right.is_pinned)) {
        return left.is_pinned ? -1 : 1;
      }
      return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
    });

  const loadMessages = useCallback(async (conversationId, options = {}) => {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    const { silent = false } = options;
    if (!silent) {
      setIsLoadingMessages(true);
    }
    setError("");

    try {
      const data = await getMessages(conversationId);

      const messageList = Array.isArray(data) ? data : (data.messages ?? []);

      setMessages(messageList.map(normalizeMessage));
    } catch (loadError) {
      console.error("Lỗi tải tin nhắn:", loadError);

      setMessages([]);

      const message = getUserErrorMessage(
        loadError,
        "Không thể tải lịch sử tin nhắn.",
      );
      setError(message);
      toast.error(message);
    } finally {
      setIsLoadingMessages(false);
    }
  }, [toast]);

  const loadConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    setError("");

    try {
      const data = await getConversations();

      const conversationList = Array.isArray(data)
        ? data
        : (data.conversations ?? []);

      setConversations(sortConversations(conversationList));

      if (conversationList.length === 0) {
        setSelectedConversation(null);
        setMessages([]);
        return;
      }

      setSelectedConversation((currentId) => {
        const currentStillExists = conversationList.some(
          (conversation) => conversation.id === currentId,
        );

        if (currentStillExists) {
          return currentId;
        }

        if (!getPreferences().openLatestConversation) {
          return null;
        }

        return conversationList[0].id;
      });
    } catch (loadError) {
      console.error("Lỗi tải hội thoại:", loadError);

      setConversations([]);
      setSelectedConversation(null);

      const message = getUserErrorMessage(
        loadError,
        "Không thể tải danh sách hội thoại.",
      );
      setError(message);
      toast.error(message);
    } finally {
      setIsLoadingConversations(false);
    }
  }, [toast]);

  useEffect(() => {
    // Initial remote data synchronization is intentionally performed on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (selectedConversation) {
      // Synchronize messages whenever the active remote conversation changes.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadMessages(selectedConversation);
    }
  }, [selectedConversation, loadMessages]);

  const getApiErrorMessage = (error, fallbackMessage) => {
    const message = getUserErrorMessage(error, fallbackMessage);
    if (message) toast.error(message);
    return message;
  };

  const createConversation = async (brandId = null) => {
    if (isTyping) return null;

    setError("");

    try {
      const newConversation = await createConversationApi(
        "Cuộc trò chuyện mới",
        Number.isInteger(brandId) ? brandId : null,
      );

      if (!newConversation?.id) {
        throw new Error("Backend không trả về ID hội thoại.");
      }

      setConversations((previous) => [
        newConversation,
        ...previous.filter(
          (conversation) => conversation.id !== newConversation.id,
        ),
      ]);

      setSelectedConversation(newConversation.id);

      setMessages([]);

      return newConversation;
    } catch (createError) {
      console.error("Lỗi tạo hội thoại:", createError);

      setError(
        getApiErrorMessage(createError, "Không thể tạo cuộc trò chuyện mới."),
      );

      return null;
    }
  };

  const selectConversation = (id) => {
    if (isTyping) return;

    if (id === selectedConversation) {
      return;
    }

    setSelectedConversation(id);
    localStorage.setItem("currentConversationId", String(id));
  };

  const renameConversation = async (id, title) => {
    setError("");
    try {
      const updated = await renameConversationApi(id, title);
      setConversations((previous) =>
        sortConversations(previous.map((item) => (item.id === id ? updated : item))),
      );
      return updated;
    } catch (actionError) {
      setError(getApiErrorMessage(actionError, "Không thể đổi tên cuộc trò chuyện."));
      throw actionError;
    }
  };

  const deleteConversation = async (id) => {
    setError("");
    try {
      await deleteConversationApi(id);
      const remaining = conversations.filter((item) => item.id !== id);
      setConversations(remaining);
      if (selectedConversation === id) {
        const nextId = remaining[0]?.id ?? null;
        setSelectedConversation(nextId);
        if (nextId) {
          localStorage.setItem("currentConversationId", String(nextId));
        } else {
          setMessages([]);
          localStorage.removeItem("currentConversationId");
        }
      } else if (localStorage.getItem("currentConversationId") === String(id)) {
        localStorage.removeItem("currentConversationId");
      }
    } catch (actionError) {
      setError(getApiErrorMessage(actionError, "Không thể xóa cuộc trò chuyện."));
      throw actionError;
    }
  };

  const togglePinConversation = async (id, isPinned) => {
    setError("");
    try {
      const updated = await togglePinConversationApi(id, isPinned);
      setConversations((previous) =>
        sortConversations(previous.map((item) => (item.id === id ? updated : item))),
      );
      return updated;
    } catch (actionError) {
      setError(getApiErrorMessage(actionError, "Không thể cập nhật trạng thái ghim."));
      throw actionError;
    }
  };

  const clearConversationMessages = async (id) => {
    setError("");
    try {
      await clearConversationMessagesApi(id);
      if (selectedConversation === id) setMessages([]);
      await loadConversations();
    } catch (actionError) {
      setError(
        getApiErrorMessage(actionError, "Không thể xóa toàn bộ tin nhắn."),
      );
      throw actionError;
    }
  };

  const setConversationBrand = async (brandId) => {
    if (!selectedConversation || isTyping) return null;
    try {
      const updated = await updateConversationBrandApi(
        selectedConversation,
        brandId,
      );
      setConversations((previous) =>
        previous.map((item) =>
          item.id === selectedConversation ? updated : item,
        ),
      );
      return updated;
    } catch (actionError) {
      setError(
        getApiErrorMessage(
          actionError,
          "Không thể cập nhật thương hiệu cho cuộc trò chuyện.",
        ),
      );
      return null;
    }
  };

  const sendMessage = async ({
    content,
    promptType,
    platformName = "",
    attachments = [],
    adBrief = null,
    brandId,
  }) => {
    const normalizedContent = content?.trim();

    if (!normalizedContent || isTyping) {
      return;
    }

    let conversationId = selectedConversation;
    let controller = null;

    setError("");

    try {
      if (!conversationId) {
        const newConversation = await createConversationApi(
          "Cuộc trò chuyện mới",
          brandId,
        );

        conversationId = newConversation.id;

        setConversations((previous) => [newConversation, ...previous]);

        setSelectedConversation(conversationId);
      }

      setIsTyping(true);

      const uploadedAttachments = attachments.length
        ? await uploadFiles(conversationId, attachments)
        : [];

      const timestamp = Date.now();

      const userMessage = {
        id: `temporary-user-${timestamp}`,
        role: "user",
        content: normalizedContent,
        time: formatTime(),
        attachments: uploadedAttachments,
        prompt_type: promptType,
        ad_brief: adBrief,
        brand_id: brandId,
      };

      const assistantMessageId = `temporary-assistant-${timestamp}`;

      setMessages((previous) => [...previous, userMessage]);

      controller = new AbortController();

      abortControllerRef.current = controller;

      let assistantCreated = false;

      await sendMessageStream({
        conversationId,
        content: normalizedContent,
        promptType,
        platformName,
        signal: controller.signal,
        attachmentIds: uploadedAttachments.map((item) => item.id),
        adBrief,
        brandId,

        onChunk: (_chunk, fullContent) => {
          if (controller.signal.aborted) return;

          if (!assistantCreated) {
            assistantCreated = true;

            setMessages((previous) => [
              ...previous,
              {
                id: assistantMessageId,
                role: "assistant",
                content: fullContent,
                time: formatTime(),
              },
            ]);

            return;
          }

          setMessages((previous) =>
            previous.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content: fullContent,
                  }
                : message,
            ),
          );
        },
      });

      await loadMessages(conversationId, { silent: true });
      await loadConversations();
      return true;
    } catch (sendError) {
      if (sendError.name === "AbortError") {
        return true;
      }

      console.error("Lỗi gửi tin nhắn:", sendError);

      const errorMessage =
        sendError.code === "AI_STREAM_ERROR"
          ? sendError.message
          : getUserErrorMessage(
              sendError,
              "Không thể kết nối với AdGen AI.",
            );

      setError(errorMessage);
      toast.error(errorMessage);
      return false;
    } finally {
      if (controller && abortControllerRef.current === controller) {
        setIsTyping(false);
        abortControllerRef.current = null;
      }
    }
  };

  const runMessageAction = async (
    messageId,
    action,
    fallbackPromptType = null,
    customPrompt = null,
  ) => {
    if (isTyping) return false;

    const targetIndex = messages.findIndex(
      (message) => message.id === messageId,
    );
    if (targetIndex === -1) return false;

    let sourceMessage = null;
    for (let index = targetIndex; index >= 0; index -= 1) {
      if (messages[index].role === "user") {
        sourceMessage = messages[index];
        break;
      }
    }

    let actionPrompt = customPrompt || MESSAGE_ACTION_PROMPTS[action];
    if (action === "emoji") {
      const hasEmoji = /\p{Extended_Pictographic}/u.test(
        messages[targetIndex].content || "",
      );
      actionPrompt = hasEmoji
        ? "Hãy tạo phiên bản mới của câu trả lời AI ngay trước đó và bỏ emoji. Giữ nguyên nội dung, dữ kiện và định dạng Markdown."
        : "Hãy tạo phiên bản mới của câu trả lời AI ngay trước đó với emoji phù hợp ở mức vừa phải. Không lạm dụng emoji và giữ nguyên dữ kiện.";
    }

    if (!actionPrompt) return false;

    return sendMessage({
      content: actionPrompt,
      promptType: sourceMessage?.prompt_type || fallbackPromptType,
      adBrief: sourceMessage?.ad_brief || null,
    });
  };

  const editMessage = async ({
    messageId,
    content,
    promptType,
    platformName = "",
  }) => {
    const normalizedContent = content?.trim();

    if (!messageId || !normalizedContent || isTyping) {
      return;
    }

    const numericMessageId = Number(messageId);

    if (Number.isNaN(numericMessageId)) {
      setError("Tin nhắn này chưa được đồng bộ với máy chủ.");

      return;
    }

    const assistantMessageId = `temporary-assistant-${Date.now()}`;

    setError("");
    setIsTyping(true);

    const controller = new AbortController();

    abortControllerRef.current = controller;

    setMessages((previous) => {
      const editedMessageIndex = previous.findIndex(
        (message) => Number(message.id) === numericMessageId,
      );

      if (editedMessageIndex === -1) {
        return previous;
      }

      const messagesBeforeAndEdited = previous.slice(0, editedMessageIndex + 1);

      messagesBeforeAndEdited[editedMessageIndex] = {
        ...messagesBeforeAndEdited[editedMessageIndex],
        content: normalizedContent,
        time: formatTime(),
      };

      return messagesBeforeAndEdited;
    });

    try {
      let assistantCreated = false;

      await editMessageStream({
        messageId: numericMessageId,
        content: normalizedContent,
        promptType,
        platformName,
        signal: controller.signal,

        onChunk: (_chunk, fullContent) => {
          if (controller.signal.aborted) return;

          if (!assistantCreated) {
            assistantCreated = true;

            setMessages((previous) => [
              ...previous,
              {
                id: assistantMessageId,
                role: "assistant",
                content: fullContent,
                time: formatTime(),
                isStreaming: true,
              },
            ]);

            return;
          }

          setMessages((previous) =>
            previous.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content: fullContent,
                    isStreaming: true,
                  }
                : message,
            ),
          );
        },
      });

      await loadMessages(selectedConversation, { silent: true });
      await loadConversations();
    } catch (editError) {
      if (editError.name === "AbortError") {
        return;
      }

      console.error("Lỗi chỉnh sửa tin nhắn:", editError);

      const message =
        editError.code === "AI_STREAM_ERROR"
          ? editError.message
          : getUserErrorMessage(
              editError,
              "Không thể lưu hoặc tạo lại tin nhắn.",
            );
      setError(message);
      toast.error(message);
    } finally {
      if (abortControllerRef.current === controller) {
        setIsTyping(false);
        abortControllerRef.current = null;
      }
    }
  };

  const stopGenerating = () => {
    abortControllerRef.current?.abort();

    abortControllerRef.current = null;
    setIsTyping(false);
    setMessages((previous) =>
      previous.map((message) =>
        message.isStreaming
          ? { ...message, isStreaming: false }
          : message,
      ),
    );
  };

  return {
    conversations,
    selectedConversation,
    messages,

    isTyping,
    isLoadingConversations,
    isLoadingMessages,
    error,

    createConversation,
    selectConversation,
    sendMessage,
    editMessage,
    renameConversation,
    deleteConversation,
    togglePinConversation,
    clearConversationMessages,
    setConversationBrand,
    runMessageAction,
    stopGenerating,

    loadConversations,
    loadMessages,
  };
}

export default useChat;
