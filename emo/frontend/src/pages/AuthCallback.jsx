import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { http } from "../lib/api";
import { AppTopBar } from "../components/EmoLogo";

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const sessionId = params.get("session_id");

    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    http
      .post("/auth/google/session", null, { headers: { "X-Session-ID": sessionId } })
      .then((res) => {
        // Clean URL fragment
        window.history.replaceState({}, document.title, "/chat");
        navigate("/chat", { replace: true, state: { user: res.data } });
      })
      .catch(() => {
        navigate("/login", { replace: true });
      });
  }, [navigate]);

  return (
    <div className="login-page h-screen w-full flex flex-col">
      <AppTopBar />
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <p className="text-sm text-secondary-em">Connexion en cours…</p>
        <div className="dot-loading"><span /><span /><span /></div>
      </div>
    </div>
  );
}
