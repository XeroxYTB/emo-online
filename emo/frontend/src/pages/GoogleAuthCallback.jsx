import React, { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { http, saveSessionToken } from "../lib/api";
import EmoEyes from "../components/EmoEyes";

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

    http
      .post("/auth/google/exchange", null, { params: { token } })
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
    <div className="h-screen w-full flex flex-col items-center justify-center gap-4">
      <EmoEyes mode="normal" thinking size={100} />
      <p className="text-sm text-secondary-em">Connexion Google en cours...</p>
    </div>
  );
}
