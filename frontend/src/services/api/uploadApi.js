import api from "./axios";

export const uploadFiles = async (conversationId, files) => {
  const uploadedFiles = [];

  for (const file of files) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post(`/uploads/${conversationId}`, formData);
    uploadedFiles.push(response.data);
  }

  return uploadedFiles;
};

export const downloadAttachment = async (fileId) => {
  const response = await api.get(`/uploads/file/${fileId}/download`, {
    responseType: "blob",
  });
  return response.data;
};
