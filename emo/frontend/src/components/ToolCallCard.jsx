import React, { useState, useEffect } from "react";
import { ChevronRight, ChevronDown, Terminal, FileText, FolderTree, Wrench, AlertCircle, Globe, Search, Pencil, Trash2, Move, FileSearch, Compass, Sparkles, History, MousePointer2, Eye, EyeOff, Copy, Check, ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { hasToolPreview, buildImagePreviewSrc } from "../lib/resolveToolPreview";
import { getFileContentFromToolEvent, isCopyableFileToolEvent } from "../lib/filePreview";
import ChatPreviewBubble from "./ChatPreviewBubble";
import ImageGeneratingPlaceholder from "./ImageGeneratingPlaceholder";

const ICONS = {
  exec_shell: Terminal,
  read_file: FileText,
  write_file: FileText,
  edit_file: Pencil,
  list_dir: FolderTree,
  grep: Search,
  find_files: FileSearch,
  delete_path: Trash2,
  move_path: Move,
  web_search: Search,
  web_fetch: Globe,
  browser_visit: Compass,
  browser_open: Compass,
  browser_click: MousePointer2,
  browser_type: Compass,
  browser_snapshot: Compass,
  browser_scroll: Compass,
  browser_press: Compass,
  browser_close: Compass,
  emo_reflect: Sparkles,
  emo_remember: Sparkles,
  emo_introspect: Sparkles,
  emo_read_self: Sparkles,
  emo_edit_self: Sparkles,
  emo_list_self_saves: History,
  emo_restore_self: History,
  generate_image: ImageIcon,
};

const COLORS = {
  exec_shell: "#06B6D4",
  read_file: "#A855F7",
  write_file: "#EC4899",
  edit_file: "#F472B6",
  list_dir: "#F59E0B",
  grep: "#22D3EE",
  find_files: "#818CF8",
  delete_path: "#EF4444",
  move_path: "#FB923C",
  web_search: "#10B981",
  web_fetch: "#3B82F6",
  browser_visit: "#6366F1",
  browser_open: "#6366F1",
  browser_click: "#38BDF8",
  browser_type: "#818CF8",
  emo_reflect: "#E879F9",
  emo_remember: "#C084FC",
  emo_introspect: "#A855F7",
  emo_read_self: "#E879F9",
  emo_edit_self: "#E879F9",
  emo_list_self_saves: "#C084FC",
  emo_restore_self: "#C084FC",
  generate_image: "#E879F9",
};

export const ToolCallCard = ({ event, liveHtmlByPath = {}, showCopyCode = false }) => {
  const [open, setOpen] = useState(event.state !== "done");
  const [copied, setCopied] = useState(false);
  const isImageGen = event.tool === "generate_image";
  const imagePreviewSrc = event.inlinePreview?.type === "image"
    ? buildImagePreviewSrc(event.inlinePreview)
    : buildImagePreviewSrc(event.result);
  const canPreview = hasToolPreview(event) || Boolean(isImageGen && imagePreviewSrc) || Boolean(
    event.args?.url && [
      "browser_visit", "browser_open", "web_fetch",
      "browser_click", "browser_snapshot", "browser_scroll", "browser_press", "browser_type",
    ].includes(event.tool),
  );
  const [previewOpen, setPreviewOpen] = useState(
    canPreview && (event.state === "done" || ["browser_visit", "browser_open"].includes(event.tool)),
  );
  const Icon = ICONS[event.tool] || Wrench;
  const color = COLORS[event.tool] || "var(--mode-color)";
  const isError = event.state === "error" || (event.result && event.result.ok === false);
  const isExecuting = event.state === "executing";
  const waitingForImage = isImageGen && event.result?.has_image && !imagePreviewSrc;
  const showImageGenLoading = isImageGen && (isExecuting || waitingForImage);
  const fileContent = showCopyCode && isCopyableFileToolEvent(event)
    ? getFileContentFromToolEvent(event, liveHtmlByPath)
    : "";
  const canCopyCode = Boolean(fileContent);

  const handleCopyCode = async () => {
    if (!fileContent) return;
    try {
      await navigator.clipboard.writeText(fileContent);
      setCopied(true);
      toast.success("Code copié");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Impossible de copier");
    }
  };

  useEffect(() => {
    if (isImageGen && isExecuting) {
      setPreviewOpen(true);
    } else if (event.state === "done" && canPreview) {
      setPreviewOpen(true);
    }
  }, [event.state, canPreview, event.inlinePreview, event.result, isImageGen, isExecuting]);

  const summary = (() => {
    if (isExecuting) return "En cours…";
    if (isError) return event.result?.error || "erreur";
    if (event.result?.exit_code !== undefined) return `code ${event.result.exit_code}`;
    if (event.result?.count !== undefined) return `${event.result.count} résultats`;
    if (event.result?.results !== undefined) return `${event.result.results.length} résultats`;
    if (event.result?.text !== undefined && event.result?.url !== undefined) return `${event.result.text.length} car.`;
    if (event.result?.content !== undefined) return `${event.result.content.length} car.`;
    if (event.result?.matches !== undefined) return `${event.result.matches.length} correspondances`;
    if (event.result?.entries !== undefined) return `${event.result.entries.length} entrées`;
    if (event.result?.replacements !== undefined) return `${event.result.replacements} remplacement(s)`;
    if (event.result?.files !== undefined && event.result?.dirs !== undefined) return `${event.result.files.length} fichiers · ${event.result.dirs.length} dossiers`;
    if (event.result?.files !== undefined && Array.isArray(event.result.files)) return `${event.result.files.length} fichiers`;
    return "ok";
  })();

  return (
    <div className="space-y-2 my-2">
      <div
        data-testid={`tool-call-${event.tool}`}
        className="rounded-xl overflow-hidden"
        style={{
          background: "var(--emo-card-bg)",
          border: `1px solid ${isError ? "rgba(239,68,68,0.3)" : "var(--emo-border)"}`,
        }}
      >
        <div className="flex items-center gap-1">
          <button
            onClick={() => setOpen(!open)}
            className="flex-1 flex items-center gap-2.5 px-3 py-2 text-xs em-hover-subtle transition min-w-0"
          >
            {open ? <ChevronDown size={12} className="opacity-50 flex-shrink-0" /> : <ChevronRight size={12} className="opacity-50 flex-shrink-0" />}
            <Icon size={13} style={{ color }} className="flex-shrink-0" />
            <span className="font-code text-[12px] flex-shrink-0" style={{ color }}>{event.tool}</span>
            <span className="text-secondary-em font-code truncate flex-1 text-left">
              {formatArgs(event.tool, event.args)}
            </span>
            {isExecuting ? (
              <span className="inline-flex items-center gap-1 text-[10px] text-secondary-em flex-shrink-0">
                <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />
                En cours
              </span>
            ) : (
          <span
            className="text-[10px] px-2 py-0.5 rounded-full flex-shrink-0"
            style={{
              background: isError ? "var(--emo-error-bg)" : "var(--emo-success-bg)",
              color: isError ? "var(--emo-error-text)" : "var(--emo-success-text)",
            }}
          >
                {isError && <AlertCircle size={9} className="inline mr-1" />}
                {summary}
              </span>
            )}
          </button>
          {canCopyCode && event.state === "done" && !isError && (
            <button
              type="button"
              data-testid="tool-copy-code-btn"
              onClick={handleCopyCode}
              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-2 text-[10px] em-hover transition border-l em-border-l"
              style={{ color: copied ? "var(--emo-success-text)" : "var(--emo-text-muted)" }}
              title="Copier tout le code"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              <span className="hidden sm:inline">{copied ? "Copié" : "Copier"}</span>
            </button>
          )}
          {canPreview && event.state === "done" && !isError && (
            <button
              type="button"
              data-testid="tool-preview-toggle"
              onClick={() => setPreviewOpen((v) => !v)}
              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-2 text-[10px] em-hover transition border-l em-border-l"
              style={{ color: previewOpen ? "var(--mode-color)" : "var(--emo-text-muted)" }}
              title={previewOpen ? "Masquer l'aperçu" : "Afficher l'aperçu"}
            >
              {previewOpen ? <EyeOff size={12} /> : <Eye size={12} />}
              <span className="hidden sm:inline">{previewOpen ? "Masquer" : "Aperçu"}</span>
            </button>
          )}
        </div>
        {open && (
          <div className="px-3 pb-3 pt-1 em-border-t space-y-2">
            {event.args && Object.keys(event.args).length > 0 && (
              <div>
                <div className="text-[9px] uppercase tracking-[0.18em] text-muted-em mb-1">Arguments</div>
                <pre className="font-code text-[11px] p-2 rounded overflow-x-auto" style={{ background: "var(--emo-pre-bg)", color: "var(--emo-code-text)" }}>
                  {JSON.stringify(event.args, null, 2)}
                </pre>
              </div>
            )}
            {event.result && (
              <div>
                <div className="text-[9px] uppercase tracking-[0.18em] text-muted-em mb-1">Résultat</div>
                <pre className="font-code text-[11px] p-2 rounded overflow-x-auto max-h-64 overflow-y-auto" style={{ background: "var(--emo-pre-bg)", color: isError ? "var(--emo-error-text)" : "var(--emo-code-text)" }}>
                  {formatResult(event.result)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {previewOpen && showImageGenLoading && (
        <ImageGeneratingPlaceholder prompt={event.args?.prompt} />
      )}

      {previewOpen && canPreview && !showImageGenLoading && (
        <ChatPreviewBubble
          event={event}
          liveHtmlByPath={liveHtmlByPath}
          showCopyCode={showCopyCode}
        />
      )}
    </div>
  );
};

function formatArgs(tool, args) {
  if (!args) return "";
  if (tool === "exec_shell") return args.cmd || "";
  if (tool === "read_file" || tool === "list_dir" || tool === "delete_path") return args.path || "";
  if (tool === "write_file") return `${args.path} (${(args.content || "").length} car.)`;
  if (tool === "edit_file") return args.path || "";
  if (tool === "grep") return `"${args.pattern || ""}" in ${args.path || "."}`;
  if (tool === "find_files") return args.pattern || "";
  if (tool === "move_path") return `${args.from} → ${args.to}`;
  if (tool === "web_search") return `"${args.query || ""}"${args.focus && args.focus !== "general" ? ` [${args.focus}]` : ""}`;
  if (tool === "web_fetch" || tool === "browser_visit" || tool === "browser_open") return args.url || "";
  if (tool.startsWith("browser_")) {
    if (args.x != null && args.y != null) return `@${args.x},${args.y}`;
    if (args.ref != null) return `ref=${args.ref}`;
    if (args.selector) return args.selector;
    if (args.text) return `"${String(args.text).slice(0, 40)}"`;
    return args.url || "";
  }
  if (tool === "emo_reflect") return (args.thought || "").slice(0, 60);
  if (tool === "emo_remember") return (args.content || "").slice(0, 60);
  if (tool === "emo_edit_self") return `${args.section || ""} (${(args.content || "").length} car.)`;
  if (tool === "emo_read_self") return args.section || "tout";
  if (tool === "emo_restore_self") return (args.version_id || "").slice(0, 8);
  if (tool === "generate_image") return (args.prompt || "").slice(0, 80);
  return JSON.stringify(args);
}

function formatResult(result) {
  if (!result) return "";
  if (result.ok === false) return `ERREUR : ${result.error}`;
  if (result.stdout !== undefined || result.stderr !== undefined) {
    let out = "";
    if (result.stdout) out += result.stdout;
    if (result.stderr) out += (out ? "\n--- stderr ---\n" : "") + result.stderr;
    return out || "(aucune sortie)";
  }
  if (result.results !== undefined) {
    return result.results.map((r, i) => {
      const dom = r.domain ? ` (${r.domain})` : "";
      return `${i + 1}. ${r.title}${dom}\n   ${r.url}\n   ${r.snippet || ""}`;
    }).join("\n\n").slice(0, 4000);
  }
  if (result.text !== undefined && result.url !== undefined) {
    let s = `📄 ${result.title || "(sans titre)"}\n🔗 ${result.url}\n\n`;
    s += result.text.slice(0, 3000);
    if (result.truncated) s += "\n\n... [tronqué]";
    if (result.links?.length) {
      s += `\n\n--- ${result.links.length} liens ---\n`;
      s += result.links.slice(0, 10).map((l) => `· ${l.text} → ${l.url}`).join("\n");
    }
    return s;
  }
  if (result.content !== undefined) return result.content.slice(0, 4000);
  if (result.matches !== undefined) {
    return result.matches.map((m) => `${m.file}:${m.line}: ${m.text}`).join("\n").slice(0, 4000);
  }
  if (result.entries !== undefined) {
    return result.entries.map((e) => `${e.is_dir ? "[dir]" : "     "} ${e.path}`).join("\n").slice(0, 4000);
  }
  if (result.files !== undefined && result.dirs !== undefined) {
    return `📁 ${result.path}\n\n` +
      result.dirs.map((d) => `[dir]  ${d}`).join("\n") + "\n" +
      result.files.map((f) => `       ${f}`).join("\n");
  }
  if (result.files !== undefined && Array.isArray(result.files)) {
    return result.files.join("\n").slice(0, 4000);
  }
  return JSON.stringify(result, null, 2);
}

export default ToolCallCard;
