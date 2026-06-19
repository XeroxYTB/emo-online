import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, getApiBase, saveSessionToken, wakeBackend } from "../lib/api";
import { frontendUrl } from "../lib/paths";
import EmoEyes from "../components/EmoEyes";
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

function BootScreen({ message, showRetry, onRetry }) {
  return (
    <div className="login-page h-screen w-full flex flex-col items-center justify-center gap-5 px-6">
      <div className="login-orb login-orb-1" />
      <div className="login-orb login-orb-2" />
      <EmoEyes mode="normal" thinking size={88} />
      <div className="text-center z-10 space-y-3">
        <p className="text-sm text-secondary-em tracking-wide">{message}</p>
        <div className="login-boot-dots flex justify-center gap-1.5">
          <span /><span /><span />
        </div>
      </div>
      {showRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="login-submit z-10 px-8 py-3 rounded-2xl text-sm font-semibold transition-all hover:brightness-110"
        >
          Réessayer
        </button>
      )}
    </div>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [bootPhase, setBootPhase] = useState("connecting");
  const [bootMessage, setBootMessage] = useState("Préparation de ton espace…");
  const [googleReady, setGoogleReady] = useState(false);
  const [googleAuto, setGoogleAuto] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [desktop] = useState(isDesktopApp);
  const autoGoogleTried = useRef(false);
  const bootStarted = useRef(false);

  const runBoot = useCallback(async () => {
    setBootPhase("connecting");
    setBootMessage("Préparation de ton espace…");

    const warm = await wakeBackend({
      maxWaitMs: 90000,
      onProgress: ({ message }) => setBootMessage(message || "Connexion…"),
    });

    if (!warm.ok) {
      setBootPhase("offline");
      setBootMessage("Connexion au serveur en cours. Réessaie dans un instant.");
      return;
    }

    setGoogleReady(!!warm.google);

    try {
      await http.get("/auth/me");
      navigate("/chat", { replace: true });
      return;
    } catch (_) {
      // pas connecté — afficher login
    }

    if (!warm.google) {
      try {
        const r = await http.get("/auth/google/status");
        setGoogleReady(!!(r.data?.configured || r.data?.client_id));
      } catch (_) {
        setGoogleReady(false);
      }
    }

    setBootPhase("ready");
  }, [navigate]);

  useEffect(() => {
    if (bootStarted.current) return;
    bootStarted.current = true;
    runBoot();
  }, [runBoot]);

  const handleGoogleRedirect = useCallback(async () => {
    setGoogleBusy(true);
    const warm = await wakeBackend({
      maxWaitMs: 60000,
      onProgress: ({ message }) => setBootMessage(message || "Connexion…"),
    });
    if (!warm.ok) {
      setGoogleBusy(false);
      toast.error("Connexion momentanément indisponible. Réessaie dans quelques secondes.");
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
        google_auth_failed: "Connexion Google impossible. Réessaie.",
        access_denied: "Connexion annulée.",
        no_email: "Email Google non disponible.",
        missing_code: "Réponse Google invalide.",
        missing_token: "Session expirée — reconnecte-toi.",
        redirect_uri_mismatch: "Configuration OAuth incorrecte.",
        invalid_client: "Configuration Google incorrecte.",
        rate_limited: "Trop de tentatives — attends un moment.",
      };
      toast.error(msgs[err] || "Connexion impossible. Réessaie.");
    }
  }, [searchParams]);

  useEffect(() => {
    if (bootPhase !== "ready" || !googleReady || !desktop || searchParams.get("error")) return;
    if (autoGoogleTried.current) return;
    autoGoogleTried.current = true;
    setGoogleAuto(true);
    handleGoogleRedirect();
  }, [bootPhase, googleReady, desktop, searchParams, handleGoogleRedirect]);

  const handlePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (bootPhase === "offline") {
        const warm = await wakeBackend({ maxWaitMs: 45000 });
        if (!warm.ok) {
          toast.error("Serveur indisponible. Réessaie dans quelques secondes.");
          return;
        }
        setBootPhase("ready");
      }
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

  if (bootPhase === "connecting" || googleAuto) {
    return (
      <BootScreen
        message={googleAuto ? "Connexion Google…" : bootMessage}
        showRetry={false}
      />
    );
  }

  if (bootPhase === "offline") {
    return (
      <BootScreen
        message={bootMessage}
        showRetry
        onRetry={() => {
          bootStarted.current = false;
          runBoot();
        }}
      />
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

        {googleReady && (
          <>
            <button
              type="button"
              onClick={handleGoogleRedirect}
              data-testid="google-login-btn"
              disabled={loading || googleBusy}
              className="google-btn w-full flex items-center justify-center gap-3 py-3.5 rounded-2xl text-sm font-medium transition-all hover:brightness-105 mb-2 disabled:opacity-70"
            >
              {googleBusy ? (
                <>
                  <Loader2 size={18} className="animate-spin opacity-70" />
                  Connexion en cours…
                </>
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

            <div className="flex items-center my-5">
              <div className="flex-1 h-px bg-white/5" />
              <span className="px-3 text-[10px] tracking-[0.2em] uppercase text-muted-em">ou</span>
              <div className="flex-1 h-px bg-white/5" />
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
            disabled={loading || googleBusy}
            className="login-submit w-full py-3.5 rounded-2xl text-sm font-semibold transition-all disabled:opacity-50 hover:brightness-110 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Connexion…
              </>
            ) : (
              mode === "signup" ? "Créer mon compte" : "Se connecter"
            )}
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

        <p className="text-center text-[10px] text-muted-em/60 mt-5">
          Connexion chiffrée · Données privées
        </p>
      </div>
    </div>
  );
}
