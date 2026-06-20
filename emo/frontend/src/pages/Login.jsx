import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, getApiBase, saveSessionToken, wakeBackend } from "../lib/api";
import { frontendUrl } from "../lib/paths";
import { AppTopBar } from "../components/EmoLogo";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

const isDesktopApp = () => {
  if (window.__EMO_DESKTOP__ === true) return true;
  if (/EmoDesktop/i.test(navigator.userAgent || "")) return true;
  if (new URLSearchParams(window.location.search).get("desktop") === "1") {
    try { localStorage.setItem("emo_desktop", "1"); } catch (_) {}
    return true;
  }
  try { return localStorage.getItem("emo_desktop") === "1"; } catch (_) { return false; }
};

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const [googleAuto, setGoogleAuto] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [desktop] = useState(isDesktopApp);
  const autoGoogleTried = useRef(false);
  const bootStarted = useRef(false);

  const finishGoogleStatus = useCallback(async (warm) => {
    if (warm?.google) {
      setGoogleReady(true);
      return;
    }
    try {
      const r = await http.get("/auth/google/status", { timeout: 8000 });
      setGoogleReady(!!(r.data?.configured || r.data?.client_id));
    } catch (_) {
      setGoogleReady(false);
    }
  }, []);

  useEffect(() => {
    if (bootStarted.current) return;
    bootStarted.current = true;

    (async () => {
      const warmPromise = wakeBackend({ maxWaitMs: 20000 }).catch(() => ({ ok: false }));

      try {
        await http.get("/auth/me", { timeout: 8000 });
        navigate("/chat", { replace: true });
        return;
      } catch (_) {}

      const warm = await warmPromise;
      if (warm?.ok) await finishGoogleStatus(warm);
      else finishGoogleStatus({ ok: false });
    })();
  }, [navigate, finishGoogleStatus]);

  const handleGoogleRedirect = useCallback(async () => {
    setGoogleBusy(true);
    const warm = await wakeBackend({ maxWaitMs: 45000 });
    if (!warm.ok) {
      setGoogleBusy(false);
      toast.error("Service indisponible.");
      return;
    }
    if (warm.google) setGoogleReady(true);
    const redirectUrl = frontendUrl("/auth/google/callback");
    const desktopFlag = desktop ? "&desktop=1" : "";
    window.location.href = `${getApiBase()}/auth/google/login?redirect=${encodeURIComponent(redirectUrl)}${desktopFlag}`;
  }, [desktop]);

  useEffect(() => {
    const err = searchParams.get("error");
    if (err) {
      setGoogleAuto(false);
      const msgs = {
        google_auth_failed: "Connexion Google impossible.",
        access_denied: "Connexion annulée.",
        no_email: "Email Google indisponible.",
        missing_code: "Réponse Google invalide.",
        missing_token: "Session expirée.",
        redirect_uri_mismatch: "Configuration OAuth incorrecte.",
        invalid_client: "Configuration Google incorrecte.",
        rate_limited: "Trop de tentatives.",
      };
      toast.error(msgs[err] || "Connexion impossible.");
    }
  }, [searchParams]);

  useEffect(() => {
    if (!googleReady || !desktop || searchParams.get("error")) return;
    if (autoGoogleTried.current) return;
    autoGoogleTried.current = true;
    setGoogleAuto(true);
    handleGoogleRedirect();
  }, [googleReady, desktop, searchParams, handleGoogleRedirect]);

  const handlePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await wakeBackend({ maxWaitMs: 45000 });
      if (mode === "signup") {
        const res = await http.post("/auth/signup", { email, password, name });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      } else {
        const res = await http.post("/auth/login", { email, password });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      }
      navigate("/chat", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Identifiants incorrects");
    } finally {
      setLoading(false);
    }
  };

  if (googleAuto) {
    return (
      <div className="login-page h-screen w-full flex flex-col">
        <AppTopBar />
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
          <Loader2 size={24} className="animate-spin text-muted-em" />
          <p className="text-sm text-secondary-em">Connexion Google…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />

      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div
          data-testid="login-card"
          className="login-card w-full max-w-sm rounded-xl p-8"
          style={{ background: "var(--emo-surface)", border: "1px solid var(--emo-border)", animation: "fadeIn 0.4s ease" }}
        >
          <div className="mb-6">
            <h1 className="font-heading text-xl font-semibold" style={{ color: "var(--emo-text)" }}>
              Connexion
            </h1>
          </div>

          {googleReady && (
            <>
              <button
                type="button"
                onClick={handleGoogleRedirect}
                data-testid="google-login-btn"
                disabled={loading || googleBusy}
                className="google-btn w-full flex items-center justify-center gap-3 py-2.5 rounded-lg text-sm font-medium transition-colors mb-4 disabled:opacity-60"
              >
                {googleBusy ? (
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
                  </>
                )}
              </button>

              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px" style={{ background: "var(--emo-border)" }} />
                <span className="text-xs text-muted-em">ou</span>
                <div className="flex-1 h-px" style={{ background: "var(--emo-border)" }} />
              </div>
            </>
          )}

          <form onSubmit={handlePassword} className="space-y-3">
            {mode === "signup" && (
              <input
                data-testid="name-input"
                type="text"
                placeholder="Nom"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="login-input w-full px-3 py-2.5 rounded-lg text-sm"
              />
            )}
            <input
              data-testid="email-input"
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="login-input w-full px-3 py-2.5 rounded-lg text-sm"
            />
            <input
              data-testid="password-input"
              type="password"
              placeholder="Mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="login-input w-full px-3 py-2.5 rounded-lg text-sm"
            />
            <button
              data-testid="password-submit-btn"
              type="submit"
              disabled={loading || googleBusy}
              className="login-submit w-full py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Connexion…
                </>
              ) : (
                mode === "signup" ? "Créer un compte" : "Se connecter"
              )}
            </button>
          </form>

          <p className="text-center text-xs text-muted-em mt-5">
            {mode === "signup" ? "Compte existant" : "Créer un compte"}{" "}
            <button
              data-testid="toggle-mode-btn"
              type="button"
              onClick={() => setMode(mode === "signup" ? "login" : "signup")}
              className="underline hover:text-secondary-em transition"
              style={{ color: "var(--emo-text-secondary)" }}
            >
              {mode === "signup" ? "Se connecter" : "S'inscrire"}
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
