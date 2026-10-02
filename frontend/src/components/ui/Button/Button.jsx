import "./Button.css";

function Button({
  children,
  variant = "primary",
  size = "md",
  type = "button",
  disabled = false,
  loading = false,
  fullWidth = false,
  onClick,
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`btn btn-${variant} btn-${size} ${
        fullWidth ? "btn-full" : ""
      }`}
      onClick={onClick}
    >
      {loading ? "Loading..." : children}
    </button>
  );
}

export default Button;
