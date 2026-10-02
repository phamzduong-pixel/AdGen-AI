import api from "./axios";

export const getTemplates = async (params = {}) => {
  const response = await api.get("/templates", { params });
  return response.data;
};

export const getTemplateFavorites = async () => {
  const response = await api.get("/templates/favorites");
  return response.data;
};

export const favoriteTemplate = async (templateId) => {
  const response = await api.post(`/templates/${templateId}/favorite`);
  return response.data;
};

export const unfavoriteTemplate = async (templateId) => {
  const response = await api.delete(`/templates/${templateId}/favorite`);
  return response.data;
};

export const createCustomTemplate = async (payload) => {
  const response = await api.post("/templates/custom", payload);
  return response.data;
};

export const updateCustomTemplate = async (templateId, payload) => {
  const response = await api.patch(
    `/templates/custom/${templateId}`,
    payload,
  );
  return response.data;
};

export const deleteCustomTemplate = async (templateId) => {
  const response = await api.delete(`/templates/custom/${templateId}`);
  return response.data;
};
