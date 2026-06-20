import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, saveSessionToken, authRequest, formatApiError } from "../lib/api";
import { AppTopBar, EmoLogo } from "../components/EmoLogo";
import GoogleSignInButton, { getGoogleClientId, loadGoogleIdentity } from "../components/GoogleSignInButton";
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

const GOOGLE_ORIGINS = ["https://xeroxytb.com", "https://www.xeroxytb.com"];

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleClientId, setGoogleClientId] = useState(() => getGoogleClientId());
  const [googleBusy, setGoogleBusy] = useState(false);
  const [desktop] = useState(isDesktopApp);
  const autoGoogleTried = useRef(false);
  const bootStarted = useRef(false);

  const googleReady = !!googleClientId;
  const siteOrigin = typeof window !== "undefined" ? window.location.origin : "";

  const refreshGoogleStatus = useCallback(async () => {
    try {
      const r = await authRequest(() => http.get("/auth/google/status", { timeout: 15000 }), { maxAttempts: 3 });
      if (r.data?.client_id) setGoogleClientId(r.data.client_id);
      return !!r.data?.client_id;
    } catch (_) {}
    return !!getGoogleClientId();
  }, []);

  const verifyGoogleCredential = useCallback(async (credential) => {
    setGoogleBusy(true);
    try {
      const res = await authRequest(
        () => http.post("/auth/google/verify", { credential }, { timeout: 45000 }),
        { maxAttempts: 8 }
      );
      if (res.data?.session_token) saveSessionToken(res.data.session_token);
      navigate("/chat", { replace: true, state: { user: res.data } });
    } catch (err) {
      toast.error(formatApiError(err, "Connexion Google impossible."));
    } finally {
      setGoogleBusy(false);
    }
  }, [navigate]);

  useEffect(() => {
    if (bootStarted.current) return;
    bootStarted.current = true;

    (async () => {
      try {
        await authRequest(() => http.get("/auth/me", { timeout: 10000 }), { maxAttempts: 2 });
        navigate("/chat", { replace: true });
        return;
      } catch (_) {}

      refreshGoogleStatus();
    })();
  }, [navigate, refreshGoogleStatus]);

  useEffect(() => {
    const err = searchParams.get("error");
    if (!err) return;
    const msgs = {
      google_auth_failed: "Connexion Google impossible.",
      access_denied: "Connexion annulée.",
      no_email: "Email Google indisponible.",
      missing_code: "Réponse Google invalide.",
      missing_token: "Session expirée.",
      redirect_uri_mismatch: "Configuration OAuth incorrecte.",
      invalid_client: "Configuration Google incorrecte.",
      origin_mismatch: "Ajoutez xeroxytb.com dans Google Cloud Console (origines JavaScript).",
      rate_limited: "Trop de tentatives.",
    };
    toast.error(msgs[err] || "Connexion impossible.");
  }, [searchParams]);

  useEffect(() => {
    if (!googleReady || !desktop || searchParams.get("error")) return;
    if (autoGoogleTried.current) return;
    autoGoogleTried.current = true;

    (async () => {
      try {
        await loadGoogleIdentity(googleClientId, verifyGoogleCredential);
        window.google?.accounts?.id?.prompt?.();
      } catch (_) {}
    })();
  }, [googleReady, desktop, searchParams, googleClientId, verifyGoogleCredential]);

  const handlePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "signup") {
        const res = await authRequest(
          () => http.post("/auth/signup", { email, password, name }),
          { maxAttempts: 8 }
        );
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      } else {
        const res = await authRequest(
          () => http.post("/auth/login", { email, password }),
          { maxAttempts: 8 }
        );
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      }
      navigate("/chat", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err, "Identifiants incorrects"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />

      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div
          data-testid="login-card"
          className="login-card w-full max-w-sm rounded-xl p-8"
          style={{ background: "var(--emo-surface)", border: "1px solid var(--emo-border)", animation: "fadeIn 0.4s ease" }}
        >
          <div className="mb-6 flex flex-col items-center text-center">
            <EmoLogo size="md" layout="stacked" showSubtitle={false} className="mb-5" />
            <h1 className="font-heading text-xl font-semibold w-full text-left" style={{ color: "var(--emo-text)" }}>
              Connexion
            </h1>
          </div>

          {googleReady && (
            <>
              <div
                className="mb-3 rounded-lg px-3 py-2 text-xs leading-relaxed"
                style={{ background: "var(--emo-surface-raised)", color: "var(--emo-text-secondary)", border: "1px solid var(--emo-border)" }}
              >
                Google bloqué (origin_mismatch) ? Ajoute dans{" "}
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline"
                  style={{ color: "var(--emo-accent)" }}
                >
                  Google Cloud Console
                </a>
                {" "}→ Origines JS : {GOOGLE_ORIGINS.join(", ")}
                {siteOrigin && !GOOGLE_ORIGINS.includes(siteOrigin) ? ` (et ${siteOrigin})` : ""}
              </div>

              <GoogleSignInButton
                clientId={googleClientId}
                onCredential={verifyGoogleCredential}
                disabled={loading}
                busy={googleBusy}
              />

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
