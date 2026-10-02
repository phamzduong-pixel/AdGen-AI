import api from "./axios";

export const getMessages = async (conversationId) => {
  const response = await api.get(`/messages/${conversationId}`);

  return response.data;
};

export const sendMessage = async (conversationId, content) => {
  const response = await api.post("/messages", {
    conversation_id: conversationId,
    content,
  });

  return response.data;
};

export const editMessage = async (messageId, content) => {
  const response = await api.put(`/messages/${messageId}`, {
    content,
  });

  return response.data;
};
