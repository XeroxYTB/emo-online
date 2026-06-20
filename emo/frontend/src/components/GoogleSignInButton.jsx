import React, { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getApiBase } from "../lib/api";
import { frontendUrl } from "../lib/paths";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const ENV_CLIENT_ID = (process.env.REACT_APP_GOOGLE_CLIENT_ID || "").trim();
/** Client OAuth public — fallback si le build n'a pas REACT_APP_GOOGLE_CLIENT_ID */
export const PROD_GOOGLE_CLIENT_ID =
  "791552572109-va37rj7pooi3opca3bqe61h15ka8gob9.apps.googleusercontent.com";

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
  return (override || ENV_CLIENT_ID || PROD_GOOGLE_CLIENT_ID).trim();
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

async function triggerGooglePopup(clientId, onCredential) {
  const cid = await loadGoogleIdentity(clientId, onCredential);
  const temp = document.createElement("div");
  temp.style.cssText = "position:fixed;left:-9999px;top:0;width:320px;height:48px;opacity:0.01;";
  document.body.appendChild(temp);
  try {
    window.google.accounts.id.renderButton(temp, {
      type: "standard",
      theme: "outline",
      size: "large",
      text: "continue_with",
      width: 320,
      locale: "fr",
    });
    await new Promise((r) => setTimeout(r, 400));
    const btn = temp.querySelector('[role="button"]') || temp.querySelector("div[tabindex]");
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  } finally {
    setTimeout(() => temp.remove(), 8000);
  }
}

export function GoogleSignInButton({ clientId, onCredential, disabled, busy, onBusyChange }) {
  const cid = getGoogleClientId(clientId);
  const [gisReady, setGisReady] = useState(false);

  useEffect(() => {
    if (!cid) return;
    loadGoogleIdentity(cid, onCredential)
      .then(() => setGisReady(true))
      .catch(() => setGisReady(false));
  }, [cid, onCredential]);

  const handleClick = useCallback(async () => {
    if (disabled || busy || !cid) return;
    onBusyChange?.(true);
    try {
      const opened = await triggerGooglePopup(cid, onCredential);
      if (!opened) throw new Error("popup");
    } catch (_) {
      const redirectUrl = frontendUrl("/auth/google/callback");
      window.location.assign(
        `${getApiBase()}/auth/google/login?redirect=${encodeURIComponent(redirectUrl)}`
      );
    } finally {
      onBusyChange?.(false);
    }
  }, [cid, disabled, busy, onCredential, onBusyChange]);

  if (!cid) return null;

  return (
    <button
      type="button"
      data-testid="google-login-btn"
      onClick={handleClick}
      disabled={disabled || busy}
      className="google-btn w-full flex items-center justify-center gap-3 py-2.5 rounded-lg text-sm font-medium transition-colors mb-4 disabled:opacity-60"
    >
      {busy ? (
        <>
          <Loader2 size={16} className="animate-spin opacity-70" />
          Connexion…
        </>
      ) : (
        <>
          <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.56 2.95-2.24 5.45-4.78 7.12l7.73 6.01C43.44 37.74 46.98 31.64 46.98 24.55z" />
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6.01c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
          </svg>
          Continuer avec Google
          {!gisReady && <span className="sr-only"> (chargement)</span>}
        </>
      )}
    </button>
  );
}

export default GoogleSignInButton;
