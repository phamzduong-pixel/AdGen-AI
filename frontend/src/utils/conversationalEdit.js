export const createIdempotencyKey = () => {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export const reuseIdempotencyKey = (currentKey) => currentKey || createIdempotencyKey();

export const buildConversationalEditRequest = (instruction, mergeSourceAssetIds = []) => ({
  instruction: instruction.trim(),
  merge_source_asset_ids: [...new Set(mergeSourceAssetIds.filter((assetId) => Number.isInteger(assetId) && assetId > 0))],
});

export const getConversationalOperationNames = (plan) => (
  plan?.operations?.map((operation) => operation.operation) || []
);

export const getConversationalExecutionOutcome = (result) => {
  const createdAssets = Array.isArray(result?.created_assets) ? result.created_assets : [];
  const recoverableAssets = createdAssets.filter((asset) => asset?.status !== "failed");
  const latestAsset = recoverableAssets[recoverableAssets.length - 1] || result?.output_asset || null;
  const status = ["completed", "partial", "processing", "recovery_required"].includes(result?.status)
    ? result.status
    : "failed";
  return {
    status,
    latestAssetId: latestAsset?.id || null,
    createdAssetCount: createdAssets.length,
    createdAssets,
    failedOperation: result?.failed_operation || null,
    failedOperationIndex: Number.isInteger(result?.failed_operation_index)
      ? result.failed_operation_index
      : null,
    message: result?.error || (
      status === "completed"
        ? "\u0110\u00e3 ho\u00e0n th\u00e0nh k\u1ebf ho\u1ea1ch ch\u1ec9nh s\u1eeda video."
        : status === "partial"
          ? "K\u1ebf ho\u1ea1ch th\u1ef1c hi\u1ec7n m\u1ed9t ph\u1ea7n; c\u00e1c version \u0111\u00e3 t\u1ea1o v\u1eabn \u0111\u01b0\u1ee3c gi\u1eef l\u1ea1i."
          : status === "processing"
            ? "Yêu cầu vẫn đang được xử lý."
            : status === "recovery_required"
              ? "Kết quả cần được kiểm tra lại trước khi thử tiếp."
              : "\u004b\u0068\u00f4\u006e\u0067 \u0074\u0068\u1ec3 \u0068\u006f\u00e0\u006e \u0074\u0068\u00e0\u006e\u0068 \u006b\u1ebf \u0068\u006f\u1ea1\u0063\u0068 \u0063\u0068\u1ec9\u006e\u0068 \u0073\u1eed\u0061 \u0076\u0069\u0064\u0065\u006f."
    ),
  };
};
