import { FiChevronDown } from "react-icons/fi";

import {
  EXTRA_PLATFORM_OPTIONS,
  LEGACY_PLATFORM_LABELS,
  PRIMARY_PLATFORM_OPTIONS,
  getPlatformLabel,
  isCurrentPlatform,
} from "../../../constants/platforms";
import "./PromptSelector.css";

function PromptSelector({
  value,
  onChange,
  platformName = "",
  onPlatformNameChange,
  disabled = false,
  compact = false,
}) {
  const isLegacy = value && !isCurrentPlatform(value);

  return (
    <div
      className={`prompt-selector \${compact ? "prompt-selector--compact" : ""}`}
    >
      {!compact && (
        <label className="prompt-selector__label" htmlFor="prompt-type">
          Nền tảng đăng nội dung
        </label>
      )}

      <div className="prompt-selector__control">
        <select
          id="prompt-type"
          className="prompt-selector__select"
          value={value || "facebook"}
          onChange={(event) => onChange?.(event.target.value)}
          disabled={disabled}
          aria-label="Chọn nền tảng đăng nội dung"
        >
          <optgroup label="Thường dùng">
            {PRIMARY_PLATFORM_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </optgroup>
          <optgroup label="Xem thêm">
            {EXTRA_PLATFORM_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </optgroup>
          {isLegacy && (
            <option value={value}>
              {"Nền tảng cũ: " +
                (LEGACY_PLATFORM_LABELS[value] || getPlatformLabel(value))}
            </option>
          )}
        </select>

        <FiChevronDown />
      </div>
      {value === "other" && (
        <input
          className="prompt-selector__custom-name"
          value={platformName}
          maxLength={80}
          required
          disabled={disabled}
          placeholder="Tên nền tảng hoặc nơi đăng"
          onChange={(event) => onPlatformNameChange?.(event.target.value)}
        />
      )}
    </div>
  );
}

export default PromptSelector;
