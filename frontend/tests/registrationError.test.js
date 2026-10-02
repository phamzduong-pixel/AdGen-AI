import assert from "node:assert/strict";
import test from "node:test";

import { getRegistrationApiError } from "../src/utils/registrationError.js";

test("registration API duplicate errors map to the correct field", () => {
  assert.deepEqual(
    getRegistrationApiError({
      response: { status: 400, data: { detail: "Username đã được sử dụng" } },
    }),
    { username: "Tên đăng nhập đã tồn tại." },
  );
  assert.deepEqual(
    getRegistrationApiError({
      response: { status: 400, data: { detail: "Email đã được sử dụng" } },
    }),
    { email: "Email đã được sử dụng." },
  );
});

test("registration API hides validation and server implementation details", () => {
  assert.deepEqual(
    getRegistrationApiError({
      response: { status: 422, data: { detail: [{ type: "value_error" }] } },
    }),
    {
      form: "Thông tin đăng ký chưa hợp lệ. Vui lòng kiểm tra lại các trường.",
    },
  );
  assert.deepEqual(
    getRegistrationApiError({
      response: { status: 500, data: { detail: "internal stack trace" } },
    }),
    { form: "Hệ thống đang gặp sự cố. Vui lòng thử lại sau." },
  );
});
