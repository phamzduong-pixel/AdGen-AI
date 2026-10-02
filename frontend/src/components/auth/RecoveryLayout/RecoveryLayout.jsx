import { FiArrowLeft, FiShield } from "react-icons/fi";
import { Link } from "react-router-dom";

import "./RecoveryLayout.css";

function RecoveryLayout({
  title,
  description,
  children,
  backTo = "/login",
  backLabel = "Quay lại đăng nhập",
}) {
  return (
    <main className="recovery-page">
      <Link to="/" className="recovery-brand">
        <span className="recovery-brand__logo">DG</span>
        <span>AdGen AI</span>
      </Link>
      <section className="recovery-card">
        <div className="recovery-card__icon" aria-hidden="true">
          <FiShield />
        </div>
        <header className="recovery-card__header">
          <h1>{title}</h1>
          <p>{description}</p>
        </header>
        {children}
        <Link to={backTo} className="recovery-back-link">
          <FiArrowLeft aria-hidden="true" />
          <span>{backLabel}</span>
        </Link>
      </section>
    </main>
  );
}

export default RecoveryLayout;
