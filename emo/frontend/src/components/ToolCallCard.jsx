import React, { useState } from "react";
import { ChevronRight, ChevronDown, Terminal, FileText, FolderTree, Wrench, AlertCircle, Globe, Search, Pencil, Trash2, Move, FileSearch, Compass, Sparkles, History, MousePointer2 } from "lucide-react";
import ToolInlinePreview from "./ToolInlinePreview";

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
};

export const ToolCallCard = ({ event }) => {
  // event = {state: "executing"|"done"|"error", tool, args, result, id}
  const [open, setOpen] = useState(event.state !== "done");
  const Icon = ICONS[event.tool] || Wrench;
  const color = COLORS[event.tool] || "var(--mode-color)";
  const isError = event.state === "error" || (event.result && event.result.ok === false);
  const isExecuting = event.state === "executing";

  const summary = (() => {
    if (isExecuting) return "En cours…";
    if (isError) return event.result?.error || "erreur";
    if (event.result?.exit_code !== undefined) return `exit ${event.result.exit_code}`;
    if (event.result?.count !== undefined) return `${event.result.count} résultats`;
    if (event.result?.results !== undefined) return `${event.result.results.length} résultats`;
    if (event.result?.text !== undefined && event.result?.url !== undefined) return `${event.result.text.length} chars`;
    if (event.result?.content !== undefined) return `${event.result.content.length} chars`;
    if (event.result?.matches !== undefined) return `${event.result.matches.length} matches`;
    if (event.result?.entries !== undefined) return `${event.result.entries.length} entrées`;
    if (event.result?.replacements !== undefined) return `${event.result.replacements} remplacement(s)`;
    if (event.result?.files !== undefined && event.result?.dirs !== undefined) return `${event.result.files.length} fichiers · ${event.result.dirs.length} dossiers`;
    if (event.result?.files !== undefined && Array.isArray(event.result.files)) return `${event.result.files.length} fichiers`;
    return "ok";
  })();

  return (
    <div
      data-testid={`tool-call-${event.tool}`}
      className="rounded-xl my-2 overflow-hidden"
      style={{
        background: "rgba(0,0,0,0.3)",
        border: `1px solid ${isError ? "rgba(239,68,68,0.3)" : "rgba(255,255,255,0.06)"}`,
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-xs hover:bg-white/[0.03] transition"
      >
        {open ? <ChevronDown size={12} className="opacity-50" /> : <ChevronRight size={12} className="opacity-50" />}
        <Icon size={13} style={{ color }} />
        <span className="font-code text-[12px]" style={{ color }}>{event.tool}</span>
        <span className="text-muted-em font-code truncate flex-1 text-left">
          {formatArgs(event.tool, event.args)}
        </span>
        {isExecuting ? (
          <span className="inline-flex items-center gap-1 text-[10px] text-secondary-em">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />
            En cours
          </span>
        ) : (
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full ${
              isError ? "text-red-300" : "text-emerald-300"
            }`}
            style={{
              background: isError ? "rgba(239,68,68,0.12)" : "rgba(52,211,153,0.1)",
            }}
          >
            {isError && <AlertCircle size={9} className="inline mr-1" />}
            {summary}
          </span>
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-white/5 space-y-2">
          <ToolInlinePreview event={event} />
          {event.args && Object.keys(event.args).length > 0 && (
            <div>
              <div className="text-[9px] uppercase tracking-[0.18em] text-muted-em mb-1">args</div>
              <pre className="font-code text-[11px] p-2 rounded bg-black/40 overflow-x-auto" style={{ color: "#E9D5FF" }}>
                {JSON.stringify(event.args, null, 2)}
              </pre>
            </div>
          )}
          {event.result && (
            <div>
              <div className="text-[9px] uppercase tracking-[0.18em] text-muted-em mb-1">result</div>
              <pre className="font-code text-[11px] p-2 rounded bg-black/40 overflow-x-auto max-h-64 overflow-y-auto" style={{ color: isError ? "#FCA5A5" : "#E9D5FF" }}>
                {formatResult(event.result)}
              </pre>
            </div>
          )}
        </div>
      )}
      {!open && event.state === "done" && !isError && (
        <div className="px-3 pb-2">
          <ToolInlinePreview event={event} />
        </div>
      )}
    </div>
  );
};

function formatArgs(tool, args) {
  if (!args) return "";
  if (tool === "exec_shell") return args.cmd || "";
  if (tool === "read_file" || tool === "list_dir" || tool === "delete_path") return args.path || "";
  if (tool === "write_file") return `${args.path} (${(args.content || "").length} chars)`;
  if (tool === "edit_file") return args.path || "";
  if (tool === "grep") return `"${args.pattern || ""}" in ${args.path || "."}`;
  if (tool === "find_files") return args.pattern || "";
  if (tool === "move_path") return `${args.from} → ${args.to}`;
  if (tool === "web_search") return `"${args.query || ""}"${args.focus && args.focus !== "general" ? ` [${args.focus}]` : ""}`;
  if (tool === "web_fetch" || tool === "browser_visit" || tool === "browser_open") return args.url || "";
  if (tool.startsWith("browser_")) {
    if (args.ref != null) return `ref=${args.ref}`;
    if (args.selector) return args.selector;
    if (args.text) return `"${String(args.text).slice(0, 40)}"`;
    return args.url || "";
  }
  if (tool === "emo_reflect") return (args.thought || "").slice(0, 60);
  if (tool === "emo_remember") return (args.content || "").slice(0, 60);
  if (tool === "emo_edit_self") return `${args.section || ""} (${(args.content || "").length} chars)`;
  if (tool === "emo_read_self") return args.section || "all";
  if (tool === "emo_restore_self") return (args.version_id || "").slice(0, 8);
  return JSON.stringify(args);
}

function formatResult(result) {
  if (!result) return "";
  if (result.ok === false) return `ERROR: ${result.error}`;
  if (result.stdout !== undefined || result.stderr !== undefined) {
    let out = "";
    if (result.stdout) out += result.stdout;
    if (result.stderr) out += (out ? "\n--- stderr ---\n" : "") + result.stderr;
    return out || "(no output)";
  }
  if (result.results !== undefined) {
    return result.results.map((r, i) => {
      const dom = r.domain ? ` (${r.domain})` : "";
      return `${i + 1}. ${r.title}${dom}\n   ${r.url}\n   ${r.snippet || ""}`;
    }).join("\n\n").slice(0, 4000);
  }
  if (result.text !== undefined && result.url !== undefined) {
    // web_fetch
    let s = `📄 ${result.title || "(no title)"}\n🔗 ${result.url}\n\n`;
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
