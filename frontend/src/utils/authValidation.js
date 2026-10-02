export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,32}$/;

export function validateLogin(values) {
  const errors = {};
  if (!values.username.trim()) {
    errors.username = "Vui lòng nhập email hoặc tên đăng nhập.";
  }
  if (!values.password) {
    errors.password = "Vui lòng nhập mật khẩu.";
  }
  return errors;
}

export function validateRegistration(values) {
  const errors = {};
  const username = values.username.trim();
  const email = values.email.trim();

  if (!username) {
    errors.username = "Vui lòng nhập tên đăng nhập.";
  } else if (!USERNAME_PATTERN.test(username)) {
    errors.username =
      "Dùng 3–32 ký tự: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.";
  }

  if (!email) {
    errors.email = "Vui lòng nhập email.";
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = "Email chưa đúng định dạng.";
  }

  if (!values.password) {
    errors.password = "Vui lòng nhập mật khẩu.";
  } else if (values.password.length < 8) {
    errors.password = "Mật khẩu phải có ít nhất 8 ký tự.";
  } else if (new TextEncoder().encode(values.password).length > 72) {
    errors.password = "Mật khẩu không được vượt quá 72 byte.";
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = "Vui lòng xác nhận mật khẩu.";
  } else if (values.password !== values.confirmPassword) {
    errors.confirmPassword = "Mật khẩu xác nhận không khớp.";
  }

  return errors;
}
