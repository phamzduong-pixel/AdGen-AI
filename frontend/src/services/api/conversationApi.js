import api from "./axios";

export const getConversations = async () => {
  const response = await api.get("/conversations");
  return response.data;
};

export const createConversation = async (
  title = "Cuộc trò chuyện mới",
  brandId = null,
) => {
  const response = await api.post("/conversations", {
    title,
    brand_id: brandId,
  });
  return response.data;
};

export const updateConversationBrand = async (id, brandId) => {
  const response = await api.patch(`/conversations/${id}/brand`, {
    brand_id: brandId,
  });
  return response.data;
};

export const renameConversation = async (id, title) => {
  const response = await api.put(`/conversations/${id}`, { title });
  return response.data;
};

export const deleteConversation = async (id) => {
  const response = await api.delete(`/conversations/${id}`);
  return response.data;
};

export const togglePinConversation = async (id, isPinned) => {
  const response = await api.patch(`/conversations/${id}/pin`, {
    is_pinned: isPinned,
  });
  return response.data;
};
