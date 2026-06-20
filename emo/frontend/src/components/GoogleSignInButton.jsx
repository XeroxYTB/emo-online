import React, { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const ENV_CLIENT_ID = (process.env.REACT_APP_GOOGLE_CLIENT_ID || "").trim();

let gisLoadPromise = null;

function loadGisScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gisLoadPromise) return gisLoadPromise;
  gisLoadPromise = new Promise((resolve, reject) => {
    const done = () => {
      if (window.google?.accounts?.id) resolve();
      else reject(new Error("Google Identity Services indisponible"));
    };
    const existing = document.querySelector(`script[src="${GIS_SRC}"]`);
    if (existing) {
      if (window.google?.accounts?.id) return resolve();
      existing.addEventListener("load", done, { once: true });
      existing.addEventListener("error", () => reject(new Error("Script Google bloqué")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = done;
    script.onerror = () => reject(new Error("Script Google bloqué"));
    document.head.appendChild(script);
  });
  return gisLoadPromise;
}

export function getGoogleClientId(override) {
  return (override || ENV_CLIENT_ID || "").trim();
}

export async function loadGoogleIdentity(clientId, onCredential) {
  const cid = getGoogleClientId(clientId);
  if (!cid) throw new Error("Google client_id manquant");
  await loadGisScript();
  window.google.accounts.id.initialize({
    client_id: cid,
    callback: (response) => {
      if (response?.credential) onCredential(response.credential);
    },
    auto_select: false,
    cancel_on_tap_outside: true,
    itp_support: true,
    ux_mode: "popup",
  });
  return cid;
}

export function GoogleSignInButton({ clientId, onCredential, disabled, busy }) {
  const hostRef = useRef(null);

  useEffect(() => {
    const cid = getGoogleClientId(clientId);
    if (!cid || !hostRef.current) return;

    let cancelled = false;
    const host = hostRef.current;

    (async () => {
      try {
        await loadGoogleIdentity(cid, (credential) => {
          if (!disabled && !busy) onCredential?.(credential);
        });
        if (cancelled || !host) return;

        host.innerHTML = "";
        const width = Math.max(280, Math.min(host.offsetWidth || 320, 400));
        window.google.accounts.id.renderButton(host, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width,
          locale: "fr",
        });
      } catch (_) {
        /* bouton masqué si GIS indisponible */
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientId, onCredential, disabled, busy]);

  const cid = getGoogleClientId(clientId);
  if (!cid) return null;

  return (
    <div className="google-btn-host relative w-full mb-4" style={{ minHeight: 44 }}>
      {busy && (
        <div
          className="absolute inset-0 z-20 flex items-center justify-center gap-2 rounded-lg text-sm font-medium"
          style={{ background: "rgba(255,255,255,0.92)", color: "#18181b" }}
        >
          <Loader2 size={16} className="animate-spin opacity-70" />
          Connexion…
        </div>
      )}
      <div
        ref={hostRef}
        data-testid="google-login-btn"
        className={`flex w-full justify-center overflow-hidden rounded-lg ${disabled || busy ? "pointer-events-none opacity-60" : ""}`}
      />
    </div>
  );
}

export default GoogleSignInButton;
