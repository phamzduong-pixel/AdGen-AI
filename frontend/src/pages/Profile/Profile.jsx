import { useState } from "react";
import {
  FiBarChart2,
  FiBookmark,
  FiFolder,
  FiMessageSquare,
  FiSave,
  FiUser,
} from "react-icons/fi";
import useToast from "../../components/ui/Toast/useToast";
import useAuth from "../../hooks/useAuth";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { updateUserProfile } from "../../services/api/userApi";
import { getUserErrorMessage } from "../../utils/apiError";
import "./Profile.css";

const PLATFORM_LABELS = {
  facebook: "Facebook",
  google_ads: "Google Ads",
  landing_page: "Landing Page",
  instagram: "Instagram",
  tiktok: "TikTok",
  email: "Email Marketing",
};

function ProfileForm({ user, onUpdated }) {
  const toast = useToast();
  const [form, setForm] = useState({
    username: user.username,
    email: user.email,
  });
  const [pending, setPending] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    try {
      const updated = await updateUserProfile({
        username: form.username.trim(),
        email: form.email.trim(),
      });
      onUpdated(updated);
      toast.success("Đã cập nhật hồ sơ thành công.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể cập nhật hồ sơ."));
    } finally {
      setPending(false);
    }
  };

  return (
    <form className="profile-form" onSubmit={submit}>
      <label>
        <span>Username</span>
        <input
          value={form.username}
          onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
          minLength="3"
          maxLength="32"
          pattern="[A-Za-z0-9_.-]+"
          required
        />
      </label>
      <label>
        <span>Email</span>
        <input
          type="email"
          value={form.email}
          onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
          required
        />
      </label>
      <button type="submit" disabled={pending}>
        <FiSave /> {pending ? "Đang lưu..." : "Lưu hồ sơ"}
      </button>
    </form>
  );
}

function Profile() {
  const { user, loading, setUser } = useAuth();
  const createdAt = user?.created_at ? new Date(`${user.created_at}Z`) : null;

  return (
    <WorkspaceLayout title="Hồ sơ cá nhân" subtitle="Thông tin tài khoản và hoạt động của bạn">
      {loading ? (
        <div className="profile-loading">Đang tải hồ sơ...</div>
      ) : user ? (
        <div className="profile-page__grid">
          <section className="profile-card profile-card--identity">
            <div className="profile-avatar"><FiUser /></div>
            <h2>{user.username}</h2>
            <p>{user.email}</p>
            <small>
              Tham gia{" "}
              {createdAt && !Number.isNaN(createdAt.getTime())
                ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" }).format(createdAt)
                : "—"}
            </small>
          </section>
          <section className="profile-stats">
            <article><FiMessageSquare /><strong>{user.total_conversations}</strong><span>Hội thoại</span></article>
            <article><FiBookmark /><strong>{user.total_saved_contents}</strong><span>Đã lưu</span></article>
            <article><FiFolder /><strong>{user.total_campaigns}</strong><span>Chiến dịch</span></article>
            <article><FiBarChart2 /><strong>{PLATFORM_LABELS[user.top_platform] || user.top_platform || "—"}</strong><span>Nền tảng phổ biến</span></article>
          </section>
          <section className="profile-card profile-card--form">
            <h2>Chỉnh sửa thông tin</h2>
            <p>Username và email phải là duy nhất trong hệ thống.</p>
            <ProfileForm
              key={`${user.id}-${user.username}-${user.email}`}
              user={user}
              onUpdated={setUser}
            />
          </section>
        </div>
      ) : null}
    </WorkspaceLayout>
  );
}

export default Profile;
