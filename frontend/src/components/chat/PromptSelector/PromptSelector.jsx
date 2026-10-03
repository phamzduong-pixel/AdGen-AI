import { useEffect, useRef, useState } from "react";
import { FiCheck, FiChevronDown } from "react-icons/fi";

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
  const containerRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const isLegacy = value && !isCurrentPlatform(value);
  const groups = [
    { label: "Thường dùng", options: PRIMARY_PLATFORM_OPTIONS },
    { label: "Xem thêm", options: EXTRA_PLATFORM_OPTIONS },
    ...(isLegacy
      ? [{
          label: "Đã dùng trước đây",
          options: [{
            value,
            label: `Nền tảng cũ: ${LEGACY_PLATFORM_LABELS[value] || getPlatformLabel(value)}`,
          }],
        }]
      : []),
  ];
  const options = groups.flatMap((group) => group.options);
  const selectedOption = options.find((option) => option.value === value);
  const selectedLabel = selectedOption?.label || getPlatformLabel(value || "facebook");

  useEffect(() => {
    const handleOutsidePointer = (event) => {
      if (!containerRef.current?.contains(event.target)) setIsOpen(false);
    };
    document.addEventListener("pointerdown", handleOutsidePointer);
    return () => document.removeEventListener("pointerdown", handleOutsidePointer);
  }, []);



  const selectOption = (nextValue) => {
    onChange?.(nextValue);
    setIsOpen(false);
  };

  const handleKeyDown = (event) => {
    if (disabled) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setIsOpen(false);
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (!isOpen) {
        setActiveIndex(Math.max(0, options.findIndex((option) => option.value === value)));
        setIsOpen(true);
      } else if (options[activeIndex]) {
        selectOption(options[activeIndex].value);
      }
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      const currentIndex = isOpen
        ? activeIndex
        : Math.max(0, options.findIndex((option) => option.value === value));
      setActiveIndex((currentIndex + direction + options.length) % options.length);
      setIsOpen(true);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`prompt-selector ${compact ? "prompt-selector--compact" : ""}`}
    >
      {!compact && (
        <label className="prompt-selector__label" htmlFor="prompt-type">
          Nền tảng đăng nội dung
        </label>
      )}

      <div className="prompt-selector__control">
        <button
          id="prompt-type"
          type="button"
          className={`prompt-selector__select ${isOpen ? "is-open" : ""}`}
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-label="Chọn nền tảng đăng nội dung"
          disabled={disabled}
          onClick={() => {
            setActiveIndex(Math.max(0, options.findIndex((option) => option.value === value)));
            setIsOpen((current) => !current);
          }}
          onKeyDown={handleKeyDown}
        >
          <span>{selectedLabel}</span>
          <FiChevronDown aria-hidden="true" />
        </button>

        {isOpen && (
          <div className="prompt-selector__menu" role="listbox" aria-label="Nền tảng đăng nội dung">
            {groups.map((group) => (
              <div className="prompt-selector__group" key={group.label}>
                <div className="prompt-selector__group-label">{group.label}</div>
                {group.options.map((option) => {
                  const optionIndex = options.findIndex((item) => item.value === option.value);
                  const isSelected = option.value === value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className={`prompt-selector__option ${isSelected ? "is-selected" : ""} ${optionIndex === activeIndex ? "is-active" : ""}`}
                      role="option"
                      aria-selected={isSelected}
                      onMouseEnter={() => setActiveIndex(optionIndex)}
                      onClick={() => selectOption(option.value)}
                    >
                      <span>{option.label}</span>
                      {isSelected && <FiCheck aria-hidden="true" />}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        )}
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