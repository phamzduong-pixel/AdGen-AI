import { useEffect, useState } from "react";
import { FiArrowRight, FiLoader, FiZap } from "react-icons/fi";

import { getTemplates } from "../../../services/api/templateApi";
import "./TemplateQuickStart.css";

function TemplateQuickStart({ onSelect }) {
  const [templates, setTemplates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getTemplates({ popular_only: true })
      .then((data) => {
        if (active) {
          setTemplates(Array.isArray(data) ? data.slice(0, 6) : []);
        }
      })
      .catch(() => {
        if (active) setTemplates([]);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (isLoading) {
    return (
      <div className="template-quick-start__loading">
        <FiLoader />
        Đang tải gợi ý...
      </div>
    );
  }

  if (!templates.length) return null;

  return (
    <div className="template-quick-start">
      {templates.map((template) => (
        <button
          type="button"
          key={template.id}
          onClick={() => onSelect?.(template)}
        >
          <span className="template-quick-start__icon">
            <FiZap />
          </span>
          <span>
            <strong>{template.title}</strong>
            <small>{template.description}</small>
          </span>
          <FiArrowRight className="template-quick-start__arrow" />
        </button>
      ))}
    </div>
  );
}

export default TemplateQuickStart;
