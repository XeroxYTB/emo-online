import React, { useCallback, useEffect, useState } from "react";
import { Shield, RefreshCw, Play, Square, ExternalLink } from "lucide-react";
import { toast } from "sonner";

const AGENT_LOCAL = "http://127.0.0.1:17841";

const PERM_FIELDS = [
  { key: "allow_shell", label: "Shell" },
  { key: "allow_read", label: "Lecture" },
  { key: "allow_grep", label: "Recherche" },
  { key: "allow_write", label: "Écriture" },
  { key: "allow_delete", label: "Suppression" },
];

export default function AgentPermissionsPanel({ agentOnline }) {
  const [reachable, setReachable] = useState(false);
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState(null);
  const [perms, setPerms] = useState({
    allow_shell: true,
    allow_read: true,
    allow_grep: true,
    allow_write: false,
    allow_delete: false,
    enabled: true,
  });

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${AGENT_LOCAL}/api/state`, { signal: AbortSignal.timeout(2500) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const s = await r.json();
      setState(s);
      if (s.permissions) setPerms({ ...s.permissions, enabled: true });
      setReachable(true);
    } catch {
      setReachable(false);
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 8000);
    return () => clearInterval(id);
  }, [refresh]);

  const save = async () => {
    try {
      const r = await fetch(`${AGENT_LOCAL}/api/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ permissions: { ...perms, enabled: true } }),
      });
      if (!r.ok) throw new Error("save failed");
      toast.success("Permissions enregistrées");
      refresh();
    } catch {
      toast.error("Agent local indisponible");
    }
  };

  const startAgent = async () => {
    try {
      const r = await fetch(`${AGENT_LOCAL}/api/start`, { method: "POST" });
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || "start failed");
      toast.success("Agent démarré");
      refresh();
    } catch (e) {
      toast.error(e.message || "Impossible de démarrer l'agent");
    }
  };

  const stopAgent = async () => {
    try {
      await fetch(`${AGENT_LOCAL}/api/stop`, { method: "POST" });
      toast.info("Agent arrêté");
      refresh();
    } catch {
      toast.error("Agent local inaccessible");
    }
  };

  return (
    <div className="space-y-4 text-sm">
      <div className="flex items-center gap-2 text-xs">
        <div
          className={`w-2 h-2 rounded-full ${agentOnline ? "emo-status-dot-online" : "emo-status-dot-offline"}`}
        />
        <span className="text-secondary-em">
          Agent : <strong style={{ color: agentOnline ? "var(--emo-status-online)" : "var(--emo-status-offline)" }}>{agentOnline ? "En ligne" : "Hors ligne"}</strong>
        </span>
        <button type="button" onClick={refresh} className="ml-auto p-1 rounded em-hover" title="Rafraîchir">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {!reachable ? (
        <div
          className="p-3 rounded-xl text-[12px] leading-relaxed emo-alert-warning"
        >
          <p>
            Agent local non détecté. Installez et lancez Emo-Agent.
          </p>
          <a
            href={AGENT_LOCAL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 mt-2 text-[11px] hover:underline"
            style={{ color: "var(--emo-link)" }}
          >
            <ExternalLink size={11} /> Ouvrir {AGENT_LOCAL}
          </a>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 text-[11px] text-muted-em">
            <Shield size={12} />
            Agent local {state?.running ? (state?.connected ? "connecté" : "connexion…") : "arrêté"}
          </div>

          <div className="space-y-2">
            {PERM_FIELDS.map(({ key, label }) => (
              <label
                key={key}
                className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer em-hover-subtle"
                style={{ border: "1px solid var(--emo-border)" }}
              >
                <input
                  type="checkbox"
                  checked={!!perms[key]}
                  onChange={(e) => setPerms((p) => ({ ...p, [key]: e.target.checked }))}
                />
                <span className="text-[13px]">{label}</span>
              </label>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={save}
              className="flex-1 py-2 rounded-lg text-xs font-medium emo-btn-soft"
            >
              Enregistrer
            </button>
            {state?.running ? (
              <button type="button" onClick={stopAgent} className="px-3 py-2 rounded-lg text-xs flex items-center gap-1 emo-alert-error">
                <Square size={11} /> Arrêter
              </button>
            ) : (
              <button type="button" onClick={startAgent} className="px-3 py-2 rounded-lg text-xs flex items-center gap-1 emo-alert-success">
                <Play size={11} /> Démarrer
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
