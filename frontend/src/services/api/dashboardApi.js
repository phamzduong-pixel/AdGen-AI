import api from "./axios";

export const getDashboardSummary = async () => {
  const response = await api.get("/dashboard/summary");
  return response.data;
};

export const getDashboardActivity = async () => {
  const response = await api.get("/dashboard/activity");
  return response.data;
};

export const getDashboardPlatformUsage = async () => {
  const response = await api.get("/dashboard/platform-usage");
  return response.data;
};
