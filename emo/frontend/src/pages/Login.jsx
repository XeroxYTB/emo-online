import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, saveSessionToken, clearSessionToken, authRequest, formatApiError, wakeBackend, getSessionToken, isApiReachable, apiPostJson } from "../lib/api";
import { AppTopBar, EmoLogo } from "../components/EmoLogo";
import GoogleSignInButton, { getGoogleClientId } from "../components/GoogleSignInButton";
import { toast } from "sonner";
import { Loader2, Sparkles } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const [apiDown, setApiDown] = useState(false);
  const [apiWaking, setApiWaking] = useState(false);
  const bootStarted = useRef(false);

  const retryApiConnection = useCallback(async () => {
    setApiWaking(true);
    const warm = await wakeBackend({ maxWaitMs: 35000 }).catch(() => ({ ok: false }));
    setApiWaking(false);
    setApiDown(!warm?.ok);
    if (warm?.ok) {
      toast.success(warm.waking ? "Serveur HF occupé — vous pouvez vous connecter." : "API connectée.");
    } else {
      toast.error("API toujours injoignable. Réessayez dans 1–2 min.");
    }
    return warm;
  }, []);

  const ensureApiReady = useCallback(async () => {
    if (isApiReachable()) return { ok: true };
    return wakeBackend({ maxWaitMs: 15000 }).catch(() => ({ ok: false }));
  }, []);

  const verifyGoogleCredential = useCallback(async (credential) => {
    setGoogleBusy(true);
    try {
      const warm = await ensureApiReady();
      if (!warm?.ok) {
        setApiDown(true);
        toast.error("API injoignable. Le serveur HF démarre — réessayez dans 1–2 min.");
        return;
      }
      const res = await authRequest(
        () => apiPostJson("/auth/google/verify", { credential }, { timeout: 20000 }),
        { maxAttempts: 3 }
      );
      if (res.data?.session_token) saveSessionToken(res.data.session_token);
      navigate("/chat", { replace: true, state: { user: res.data } });
    } catch (err) {
      if (!err?.response) setApiDown(true);
      toast.error(formatApiError(err, "Connexion Google impossible."));
    } finally {
      setGoogleBusy(false);
    }
  }, [navigate, ensureApiReady]);

  useEffect(() => {
    if (bootStarted.current) return;
    bootStarted.current = true;

    const ctrl = new AbortController();
    (async () => {
      if (!getSessionToken()) {
        const warm = await wakeBackend({ maxWaitMs: 20000 }).catch(() => ({ ok: false }));
        setApiDown(!warm?.ok);
        setApiWaking(!!warm?.waking);
        return;
      }
      try {
        await http.get("/auth/me", {
          timeout: 12000,
          signal: ctrl.signal,
          _emoSkipRetry: true,
          _emoMaxRetries: 0,
        });
        navigate("/chat", { replace: true });
      } catch (_) {
        if (ctrl.signal.aborted) return;
        clearSessionToken();
        const warm = await wakeBackend({ maxWaitMs: 20000 }).catch(() => ({ ok: false }));
        setApiDown(!warm?.ok);
        setApiWaking(!!warm?.waking);
      }
    })();
    return () => ctrl.abort();
  }, [navigate]);

  useEffect(() => {
    const err = searchParams.get("error");
    if (!err) return;
    const msgs = {
      google_auth_failed: "Connexion Google impossible.",
      access_denied: "Connexion annulée.",
      origin_mismatch: "Ajoutez xeroxytb.com dans Google Cloud (origines JS).",
      redirect_uri_mismatch: "URI de redirection Google incorrecte.",
    };
    toast.error(msgs[err] || "Connexion impossible.");
  }, [searchParams]);

  const handlePassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const warm = await ensureApiReady();
      if (!warm?.ok) {
        setApiDown(true);
        toast.error("API injoignable. Le serveur HF démarre — réessayez dans 1–2 min.");
        return;
      }
      let sessionUser;
      if (mode === "signup") {
        const res = await apiPostJson("/auth/signup", { email, password, name });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
        sessionUser = res.data;
      } else {
        const res = await apiPostJson("/auth/login", { email, password });
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
        sessionUser = res.data;
      }
      setApiDown(false);
      navigate("/chat", { replace: true, state: { user: sessionUser } });
    } catch (err) {
      if (!err?.response) setApiDown(true);
      toast.error(formatApiError(err, "Identifiants incorrects"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />

      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-[420px]">
          {/* Hero */}
          <div className="text-center mb-8">
            <EmoLogo size="lg" layout="stacked" showSubtitle className="mb-6" />
            <p className="text-sm text-secondary-em max-w-xs mx-auto">
              Assistant IA avec agent local, navigation web et création de fichiers.
            </p>
          </div>

          {/* Card */}
          <div
            data-testid="login-card"
            className="login-card p-7"
            style={{ animation: "fadeIn 0.4s ease" }}
          >
            <div className="flex items-center gap-2 mb-6">
              <Sparkles size={16} style={{ color: "var(--emo-accent)" }} />
              <h1 className="font-heading text-lg font-semibold" style={{ color: "var(--emo-text)" }}>
                {mode === "signup" ? "Créer un compte" : "Se connecter"}
              </h1>
            </div>

            {apiDown && (
              <div className="mb-4 text-xs rounded-xl px-3 py-2.5 emo-alert-warning space-y-2">
                <p>
                  {apiWaking
                    ? "Serveur HF occupé (limite de requêtes). Connexion possible — réessayez."
                    : "Serveur HF en démarrage ou injoignable. Attendez 1–3 min puis réessayez."}
                </p>
                <button
                  type="button"
                  onClick={retryApiConnection}
                  disabled={apiWaking}
                  className="text-xs font-medium underline"
                  style={{ color: "var(--emo-accent)" }}
                >
                  {apiWaking ? "Connexion…" : "Réessayer la connexion API"}
                </button>
              </div>
            )}

            <GoogleSignInButton
              clientId={getGoogleClientId()}
              onCredential={verifyGoogleCredential}
              disabled={loading}
              busy={googleBusy}
              onBusyChange={setGoogleBusy}
            />

            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px" style={{ background: "var(--emo-border)" }} />
              <span className="text-xs text-muted-em font-medium">ou</span>
              <div className="flex-1 h-px" style={{ background: "var(--emo-border)" }} />
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
                  className="login-input w-full px-3.5 py-2.5 text-sm"
                />
              )}
              <input
                data-testid="email-input"
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="login-input w-full px-3.5 py-2.5 text-sm"
              />
              <input
                data-testid="password-input"
                type="password"
                placeholder="Mot de passe"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="login-input w-full px-3.5 py-2.5 text-sm"
              />
              <button
                data-testid="password-submit-btn"
                type="submit"
                disabled={loading || googleBusy}
                className="login-submit w-full py-2.5 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2 mt-1"
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

            <p className="text-center text-xs text-muted-em mt-6">
              {mode === "signup" ? "Déjà un compte ?" : "Pas encore de compte ?"}{" "}
              <button
                data-testid="toggle-mode-btn"
                type="button"
                onClick={() => setMode(mode === "signup" ? "login" : "signup")}
                className="font-medium underline-offset-2 hover:underline transition"
                style={{ color: "var(--emo-accent)" }}
              >
                {mode === "signup" ? "Se connecter" : "S'inscrire"}
              </button>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
