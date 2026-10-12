import { useEffect, useRef, useState } from "react";
import { FiBriefcase, FiCheck, FiChevronDown } from "react-icons/fi";
import "./BrandSelector.css";

function BrandSelector({
  brands = [],
  value = null,
  onChange,
  disabled = false,
  compact = false,
}) {
  const containerRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const options = [
    {
      value: "",
      label: "Không dùng thương hiệu",
      description: "AI viết theo yêu cầu hiện tại.",
    },
    ...brands.map((brand) => ({
      value: String(brand.id),
      label: brand.name,
      description:
        brand.default_tone || brand.industry || "Giữ nhất quán cho nội dung AI.",
      isDefault: Boolean(brand.is_default),
    })),
  ];

  const selectedValue = value == null ? "" : String(value);
  const selectedOption =
    options.find((option) => option.value === selectedValue) || options[0];

  useEffect(() => {
    const handlePointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, []);

  const selectOption = (nextValue) => {
    onChange?.(nextValue ? Number(nextValue) : null);
    setIsOpen(false);
  };

  const handleKeyDown = (event) => {
    if (disabled) return;

    if (event.key === "Escape") {
      setIsOpen(false);
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (isOpen) {
        selectOption(options[activeIndex]?.value ?? "");
      } else {
        const selectedIndex = options.findIndex(
          (option) => option.value === selectedValue,
        );
        setActiveIndex(Math.max(0, selectedIndex));
        setIsOpen(true);
      }
      return;
    }

    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex((current) =>
        Math.min(Math.max(current + direction, 0), options.length - 1),
      );
      setIsOpen(true);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`brand-selector ${compact ? "brand-selector--compact" : ""}`}
      title="Hồ sơ thương hiệu giúp AI giữ đúng phong cách và thông tin thương hiệu"
    >
      {!compact && <span className="brand-selector__label">Thương hiệu</span>}
      <div className="brand-selector__control">
        <button
          type="button"
          className="brand-selector__select"
          onClick={() => {
            if (!disabled) {
              const selectedIndex = options.findIndex(
                (option) => option.value === selectedValue,
              );
              setActiveIndex(Math.max(0, selectedIndex));
              setIsOpen((open) => !open);
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-label="Chọn hồ sơ thương hiệu để AI viết nhất quán"
        >
          <FiBriefcase className="brand-selector__icon" aria-hidden="true" />
          <span className="brand-selector__selected-label">
            {selectedOption.label}
          </span>
          <FiChevronDown className="brand-selector__chevron" aria-hidden="true" />
        </button>

        {isOpen && (
          <div className="brand-selector__menu" role="listbox">
            <div className="brand-selector__menu-head">
              <strong>Hồ sơ thương hiệu</strong>
              <span>
                Giúp AI giữ đúng phong cách, thông tin và từ ngữ bạn muốn dùng.
              </span>
            </div>

            <div className="brand-selector__group">
              <div className="brand-selector__group-label">LỰA CHỌN</div>
              <button
                type="button"
                className={`brand-selector__option ${
                  selectedOption.value === "" ? "is-selected" : ""
                }`}
                role="option"
                aria-selected={selectedOption.value === ""}
                onClick={() => selectOption("")}
                onMouseEnter={() => setActiveIndex(0)}
              >
                <span className="brand-selector__option-copy">
                  <span className="brand-selector__option-label">
                    Không dùng thương hiệu
                  </span>
                  <span className="brand-selector__option-description">
                    AI viết theo yêu cầu hiện tại.
                  </span>
                </span>
                {selectedOption.value === "" && <FiCheck aria-hidden="true" />}
              </button>
            </div>

            <div className="brand-selector__group">
              <div className="brand-selector__group-label">THƯƠNG HIỆU CỦA BẠN</div>
              {brands.length > 0 ? (
                brands.map((brand, index) => {
                  const optionValue = String(brand.id);
                  const isSelected = selectedValue === optionValue;

                  return (
                    <button
                      type="button"
                      className={`brand-selector__option ${
                        isSelected ? "is-selected" : ""
                      }`}
                      key={brand.id}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => selectOption(optionValue)}
                      onMouseEnter={() => setActiveIndex(index + 1)}
                    >
                      <span className="brand-selector__option-copy">
                        <span className="brand-selector__option-label">
                          {brand.name}
                          {brand.is_default && <small> · Mặc định</small>}
                        </span>
                        <span className="brand-selector__option-description">
                          {brand.default_tone ||
                            brand.industry ||
                            "Giữ nhất quán cho nội dung AI."}
                        </span>
                      </span>
                      {isSelected && <FiCheck aria-hidden="true" />}
                    </button>
                  );
                })
              ) : (
                <div className="brand-selector__empty">
                  Bạn chưa có hồ sơ thương hiệu. AI sẽ viết theo yêu cầu hiện tại.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default BrandSelector;
