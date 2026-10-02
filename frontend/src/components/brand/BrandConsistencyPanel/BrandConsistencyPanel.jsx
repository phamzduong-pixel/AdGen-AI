import { FiAlertCircle, FiCheckCircle } from "react-icons/fi";
import Modal from "../../ui/Modal/Modal";
import "./BrandConsistencyPanel.css";

function BrandConsistencyPanel({ open, brandName, result, loading, onClose }) {
  return (
    <Modal
      open={open}
      title={`Kiểm tra thương hiệu${brandName ? ` · ${brandName}` : ""}`}
      onClose={onClose}
      closeDisabled={loading}
    >
      {loading ? (
        <div className="brand-check__loading">AI đang đối chiếu quy chuẩn...</div>
      ) : result ? (
        <div className="brand-check">
          <div className={`brand-check__score ${result.is_consistent ? "is-good" : ""}`}>
            {result.is_consistent ? <FiCheckCircle /> : <FiAlertCircle />}
            <strong>{result.score}/100</strong>
            <span>{result.is_consistent ? "Nhất quán" : "Cần điều chỉnh"}</span>
          </div>
          <section>
            <h3>Điểm cần lưu ý</h3>
            {result.issues?.length ? (
              <ul>{result.issues.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : <p>Không phát hiện vấn đề đáng kể.</p>}
          </section>
          <section>
            <h3>Đề xuất</h3>
            {result.suggestions?.length ? (
              <ul>{result.suggestions.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : <p>Nội dung đã phù hợp với hồ sơ.</p>}
          </section>
          {result.matched_guidelines?.length > 0 && (
            <section>
              <h3>Quy chuẩn đã đáp ứng</h3>
              <ul>{result.matched_guidelines.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
          )}
          <small>{result.disclaimer}</small>
        </div>
      ) : null}
    </Modal>
  );
}

export default BrandConsistencyPanel;
