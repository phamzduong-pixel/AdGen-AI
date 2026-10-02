import { useEffect, useRef, useState } from "react";

import "./GoogleLoginButton.css";

const GOOGLE_SCRIPT_ID = "google-identity-services";
const GOOGLE_CLIENT_ID_PATTERN =
  /^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$/;
let googleScriptPromise;
let credentialHandler;
let initializedClientId;

function loadGoogleIdentityServices() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (googleScriptPromise) return googleScriptPromise;

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID);
    const script = existingScript || document.createElement("script");

    script.addEventListener("load", resolve, { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("Không thể tải Google Identity Services")),
      { once: true },
    );

    if (!existingScript) {
      script.id = GOOGLE_SCRIPT_ID;
      script.src = "https://accounts.google.com/gsi/client?hl=vi";
      script.async = true;
      document.head.appendChild(script);
    }
  });

  return googleScriptPromise;
}

function isConfiguredGoogleClientId(id) {
  if (!id) return false;
  if (!GOOGLE_CLIENT_ID_PATTERN.test(id)) return false;
  if (id.includes("example") || id.includes("your-client-id")) return false;
  return true;
}

function GoogleLoginButton({ onCredential, disabled = false }) {
  const containerRef = useRef(null);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim();
  const hasValidClientId = isConfiguredGoogleClientId(clientId);
  const [scriptError, setScriptError] = useState("");

  useEffect(() => {
    credentialHandler = onCredential;
    if (!hasValidClientId || disabled) return undefined;

    let active = true;
    loadGoogleIdentityServices()
      .then(() => {
        if (!active || !containerRef.current) return;
        if (initializedClientId !== clientId) {
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: (response) => credentialHandler?.(response.credential),
            auto_select: false,
          });
          initializedClientId = clientId;
        }
        containerRef.current.replaceChildren();
        window.google.accounts.id.renderButton(containerRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          logo_alignment: "left",
          locale: "vi",
          width: Math.min(containerRef.current.clientWidth || 400, 400),
        });
      })
      .catch(() => {
        if (active) {
          setScriptError(
            "Không tải được đăng nhập Google. Hãy kiểm tra kết nối mạng.",
          );
        }
      });

    return () => {
      active = false;
      if (credentialHandler === onCredential) credentialHandler = undefined;
    };
  }, [clientId, disabled, hasValidClientId, onCredential]);

  if (!hasValidClientId) {
    return (
      <button
        type="button"
        className="google-login-unavailable"
        disabled
        title="Chưa cấu hình Google OAuth Client ID hợp lệ"
      >
        <span className="google-login__mark" aria-hidden="true">G</span>
        <span>Đăng nhập bằng Google</span>
        <small className="google-login__config-note">Chưa cấu hình</small>
      </button>
    );
  }

  if (scriptError) {
    return (
      <p className="google-login-error" role="alert">
        {scriptError}
      </p>
    );
  }

  return (
    <div
      className={`google-login${disabled ? " google-login--disabled" : ""}`}
      aria-busy={disabled}
    >
      <div ref={containerRef} className="google-login__button" />
      {!window.google?.accounts?.id && (
        <span className="google-login__loading">Đang tải Google...</span>
      )}
    </div>
  );
}

export default GoogleLoginButton;
