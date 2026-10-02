import { useEffect, useState } from "react";

import Modal from "../../ui/Modal/Modal";
import {
  PLATFORM_OPTIONS,
  getPlatformLabel,
} from "../../../constants/platforms";
import "./TemplateFormModal.css";

const EMPTY_FORM = {
  title: "",
  description: "",
  platform: "facebook",
  platform_name: "",
  category: "Mẫu cá nhân",
  prompt_template: "",
  default_tone: "Chuyên nghiệp",
  default_length: "Trung bình",
  suggested_cta: "",
  source_saved_content_id: "",
};

function TemplateFormModal({
  open,
  template,
  savedContents,
  onClose,
  onSubmit,
}) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    // Reset the controlled form whenever a different modal session opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setForm(
      template
        ? {
            title: template.title,
            description: template.description,
            platform: template.platform,
            platform_name: template.platform_name || "",
            category: template.category,
            prompt_template: template.prompt_template,
            default_tone: template.default_tone,
            default_length: template.default_length,
            suggested_cta: template.suggested_cta,
            source_saved_content_id: "",
          }
        : EMPTY_FORM,
    );
    setError("");
  }, [open, template]);

  const update = (event) => {
    const { name, value } = event.target;
    setError("");
    if (name === "source_saved_content_id") {
      const selected = savedContents.find(
        (item) => String(item.id) === value,
      );
      setForm((current) => ({
        ...current,
        source_saved_content_id: value,
        title: selected?.title || current.title,
        platform: selected?.platform || current.platform,
        platform_name: selected?.platform_name || "",
        prompt_template: selected?.content || current.prompt_template,
      }));
      return;
    }
    setForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "platform" && value !== "other" ? { platform_name: "" } : {}),
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.title.trim()) {
      setError("Tên mẫu không được để trống.");
      return;
    }
    if (!form.prompt_template.trim() && !form.source_saved_content_id) {
      setError("Nội dung mẫu không được để trống.");
      return;
    }
    if (form.platform === "other" && !form.platform_name.trim()) {
      setError("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung.");
      return;
    }

    const payload = {
      title: form.title.trim(),
      description: form.description.trim(),
      platform: form.platform,
      platform_name: form.platform === "other" ? form.platform_name.trim() : "",
      category: form.category.trim() || "Mẫu cá nhân",
      prompt_template: form.prompt_template.trim(),
      default_tone: form.default_tone,
      default_length: form.default_length,
      suggested_cta: form.suggested_cta.trim(),
    };
    if (!template && form.source_saved_content_id) {
      payload.source_saved_content_id = Number(
        form.source_saved_content_id,
      );
    }

    setIsSubmitting(true);
    const result = await onSubmit?.(payload);
    setIsSubmitting(false);
    if (result) onClose();
  };

  return (
    <Modal
      open={open}
      title={template ? "Chỉnh sửa mẫu cá nhân" : "Tạo mẫu cá nhân"}
      onClose={onClose}
      closeDisabled={isSubmitting}
      size="lg"
    >
      <form className="template-form" onSubmit={submit}>
        {!template && savedContents.length > 0 && (
          <label className="template-form__wide">
            <span>Tạo nhanh từ nội dung đã lưu</span>
            <select
              name="source_saved_content_id"
              value={form.source_saved_content_id}
              onChange={update}
              disabled={isSubmitting}
            >
              <option value="">Không sử dụng nội dung đã lưu</option>
              {savedContents.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
        )}

        <label>
          <span>Tên mẫu *</span>
          <input
            name="title"
            value={form.title}
            onChange={update}
            maxLength={160}
            disabled={isSubmitting}
          />
        </label>
        <label>
          <span>Nền tảng</span>
          <select
            name="platform"
            value={form.platform}
            onChange={update}
            disabled={isSubmitting}
          >
            {template && !PLATFORM_OPTIONS.some((item) => item.value === form.platform) && (
              <option value={form.platform} key={form.platform}>
                Nền tảng cũ: {getPlatformLabel(form.platform, form.platform_name)}
              </option>
            )}
            {PLATFORM_OPTIONS.map((item) => (
              <option value={item.value} key={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>        {form.platform === "other" && (
          <label className="template-form__wide">
            <span>Tên nền tảng hoặc nơi đăng *</span>
            <input
              name="platform_name"
              value={form.platform_name}
              onChange={update}
              maxLength={80}
              placeholder="Ví dụ: Zalo OA hoặc website của cửa hàng"
              disabled={isSubmitting}
              required
            />
          </label>
        )}
        <label className="template-form__wide">
          <span>Mô tả ngắn</span>
          <input
            name="description"
            value={form.description}
            onChange={update}
            maxLength={500}
            disabled={isSubmitting}
          />
        </label>
        <label>
          <span>Danh mục</span>
          <input
            name="category"
            value={form.category}
            onChange={update}
            maxLength={80}
            disabled={isSubmitting}
          />
        </label>
        <label>
          <span>CTA gợi ý</span>
          <input
            name="suggested_cta"
            value={form.suggested_cta}
            onChange={update}
            maxLength={300}
            disabled={isSubmitting}
          />
        </label>
        <label>
          <span>Giọng văn</span>
          <select
            name="default_tone"
            value={form.default_tone}
            onChange={update}
            disabled={isSubmitting}
          >
            {["Chuyên nghiệp", "Gần gũi", "Trẻ trung", "Cao cấp", "Hài hước", "Thuyết phục"].map(
              (item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ),
            )}
          </select>
        </label>
        <label>
          <span>Độ dài</span>
          <select
            name="default_length"
            value={form.default_length}
            onChange={update}
            disabled={isSubmitting}
          >
            {["Ngắn", "Trung bình", "Dài"].map((item) => (
              <option value={item} key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="template-form__wide">
          <span>Nội dung hướng dẫn cho AI *</span>
          <textarea
            name="prompt_template"
            value={form.prompt_template}
            onChange={update}
            rows={7}
            maxLength={20000}
            disabled={isSubmitting}
          />
          <small>
            Nội dung này chỉ được điền vào ô chat để bạn kiểm tra trước khi gửi.
          </small>
        </label>

        {error && (
          <p className="template-form__error" role="alert">
            {error}
          </p>
        )}

        <div className="template-form__actions">
          <button type="button" onClick={onClose} disabled={isSubmitting}>
            Hủy
          </button>
          <button type="submit" className="is-primary" disabled={isSubmitting}>
            {isSubmitting
              ? "Đang lưu..."
              : template
                ? "Lưu thay đổi"
                : "Tạo mẫu"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default TemplateFormModal;
