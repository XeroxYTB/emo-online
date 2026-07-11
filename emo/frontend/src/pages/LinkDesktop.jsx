import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, getSessionToken, formatApiError } from "../lib/api";
import { AppTopBar, EmoLogo } from "../components/EmoLogo";
import { toast } from "sonner";
import { CheckCircle2, Link2, Loader2, Monitor, XCircle } from "lucide-react";

export default function LinkDesktop() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const code = (searchParams.get("code") || "").trim().toUpperCase();
  const port = searchParams.get("port") || "8000";

  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [phase, setPhase] = useState("confirm"); // confirm | linking | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const returnPath = `/link-desktop?code=${encodeURIComponent(code)}&port=${encodeURIComponent(port)}`;

  useEffect(() => {
    if (!code) {
      navigate("/chat", { replace: true });
      return;
    }
    const token = getSessionToken();
    if (!token) {
      navigate(`/login?returnTo=${encodeURIComponent(returnPath)}`, { replace: true });
      return;
    }
    (async () => {
      try {
        const res = await http.get("/auth/me");
        setUser(res.data);
        setPhase("confirm");
      } catch (_) {
        navigate(`/login?returnTo=${encodeURIComponent(returnPath)}`, { replace: true });
      } finally {
        setLoading(false);
      }
    })();
  }, [code, port, navigate, returnPath]);

  const acceptLink = useCallback(async () => {
    if (!code) return;
    setPhase("linking");
    setErrorMsg("");
    try {
      await http.post("/desktop/pair/claim", { code });
      // Fast-path même machine : tokens directs au dashboard local (optionnel)
      const session = getSessionToken();
      try {
        const agentRes = await http.get("/agent/token");
        const agentToken = agentRes.data?.agent_token || "";
        await fetch(`http://127.0.0.1:${port}/pair`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code,
            session_token: session,
            agent_token: agentToken,
            email: user?.email || "",
          }),
          signal: AbortSignal.timeout(2000),
        });
      } catch (_) {
        /* desktop poll cloud — OK */
      }
      setPhase("success");
      toast.success("Émo Desktop lié à votre compte");
    } catch (err) {
      setPhase("error");
      setErrorMsg(formatApiError(err, "Impossible de lier le desktop"));
      toast.error(formatApiError(err, "Liaison impossible"));
    }
  }, [code, port, user?.email]);

  if (loading) {
    return (
      <div className="login-page h-screen w-full flex flex-col items-center justify-center">
        <Loader2 className="animate-spin text-muted-em" size={28} />
      </div>
    );
  }

  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />
      <main className="flex-1 flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-[440px]">
          <div className="text-center mb-8">
            <EmoLogo size="lg" layout="stacked" showSubtitle className="mb-6" />
          </div>

          <div className="login-card p-7 space-y-5" data-testid="link-desktop-card">
            <div className="flex items-center gap-2">
              <Monitor size={18} style={{ color: "var(--emo-accent)" }} />
              <h1 className="font-heading text-lg font-semibold" style={{ color: "var(--emo-text)" }}>
                Lier Émo Desktop
              </h1>
            </div>

            {phase === "confirm" && (
              <>
                <p className="text-sm text-secondary-em leading-relaxed">
                  L&apos;application <strong>Émo Desktop</strong> sur votre PC demande à se connecter à votre compte
                  Emo Online.
                </p>
                <div
                  className="rounded-xl px-4 py-3 text-sm space-y-1"
                  style={{ background: "var(--emo-surface-raised)", border: "1px solid var(--emo-border)" }}
                >
                  <p style={{ color: "var(--emo-text)" }}>
                    <strong>{user?.name || user?.email || "Compte connecté"}</strong>
                  </p>
                  {user?.email && (
                    <p className="text-xs text-muted-em">{user.email}</p>
                  )}
                  <p className="text-xs text-muted-em pt-1">
                    Code appareil : <code className="font-code tracking-widest">{code}</code>
                  </p>
                </div>
                <p className="text-[11px] text-muted-em">
                  En acceptant, le desktop pourra envoyer des messages, synchroniser vos conversations et utiliser
                  l&apos;agent local.
                </p>
                <div className="flex gap-3 pt-1">
                  <button
                    type="button"
                    data-testid="link-desktop-cancel"
                    onClick={() => navigate("/chat", { replace: true })}
                    className="flex-1 py-2.5 rounded-xl text-sm border transition"
                    style={{ borderColor: "var(--emo-border)", color: "var(--emo-text)" }}
                  >
                    Annuler
                  </button>
                  <button
                    type="button"
                    data-testid="link-desktop-accept"
                    onClick={acceptLink}
                    className="flex-1 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2"
                    style={{
                      background: "var(--mode-color)",
                      color: "var(--emo-on-mode)",
                      boxShadow: "0 0 20px var(--mode-glow)",
                    }}
                  >
                    <Link2 size={15} /> Accepter
                  </button>
                </div>
              </>
            )}

            {phase === "linking" && (
              <div className="flex flex-col items-center gap-3 py-6 text-secondary-em">
                <Loader2 size={32} className="animate-spin" style={{ color: "var(--emo-accent)" }} />
                <p className="text-sm">Liaison en cours…</p>
              </div>
            )}

            {phase === "success" && (
              <div className="flex flex-col items-center gap-4 py-4 text-center">
                <CheckCircle2 size={40} style={{ color: "var(--emo-status-online)" }} />
                <div>
                  <p className="font-medium" style={{ color: "var(--emo-text)" }}>
                    Desktop connecté
                  </p>
                  <p className="text-sm text-secondary-em mt-2">
                    Retournez sur <strong>Émo Desktop</strong> — la synchronisation démarre automatiquement.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => navigate("/chat", { replace: true })}
                  className="w-full py-2.5 rounded-xl text-sm font-medium"
                  style={{ background: "var(--emo-surface-raised)", border: "1px solid var(--emo-border)" }}
                >
                  Ouvrir le chat
                </button>
              </div>
            )}

            {phase === "error" && (
              <div className="flex flex-col items-center gap-4 py-4 text-center">
                <XCircle size={40} style={{ color: "var(--emo-error-text)" }} />
                <p className="text-sm text-secondary-em">{errorMsg}</p>
                <button
                  type="button"
                  onClick={() => setPhase("confirm")}
                  className="w-full py-2.5 rounded-xl text-sm"
                  style={{ border: "1px solid var(--emo-border)" }}
                >
                  Réessayer
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
