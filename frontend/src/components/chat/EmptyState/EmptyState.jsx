import { FiZap } from "react-icons/fi";

import "./EmptyState.css";
import TemplateQuickStart from "../../templates/TemplateQuickStart/TemplateQuickStart";

function EmptyState({ onTemplateSelect }) {
  return (
    <div className="empty-state">
      <div className="empty-state__hero">
        <div className="empty-state__logo">
          <FiZap />
        </div>

        <span className="empty-state__eyebrow">AdGen AI</span>

        <h1 className="empty-state__title">
          Hôm nay bạn muốn tạo nội dung gì?
        </h1>

        <p className="empty-state__description">
          Chọn một gợi ý bên dưới hoặc nhập yêu cầu riêng để bắt đầu tạo nội
          dung quảng cáo bằng AI.
        </p>
      </div>

      <TemplateQuickStart onSelect={onTemplateSelect} />
    </div>
  );
}

export default EmptyState;
