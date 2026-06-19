import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, API, saveSessionToken, wakeBackend } from "../lib/api";
import { frontendUrl } from "../lib/paths";
import EmoEyes from "../components/EmoEyes";
import { toast } from "sonner";

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
  const [checking, setChecking] = useState(true);
  const [googleReady, setGoogleReady] = useState(false);
  const [googleAuto, setGoogleAuto] = useState(false);
  const [googleWaking, setGoogleWaking] = useState(false);
  const [desktop] = useState(isDesktopApp);
  const autoGoogleTried = useRef(false);

  const handleGoogleRedirect = useCallback(async () => {
    setGoogleWaking(true);
    const warm = await wakeBackend(5);
    if (!warm.ok) {
      setGoogleWaking(false);
      toast.error("API Hugging Face surchargée (429). Attends 30 s et réessaie.");
      return;
    }
    const redirectUrl = frontendUrl("/auth/google/callback");
    const desktopFlag = desktop ? "&desktop=1" : "";
    window.location.href = `${API}/auth/google/login?redirect=${encodeURIComponent(redirectUrl)}${desktopFlag}`;
  }, [desktop]);

  useEffect(() => {
    const err = searchParams.get("error");
    if (err) {
      setGoogleAuto(false);
      const msgs = {
        google_auth_failed: "Connexion Google échouée. Vérifie la config OAuth.",
        access_denied: "Connexion Google annulée.",
        no_email: "Google n'a pas fourni d'email.",
        missing_code: "Réponse Google invalide.",
        missing_token: "Session expirée — réessaie.",
        redirect_uri_mismatch: "URI de redirection incorrecte dans Google Cloud Console.",
        invalid_client: "Identifiants Google invalides.",
        rate_limited: "API surchargée — réessaie dans 30 secondes.",
      };
      toast.error(msgs[err] || `Erreur Google (${err})`);
    }
  }, [searchParams]);

  useEffect(() => {
    wakeBackend(2).catch(() => {});
    http.get("/auth/me")
      .then(() => navigate("/chat", { replace: true }))
      .catch(() => setChecking(false));
    http.get("/auth/google/status")
      .then((r) => {
        setGoogleReady(!!(r.data?.configured || r.data?.client_id));
      })
      .catch(() => {
        setGoogleReady(false);
      });
  }, [navigate]);

  // App bureau : connexion Google automatique (redirect OAuth, compatible WebView2)
  useEffect(() => {
    if (checking || !googleReady || !desktop || searchParams.get("error")) return;
    if (autoGoogleTried.current) return;
    autoGoogleTried.current = true;
    setGoogleAuto(true);
    handleGoogleRedirect();
  }, [checking, googleReady, desktop, searchParams, handleGoogleRedirect]);

  // Toujours OAuth redirect (evite erreur GSI "origin not allowed" en local)
  // Le bouton GIS Google est desactive — redirect via backend fonctionne partout.

  const handlePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "signup") {
        const res = await http.post("/auth/signup", { email, password, name });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      } else {
        const res = await http.post("/auth/login", { email, password });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
      }
      navigate("/chat", { replace: true });
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur d'authentification");
    } finally {
      setLoading(false);
    }
  };

  if (checking || googleAuto) {
    return (
      <div className="login-page h-screen w-full flex flex-col items-center justify-center gap-4">
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <EmoEyes mode="normal" thinking size={80} />
        <p className="text-sm text-secondary-em tracking-wide">
          {googleAuto ? "Connexion Google automatique..." : "Chargement..."}
        </p>
      </div>
    );
  }

  return (
    <div className="login-page h-screen w-full flex items-center justify-center px-4 mode-normal relative overflow-hidden">
      <div className="login-orb login-orb-1" />
      <div className="login-orb login-orb-2" />
      <div className="login-orb login-orb-3" />
      <div
        data-testid="login-card"
        className="login-card w-full max-w-md glass-panel rounded-3xl p-8 relative z-10"
        style={{ animation: "fadeIn 0.6s ease" }}
      >
        <div className="flex flex-col items-center mb-8">
          <div className="mb-2">
            <EmoEyes mode="normal" mood="curieuse" size={96} />
          </div>
          <h1 className="font-heading text-4xl mt-2 font-semibold tracking-tight">
            <span style={{ color: "var(--emo-text)" }}>Ém</span>
            <span style={{ color: "var(--mode-color)", textShadow: "0 0 20px var(--mode-glow)" }}>o</span>
            <span className="text-lg font-normal text-muted-em ml-2">Online</span>
          </h1>
          <p className="text-sm text-secondary-em mt-2 text-center max-w-xs leading-relaxed">
            Ton assistant IA. Code, création et projets — sur le cloud ou ton PC.
          </p>
        </div>

        <button
          type="button"
          onClick={handleGoogleRedirect}
          data-testid="google-login-btn"
          disabled={loading || googleWaking}
          className="google-btn w-full flex items-center justify-center gap-3 py-3.5 rounded-2xl text-sm font-medium transition-all hover:brightness-105 mb-2 disabled:opacity-60"
        >
          {googleWaking ? (
            <>Réveil du serveur…</>
          ) : (
          <>
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.56 2.95-2.24 5.45-4.78 7.12l7.73 6.01C43.44 37.74 46.98 31.64 46.98 24.55z" />
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6.01c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
          </svg>
          Continuer avec Google
          </>
          )}
        </button>

        {!googleReady && (
          <p className="text-[11px] text-center text-muted-em mb-1 -mt-1">
            Connexion Google indisponible — l&apos;API backend est hors ligne.
          </p>
        )}

        <div className="flex items-center my-5">
          <div className="flex-1 h-px bg-white/5" />
          <span className="px-3 text-[10px] tracking-[0.2em] uppercase text-muted-em">ou</span>
          <div className="flex-1 h-px bg-white/5" />
        </div>

        <form onSubmit={handlePassword} className="space-y-3">
          {mode === "signup" && (
            <input
              data-testid="name-input"
              type="text"
              placeholder="Nom"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="login-input w-full px-4 py-3 rounded-xl text-sm focus:outline-none transition placeholder:text-muted-em"
            />
          )}
          <input
            data-testid="email-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="login-input w-full px-4 py-3 rounded-xl text-sm focus:outline-none transition placeholder:text-muted-em"
          />
          <input
            data-testid="password-input"
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="login-input w-full px-4 py-3 rounded-xl text-sm focus:outline-none transition placeholder:text-muted-em"
          />
          <button
            data-testid="password-submit-btn"
            type="submit"
            disabled={loading}
            className="login-submit w-full py-3.5 rounded-2xl text-sm font-semibold transition-all disabled:opacity-50 hover:brightness-110"
          >
            {loading ? "..." : mode === "signup" ? "Créer mon compte" : "Se connecter"}
          </button>
        </form>

        <p className="text-center text-xs text-muted-em mt-4">
          {mode === "signup" ? "Déjà un compte ?" : "Pas encore inscrit ?"}{" "}
          <button
            data-testid="toggle-mode-btn"
            type="button"
            onClick={() => setMode(mode === "signup" ? "login" : "signup")}
            className="underline hover:text-white transition"
          >
            {mode === "signup" ? "Connecte-toi" : "Crée un compte"}
          </button>
        </p>
      </div>
    </div>
  );
}
