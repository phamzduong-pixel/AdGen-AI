import api from "./axios";

export const getUserProfile = async () => {
  const response = await api.get("/users/me");
  return response.data;
};

export const updateUserProfile = async (data) => {
  const response = await api.patch("/users/me", data);
  return response.data;
};

export const uploadUserAvatar = async (file) => {
  const data = new FormData();
  data.append("file", file);
  const response = await api.post("/users/me/avatar", data);
  return response.data;
};

export const getUserAvatarBlob = async () => {
  const response = await api.get("/users/me/avatar", { responseType: "blob" });
  return response.data;
};

export const deleteUserAvatar = async () => {
  const response = await api.delete("/users/me/avatar");
  return response.data;
};
export const changePassword = async (data) => {
  const response = await api.post("/users/me/change-password", data);
  return response.data;
};

export const getUserSettings = async () => {
  const response = await api.get("/users/me/settings");
  return response.data;
};

export const updateUserSettings = async (data) => {
  const response = await api.put("/users/me/settings", data);
  return response.data;
};
