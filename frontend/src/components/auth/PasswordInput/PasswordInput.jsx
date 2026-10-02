import { useState } from "react";
import { FiEye, FiEyeOff, FiLock } from "react-icons/fi";

import "./PasswordInput.css";

function PasswordInput({
  id,
  name,
  value,
  onChange,
  placeholder,
  autoComplete,
  disabled = false,
  error,
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div
      className={`password-input${error ? " password-input--error" : ""}`}
    >
      <FiLock className="password-input__leading" aria-hidden="true" />
      <input
        id={id}
        name={name}
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        disabled={disabled}
        maxLength={128}
        aria-invalid={Boolean(error)}
        aria-describedby={`${id}-error`}
      />
      <button
        type="button"
        className="password-input__toggle"
        onClick={() => setVisible((current) => !current)}
        onMouseDown={(event) => event.preventDefault()}
        disabled={disabled}
        aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
        title={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
      >
        {visible ? <FiEyeOff /> : <FiEye />}
      </button>
    </div>
  );
}

export default PasswordInput;
