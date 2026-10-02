import api from "./axios";

export const getCampaigns = async (filters = {}) => {
  const response = await api.get("/campaigns", {
    params: {
      query: filters.query || undefined,
      status: filters.status || undefined,
      platform: filters.platform || undefined,
    },
  });
  return response.data;
};

export const getCampaign = async (campaignId) => {
  const response = await api.get(`/campaigns/${campaignId}`);
  return response.data;
};

export const createCampaign = async (data) => {
  const response = await api.post("/campaigns", data);
  return response.data;
};

export const updateCampaign = async (campaignId, data) => {
  const response = await api.patch(`/campaigns/${campaignId}`, data);
  return response.data;
};

export const deleteCampaign = async (campaignId) => {
  const response = await api.delete(`/campaigns/${campaignId}`);
  return response.data;
};

export const addCampaignContent = async (campaignId, savedContentId) => {
  const response = await api.post(`/campaigns/${campaignId}/contents`, {
    saved_content_id: savedContentId,
  });
  return response.data;
};

export const removeCampaignContent = async (campaignId, savedContentId) => {
  const response = await api.delete(
    `/campaigns/${campaignId}/contents/${savedContentId}`,
  );
  return response.data;
};

export const setCampaignPrimaryContent = async (
  campaignId,
  savedContentId,
) => {
  const response = await api.patch(
    `/campaigns/${campaignId}/contents/${savedContentId}/primary`,
  );
  return response.data;
};
