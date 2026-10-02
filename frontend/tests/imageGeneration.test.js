import test from "node:test";
import assert from "node:assert/strict";

import {
  getImageActionLabel,
  getImageGenerationErrorMessage,
} from "../src/utils/imageGeneration.js";

const providerError = (code, status = 502) => ({
  response: {
    status,
    data: { detail: { code, message: "internal provider detail" } },
  },
});

test("uses create label without a reference and edit label with a source", () => {
  assert.equal(
    getImageActionLabel({ referenceFile: null, sourceAsset: null }),
    "Tạo ảnh quảng cáo",
  );
  assert.equal(
    getImageActionLabel({ referenceFile: { name: "reference.png" }, sourceAsset: null }),
    "Chỉnh sửa ảnh",
  );
  assert.equal(
    getImageActionLabel({ referenceFile: null, sourceAsset: { id: 7 } }),
    "Chỉnh sửa ảnh",
  );
});

test("maps stable provider error codes to distinct messages", () => {
  assert.match(getImageGenerationErrorMessage(providerError("RESOURCE_EXHAUSTED", 429)), /quota|rate limit/i);
  assert.match(getImageGenerationErrorMessage(providerError("INVALID_ARGUMENT", 400)), /tham số|không hợp lệ/i);
  assert.match(getImageGenerationErrorMessage(providerError("MODEL_NOT_FOUND")), /model/i);
  assert.match(getImageGenerationErrorMessage(providerError("PERMISSION_DENIED")), /quyền/i);
  assert.match(getImageGenerationErrorMessage(providerError("UNAUTHENTICATED")), /API key|xác thực/i);
  assert.match(getImageGenerationErrorMessage(providerError("PROVIDER_TIMEOUT", 504)), /lâu|thử lại/i);
  assert.match(getImageGenerationErrorMessage(providerError("IMAGE_OUTPUT_MISSING")), /ảnh hợp lệ/i);
  assert.match(getImageGenerationErrorMessage(providerError("PROVIDER_ERROR")), /provider|tạo ảnh/i);
});

test("keeps bare 429 neutral instead of claiming quota exhaustion", () => {
  const message = getImageGenerationErrorMessage({
    response: { status: 429, data: { detail: { code: "PROVIDER_ERROR", message: "limited" } } },
  });
  assert.match(message, /giới hạn yêu cầu hoặc tài nguyên/i);
  assert.doesNotMatch(message, /quota|rate limit/i);
});

test("keeps legacy explicit quota responses compatible", () => {
  const legacyQuota = getImageGenerationErrorMessage({
    response: {
      status: 429,
      data: { detail: "Image generation is temporarily limited by provider quota or rate limit" },
    },
  });
  assert.match(legacyQuota, /quota|rate limit/i);

  const legacyUnknown = getImageGenerationErrorMessage({
    response: { status: 429, data: { detail: "provider rejected request" } },
  });
  assert.match(legacyUnknown, /giới hạn yêu cầu hoặc tài nguyên/i);
  assert.doesNotMatch(legacyUnknown, /quota|rate limit/i);
});

test("does not expose unknown internal details", () => {
  const message = getImageGenerationErrorMessage({
    response: { status: 502, data: { detail: { code: "UNKNOWN", message: "api_key=SECRET internal-url" } } },
  });
  assert.doesNotMatch(message, /SECRET|api_key|internal-url/i);
});