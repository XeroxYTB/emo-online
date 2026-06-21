import React, { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AppTopBar } from "../components/EmoLogo";
import { toast } from "sonner";

export default function ConnectionsCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const provider = searchParams.get("provider") || "";
    const status = searchParams.get("status");
    const error = searchParams.get("error");

    if (status === "ok") {
      toast.success(`${provider || "Compte"} connecté`);
    } else if (status === "error") {
      toast.error(error || "Connexion annulée");
    }

    navigate("/chat?settings=connections", { replace: true });
  }, [navigate, searchParams]);

  return (
    <div className="h-screen w-full flex flex-col" style={{ background: "var(--emo-bg)" }}>
      <AppTopBar />
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <div className="login-boot-dots flex justify-center gap-1.5">
          <span /><span /><span />
        </div>
        <p className="text-sm text-secondary-em">Liaison du compte…</p>
      </div>
    </div>
  );
}
