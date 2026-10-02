import { useEffect, useState } from "react";
import {
  FiCheck,
  FiDownload,
  FiMessageSquare,
  FiMonitor,
  FiMoon,
  FiSettings,
  FiSliders,
  FiSun,
} from "react-icons/fi";

import ChangePasswordForm from "../../components/settings/ChangePasswordForm/ChangePasswordForm";
import ActiveSessions from "../../components/settings/ActiveSessions/ActiveSessions";
import useToast from "../../components/ui/Toast/useToast";
import useTheme from "../../hooks/useTheme";
import WorkspaceLayout from "../../layouts/WorkspaceLayout";
import { PLATFORM_OPTIONS } from "../../constants/platforms";
import {
  getUserSettings,
  updateUserSettings,
} from "../../services/api/userApi";
import {
  getPreferences,
  savePreferences,
} from "../../utils/settingsStorage";
import { getUserErrorMessage } from "../../utils/apiError";
import "./Settings.css";

const THEMES = [
  { value: "light", label: "Sáng", icon: FiSun },
  { value: "dark", label: "Tối", icon: FiMoon },
  { value: "system", label: "Hệ thống", icon: FiMonitor },
];

function Toggle({ label, description, checked, onChange }) {
  return (
    <label className="settings-toggle">
      <span><strong>{label}</strong><small>{description}</small></span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <i />
    </label>
  );
}

function Settings() {
  const toast = useToast();
  const { setTheme } = useTheme();
  const [preferences, setPreferences] = useState(getPreferences);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    getUserSettings()
      .then((remote) => {
        if (!active) return;
        setPreferences((current) => ({
          ...current,
          defaultPlatform: remote.default_platform,
          defaultPlatformName: remote.default_platform_name || "",
          defaultTone: remote.default_tone,
          defaultLanguage: remote.default_language,
          defaultLength: remote.default_length,
          defaultExportFormat: remote.default_export_format,
          includeTimestamps: remote.include_timestamps,
        }));
      })
      .catch((error) => {
        toast.error(getUserErrorMessage(error, "Không thể đồng bộ cài đặt."));
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [toast]);

  const update = (name, value) => {
    setSaved(false);
    setPreferences((current) => ({ ...current, [name]: value }));
    if (name === "theme") setTheme(value);
  };

  const save = async () => {
    if (pending) return;
    setPending(true);
    try {
      savePreferences(preferences);
      await updateUserSettings({
        default_platform: preferences.defaultPlatform,
        default_platform_name: preferences.defaultPlatform === "other" ? preferences.defaultPlatformName?.trim() || null : null,
        default_tone: preferences.defaultTone,
        default_language: preferences.defaultLanguage,
        default_length: preferences.defaultLength,
        default_export_format: preferences.defaultExportFormat,
        include_timestamps: preferences.includeTimestamps,
      });
      setSaved(true);
      toast.success("Đã lưu cài đặt.");
    } catch (error) {
      toast.error(getUserErrorMessage(error, "Không thể lưu cài đặt."));
    } finally {
      setPending(false);
    }
  };

  return (
    <WorkspaceLayout title="Cài đặt" subtitle="Tùy chỉnh trải nghiệm AdGen AI">
      {loading ? <div className="settings-loading">Đang tải cài đặt...</div> : (
        <div className="settings-groups">
          <section className="settings-section">
            <header><FiSun /><div><h2>Giao diện</h2><p>Áp dụng ngay cho toàn bộ ứng dụng.</p></div></header>
            <div className="settings-themes">
              {THEMES.map(({ value, label, icon: Icon }) => (
                <button key={value} type="button" className={preferences.theme === value ? "is-active" : ""} onClick={() => update("theme", value)}>
                  <Icon /> {label} {preferences.theme === value && <FiCheck />}
                </button>
              ))}
            </div>
          </section>

          <section className="settings-section">
            <header><FiMessageSquare /><div><h2>Chat</h2><p>Hành vi hội thoại và lịch sử.</p></div></header>
            <Toggle label="Tự động cuộn" description="Theo dõi phản hồi AI khi streaming." checked={preferences.autoScroll} onChange={(value) => update("autoScroll", value)} />
            <Toggle label="Hiển thị thời gian" description="Hiển thị thời gian dưới mỗi tin nhắn." checked={preferences.showMessageTime} onChange={(value) => update("showMessageTime", value)} />
            <Toggle label="Xác nhận trước khi xóa" description="Tránh xóa nhầm hội thoại." checked={preferences.confirmBeforeDelete} onChange={(value) => update("confirmBeforeDelete", value)} />
            <Toggle label="Mở hội thoại gần nhất" description="Tự chọn hội thoại mới nhất khi vào Chat." checked={preferences.openLatestConversation} onChange={(value) => update("openLatestConversation", value)} />
          </section>

          <section className="settings-section">
            <header><FiSliders /><div><h2>Tùy chọn AI</h2><p>Giá trị mặc định khi tạo nội dung.</p></div></header>
            <div className="settings-select-grid">              <label><span>Nền tảng</span><select value={preferences.defaultPlatform} onChange={(event) => update("defaultPlatform", event.target.value)}>
                {PLATFORM_OPTIONS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select></label>
              {preferences.defaultPlatform === "other" && (
                <label><span>Tên nền tảng mặc định</span><input value={preferences.defaultPlatformName || ""} maxLength={80} placeholder="Ví dụ: Zalo OA" onChange={(event) => update("defaultPlatformName", event.target.value)} /></label>
              )}
              <label><span>Giọng văn</span><select value={preferences.defaultTone} onChange={(event) => update("defaultTone", event.target.value)}><option value="professional">Chuyên nghiệp</option><option value="friendly">Thân thiện</option><option value="persuasive">Thuyết phục</option><option value="creative">Sáng tạo</option></select></label>
              <label><span>Ngôn ngữ</span><select value={preferences.defaultLanguage} onChange={(event) => update("defaultLanguage", event.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
              <label><span>Độ dài</span><select value={preferences.defaultLength} onChange={(event) => update("defaultLength", event.target.value)}><option value="short">Ngắn</option><option value="medium">Trung bình</option><option value="long">Dài</option></select></label>
            </div>
          </section>

          <section className="settings-section">
            <header><FiDownload /><div><h2>Xuất dữ liệu</h2><p>Định dạng mặc định cho nội dung tải xuống.</p></div></header>
            <div className="settings-select-grid">
              <label><span>Định dạng</span><select value={preferences.defaultExportFormat} onChange={(event) => update("defaultExportFormat", event.target.value)}><option value="markdown">Markdown</option><option value="txt">Text</option><option value="pdf">PDF</option></select></label>
            </div>
            <Toggle label="Kèm thời gian tin nhắn" description="Thêm thời gian vào nội dung xuất." checked={preferences.includeTimestamps} onChange={(value) => update("includeTimestamps", value)} />
          </section>

          <ChangePasswordForm />
          <ActiveSessions />

          <div className="settings-save-row">
            <button type="button" onClick={save} disabled={pending}>
              {saved ? <FiCheck /> : <FiSettings />}
              {pending ? "Đang lưu..." : saved ? "Đã lưu" : "Lưu cài đặt"}
            </button>
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}

export default Settings;
