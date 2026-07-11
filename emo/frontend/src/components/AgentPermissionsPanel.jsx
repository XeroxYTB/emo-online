import React, { useCallback, useEffect, useState } from "react";
import { Monitor, RefreshCw, Link2 } from "lucide-react";
import { http } from "../lib/api";
import { parseAgentStatus } from "../lib/agentStatus";
import { EmoLogo } from "./EmoLogo";
import { Link } from "react-router-dom";

export default function AgentPermissionsPanel({ agentOnline, desktopOnline }) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({
    connected: false,
    online: false,
    desktopOnline: false,
    linked: false,
    context: null,
  });

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await http.get("/agent/status");
      const parsed = parseAgentStatus(r.data);
      setStatus({
        connected: parsed.connected,
        online: parsed.agentToolsOnline,
        desktopOnline: parsed.desktopOnline,
        linked: parsed.desktopLinked,
        context: r.data.context || null,
      });
    } catch {
      setStatus((s) => ({ ...s, connected: false, desktopOnline: false, online: false }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const connected = status.desktopOnline || desktopOnline || agentOnline;
  const hostname = status.context?.hostname || status.context?.os || "";

  return (
    <div className="space-y-4 text-sm">
      <div
        className="rounded-xl p-4 text-center space-y-2"
        style={{
          background: "var(--emo-surface-raised)",
          border: `1px solid ${connected ? "var(--emo-status-online)" : "var(--emo-border)"}`,
          boxShadow: connected ? "0 0 16px var(--emo-status-online-glow)" : "none",
        }}
      >
        <EmoLogo size="sm" layout="stacked" subtitle="Desktop" online={connected} className="mx-auto" />
        <div className="flex items-center justify-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "emo-status-dot-online" : "emo-status-dot-offline"}`} />
          <span
            className="text-xs uppercase tracking-wider font-semibold"
            style={{ color: connected ? "var(--emo-status-online)" : "var(--emo-status-offline)" }}
          >
            {connected ? "Desktop connecté" : status.linked ? "Lié — en attente" : "Hors ligne"}
          </span>
          <button type="button" onClick={refresh} className="p-1 rounded em-hover" title="Rafraîchir">
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
        {connected && hostname ? (
          <p className="text-[11px] text-muted-em font-code">{hostname}</p>
        ) : null}
      </div>

      {connected ? (
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <StatusPill label="App desktop" ok={status.desktopOnline || desktopOnline} />
          <StatusPill label="Agent outils" ok={status.online} />
        </div>
      ) : (
        <div
          className="p-3 rounded-xl text-[12px] leading-relaxed space-y-2"
          style={{ background: "var(--emo-bg-subtle)", border: "1px solid var(--emo-border)" }}
        >
          <p className="text-secondary-em flex items-center gap-2">
            <Monitor size={14} /> Émo Desktop non connecté
          </p>
          <ol className="list-decimal list-inside space-y-1 text-muted-em">
            <li>Télécharge et lance <strong>Émo Desktop</strong></li>
            <li>Clique <strong>link</strong> dans l&apos;app</li>
            <li>Connecte-toi ici si besoin → <strong>Accepter</strong></li>
          </ol>
          <Link
            to="/link-desktop"
            className="inline-flex items-center gap-1.5 text-[11px] font-medium hover:underline"
            style={{ color: "var(--mode-color)" }}
          >
            <Link2 size={12} /> Page de liaison Emo Online
          </Link>
        </div>
      )}
    </div>
  );
}

function StatusPill({ label, ok }) {
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg"
      style={{ background: "var(--emo-surface)", border: "1px solid var(--emo-border)" }}
    >
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${ok ? "emo-status-dot-online" : "emo-status-dot-offline"}`} />
      <span className="text-secondary-em truncate">{label}</span>
    </div>
  );
}
