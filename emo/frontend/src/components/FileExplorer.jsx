import React, { useEffect, useState, useCallback } from "react";
import Editor, { loader } from "@monaco-editor/react";
import { http } from "../lib/api";
import { Folder, File as FileIcon, RefreshCw, Save, ArrowUp, AlertCircle, Eye, Code2 } from "lucide-react";
import { toast } from "sonner";
import FilePreviewPane from "./FilePreviewPane";
import { basename, isHtmlPath, parentDir } from "../lib/filePreview";

const joinPath = (base, name) => {
  if (!base || base === "~") return name;
  const sep = base.includes("\\") ? "\\" : "/";
  if (base.endsWith(sep)) return `${base}${name}`;
  return `${base}${sep}${name}`;
};

const detectLang = (path) => {
  const ext = path.split(".").pop().toLowerCase();
  const map = {
    py: "python", js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript",
    json: "json", html: "html", css: "css", scss: "scss", md: "markdown",
    cpp: "cpp", c: "c", h: "cpp", hpp: "cpp", cs: "csharp", java: "java",
    rs: "rust", go: "go", lua: "lua", sh: "shell", yml: "yaml", yaml: "yaml",
    toml: "toml", xml: "xml", svg: "xml", gd: "gdscript",
  };
  return map[ext] || "plaintext";
};

export default function FileExplorer({ agentOnline, externalPreview = null }) {
  const [cwd, setCwd] = useState("~");
  const [listing, setListing] = useState({ files: [], dirs: [], path: "~" });
  const [loading, setLoading] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [editorLoading, setEditorLoading] = useState(false);
  const [fsError, setFsError] = useState("");
  const [editorFailed, setEditorFailed] = useState(false);
  const [editorTheme, setEditorTheme] = useState("vs-dark");
  const [viewMode, setViewMode] = useState("code");

  useEffect(() => {
    const syncTheme = () => {
      setEditorTheme(document.documentElement.classList.contains("theme-light") ? "vs" : "vs-dark");
    };
    syncTheme();
    const obs = new MutationObserver(syncTheme);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

  const refresh = useCallback(async (path) => {
    if (!agentOnline) return;
    setLoading(true);
    setFsError("");
    try {
      const r = await http.get("/agent/fs/list", { params: { path } });
      setListing({
        path: r.data?.path || path,
        files: Array.isArray(r.data?.files) ? r.data.files : [],
        dirs: Array.isArray(r.data?.dirs) ? r.data.dirs : [],
      });
      setCwd(r.data?.path || path);
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || "Erreur";
      setFsError(String(msg));
      toast.error("Fichiers : " + msg);
    } finally {
      setLoading(false);
    }
  }, [agentOnline]);

  useEffect(() => {
    loader.init().catch(() => setEditorFailed(true));
  }, []);

  useEffect(() => {
    if (agentOnline) refresh("~");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentOnline]);

  useEffect(() => {
    if (!externalPreview?.path) return;
    const path = externalPreview.path;
    setCurrentFile(path);
    if (externalPreview.preview != null) {
      setContent(externalPreview.preview);
      setOriginalContent(externalPreview.preview);
    }
    setViewMode("code");
    const parent = parentDir(path);
    if (parent && parent !== cwd) refresh(parent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalPreview?.path, externalPreview?.preview]);

  const openFile = async (name) => {
    const path = joinPath(cwd, name);
    setEditorLoading(true);
    setEditorFailed(false);
    try {
      const r = await http.get("/agent/fs/read", { params: { path } });
      setCurrentFile(r.data.path);
      setContent(r.data.content || "");
      setOriginalContent(r.data.content || "");
      setViewMode("code");
    } catch (e) {
      toast.error("Lecture : " + (e?.response?.data?.detail || e.message));
    } finally {
      setEditorLoading(false);
    }
  };

  const saveFile = async () => {
    if (!currentFile) return;
    try {
      await http.post("/agent/fs/write", { path: currentFile, content });
      setOriginalContent(content);
      toast.success("Sauvegardé");
    } catch (e) {
      toast.error("Écriture : " + (e?.response?.data?.detail || e.message));
    }
  };

  const cdUp = () => {
    refresh(parentDir(cwd));
  };

  const dirs = listing.dirs || [];
  const files = listing.files || [];
  const dirty = content !== originalContent;
  const fileName = currentFile ? basename(currentFile) : null;
  const isHtml = currentFile ? isHtmlPath(currentFile) : false;
  const showPreviewTab = currentFile && !isHtml;
  const effectiveViewMode = isHtml ? "code" : viewMode;

  if (!agentOnline) {
    return (
      <div className="p-6 text-center text-sm text-secondary-em">
        <p className="mb-2">Agent local hors ligne.</p>
        <p className="text-xs text-muted-em">Agent local requis.</p>
        {externalPreview?.path && (
          <div className="mt-6 h-48 overflow-auto">
            {isHtmlPath(externalPreview.path) ? (
              <pre
                className="text-[10px] font-code p-2 rounded-lg h-full overflow-auto whitespace-pre-wrap"
                style={{ background: "var(--emo-editor-bg)", color: "var(--emo-editor-text)" }}
              >
                {(externalPreview.preview || "").slice(0, 4000)}
              </pre>
            ) : (
              <FilePreviewPane path={externalPreview.path} content={externalPreview.preview || ""} />
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      <div className="flex items-center gap-1 px-2 py-1.5 em-border-b text-xs flex-shrink-0">
        <button onClick={cdUp} className="p-1 rounded em-hover" data-testid="cd-up-btn" title="Dossier parent">
          <ArrowUp size={12} />
        </button>
        <code className="flex-1 font-code text-[10px] text-secondary-em truncate" data-testid="fs-cwd">{cwd}</code>
        <button onClick={() => refresh(cwd)} className="p-1 rounded em-hover" data-testid="fs-refresh-btn" title="Actualiser">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {fsError && (
        <div className="mx-2 mt-1.5 flex items-start gap-2 rounded-lg px-2 py-1.5 text-[10px] flex-shrink-0 emo-alert-error">
          <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
          <span>{fsError}</span>
        </div>
      )}

      <div className="flex-1 flex min-h-0 overflow-hidden">
        <div className="w-[108px] flex-shrink-0 em-border-r overflow-y-auto scrollbar-thin py-1" data-testid="file-tree">
          {dirs.map((d) => (
            <button
              key={`d-${d}`}
              onClick={() => refresh(joinPath(cwd, d))}
              className="w-full flex items-center gap-1 px-2 py-1 text-[10px] em-hover-subtle text-secondary-em"
              data-testid={`fs-dir-${d}`}
            >
              <Folder size={10} className="opacity-70 flex-shrink-0" style={{ color: "var(--mode-color)" }} />
              <span className="truncate">{d}</span>
            </button>
          ))}
          {files.map((f) => {
            const active = currentFile?.endsWith(f) || currentFile?.endsWith("\\" + f) || currentFile?.endsWith("/" + f);
            return (
              <button
                key={`f-${f}`}
                onClick={() => openFile(f)}
                className="w-full flex items-center gap-1 px-2 py-1 text-[10px] em-hover-subtle"
                data-testid={`fs-file-${f}`}
                style={{
                  color: active ? "var(--emo-text)" : "var(--emo-text-secondary)",
                  background: active ? "var(--emo-tab-active-bg)" : "transparent",
                }}
              >
                <FileIcon size={10} className="opacity-50 flex-shrink-0" />
                <span className="truncate">{f}</span>
              </button>
            );
          })}
          {files.length === 0 && dirs.length === 0 && !loading && (
            <p className="text-[10px] text-muted-em px-2 py-2">vide</p>
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {currentFile ? (
            <>
              <div className="flex items-center gap-1 px-2 py-1 em-border-b flex-shrink-0">
                <span className="flex-1 font-code text-[10px] text-secondary-em truncate" data-testid="editor-path" title={currentFile}>
                  {fileName}
                </span>
                <div className="flex rounded-md overflow-hidden flex-shrink-0" style={{ border: "1px solid var(--emo-border)" }}>
                  {showPreviewTab && (
                    <button
                      type="button"
                      onClick={() => setViewMode("preview")}
                      className="flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] transition"
                      style={{
                        background: viewMode === "preview" ? "var(--emo-tab-active-bg)" : "transparent",
                        color: viewMode === "preview" ? "var(--emo-text)" : "var(--emo-text-muted)",
                      }}
                      data-testid="file-tab-preview"
                    >
                      <Eye size={9} /> Aperçu
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setViewMode("code")}
                    className="flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] transition"
                    style={{
                      background: viewMode === "code" ? "var(--emo-tab-active-bg)" : "transparent",
                      color: viewMode === "code" ? "var(--emo-text)" : "var(--emo-text-muted)",
                    }}
                    data-testid="file-tab-code"
                  >
                    <Code2 size={9} /> Code
                  </button>
                </div>
                <button
                  onClick={saveFile}
                  disabled={!dirty}
                  data-testid="editor-save-btn"
                  className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] transition disabled:opacity-30 flex-shrink-0"
                  style={{
                    background: dirty ? "var(--mode-color)" : "transparent",
                    color: dirty ? "var(--emo-on-mode)" : "var(--emo-text-muted)",
                  }}
                >
                  <Save size={9} /> {dirty ? "Enreg." : "OK"}
                </button>
              </div>

              <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
                {effectiveViewMode === "preview" && showPreviewTab ? (
                  <FilePreviewPane path={currentFile} content={content} />
                ) : editorLoading ? (
                  <div className="flex-1 flex items-center justify-center text-xs text-muted-em">Chargement…</div>
                ) : editorFailed ? (
                  <textarea
                    className="flex-1 w-full text-xs font-code p-3 resize-none focus:outline-none"
                    style={{ background: "var(--emo-editor-bg)", color: "var(--emo-editor-text)" }}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                  />
                ) : (
                  <Editor
                    height="100%"
                    language={detectLang(currentFile)}
                    value={content}
                    onChange={(v) => setContent(v ?? "")}
                    theme={editorTheme}
                    loading={<div className="p-4 text-xs text-muted-em">Chargement…</div>}
                    onMount={() => setEditorFailed(false)}
                    beforeMount={() => setEditorFailed(false)}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 11,
                      fontFamily: "JetBrains Mono, monospace",
                      scrollBeyondLastLine: false,
                      padding: { top: 6, bottom: 6 },
                      wordWrap: "on",
                    }}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-muted-em p-4 text-center">
              {editorLoading ? "Chargement…" : "Choisis un fichier dans la liste"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
