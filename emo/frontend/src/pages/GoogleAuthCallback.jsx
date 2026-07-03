import React, { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiPostJson, saveSessionToken } from "../lib/api";
import { AppTopBar } from "../components/EmoLogo";

export default function GoogleAuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const session = searchParams.get("session");
    if (session) {
      saveSessionToken(session);
      navigate("/chat", { replace: true });
      return;
    }

    const token = searchParams.get("token");
    if (!token) {
      navigate("/login?error=missing_token", { replace: true });
      return;
    }

    apiPostJson(`/auth/google/exchange?token=${encodeURIComponent(token)}`, {})
      .then((res) => {
        if (res.data?.session_token) saveSessionToken(res.data.session_token);
        navigate("/chat", { replace: true, state: { user: res.data } });
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail || "google_auth_failed";
        navigate(`/login?error=${encodeURIComponent(detail)}`, { replace: true });
      });
  }, [navigate, searchParams]);

  return (
    <div className="h-screen w-full flex flex-col" style={{ background: "var(--emo-bg)" }}>
      <AppTopBar />
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <div className="login-boot-dots flex justify-center gap-1.5">
          <span /><span /><span />
        </div>
        <p className="text-sm text-secondary-em">Connexion en cours…</p>
      </div>
    </div>
  );
}
