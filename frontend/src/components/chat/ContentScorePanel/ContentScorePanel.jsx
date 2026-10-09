import { createPortal } from "react-dom";
import { FiCheckCircle, FiLoader, FiRefreshCw, FiX } from "react-icons/fi";

import "./ContentScorePanel.css";

function ContentScorePanel({
  open,
  result,
  loading,
  onClose,
  onCreateImproved,
}) {
  if (!open) return null;

  return createPortal(
    <div className="content-score-modal" role="dialog" aria-modal="true">
      <button
        type="button"
        className="content-score-modal__backdrop"
        onClick={loading ? undefined : onClose}
        aria-label="Đóng đánh giá"
      />
      <section className="content-score-panel">
        <header className="content-score-panel__header">
          <div>
            <span>Phân tích bởi AdGen AI</span>
            <h2>Đánh giá nội dung quảng cáo</h2>
          </div>
          <button
            type="button"
            className="content-score-panel__close"
            onClick={onClose}
            disabled={loading}
            aria-label="Đóng"
          >
            <FiX />
          </button>
        </header>

        {loading ? (
          <div className="content-score-panel__loading">
            <FiLoader />
            <strong>Đang phân tích nội dung...</strong>
            <span>AdGen AI đang phân tích theo 9 tiêu chí.</span>
          </div>
        ) : result ? (
          <div className="content-score-panel__body">
            <div className="content-score-panel__summary">
              <div className="content-score-panel__overall">
                <strong>{result.overall_score}</strong>
                <span>/ 100</span>
              </div>
              <div>
                <h3>Điểm tổng</h3>
                <p>
                  Đánh giá tham khảo dựa trên chất lượng nội dung và khả năng
                  chuyển đổi.
                </p>
              </div>
            </div>

            <div className="content-score-panel__criteria">
              {result.criteria.map((criterion) => (
                <div className="evaluation-criterion" key={criterion.name}>
                  <div>
                    <strong>{criterion.name}</strong>
                    <span>{criterion.score}</span>
                  </div>
                  <progress value={criterion.score} max="100" />
                  <p>{criterion.comment}</p>
                </div>
              ))}
            </div>

            <div className="content-score-panel__insights">
              <article className="is-strength">
                <h3><FiCheckCircle /> Điểm mạnh</h3>
                <ul>
                  {result.strengths.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>
              <article className="is-improvement">
                <h3><FiRefreshCw /> Cần cải thiện</h3>
                <ul>
                  {result.improvements.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </article>
            </div>

            <article className="content-score-panel__revision">
              <h3>Đề xuất chỉnh sửa</h3>
              <p>{result.suggested_revision}</p>
            </article>
          </div>
        ) : (
          <p className="content-score-panel__empty">
            Chưa nhận được kết quả đánh giá. Hãy đóng và thử lại.
          </p>
        )}

        <footer className="content-score-panel__footer">
          <button type="button" onClick={onClose} disabled={loading}>
            Đóng
          </button>
          {onCreateImproved && (
            <button
              type="button"
              className="is-primary"
              onClick={onCreateImproved}
              disabled={loading || !result}
            >
              <FiRefreshCw />
              Tạo bản cải thiện
            </button>
          )}
        </footer>
      </section>
    </div>,
    document.body,
  );
}

export default ContentScorePanel;
