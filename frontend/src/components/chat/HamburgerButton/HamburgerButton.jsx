import { FiMenu } from "react-icons/fi";

import "./HamburgerButton.css";

function HamburgerButton({ onClick }) {
  return (
    <button
      type="button"
      className="hamburger-button"
      onClick={onClick}
      title="Mở menu"
      aria-label="Mở menu điều hướng"
    >
      <FiMenu />
    </button>
  );
}

export default HamburgerButton;
