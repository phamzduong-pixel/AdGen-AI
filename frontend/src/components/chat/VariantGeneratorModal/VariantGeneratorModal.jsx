import { useState } from "react";
import { createPortal } from "react-dom";
import { FiLayers, FiLoader, FiX } from "react-icons/fi";

import useToast from "../../ui/Toast/useToast";
import VariantCard from "./VariantCard";
import VariantComparison from "./VariantComparison";
import "./VariantGeneratorModal.css";

const variantText = (variant) =>
  [variant.title, variant.content, variant.cta && `CTA: ${variant.cta}`]
    .filter(Boolean)
    .join("\n\n");

function VariantGeneratorModal({
  open,
  variants,
  evaluations,
  selectedLabels,
  primaryLabel,
  loading,
  evaluatingLabels,
  onClose,
  onEvaluate,
  onEvaluateSelected,
  onToggleComparison,
  onSelectPrimary,
  onSave,
}) {
  const toast = useToast();
  const [savingLabels, setSavingLabels] = useState([]);

  if (!open) return null;

  const copyVariant = async (variant) => {
    try {
      await navigator.clipboard.writeText(variantText(variant));
      toast.success(`Đã sao chép phiên bản ${variant.label}.`);
    } catch {
      toast.error("Không thể sao chép nội dung.");
    }
  };

  const saveVariant = async (variant) => {
    if (savingLabels.includes(variant.label)) return;
    setSavingLabels((current) => [...current, variant.label]);
    try {
      await onSave(variant, variantText(variant));
    } finally {
      setSavingLabels((current) =>
        current.filter((label) => label !== variant.label),
      );
    }
  };

  const selectedVariants = variants.filter((variant) =>
    selectedLabels.includes(variant.label),
  );

  return createPortal(
    <div className="variant-modal" role="dialog" aria-modal="true">
      <button
        type="button"
        className="variant-modal__backdrop"
        onClick={loading ? undefined : onClose}
        aria-label="Đóng phiên bản A/B"
      />
      <section className="variant-modal__panel">
        <header className="variant-modal__header">
          <div className="variant-modal__title">
            <span><FiLayers /></span>
            <div>
              <h2>Phiên bản quảng cáo A/B</h2>
              <p>Ba chiến lược khác nhau từ nội dung gốc</p>
            </div>
          </div>
          <button type="button" onClick={onClose} disabled={loading} aria-label="Đóng">
            <FiX />
          </button>
        </header>

        <div className="variant-modal__body">
          {loading ? (
            <div className="variant-modal__loading">
              <FiLoader />
              <strong>Đang tạo 3 phiên bản...</strong>
              <span>Thông tin gốc sẽ được giữ nguyên.</span>
            </div>
          ) : (
            <>
              <div className="variant-modal__cards">
                {variants.map((variant) => (
                  <VariantCard
                    key={variant.label}
                    variant={variant}
                    evaluation={evaluations[variant.label]}
                    evaluating={evaluatingLabels.has(variant.label)}
                    selected={selectedLabels.includes(variant.label)}
                    primary={primaryLabel === variant.label}
                    saving={savingLabels.includes(variant.label)}
                    onCopy={() => copyVariant(variant)}
                    onSave={() => saveVariant(variant)}
                    onEvaluate={() => onEvaluate(variant)}
                    onToggleComparison={() => onToggleComparison(variant.label)}
                    onSelectPrimary={() => onSelectPrimary(variant.label)}
                  />
                ))}
              </div>
              <VariantComparison
                variants={selectedVariants}
                evaluations={evaluations}
                onEvaluateAll={onEvaluateSelected}
                onSaveBest={saveVariant}
                saving={savingLabels.length > 0}
              />
            </>
          )}
        </div>
      </section>
    </div>,
    document.body,
  );
}

export default VariantGeneratorModal;
