import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, API, saveSessionToken } from "../lib/api";
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
  const [desktop] = useState(isDesktopApp);
  const autoGoogleTried = useRef(false);

  const handleGoogleRedirect = useCallback(() => {
    const origin = window.location.origin.replace("localhost", "127.0.0.1");
    const redirectUrl = `${origin}/auth/google/callback`;
    const desktopFlag = desktop ? "&desktop=1" : "";
    window.location.href = `${API}/auth/google/login?redirect=${encodeURIComponent(redirectUrl)}${desktopFlag}`;
  }, [desktop]);

  useEffect(() => {
    const err = searchParams.get("error");
    if (err) {
      setGoogleAuto(false);
      const msgs = {
        google_auth_failed: "Connexion Google echouee. Verifie les identifiants dans backend/.env",
        access_denied: "Connexion Google annulee",
        no_email: "Google n'a pas fourni d'email",
        missing_code: "Reponse Google invalide",
        missing_token: "Session Google expiree - reessaie",
        redirect_uri_mismatch: "URI redirect incorrecte dans Google Cloud Console",
        invalid_client: "GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET incorrect",
      };
      toast.error(msgs[err] || `Erreur Google (${err})`);
    }
  }, [searchParams]);

  useEffect(() => {
    http.get("/auth/me")
      .then(() => navigate("/chat", { replace: true }))
      .catch(() => setChecking(false));
    http.get("/auth/google/status")
      .then((r) => {
        setGoogleReady(!!(r.data?.configured || r.data?.client_id));
      })
      .catch(() => {
        setGoogleReady(false);
        toast.error("Backend inaccessible. Relance Emo Online.bat et attends la fin du chargement.");
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
          <div className="login-eyes-ring mb-2">
            <EmoEyes mode="normal" mood="curieuse" size={96} />
          </div>
          <h1 className="font-heading text-4xl mt-2 font-semibold tracking-tight">
            <span style={{ color: "var(--emo-text)" }}>Ém</span>
            <span style={{ color: "var(--mode-color)", textShadow: "0 0 20px var(--mode-glow)" }}>o</span>
            <span className="text-lg font-normal text-muted-em ml-2">Online</span>
          </h1>
          <p className="text-sm text-secondary-em mt-2 text-center max-w-xs leading-relaxed">
            Ton IA locale. Code, création, projets massifs — pilotés sur ton PC.
          </p>
        </div>

        {!desktop && googleReady && (
          <button
            type="button"
            onClick={handleGoogleRedirect}
            data-testid="google-login-btn"
            className="login-submit w-full py-3.5 rounded-2xl text-sm font-semibold transition-all hover:brightness-110 mb-2"
          >
            Continuer avec Google
          </button>
        )}

        {desktop && googleReady && (
          <button
            type="button"
            onClick={handleGoogleRedirect}
            className="login-submit w-full py-3.5 rounded-2xl text-sm font-semibold transition-all hover:brightness-110 mb-2"
          >
            Continuer avec Google
          </button>
        )}

        {!googleReady && (
          <button
            type="button"
            disabled
            className="w-full flex items-center justify-center gap-3 py-3 rounded-2xl glass-card text-sm font-medium opacity-40"
          >
            Google non configure
          </button>
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
