import React, { useEffect, useState } from "react";
import { http, getApiBase, getSessionToken } from "../lib/api";
import { Copy, Check, RefreshCw, Download, ShieldAlert, Apple, Box, Cpu } from "lucide-react";
import { toast } from "sonner";

const detectOS = () => {
  if (typeof navigator === "undefined") return "windows";
  const ua = navigator.userAgent || "";
  if (/Win/i.test(ua)) {
    const plat = navigator.userAgentData?.platform || navigator.platform || "";
    if (/arm|aarch/i.test(plat)) return "windows-arm";
    return "windows";
  }
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
  { id: "windows", label: "Windows x64", filename: "Emo-Agent.exe", icon: Box },
  { id: "windows-arm", label: "Windows ARM", filename: "Emo-Agent.exe", icon: Box },
  { id: "macos", label: "macOS Intel", filename: "Emo-Agent.zip", icon: Apple },
  { id: "macos-arm", label: "macOS Apple Silicon", filename: "Emo-Agent.zip", icon: Apple },
  { id: "linux", label: "Linux x64", filename: "Emo-Agent.zip", icon: Cpu },
  { id: "linux-arm", label: "Linux ARM64", filename: "Emo-Agent.zip", icon: Cpu },
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
      toast.error("Copie impossible");
    }
  };

  const rotate = async () => {
    if (!window.confirm("Régénérer le token ? L'ancien agent sera invalidé.")) return;
    const r = await http.post("/agent/token/rotate");
    setToken(r.data.agent_token);
    toast.success("Token régénéré");
  };

  const downloadAgent = async () => {
    setDownloading(true);
    try {
      const url = `${getApiBase()}/agent/binary/${os}`;
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
      const isZip = resp.headers.get("content-type")?.includes("zip")
        || resp.headers.get("content-disposition")?.includes(".zip");
      const filename = isZip ? "Emo-Agent.zip" : (DOWNLOAD_NAMES[os] || "Emo-Agent.exe");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      toast.success(
        isZip
          ? "Emo-Agent.zip téléchargé"
          : "Emo-Agent.exe — double-clic, connecte-toi avec ton compte Émo"
      );
    } catch (e) {
      toast.error(e.message || "Téléchargement impossible");
    } finally {
      setDownloading(false);
    }
  };

  const isWindows = os.startsWith("windows");
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

      <p className="text-[11px] text-secondary-em leading-relaxed">
        Installe l&apos;agent sur ton PC une fois. Ensuite pilote-le depuis{" "}
        <strong>xeroxytb.com</strong> sur n&apos;importe quel appareil (téléphone, tablette…).
      </p>

      <div>
        <label className="text-xs uppercase tracking-[0.18em] text-muted-em mb-2 block">Plateforme</label>
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
        disabled={downloading}
        className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-medium text-sm transition-all hover:scale-[1.01] disabled:opacity-50"
        style={{
          background: "var(--mode-color)",
          color: "#0A0510",
          boxShadow: "0 0 24px var(--mode-glow)",
        }}
      >
        <Download size={15} /> {downloading ? "Téléchargement…" : "Télécharger Emo Agent"}
      </button>

      <div className="text-[11px] text-secondary-em leading-relaxed space-y-2">
        {isWindows ? (
          <>
            <p>
              Un seul fichier <code className="font-code">Emo-Agent.exe</code> — double-clic, connexion avec ton
              compte Émo.
            </p>
            <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-100/90">
              Windows bloque parfois l&apos;exe (SmartScreen) : clic droit → <strong>Propriétés</strong> → cocher{" "}
              <strong>Débloquer</strong>, ou au lancement <strong>Informations complémentaires</strong> →{" "}
              <strong>Exécuter quand même</strong>.
            </p>
          </>
        ) : isUnix ? (
          <p>Archive zip avec l&apos;agent et l&apos;interface locale.</p>
        ) : null}
      </div>

      <details className="text-xs">
        <summary className="cursor-pointer text-muted-em hover:text-white">Token (avancé)</summary>
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
    </div>
  );
}
