import { useEffect, useRef, useState } from "react";
import { FiSliders, FiX } from "react-icons/fi";

import { getPreferences } from "../../../utils/settingsStorage";
import {
  EXTRA_PLATFORM_OPTIONS,
  PRIMARY_PLATFORM_OPTIONS,
} from "../../../constants/platforms";
import "./AdBriefForm.css";

const EMPTY_BRIEF = {
  product_name: "",
  description: "",
  target_audience: "",
  objective: "",
  platform: "",
  platform_name: "",
  tone: "",
  length: "",
  keywords: "",
  cta: "",
  language: "Tiếng Việt",
};

const TONE_MAP = {
  professional: "Chuyên nghiệp",
  friendly: "Gần gũi",
  persuasive: "Thuyết phục",
  creative: "Trẻ trung",
};

const LENGTH_MAP = {
  short: "Ngắn",
  medium: "Trung bình",
  long: "Dài",
};

const LANGUAGE_MAP = {
  vi: "Tiếng Việt",
  en: "English",
};

const getInitialBrief = () => {
  try {
    const prefs = getPreferences();
    return {
      ...EMPTY_BRIEF,
      tone: TONE_MAP[prefs.defaultTone] || "",
      length: LENGTH_MAP[prefs.defaultLength] || "",
      language: LANGUAGE_MAP[prefs.defaultLanguage] || "Tiếng Việt",
    };
  } catch {
    return EMPTY_BRIEF;
  }
};

const OPTIONS = {
  platform: [["", "Theo lựa chọn nội dung"], ...PRIMARY_PLATFORM_OPTIONS.map(({ value, label }) => [value, label]), ...EXTRA_PLATFORM_OPTIONS.map(({ value, label }) => [value, label])],
  objective: [["", "Chọn mục tiêu"], ["Nhận diện thương hiệu", "Nhận diện thương hiệu"], ["Tăng tương tác", "Tăng tương tác"], ["Thu hút khách hàng tiềm năng", "Khách hàng tiềm năng"], ["Tăng chuyển đổi/bán hàng", "Tăng chuyển đổi/bán hàng"], ["Tăng lượt truy cập", "Tăng lượt truy cập"]],
  tone: [["", "Tự động"], ["Chuyên nghiệp", "Chuyên nghiệp"], ["Gần gũi", "Gần gũi"], ["Trẻ trung", "Trẻ trung"], ["Cao cấp", "Cao cấp"], ["Hài hước", "Hài hước"], ["Thuyết phục", "Thuyết phục"]],
  length: [["", "Tự động"], ["Ngắn", "Ngắn"], ["Trung bình", "Trung bình"], ["Dài", "Dài"]],
  language: [["Tiếng Việt", "Tiếng Việt"], ["English", "English"], ["日本語", "日本語"], ["한국어", "한국어"]],
};

function SelectField({ label, name, value, onChange }) {
  return (
    <label className="ad-brief-form__field">
      <span>{label}</span>
      <select name={name} value={value} onChange={onChange}>
        {OPTIONS[name].map(([optionValue, optionLabel]) => (
          <option value={optionValue} key={optionValue || "default"}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function AdBriefForm({
  open,
  value,
  onApply,
  onDraftChange,
  onClear,
  onClose,
  disabled,
}) {
  const [prevValue, setPrevValue] = useState(value);
  const [draft, setDraft] = useState(() => value || getInitialBrief());
  const [error, setError] = useState("");
  const panelRef = useRef(null);

  if (value !== prevValue) {
    setPrevValue(value);
    setDraft(value || getInitialBrief());
  }

  useEffect(() => {
    if (!open) return undefined;

    const closePanel = (event) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }

      if (
        event.type === "pointerdown" &&
        !panelRef.current?.contains(event.target) &&
        !event.target.closest("[data-ad-brief-trigger]")
      ) {
        onClose();
      }
    };

    document.addEventListener("pointerdown", closePanel);
    document.addEventListener("keydown", closePanel);
    return () => {
      document.removeEventListener("pointerdown", closePanel);
      document.removeEventListener("keydown", closePanel);
    };
  }, [open, onClose]);

  const update = (event) => {
    const { name, value: fieldValue } = event.target;
    const nextDraft = {
      ...draft,
      [name]: fieldValue,
      ...(name === "platform" && fieldValue !== "other"
        ? { platform_name: "" }
        : {}),
    };
    const hasContent = Object.entries(nextDraft).some(
      ([field, currentValue]) =>
        field !== "language" && String(currentValue).trim(),
    );
    setDraft(nextDraft);
    onDraftChange(hasContent);
    setError("");
  };

  const apply = () => {
    if (draft.platform === "other" && !draft.platform_name.trim()) {
      setError("Hãy nhập tên nền tảng hoặc nơi sẽ đăng nội dung.");
      return;
    }
    if (!draft.product_name.trim() && !draft.description.trim()) {
      setError("Hãy nhập tên sản phẩm hoặc mô tả.");
      return;
    }
    onApply(draft);
    onDraftChange(true);
    onClose();
  };

  if (!open) return null;

  return (
    <section ref={panelRef} className="ad-brief-form ad-brief-form--popover">
      <header className="ad-brief-form__header">
        <span className="ad-brief-form__header-icon"><FiSliders /></span>
        <div>
          <strong>Thông tin quảng cáo</strong>
          <small>Giúp AI tạo nội dung sát yêu cầu hơn</small>
        </div>
        <button type="button" onClick={onClose} aria-label="Đóng"><FiX /></button>
      </header>

      <div className="ad-brief-form__body">
        <div className="ad-brief-form__grid">
          <label className="ad-brief-form__field">
            <span>Tên sản phẩm/dịch vụ</span>
            <input name="product_name" value={draft.product_name} onChange={update} placeholder="Ví dụ: AdGen AI" disabled={disabled} />
          </label>
          <SelectField label="Nền tảng" name="platform" value={draft.platform} onChange={update} />
          {draft.platform === "other" && (
            <label className="ad-brief-form__field ad-brief-form__field--wide">
              <span>Tên nền tảng hoặc nơi sẽ đăng *</span>
              <input
                name="platform_name"
                value={draft.platform_name}
                onChange={update}
                placeholder="Ví dụ: Zalo OA hoặc website của cửa hàng"
                maxLength={80}
                required
                disabled={disabled}
              />
            </label>
          )}
          <label className="ad-brief-form__field ad-brief-form__field--wide">
            <span>Mô tả</span>
            <textarea name="description" value={draft.description} onChange={update} placeholder="Tính năng, lợi ích, điểm khác biệt..." rows={3} disabled={disabled} />
          </label>
          <label className="ad-brief-form__field"><span>Khách hàng mục tiêu</span><input name="target_audience" value={draft.target_audience} onChange={update} placeholder="Độ tuổi, nhu cầu, hành vi..." /></label>
          <SelectField label="Mục tiêu quảng cáo" name="objective" value={draft.objective} onChange={update} />
          <SelectField label="Giọng văn" name="tone" value={draft.tone} onChange={update} />
          <SelectField label="Độ dài" name="length" value={draft.length} onChange={update} />
          <label className="ad-brief-form__field"><span>Từ khóa</span><input name="keywords" value={draft.keywords} onChange={update} placeholder="AI, quảng cáo, tiết kiệm thời gian" /></label>
          <label className="ad-brief-form__field"><span>CTA</span><input name="cta" value={draft.cta} onChange={update} placeholder="Dùng thử ngay" /></label>
          <SelectField label="Ngôn ngữ" name="language" value={draft.language} onChange={update} />
        </div>

        {error && <p className="ad-brief-form__error" role="alert">{error}</p>}

        <div className="ad-brief-form__actions">
          {value && <button type="button" onClick={() => { onClear(); setDraft(getInitialBrief()); }}>Bỏ brief</button>}
          <button type="button" onClick={onClose}>Đóng</button>
          <button type="button" className="is-primary" onClick={apply} disabled={disabled}>Áp dụng brief</button>
        </div>
      </div>
    </section>
  );
}

export default AdBriefForm;
