import api from "./axios";

const buildSourcePayload = ({
  messageId = null,
  savedContentId = null,
  content = null,
  platform = null,
  platformName = null,
  targetAudience = null,
  tone = null,
}) => ({
  ...(messageId
    ? { message_id: Number(messageId) }
    : savedContentId
      ? { saved_content_id: Number(savedContentId) }
      : { content: content?.trim() }),
  platform,
  platform_name: platformName,
  target_audience: targetAudience,
  tone,
});

export const evaluateContent = async (source) => {
  const response = await api.post(
    "/content/evaluate",
    buildSourcePayload(source),
    { timeout: 60_000 },
  );
  return response.data;
};

export const generateContentVariants = async (source) => {
  const response = await api.post(
    "/content/generate-variants",
    {
      ...buildSourcePayload(source),
      number_of_variants: 3,
    },
    { timeout: 60_000 },
  );
  return response.data;
};
