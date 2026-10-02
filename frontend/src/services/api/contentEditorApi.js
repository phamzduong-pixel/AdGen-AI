import api from "./axios";

export const createContentDocument = async (source) => {
  const response = await api.post("/contents", source);
  return response.data;
};

export const getContentDocument = async (contentId) => {
  const response = await api.get(`/contents/${contentId}`);
  return response.data;
};

export const updateContentDocument = async (contentId, data) => {
  const response = await api.patch(`/contents/${contentId}`, data);
  return response.data;
};

export const deleteContentDocument = async (contentId) => {
  const response = await api.delete(`/contents/${contentId}`);
  return response.data;
};

export const getContentVersions = async (contentId) => {
  const response = await api.get(`/contents/${contentId}/versions`);
  return response.data;
};

export const createContentVersion = async (contentId, changeSummary, createdBy = "user") => {
  const response = await api.post(`/contents/${contentId}/versions`, {
    change_summary: changeSummary || null,
    created_by: createdBy,
  });
  return response.data;
};

export const getContentVersion = async (contentId, versionId) => {
  const response = await api.get(`/contents/${contentId}/versions/${versionId}`);
  return response.data;
};

export const restoreContentVersion = async (contentId, versionId) => {
  const response = await api.post(
    `/contents/${contentId}/versions/${versionId}/restore`,
  );
  return response.data;
};

export const rewriteContent = async (contentId, action, selectedText = null) => {
  const response = await api.post(
    `/contents/${contentId}/ai-rewrite`,
    {
      action,
      selected_text: selectedText || null,
    },
    { timeout: 60_000 },
  );
  return response.data;
};

export const getCampaignContentDocuments = async (contentId) => {
  const response = await api.get(`/contents/${contentId}/campaign-contents`);
  return response.data;
};
