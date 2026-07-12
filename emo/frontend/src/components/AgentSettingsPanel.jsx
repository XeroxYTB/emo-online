import React, { useCallback, useEffect, useState } from "react";
import { http, getApiBase, getSessionToken } from "../lib/api";
import { parseAgentStatus } from "../lib/agentStatus";
import { EmoLogo } from "./EmoLogo";
import { Copy, Check, RefreshCw, Download, ShieldAlert, Apple, Box, Cpu, Monitor, Link2 } from "lucide-react";
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
  { id: "windows", label: "Windows x64", filename: "Emo-Desktop.zip", icon: Box },
  { id: "windows-arm", label: "Windows ARM", filename: "Emo-Desktop.zip", icon: Box },
  { id: "macos", label: "macOS Intel", filename: "Emo-Desktop.zip", icon: Apple },
  { id: "macos-arm", label: "macOS Apple Silicon", filename: "Emo-Desktop.zip", icon: Apple },
  { id: "linux", label: "Linux x64", filename: "Emo-Desktop.zip", icon: Cpu },
  { id: "linux-arm", label: "Linux ARM64", filename: "Emo-Desktop.zip", icon: Cpu },
];

const DOWNLOAD_NAMES = Object.fromEntries(OS_OPTIONS.map((o) => [o.id, o.filename]));

export default function AgentSettingsPanel({ agentOnline, onRefreshStatus }) {
  const [token, setToken] = useState("");
  const [copied, setCopied] = useState("");
  const [os, setOs] = useState(detectOS());
  const [downloading, setDownloading] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [status, setStatus] = useState({
    connected: false,
    online: false,
    desktopOnline: false,
    linked: false,
    context: null,
  });

  const refreshLocal = useCallback(async () => {
    try {
      const r = await http.get("/agent/status");
      const parsed = parseAgentStatus(r.data);
      setStatus({
        connected: parsed.desktopOnline || parsed.desktopLinked,
        online: parsed.agentToolsOnline,
        desktopOnline: parsed.desktopOnline,
        linked: parsed.desktopLinked,
        context: r.data.context || null,
      });
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    http.get("/agent/token").then((r) => setToken(r.data.agent_token));
    refreshLocal();
    const id = setInterval(refreshLocal, 5000);
    return () => clearInterval(id);
  }, [refreshLocal]);

  const connected = status.desktopOnline || agentOnline;

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

  const fetchAgentDownload = async (url, fallbackFilename) => {
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
    const buf = await blob.arrayBuffer();
    const bytes = new Uint8Array(buf);
    const isZipFile = bytes[0] === 0x50 && bytes[1] === 0x4b;
    const isZip =
      isZipFile ||
      resp.headers.get("content-type")?.includes("zip") ||
      resp.headers.get("content-disposition")?.includes(".zip");
    const cd = resp.headers.get("content-disposition") || "";
    const cdMatch = cd.match(/filename="?([^";]+)"?/i);
    const filename = cdMatch?.[1] || (isZip ? "Emo-Desktop.zip" : fallbackFilename);
    const outBlob = new Blob([buf], { type: isZip ? "application/zip" : blob.type });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(outBlob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    return { isZip, isFallback: resp.headers.get("X-Emo-Fallback") === "python-zip" };
  };

  const downloadDesktopExe = async () => {
    setDownloading(true);
    try {
      const { isZip, isFallback } = await fetchAgentDownload(
        `${getApiBase()}/agent/desktop-exe/windows`,
        "Emo-Desktop.exe"
      );
      if (isZip || isFallback) {
        toast.success("Version Python (zip) — extrais et lance start.bat");
      } else {
        toast.success("Emo-Desktop.exe téléchargé — double-clic pour lancer");
      }
    } catch (e) {
      toast.error(e.message || "Téléchargement impossible");
    } finally {
      setDownloading(false);
    }
  };

  const downloadAgentZip = async () => {
    setDownloadingZip(true);
    try {
      const { isZip } = await fetchAgentDownload(
        `${getApiBase()}/agent/binary/${os}`,
        "Emo-Desktop.zip"
      );
      toast.success(
        isZip
          ? "Émo Desktop (Python) téléchargé — extrais et lance start.bat ou start.sh"
          : "Émo Desktop téléchargé"
      );
    } catch (e) {
      toast.error(e.message || "Téléchargement impossible");
    } finally {
      setDownloadingZip(false);
    }
  };

  const isWindows = os === "windows" || os === "windows-arm";

  const handleRefresh = () => {
    refreshLocal();
    onRefreshStatus?.();
  };

  const hostname = status.context?.hostname || status.context?.os || "";

  return (
    <div className="space-y-5 text-sm">
      <div
        className="rounded-2xl p-5 text-center space-y-3"
        style={{
          background: "var(--emo-surface-raised)",
          border: `1px solid ${connected ? "var(--emo-status-online)" : "var(--emo-border)"}`,
          boxShadow: connected ? "0 0 24px var(--emo-status-online-glow)" : "none",
        }}
      >
        <EmoLogo size="md" layout="stacked" subtitle="Desktop" online={connected} className="mx-auto" />
        <div className="flex items-center justify-center gap-2 pt-1">
          <div className={`w-2.5 h-2.5 rounded-full ${connected ? "emo-status-dot-online" : "emo-status-dot-offline"}`} />
          <span
            className="text-xs uppercase tracking-[0.2em] font-semibold"
            style={{ color: connected ? "var(--emo-status-online)" : "var(--emo-status-offline)" }}
          >
            {connected ? "Connecté" : status.linked ? "Desktop lié — en attente" : "Hors ligne"}
          </span>
          <button
            data-testid="refresh-agent-status"
            onClick={handleRefresh}
            className="ml-2 p-1 rounded em-hover"
            type="button"
          >
            <RefreshCw size={13} />
          </button>
        </div>
        {connected && hostname ? (
          <p className="text-[11px] text-muted-em font-code">{hostname}</p>
        ) : null}
        {!connected && (
          <p className="text-[11px] text-secondary-em leading-relaxed px-2">
            Lance <strong>Émo Desktop</strong> sur ce PC, clique <strong>link</strong>, connecte-toi sur le site et
            appuie sur <strong>Accepter</strong>.
          </p>
        )}
      </div>

      <div
        className="rounded-xl p-3 space-y-2"
        style={{ background: "var(--emo-bg-subtle)", border: "1px solid var(--emo-border)" }}
      >
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-em">
          <Monitor size={12} /> État
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <StatusPill label="App desktop" ok={status.desktopOnline} />
          <StatusPill label="Agent outils" ok={status.online} />
          <StatusPill label="Compte lié" ok={status.linked} />
          <StatusPill label="Cloud" ok={!!getSessionToken()} />
        </div>
      </div>

      <div
        className="rounded-2xl p-4 space-y-2"
        style={{ background: "var(--emo-surface-raised)", border: "1px solid var(--emo-border)" }}
      >
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-em">
          <Link2 size={13} /> Connexion
        </div>
        <ol className="text-[11px] text-secondary-em space-y-1.5 list-decimal list-inside leading-relaxed">
          <li>
            {isWindows
              ? "Télécharge Emo-Desktop.exe et double-clic pour lancer"
              : "Télécharge et lance Émo Desktop (zip Python)"}
          </li>
          <li>Clique <strong>link</strong> — le site s&apos;ouvre</li>
          <li>Connecte-toi si besoin → <strong>Accepter</strong></li>
          <li>Le voyant passe au vert ici</li>
        </ol>
      </div>

      <div>
        <label className="text-xs uppercase tracking-[0.18em] text-muted-em mb-2 block">Plateforme</label>
        <div className="grid grid-cols-2 gap-2">
          {OS_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const active = os === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                data-testid={`os-${opt.id}-btn`}
                onClick={() => setOs(opt.id)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-[12px] transition"
                style={{
                  background: active ? "var(--emo-accent-soft)" : "var(--emo-surface-raised)",
                  border: `1px solid ${active ? "var(--emo-accent-border)" : "var(--emo-border)"}`,
                  color: "var(--emo-text)",
                }}
              >
                <Icon size={12} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {isWindows ? (
        <>
          <button
            type="button"
            data-testid="download-desktop-exe-btn"
            onClick={downloadDesktopExe}
            disabled={downloading}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-medium text-sm transition-all hover:scale-[1.01] disabled:opacity-50"
            style={{
              background: "var(--mode-color)",
              color: "var(--emo-on-mode)",
              boxShadow: "0 0 24px var(--mode-glow)",
            }}
          >
            <Download size={15} />{" "}
            {downloading ? "Téléchargement…" : "Télécharger Emo-Desktop.exe (Windows)"}
          </button>
          <button
            type="button"
            data-testid="download-agent-btn"
            onClick={downloadAgentZip}
            disabled={downloadingZip}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-[12px] transition disabled:opacity-50 em-hover"
            style={{
              background: "var(--emo-surface-raised)",
              border: "1px solid var(--emo-border)",
              color: "var(--emo-text-secondary)",
            }}
          >
            <Download size={13} />{" "}
            {downloadingZip ? "Téléchargement…" : "Version Python (zip)"}
          </button>
        </>
      ) : (
        <button
          type="button"
          data-testid="download-agent-btn"
          onClick={downloadAgentZip}
          disabled={downloadingZip}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-medium text-sm transition-all hover:scale-[1.01] disabled:opacity-50"
          style={{
            background: "var(--mode-color)",
            color: "var(--emo-on-mode)",
            boxShadow: "0 0 24px var(--mode-glow)",
          }}
        >
          <Download size={15} />{" "}
          {downloadingZip ? "Téléchargement…" : "Télécharger Émo Desktop"}
        </button>
      )}

      <details className="text-xs">
        <summary className="cursor-pointer text-muted-em hover:text-[var(--emo-text)]">Token agent (avancé)</summary>
        <div className="mt-3 space-y-3">
          <div className="flex items-center gap-2">
            <code
              data-testid="agent-token-display"
              className="flex-1 font-code text-[11px] px-3 py-2 rounded-lg truncate em-input"
              style={{ color: "var(--emo-code-text)" }}
            >
              {token || "…"}
            </code>
            <button type="button" data-testid="copy-token-btn" onClick={() => copy(token, "token")} className="p-2 rounded-lg glass-card">
              {copied === "token" ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
          <button
            type="button"
            onClick={rotate}
            data-testid="rotate-token-btn"
            className="text-[11px] text-muted-em hover:text-[var(--emo-error-text)] flex items-center gap-1"
          >
            <ShieldAlert size={11} /> Régénérer (invalide l&apos;ancien agent)
          </button>
        </div>
      </details>
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
