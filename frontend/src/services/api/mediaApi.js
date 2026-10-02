import api from "./axios";

export const listMediaAssets = async (conversationId) => {
  const response = await api.get(`/media/conversations/${conversationId}/assets`);
  return response.data;
};

export const generateImage = async (conversationId, payload) => {
  const response = await api.post(
    `/media/conversations/${conversationId}/images`,
    payload,
    { timeout: 120000 },
  );
  return response.data;
};

export const downloadMediaAsset = async (assetId) => {
  const response = await api.get(`/media/assets/${assetId}/download`, {
    responseType: "blob",
    timeout: 120000,
  });
  return response.data;
};
export const deleteMediaAsset = async (conversationId, assetId) => {
  await api.delete(`/media/conversations/${conversationId}/assets/${assetId}`);
};
export const registerVideoUpload = async (conversationId, sourceFileId) => {
  const response = await api.post(
    `/media/conversations/${conversationId}/videos/from-upload`,
    { source_file_id: sourceFileId },
    { timeout: 120000 },
  );
  return response.data;
};

export const editVideo = async (conversationId, sourceAssetId, payload) => {
  const response = await api.post(
    `/media/conversations/${conversationId}/videos/${sourceAssetId}/edits`,
    payload,
    { timeout: 120000 },
  );
  return response.data;
};

export const createVideoEditPlan = async (conversationId, sourceAssetId, payload) => {
  const response = await api.post(
    `/media/conversations/${conversationId}/videos/${sourceAssetId}/conversational-edit-plan`,
    payload,
    { timeout: 120000 },
  );
  return response.data;
};

export const executeVideoEditPlan = async (conversationId, sourceAssetId, plan, idempotencyKey) => {
  const response = await api.post(
    `/media/conversations/${conversationId}/videos/${sourceAssetId}/conversational-edits`,
    { plan, confirm: true },
    {
      timeout: 120000,
      ...(idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : {}),
    },
  );
  return response.data;
};

export const createVideoGenerationJob = async (conversationId, payload) => {
  const response = await api.post(`/media/conversations/${conversationId}/video-jobs`, payload, { timeout: 30000 });
  return response.data;
};

export const getVideoGenerationJob = async (jobId) => {
  const response = await api.get(`/media/jobs/${jobId}`, { timeout: 30000 });
  return response.data;
};

export const listVideoGenerationJobs = async (conversationId, limit = 10) => {
  const response = await api.get(`/media/conversations/${conversationId}/video-jobs`, {
    params: { limit },
    timeout: 30000,
  });
  return response.data;
};
