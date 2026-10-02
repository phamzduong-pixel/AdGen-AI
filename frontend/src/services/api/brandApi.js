import api from "./axios";

export const getBrands = async (query = "") => {
  const response = await api.get("/brands", {
    params: { query: query || undefined },
  });
  return response.data;
};

export const createBrand = async (data) => {
  const response = await api.post("/brands", data);
  return response.data;
};

export const updateBrand = async (brandId, data) => {
  const response = await api.patch(`/brands/${brandId}`, data);
  return response.data;
};

export const deleteBrand = async (brandId) => {
  const response = await api.delete(`/brands/${brandId}`);
  return response.data;
};

export const setDefaultBrand = async (brandId) => {
  const response = await api.patch(`/brands/${brandId}/default`);
  return response.data;
};

export const checkBrandContent = async (brandId, content, platform) => {
  const response = await api.post(`/brands/${brandId}/check-content`, {
    content,
    platform,
  });
  return response.data;
};

export const getBrandStatistics = async (brandId) => {
  const response = await api.get(`/brands/${brandId}/statistics`);
  return response.data;
};

export const uploadBrandAsset = async (brandId, file) => {
  const form = new FormData();
  form.append("file", file);
  const response = await api.post(`/brands/${brandId}/assets`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteBrandAsset = async (brandId, assetId) => {
  const response = await api.delete(`/brands/${brandId}/assets/${assetId}`);
  return response.data;
};

export const downloadBrandAsset = async (brandId, asset) => {
  const response = await api.get(
    `/brands/${brandId}/assets/${asset.id}/download`,
    { responseType: "blob" },
  );
  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = asset.file_name;
  link.click();
  URL.revokeObjectURL(url);
};
