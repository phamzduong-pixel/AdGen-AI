import { useRef } from "react";

import { sanitizeOtp } from "../../../utils/passwordReset";

import "./OtpInput.css";

function OtpInput({
  value,
  onChange,
  disabled = false,
  error = false,
  idPrefix = "otp-code",
}) {
  const inputRefs = useRef([]);
  const digits = Array.from({ length: 6 }, (_, index) => value[index] || "");

  const setDigit = (index, rawValue) => {
    const digit = sanitizeOtp(rawValue).slice(-1);
    const next = [...digits];
    next[index] = digit;
    onChange(next.join(""));
    if (digit && index < 5) inputRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index, event) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (event.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (event.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (event) => {
    const pasted = sanitizeOtp(event.clipboardData.getData("text"));
    if (!pasted) return;
    event.preventDefault();
    onChange(pasted);
    inputRefs.current[Math.min(pasted.length, 6) - 1]?.focus();
  };

  return (
    <div
      className={`otp-input${error ? " otp-input--error" : ""}`}
      onPaste={handlePaste}
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(element) => {
            inputRefs.current[index] = element;
          }}
          id={`${idPrefix}-${index}`}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          maxLength={1}
          value={digit}
          onChange={(event) => setDigit(index, event.target.value)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          disabled={disabled}
          aria-label={`Chữ số ${index + 1} của mã xác minh`}
          aria-invalid={error}
          autoFocus={index === 0}
        />
      ))}
    </div>
  );
}

export default OtpInput;
