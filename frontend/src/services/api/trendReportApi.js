import api from "./axios";

export const getTrendReports = async () => {
  const response = await api.get("/trend-reports");
  return response.data;
};

export const retrieveTrendReport = async (payload) => {
  const response = await api.post("/trend-reports/retrieve", payload);
  return response.data;
};

export const deleteTrendReport = async (reportId) => {
  await api.delete(`/trend-reports/${reportId}`);
};

export const getTrendReportTrust = async (reportId, mode = "all_evidence") => {
  const response = await api.get(`/trend-reports/${reportId}/trust`, { params: { mode } });
  return response.data;
};

export const getSourcePolicies = async () => {
  const response = await api.get("/trend-reports/source-policies");
  return response.data;
};

export const updateSourcePolicy = async ({ host, decision, note = "" }) => {
  const response = await api.put("/trend-reports/source-policies", { host, decision, note });
  return response.data;
};

export const getInsightCampaignOverview = async () => {
  const response = await api.get("/insight-campaign/overview");
  return response.data;
};

export const createBriefFromAngle = async (angleId) => {
  const response = await api.post(`/insight-campaign/advertising-angles/${angleId}/brief`);
  return response.data;
};

export const createCampaignFromBrief = async (briefId) => {
  const response = await api.post(`/insight-campaign/briefs/${briefId}/campaign`);
  return response.data;
};

export const getCampaignMetricSnapshots = async (campaignId) => {
  const response = await api.get(`/insight-campaign/campaigns/${campaignId}/metric-snapshots`);
  return response.data;
};

export const createCampaignMetricSnapshot = async (campaignId, metricPayload) => {
  const response = await api.post(`/insight-campaign/campaigns/${campaignId}/metric-snapshots`, {
    metric_payload: metricPayload,
  });
  return response.data;
};
