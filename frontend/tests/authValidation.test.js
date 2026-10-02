import assert from "node:assert/strict";
import test from "node:test";

import {
  validateLogin,
  validateRegistration,
} from "../src/utils/authValidation.js";

test("login requires both identifier and password", () => {
  assert.deepEqual(validateLogin({ username: " ", password: "" }), {
    username: "Vui lòng nhập email hoặc tên đăng nhập.",
    password: "Vui lòng nhập mật khẩu.",
  });
});

test("registration validates email, username, password and confirmation", () => {
  const errors = validateRegistration({
    username: "x!",
    email: "invalid-email",
    password: "short",
    confirmPassword: "different",
  });
  assert.ok(errors.username);
  assert.ok(errors.email);
  assert.ok(errors.password);
  assert.ok(errors.confirmPassword);
});

test("valid registration has no validation errors", () => {
  assert.deepEqual(
    validateRegistration({
      username: "adgen.user",
      email: "user@example.com",
      password: "secure-password",
      confirmPassword: "secure-password",
    }),
    {},
  );
});
