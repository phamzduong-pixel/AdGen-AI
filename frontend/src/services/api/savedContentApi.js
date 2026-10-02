import api from "./axios";

export const getSavedContents = async () => {
  const response = await api.get("/saved-contents");
  return response.data;
};

export const saveContent = async ({
  messageId = null,
  conversationId = null,
  title = null,
  content = null,
  platform = null,
  platformName = "",
  brandId = null,
}) => {
  const response = await api.post("/saved-contents", {
    message_id: messageId,
    conversation_id: conversationId,
    title,
    content,
    platform,
    platform_name: platformName || null,
    brand_id: brandId,
  });
  return response.data;
};

export const unsaveMessage = async (messageId) => {
  const response = await api.delete(`/saved-contents/message/${messageId}`);
  return response.data;
};

export const deleteSavedContent = async (savedContentId) => {
  const response = await api.delete(`/saved-contents/${savedContentId}`);
  return response.data;
};

export const recordContentActivity = async (savedContentId, actionType) => {
  const response = await api.post(
    `/saved-contents/${savedContentId}/activities`,
    { action_type: actionType },
  );
  return response.data;
};
