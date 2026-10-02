import { useState } from "react";

import Modal from "../../ui/Modal/Modal";
import { PLATFORM_OPTIONS } from "../../../constants/platforms";
import "./CampaignFormModal.css";

const EMPTY_FORM = {
  name: "",
  description: "",
  notes: "",
  product_name: "",
  target_audience: "",
  objective: "",
  platform: "",
  platform_name: "",
  status: "draft",
  brand_id: "",
};

function CampaignFormModal({ open, campaign, brands = [], pending, onClose, onSubmit }) {
  const [form, setForm] = useState(() =>
      campaign
        ? Object.fromEntries(
            Object.keys(EMPTY_FORM).map((key) => [
              key,
              campaign[key] ?? EMPTY_FORM[key],
            ]),
          )
        : EMPTY_FORM,
  );

  const update = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
      ...(name === "platform" && value !== "other" ? { platform_name: "" } : {}),
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    const result = await onSubmit({
      ...form,
      brand_id: form.brand_id ? Number(form.brand_id) : null,
    });
    if (result) onClose();
  };

  return (
    <Modal
      open={open}
      title={campaign ? "Chỉnh sửa chiến dịch" : "Tạo chiến dịch"}
      onClose={onClose}
      closeDisabled={pending}
      size="lg"
    >
      <form className="campaign-form" onSubmit={submit}>
        <label className="campaign-form__wide">
          <span>Tên chiến dịch *</span>
          <input name="name" value={form.name} onChange={update} maxLength="160" required autoFocus />
        </label>
        <label>
          <span>Sản phẩm</span>
          <input name="product_name" value={form.product_name} onChange={update} maxLength="200" />
        </label>
        <label>
          <span>Nền tảng</span>
                    <select name="platform" value={form.platform} onChange={update}>
            <option value="">Nội dung chung</option>
            {PLATFORM_OPTIONS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
          </select>
        </label>        {form.platform === "other" && (
          <label>
            <span>Tên nền tảng hoặc nơi đăng *</span>
            <input name="platform_name" value={form.platform_name} onChange={update} maxLength="80" placeholder="Ví dụ: Zalo OA" required />
          </label>
        )}
        <label>
          <span>Trạng thái</span>
          <select name="status" value={form.status} onChange={update}>
            <option value="draft">Bản nháp</option>
            <option value="active">Đang chạy</option>
            <option value="completed">Hoàn thành</option>
            <option value="archived">Lưu trữ</option>
          </select>
        </label>
        <label>
          <span>Hồ sơ thương hiệu</span>
          <select name="brand_id" value={form.brand_id ?? ""} onChange={update}>
            <option value="">Không dùng thương hiệu</option>
            {brands.map((brandItem) => (
              <option key={brandItem.id} value={brandItem.id}>
                {brandItem.name}{brandItem.is_default ? " (mặc định)" : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Mục tiêu</span>
          <input name="objective" value={form.objective} onChange={update} maxLength="500" />
        </label>
        <label className="campaign-form__wide">
          <span>Khách hàng mục tiêu</span>
          <textarea name="target_audience" value={form.target_audience} onChange={update} rows="2" />
        </label>
        <label className="campaign-form__wide">
          <span>Mô tả</span>
          <textarea name="description" value={form.description} onChange={update} rows="3" />
        </label>
        <label className="campaign-form__wide">
          <span>Ghi chú chiến dịch</span>
          <textarea name="notes" value={form.notes} onChange={update} rows="3" />
        </label>
        <div className="campaign-form__actions campaign-form__wide">
          <button type="button" onClick={onClose} disabled={pending}>Hủy</button>
          <button type="submit" className="is-primary" disabled={pending || !form.name.trim()}>
            {pending ? "Đang lưu..." : campaign ? "Lưu thay đổi" : "Tạo chiến dịch"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default CampaignFormModal;
