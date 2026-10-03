import { useRef, useState } from "react";
import {
  FiBarChart2,
  FiBookmark,
  FiCamera,
  FiFolder,
  FiMessageSquare,
  FiSave,
  FiTrash2,
  FiUser,
} from "react-icons/fi";
import UserAvatar from "../../components/user/UserAvatar";
import useToast from "../../components/ui/Toast/useToast";
import useAuth from "../../hooks/useAuth";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { deleteUserAvatar, updateUserProfile, uploadUserAvatar } from "../../services/api/userApi";
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
const MAX_AVATAR_SIZE = 5 * 1024 * 1024;
const SUPPORTED_AVATAR_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function AvatarEditor({ user, onUpdated }) {
  const toast = useToast();
  const inputRef = useRef(null);
  const [pending, setPending] = useState(false);
  const [revision, setRevision] = useState(0);

  const selectImage = () => inputRef.current?.click();
  const onFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || pending) return;
    if (!SUPPORTED_AVATAR_TYPES.has(file.type)) {
      toast.error("Vui lòng chọn ảnh JPG, PNG hoặc WEBP.");
      return;
    }
    if (file.size > MAX_AVATAR_SIZE) {
      toast.error("Ảnh đại diện không được vượt quá 5 MB.");
      return;
    }
    setPending(true);
    try {
      const updated = await uploadUserAvatar(file);
      onUpdated(updated);
      setRevision((value) => value + 1);
      toast.success("Đã cập nhật ảnh đại diện.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể tải ảnh đại diện lên."));
    } finally {
      setPending(false);
    }
  };

  const remove = async () => {
    if (pending || !user.avatar_url) return;
    setPending(true);
    try {
      const updated = await deleteUserAvatar();
      onUpdated(updated);
      setRevision((value) => value + 1);
      toast.success("Đã xóa ảnh đại diện.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể xóa ảnh đại diện."));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="profile-avatar-editor">
      <button type="button" className="profile-avatar-trigger" onClick={selectImage} disabled={pending} aria-label="Đổi ảnh đại diện" title="Đổi ảnh đại diện">
        <UserAvatar key={`${user.avatar_url || "default"}-${revision}`} user={user} className="profile-avatar" fallback={<FiUser />} />
        <span className="profile-avatar-trigger__overlay">{pending ? "Đang tải..." : <><FiCamera /> Đổi ảnh</>}</span>
      </button>
      <input ref={inputRef} className="profile-avatar-editor__input" type="file" accept="image/jpeg,image/png,image/webp" onChange={onFileChange} />
      {user.avatar_url && (
        <div className="profile-avatar-editor__actions">
          <button type="button" className="profile-avatar-editor__remove" onClick={remove} disabled={pending} aria-label="Xóa ảnh đại diện">
            <FiTrash2 /> Xóa ảnh
          </button>
        </div>
      )}
    </div>
  );
}

function ProfileForm({ user, onUpdated }) {
  const toast = useToast();
  const [form, setForm] = useState({ username: user.username, email: user.email });
  const [pending, setPending] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    try {
      const updated = await updateUserProfile({ username: form.username.trim(), email: form.email.trim() });
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
      <label><span>Username</span><input value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} minLength="3" maxLength="32" pattern="[A-Za-z0-9_.-]+" required /></label>
      <label><span>Email</span><input type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} required /></label>
      <button type="submit" disabled={pending}><FiSave /> {pending ? "Đang lưu..." : "Lưu hồ sơ"}</button>
    </form>
  );
}

function Profile() {
  const { user, loading, setUser } = useAuth();
  const createdAt = user?.created_at ? new Date(`${user.created_at}Z`) : null;
  return (
    <WorkspaceLayout title="Hồ sơ cá nhân" subtitle="Thông tin tài khoản và hoạt động của bạn">
      {loading ? <div className="profile-loading">Đang tải hồ sơ...</div> : user ? (
        <div className="profile-page__grid">
          <section className="profile-card profile-card--identity">
            <AvatarEditor user={user} onUpdated={setUser} />
            <h2>{user.username}</h2><p>{user.email}</p>
            <small>Tham gia {createdAt && !Number.isNaN(createdAt.getTime()) ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "long" }).format(createdAt) : "—"}</small>
          </section>
          <section className="profile-stats">
            <article><FiMessageSquare /><strong>{user.total_conversations}</strong><span>Hội thoại</span></article>
            <article><FiBookmark /><strong>{user.total_saved_contents}</strong><span>Đã lưu</span></article>
            <article><FiFolder /><strong>{user.total_campaigns}</strong><span>Chiến dịch</span></article>
            <article><FiBarChart2 /><strong>{PLATFORM_LABELS[user.top_platform] || user.top_platform || "—"}</strong><span>Nền tảng phổ biến</span></article>
          </section>
          <section className="profile-card profile-card--form"><h2>Chỉnh sửa thông tin</h2><p>Username và email phải là duy nhất trong hệ thống.</p><ProfileForm key={`${user.id}-${user.username}-${user.email}`} user={user} onUpdated={setUser} /></section>
        </div>
      ) : null}
    </WorkspaceLayout>
  );
}

export default Profile;