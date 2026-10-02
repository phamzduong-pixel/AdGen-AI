import api from "./axios";
import tokenStorage from "../storage/tokenStorage";

export const getMessages = async (conversationId) => {
  const response = await api.get(`/messages/${conversationId}`);

  return response.data;
};

export const sendMessage = async ({
  conversationId,
  content,
  promptType = null,
  platformName = "",
  adBrief = null,
  brandId,
}) => {
  const response = await api.post("/messages", {
    conversation_id: conversationId,
    content,
    prompt_type: promptType,
    platform_name: platformName || null,
    ad_brief: adBrief,
    ...(brandId !== undefined ? { brand_id: brandId } : {}),
  });

  return response.data;
};

const getResponseError = async (response, fallbackMessage) => {
  try {
    const data = await response.json();

    return data.detail || data.message || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
};

const STREAM_ERROR_MARKER = "[ADGEN_STREAM_ERROR]";
const QUOTA_ERROR_MARKER = "[ADGEN_QUOTA_ERROR]";

const throwIfStreamFailed = (content) => {
  if (content.includes(QUOTA_ERROR_MARKER)) {
    const error = new Error(
      "Dịch vụ Gemini đã hết hạn mức hoặc đang quá tải. Vui lòng thử lại sau.",
    );
    error.code = "AI_STREAM_ERROR";
    throw error;
  }
  if (!content.includes(STREAM_ERROR_MARKER)) return;

  const error = new Error(
    "Dịch vụ AI bị gián đoạn. Phần nội dung đã tạo vẫn được giữ lại.",
  );
  error.code = "AI_STREAM_ERROR";
  throw error;
};

const handleStreamingUnauthorized = (response) => {
  if (response.status !== 401) return;
  tokenStorage.removeAccessToken();
  localStorage.removeItem("currentConversationId");
  localStorage.removeItem("currentUser");
  sessionStorage.setItem(
    "adgen_auth_message",
    "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  );
  if (window.location.pathname !== "/login") {
    window.location.replace("/login");
  }
};

const createStreamingResponseError = (response, message) => {
  const error = new Error(message);
  error.response = {
    status: response.status,
    data: { detail: message },
  };
  return error;
};

export const sendMessageStream = async ({
  conversationId,
  content,
  promptType = null,
  platformName = "",
  onChunk,
  signal,
  attachmentIds = [],
  adBrief = null,
  brandId,
}) => {
  const accessToken = tokenStorage.getAccessToken();

  if (!accessToken) {
    throw new Error("Không tìm thấy phiên đăng nhập.");
  }

  const response = await fetch(`${api.defaults.baseURL}/messages/stream`, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      content: content.trim(),
      prompt_type: promptType,
      platform_name: platformName || null,
      attachment_ids: attachmentIds,
      ad_brief: adBrief,
      ...(brandId !== undefined ? { brand_id: brandId } : {}),
    }),
    signal,
  });

  if (!response.ok) {
    handleStreamingUnauthorized(response);
    const message = await getResponseError(response, "Không thể gửi tin nhắn.");

    throw createStreamingResponseError(response, message);
  }

  if (!response.body) {
    throw new Error("Không thể đọc phản hồi streaming.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let fullContent = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    const chunk = decoder.decode(value, {
      stream: true,
    });

    fullContent += chunk;
    throwIfStreamFailed(fullContent);

    onChunk?.(chunk, fullContent);
  }

  const finalChunk = decoder.decode();

  if (finalChunk) {
    fullContent += finalChunk;
    throwIfStreamFailed(fullContent);
    onChunk?.(finalChunk, fullContent);
  }

  return fullContent;
};

export const clearConversationMessages = async (conversationId) => {
  const response = await api.delete(
    `/messages/conversation/${conversationId}`,
  );
  return response.data;
};

export const updateMessage = async ({
  messageId,
  content,
  promptType = null,
  platformName = "",
}) => {
  const response = await api.put(`/messages/${messageId}`, {
    content,
    prompt_type: promptType,
    platform_name: platformName || null,
  });

  return response.data;
};

export const editMessageStream = async ({
  messageId,
  content,
  promptType = null,
  platformName = "",
  onChunk,
  signal,
}) => {
  const accessToken = tokenStorage.getAccessToken();

  if (!accessToken) {
    throw new Error("Không tìm thấy phiên đăng nhập.");
  }

  const response = await fetch(
    `${api.defaults.baseURL}/messages/${messageId}/stream`,
    {
      method: "PUT",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        content: content.trim(),
        prompt_type: promptType,
        platform_name: platformName || null,
      }),
      signal,
    },
  );

  if (!response.ok) {
    handleStreamingUnauthorized(response);
    const message = await getResponseError(
      response,
      "Không thể chỉnh sửa tin nhắn.",
    );

    throw createStreamingResponseError(response, message);
  }

  if (!response.body) {
    throw new Error("Không thể đọc phản hồi streaming.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let fullContent = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    const chunk = decoder.decode(value, {
      stream: true,
    });

    fullContent += chunk;
    throwIfStreamFailed(fullContent);

    onChunk?.(chunk, fullContent);
  }

  const finalChunk = decoder.decode();

  if (finalChunk) {
    fullContent += finalChunk;
    throwIfStreamFailed(fullContent);
    onChunk?.(finalChunk, fullContent);
  }

  return fullContent;
};
