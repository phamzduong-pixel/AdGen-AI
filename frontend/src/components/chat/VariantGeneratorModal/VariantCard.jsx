import {
  FiBarChart2,
  FiBookmark,
  FiCheck,
  FiCopy,
  FiLoader,
} from "react-icons/fi";

function VariantCard({
  variant,
  evaluation,
  evaluating,
  selected,
  primary,
  saving,
  onCopy,
  onSave,
  onEvaluate,
  onToggleComparison,
  onSelectPrimary,
}) {
  return (
    <article className={`variant-card ${primary ? "is-primary" : ""}`}>
      <header>
        <span className="variant-card__label">{variant.label}</span>
        <div>
          <h3>Phiên bản {variant.label}</h3>
          <p>{variant.strategy}</p>
        </div>
        {primary && <span className="variant-card__primary"><FiCheck /> Bản chính</span>}
      </header>

      {variant.title && <h4>{variant.title}</h4>}
      <p className="variant-card__content">{variant.content}</p>
      <p className="variant-card__cta"><strong>CTA:</strong> {variant.cta}</p>

      {evaluation && (
        <div className="variant-card__score">
          <strong>{evaluation.overall_score}/100</strong>
          <span>Điểm đánh giá AI</span>
        </div>
      )}

      <label className="variant-card__compare">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleComparison}
        />
        Chọn để so sánh
      </label>

      <div className="variant-card__actions">
        <button type="button" onClick={onCopy}><FiCopy /> Sao chép</button>
        <button type="button" onClick={onSave} disabled={saving}>
          {saving ? <FiLoader className="variant-card__spinner" /> : <FiBookmark />}
          Lưu
        </button>
        <button type="button" onClick={onEvaluate} disabled={evaluating || evaluation}>
          {evaluating ? <FiLoader className="variant-card__spinner" /> : <FiBarChart2 />}
          {evaluation ? "Đã đánh giá" : "Đánh giá"}
        </button>
        <button type="button" onClick={onSelectPrimary}>
          <FiCheck /> Chọn bản chính
        </button>
      </div>
    </article>
  );
}

export default VariantCard;
