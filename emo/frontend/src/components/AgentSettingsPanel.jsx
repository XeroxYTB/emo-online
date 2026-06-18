import React, { useEffect, useState } from "react";
import { http, API, getSessionToken } from "../lib/api";
import { Copy, Check, RefreshCw, Download, ShieldAlert, Terminal as TerminalIcon, Apple, Box, Cpu } from "lucide-react";
import { toast } from "sonner";

const detectOS = () => {
  if (typeof navigator === "undefined") return "windows";
  const ua = navigator.userAgent || "";
  if (/Win/i.test(ua)) return "windows";
  if (/Mac/i.test(ua)) {
    const plat = navigator.userAgentData?.platform || navigator.platform || "";
    return /arm|aarch/i.test(plat) ? "macos-arm" : "macos";
  }
  if (/Linux/i.test(ua)) {
    const plat = navigator.userAgentData?.platform || "";
    return /arm|aarch/i.test(plat) ? "linux-arm" : "linux";
  }
  return "windows";
};

const OS_OPTIONS = [
  { id: "windows", label: "Windows", filename: "Emo-Agent.exe", icon: Box },
  { id: "macos", label: "macOS Intel", filename: "Emo-Agent", icon: Apple },
  { id: "macos-arm", label: "macOS Apple Silicon", filename: "Emo-Agent", icon: Apple },
  { id: "linux", label: "Linux x64", filename: "Emo-Agent", icon: Cpu },
  { id: "linux-arm", label: "Linux ARM64", filename: "Emo-Agent", icon: Cpu },
];

const DOWNLOAD_NAMES = Object.fromEntries(OS_OPTIONS.map((o) => [o.id, o.filename]));

export default function AgentSettingsPanel({ agentOnline, onRefreshStatus }) {
  const [token, setToken] = useState("");
  const [copied, setCopied] = useState("");
  const [os, setOs] = useState(detectOS());
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    http.get("/agent/token").then((r) => setToken(r.data.agent_token));
  }, []);

  const copy = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      toast.error("Impossible de copier");
    }
  };

  const rotate = async () => {
    if (!window.confirm("Régénérer le token ? L'ancien agent sera invalidé.")) return;
    const r = await http.post("/agent/token/rotate");
    setToken(r.data.agent_token);
    toast.success("Token régénéré");
  };

  const downloadAgent = async () => {
    if (!token) {
      toast.error("Token pas encore prêt, réessaie dans 1s");
      return;
    }
    setDownloading(true);
    try {
      const url = `${API}/agent/binary/${os}?token=${encodeURIComponent(token)}`;
      const headers = {};
      const session = getSessionToken();
      if (session) {
        headers.Authorization = `Bearer ${session}`;
        headers["X-Emo-Session"] = session;
      }
      const resp = await fetch(url, { credentials: "include", headers });
      if (!resp.ok) {
        let detail = `HTTP ${resp.status}`;
        try {
          const err = await resp.json();
          detail = err.detail || detail;
        } catch (_) {}
        throw new Error(typeof detail === "string" ? detail : "Téléchargement impossible");
      }
      const blob = await resp.blob();
      const filename = DOWNLOAD_NAMES[os] || "Emo-Agent";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      toast.success(`${filename} téléchargé — double-clique pour ouvrir l'interface permissions`);
    } catch (e) {
      toast.error(e.message || "Échec du téléchargement");
    } finally {
      setDownloading(false);
    }
  };

  const isUnix = os.startsWith("macos") || os.startsWith("linux");

  return (
    <div className="space-y-5 text-sm">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${agentOnline ? "bg-emerald-400" : "bg-zinc-500"}`}
          style={{ boxShadow: agentOnline ? "0 0 8px #34d39988" : "none" }}
        />
        <span className="text-secondary-em">
          Agent local :{" "}
          <strong style={{ color: agentOnline ? "#34d399" : "#a89bbd" }}>
            {agentOnline ? "EN LIGNE" : "HORS LIGNE"}
          </strong>
        </span>
        <button
          data-testid="refresh-agent-status"
          onClick={onRefreshStatus}
          className="ml-auto p-1 rounded hover:bg-white/10"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <div>
        <label className="text-xs uppercase tracking-[0.18em] text-muted-em mb-2 block">Ta plateforme</label>
        <div className="grid grid-cols-2 gap-2">
          {OS_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const active = os === opt.id;
            return (
              <button
                key={opt.id}
                data-testid={`os-${opt.id}-btn`}
                onClick={() => setOs(opt.id)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] transition"
                style={{
                  background: active ? "rgba(168,85,247,0.15)" : "rgba(255,255,255,0.02)",
                  border: `1px solid ${active ? "rgba(168,85,247,0.4)" : "rgba(255,255,255,0.05)"}`,
                  color: active ? "#fff" : "var(--emo-text-secondary)",
                }}
              >
                <Icon size={12} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      <button
        data-testid="download-agent-btn"
        onClick={downloadAgent}
        disabled={!token || downloading}
        className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-medium text-sm transition-all hover:scale-[1.01] disabled:opacity-50"
        style={{
          background: "var(--mode-color)",
          color: "#0A0510",
          boxShadow: "0 0 24px var(--mode-glow)",
        }}
      >
        <Download size={15} /> {downloading ? "Téléchargement…" : "Télécharger Emo Agent (1 fichier)"}
      </button>

      <div className="text-[11px] text-secondary-em leading-relaxed space-y-2">
        <p>
          <strong>Un seul fichier</strong> — token et URL du site déjà intégrés. Pas de ZIP, pas de script à lancer
          manuellement.
        </p>
        {os === "windows" ? (
          <p>
            <strong>Windows :</strong> double-clique sur <code className="font-code">Emo-Agent.exe</code>. Une fenêtre
            locale s&apos;ouvre dans ton navigateur pour gérer les permissions (shell, fichiers, grep…) puis démarrer
            l&apos;agent.
          </p>
        ) : isUnix ? (
          <p>
            <strong>{os.startsWith("macos") ? "macOS" : "Linux"} :</strong>{" "}
            <code className="font-code">chmod +x Emo-Agent && ./Emo-Agent</code>
            {os.startsWith("macos") && (
              <>
                {" "}
                — si Gatekeeper bloque : clic droit → Ouvrir, ou{" "}
                <code className="font-code">xattr -d com.apple.quarantine Emo-Agent</code>
              </>
            )}
          </p>
        ) : null}
        <p className="text-muted-em">
          Le chat, les LLM et les paiements restent sur le site. Configure les permissions dans{" "}
          <strong>Profil → Agent local & permissions</strong>.
        </p>
      </div>

      <details className="text-xs">
        <summary className="cursor-pointer text-muted-em hover:text-white">Avancé : token brut</summary>
        <div className="mt-3 space-y-3">
          <div className="flex items-center gap-2">
            <code
              data-testid="agent-token-display"
              className="flex-1 font-code text-[11px] px-3 py-2 rounded-lg bg-black/50 border border-white/5 truncate"
              style={{ color: "#E9D5FF" }}
            >
              {token || "…"}
            </code>
            <button data-testid="copy-token-btn" onClick={() => copy(token, "token")} className="p-2 rounded-lg glass-card">
              {copied === "token" ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
          <button
            onClick={rotate}
            data-testid="rotate-token-btn"
            className="text-[11px] text-muted-em hover:text-red-300 flex items-center gap-1"
          >
            <ShieldAlert size={11} /> Régénérer (invalide l&apos;ancien agent)
          </button>
        </div>
      </details>

      <div className="text-[11px] text-muted-em leading-relaxed border-t border-white/5 pt-3">
        <TerminalIcon size={11} className="inline mr-1" />
        L&apos;agent exécute ce qu&apos;Émo demande selon tes permissions locales. Le token lie uniquement ton compte —
        personne d&apos;autre ne peut piloter ta machine.
      </div>
    </div>
  );
}
