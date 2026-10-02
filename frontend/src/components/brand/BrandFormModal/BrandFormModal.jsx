import { useEffect, useState } from "react";
import Modal from "../../ui/Modal/Modal";
import {
  parseBrandList,
  validateBrandProfile,
} from "../../../utils/brandProfile";
import "./BrandFormModal.css";

const EMPTY = {
  name: "",
  description: "",
  industry: "",
  website: "",
  slogan: "",
  mission: "",
  target_audience: "",
  brand_personality: "",
  default_tone: "",
  default_language: "vi",
  primary_color: "",
  secondary_color: "",
  keywords: [],
  forbidden_words: [],
  preferred_cta: "",
  writing_guidelines: "",
  is_default: false,
};

const listText = (value) =>
  Array.isArray(value) ? value.join(", ") : (value || "");
function BrandFormModal({ open, brand, pending, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!open) return;
    // Reset the remote entity snapshot whenever the modal opens.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setForm(brand ? { ...EMPTY, ...brand } : EMPTY);
    setErrors({});
  }, [brand, open]);

  const set = (field, value) =>
    setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event) => {
    event.preventDefault();
    const nextErrors = validateBrandProfile(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    const result = await onSubmit?.({
      ...form,
      name: form.name.trim(),
      website: form.website.trim() || null,
      primary_color: form.primary_color.trim() || null,
      secondary_color: form.secondary_color.trim() || null,
      keywords: Array.isArray(form.keywords)
        ? form.keywords
        : parseBrandList(form.keywords),
      forbidden_words: Array.isArray(form.forbidden_words)
        ? form.forbidden_words
        : parseBrandList(form.forbidden_words),
    });
    if (result) onClose?.();
  };

  return (
    <Modal
      open={open}
      title={brand ? "Chỉnh sửa hồ sơ thương hiệu" : "Tạo hồ sơ thương hiệu"}
      size="lg"
      onClose={onClose}
      closeDisabled={pending}
      footer={
        <div className="brand-form__actions">
          <button type="button" onClick={onClose} disabled={pending}>Hủy</button>
          <button type="submit" form="brand-profile-form" className="is-primary" disabled={pending}>
            {pending ? "Đang lưu..." : "Lưu hồ sơ"}
          </button>
        </div>
      }
    >
      <form id="brand-profile-form" className="brand-form" onSubmit={submit}>
        <fieldset>
          <legend>Thông tin cơ bản</legend>
          <div className="brand-form__grid">
            <label>Tên thương hiệu *
              <input value={form.name} maxLength={120} onChange={(e) => set("name", e.target.value)} />
              {errors.name && <small className="is-error">{errors.name}</small>}
            </label>
            <label>Ngành nghề
              <input value={form.industry || ""} maxLength={120} onChange={(e) => set("industry", e.target.value)} />
            </label>
            <label className="is-wide">Website
              <input value={form.website || ""} placeholder="https://example.com" onChange={(e) => set("website", e.target.value)} />
              {errors.website && <small className="is-error">{errors.website}</small>}
            </label>
            <label className="is-wide">Slogan
              <input value={form.slogan || ""} maxLength={240} onChange={(e) => set("slogan", e.target.value)} />
            </label>
            <label className="is-wide">Mô tả
              <textarea rows={3} value={form.description || ""} onChange={(e) => set("description", e.target.value)} />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Định hướng thương hiệu</legend>
          <div className="brand-form__grid">
            <label className="is-wide">Sứ mệnh
              <textarea rows={2} value={form.mission || ""} onChange={(e) => set("mission", e.target.value)} />
            </label>
            <label className="is-wide">Khách hàng mục tiêu
              <textarea rows={2} value={form.target_audience || ""} onChange={(e) => set("target_audience", e.target.value)} />
            </label>
            <label>Tính cách
              <input value={form.brand_personality || ""} placeholder="Hiện đại, đáng tin cậy" onChange={(e) => set("brand_personality", e.target.value)} />
            </label>
            <label>Giọng điệu
              <input value={form.default_tone || ""} placeholder="Thân thiện, chuyên nghiệp" onChange={(e) => set("default_tone", e.target.value)} />
            </label>
            <label>Ngôn ngữ
              <select value={form.default_language || "vi"} onChange={(e) => set("default_language", e.target.value)}>
                <option value="vi">Tiếng Việt</option>
                <option value="en">English</option>
                <option value="vi-en">Song ngữ Việt – Anh</option>
              </select>
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Nội dung và nhận diện</legend>
          <div className="brand-form__grid">
            <label>Màu chính
              <input value={form.primary_color || ""} placeholder="#4F46E5" onChange={(e) => set("primary_color", e.target.value)} />
              {errors.primary_color && <small className="is-error">{errors.primary_color}</small>}
            </label>
            <label>Màu phụ
              <input value={form.secondary_color || ""} placeholder="#14B8A6" onChange={(e) => set("secondary_color", e.target.value)} />
              {errors.secondary_color && <small className="is-error">{errors.secondary_color}</small>}
            </label>
            <label className="is-wide">Từ khóa ưu tiên (phân cách bằng dấu phẩy)
              <input
                value={listText(form.keywords)}
                onChange={(e) => set("keywords", e.target.value)}
              />
            </label>
            <label className="is-wide">Từ ngữ không được dùng (phân cách bằng dấu phẩy)
              <input
                value={listText(form.forbidden_words)}
                onChange={(e) => set("forbidden_words", e.target.value)}
              />
            </label>
            <label className="is-wide">CTA ưu tiên
              <input value={form.preferred_cta || ""} onChange={(e) => set("preferred_cta", e.target.value)} />
            </label>
            <label className="is-wide">Quy chuẩn viết
              <textarea rows={3} value={form.writing_guidelines || ""} onChange={(e) => set("writing_guidelines", e.target.value)} />
            </label>
            <label className="brand-form__check is-wide">
              <input type="checkbox" checked={Boolean(form.is_default)} onChange={(e) => set("is_default", e.target.checked)} />
              Dùng làm thương hiệu mặc định
            </label>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}

export default BrandFormModal;
