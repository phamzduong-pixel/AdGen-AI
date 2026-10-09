import { useEffect, useRef, useState } from "react";

import { getGoogleClientId } from "../../../services/api/authApi";
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
    script.addEventListener("error", () => reject(new Error("Không thể tải Google Identity Services")), { once: true });
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
  if (!id || !GOOGLE_CLIENT_ID_PATTERN.test(id)) return false;
  return !id.includes("example") && !id.includes("your-client-id");
}

function GoogleLoginButton({ onCredential, disabled = false }) {
  const containerRef = useRef(null);
  const envClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim() || "";
  const envClientIdIsValid = isConfiguredGoogleClientId(envClientId);
  const [clientId, setClientId] = useState(() => (envClientIdIsValid ? envClientId : ""));
  const [configLoading, setConfigLoading] = useState(() => !envClientIdIsValid);
  const [configError, setConfigError] = useState("");
  const [scriptError, setScriptError] = useState("");

  useEffect(() => {
    credentialHandler = onCredential;
    return () => {
      if (credentialHandler === onCredential) credentialHandler = undefined;
    };
  }, [onCredential]);

  useEffect(() => {
    if (envClientIdIsValid) return undefined;
    let active = true;
    getGoogleClientId()
      .then((serverClientId) => {
        if (!active) return;
        if (isConfiguredGoogleClientId(serverClientId)) {
          setClientId(serverClientId);
          setConfigError("");
        } else {
          setConfigError("Google OAuth chưa được cấu hình trên máy chủ.");
        }
      })
      .catch(() => {
        if (active) setConfigError("Không thể kiểm tra cấu hình Google OAuth.");
      })
      .finally(() => {
        if (active) setConfigLoading(false);
      });
    return () => { active = false; };
  }, [envClientIdIsValid]);

  const hasValidClientId = isConfiguredGoogleClientId(clientId);
  useEffect(() => {
    if (!hasValidClientId || disabled) return undefined;
    let active = true;
    loadGoogleIdentityServices()
      .then(() => {
        if (!active || !containerRef.current) return;
        if (initializedClientId !== clientId) {
          try {
            window.google.accounts.id.initialize({
              client_id: clientId,
              callback: (response) => credentialHandler?.(response.credential),
              error_callback: (err) => {
                console.warn("Google GSI Origin/Client Error:", err);
                if (active) setScriptError("Domain hiện tại chưa được ủy quyền cho Google Client ID này.");
              },
              auto_select: false,
            });
            initializedClientId = clientId;
          } catch (initErr) {
            console.warn("Failed to initialize Google GSI:", initErr);
            if (active) setScriptError("Không thể khởi tạo Google Identity Services.");
            return;
          }
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
        if (active) setScriptError("Không tải được đăng nhập Google. Hãy kiểm tra kết nối mạng.");
      });
    return () => { active = false; };
  }, [clientId, disabled, hasValidClientId]);

  if (configLoading) {
    return <div className="google-login-unavailable google-login-loading-state" role="status">Đang tải đăng nhập Google...</div>;
  }

  if (!hasValidClientId || scriptError) {
    return (
      <button
        type="button"
        className="google-login-unavailable"
        disabled
        title={scriptError || configError || "Google OAuth chưa được cấu hình cho domain hiện tại"}
      >
        <span className="google-login__mark" aria-hidden="true">G</span>
        <span>Đăng nhập bằng Google</span>
        <small className="google-login__config-note">
          {scriptError ? "Chưa ủy quyền domain" : "Chưa cấu hình"}
        </small>
      </button>
    );
  }

  return (
    <div className={`google-login${disabled ? " google-login--disabled" : ""}`} aria-busy={disabled}>
      <div ref={containerRef} className="google-login__button" />
      {!window.google?.accounts?.id && <span className="google-login__loading">Đang tải Google...</span>}
    </div>
  );
}

export default GoogleLoginButton;