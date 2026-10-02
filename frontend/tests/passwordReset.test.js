import assert from "node:assert/strict";
import test from "node:test";

import {
  formatCountdown,
  maskEmail,
  passwordStrength,
  sanitizeOtp,
  validateResetEmail,
  validateResetPasswords,
} from "../src/utils/passwordReset.js";

test("password reset masks email without losing its domain", () => {
  assert.equal(maskEmail("phamduong@gmail.com"), "ph*******@gmail.com");
  assert.equal(maskEmail("a@example.com"), "a***@example.com");
});

test("password reset validates email and matching passwords", () => {
  assert.ok(validateResetEmail("invalid"));
  assert.equal(validateResetEmail("user@example.com"), "");
  assert.deepEqual(
    validateResetPasswords({
      newPassword: "short",
      confirmPassword: "different",
    }),
    {
      newPassword: "Mật khẩu phải có ít nhất 8 ký tự.",
      confirmPassword: "Mật khẩu xác nhận không khớp.",
    },
  );
  assert.deepEqual(
    validateResetPasswords({
      newPassword: "secure-password-123",
      confirmPassword: "secure-password-123",
    }),
    {},
  );
});

test("OTP paste accepts only the first six digits", () => {
  assert.equal(sanitizeOtp("12a 34-5678"), "123456");
});

test("countdown and password strength stay user friendly", () => {
  assert.equal(formatCountdown(65), "1:05");
  assert.equal(passwordStrength("short1!").label, "Yếu");
  assert.equal(passwordStrength("Stronger-password-123").label, "Mạnh");
});
