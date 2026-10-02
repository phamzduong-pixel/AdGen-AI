import { useState } from "react";
import { FiKey } from "react-icons/fi";
import { useNavigate } from "react-router-dom";

import useToast from "../../ui/Toast/useToast";
import useAuth from "../../../hooks/useAuth";
import { changePassword } from "../../../services/api/userApi";
import { getUserErrorMessage } from "../../../utils/apiError";
import "./ChangePasswordForm.css";

function ChangePasswordForm() {
  const navigate = useNavigate();
  const toast = useToast();
  const { logout } = useAuth();
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [pending, setPending] = useState(false);

  const update = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    if (form.new_password !== form.confirm_password) {
      toast.warning("Xác nhận mật khẩu mới không khớp.");
      return;
    }
    setPending(true);
    try {
      const response = await changePassword(form);
      toast.success(response.message);
      sessionStorage.setItem(
        "adgen_auth_message",
        "Mật khẩu đã thay đổi. Vui lòng đăng nhập lại.",
      );
      await logout({ revoke: false });
      navigate("/login", { replace: true });
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể đổi mật khẩu."));
    } finally {
      setPending(false);
    }
  };

  return (
    <section className="settings-section">
      <header><FiKey /><div><h2>Đổi mật khẩu</h2><p>Phiên hiện tại sẽ kết thúc sau khi đổi thành công.</p></div></header>
      <form className="change-password-form" onSubmit={submit}>
        <label><span>Mật khẩu hiện tại</span><input name="current_password" type="password" value={form.current_password} onChange={update} autoComplete="current-password" required /></label>
        <label><span>Mật khẩu mới</span><input name="new_password" type="password" value={form.new_password} onChange={update} minLength="8" maxLength="128" autoComplete="new-password" required /></label>
        <label><span>Xác nhận mật khẩu mới</span><input name="confirm_password" type="password" value={form.confirm_password} onChange={update} minLength="8" maxLength="128" autoComplete="new-password" required /></label>
        <button type="submit" disabled={pending}>{pending ? "Đang đổi..." : "Đổi mật khẩu"}</button>
      </form>
    </section>
  );
}

export default ChangePasswordForm;
