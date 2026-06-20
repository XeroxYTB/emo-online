import React, { useEffect, useState, useCallback } from "react";
import Editor from "@monaco-editor/react";
import { http } from "../lib/api";
import { Folder, FolderOpen, File as FileIcon, RefreshCw, Save, ArrowUp } from "lucide-react";
import { toast } from "sonner";
import SquarePreviewFrame, { isImagePath, previewTextSnippet } from "./SquarePreviewFrame";

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

  const refresh = useCallback(async (path) => {
    if (!agentOnline) return;
    setLoading(true);
    try {
      const r = await http.get("/agent/fs/list", { params: { path } });
      setListing(r.data);
      setCwd(r.data.path);
    } catch (e) {
      toast.error("Agent : " + (e?.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }, [agentOnline]);

  useEffect(() => {
    if (agentOnline) refresh("~");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentOnline]);

  useEffect(() => {
    if (externalPreview?.path && externalPreview.path !== currentFile) {
      setCurrentFile(externalPreview.path);
      if (externalPreview.preview != null) {
        setContent(externalPreview.preview);
        setOriginalContent(externalPreview.preview);
      }
    }
  }, [externalPreview?.path]);

  const openFile = async (name) => {
    const path = `${cwd}/${name}`;
    setEditorLoading(true);
    try {
      const r = await http.get("/agent/fs/read", { params: { path } });
      setCurrentFile(r.data.path);
      setContent(r.data.content || "");
      setOriginalContent(r.data.content || "");
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
    const parts = cwd.split("/").filter(Boolean);
    if (parts.length <= 1) {
      refresh("/");
      return;
    }
    parts.pop();
    const next = (cwd.startsWith("/") ? "/" : "") + parts.join("/");
    refresh(next || "/");
  };

  const dirty = content !== originalContent;
  const previewPath = currentFile || externalPreview?.path || "";
  const previewContent = content || externalPreview?.preview || "";
  const previewIsImage = isImagePath(previewPath);

  if (!agentOnline) {
    return (
      <div className="p-6 text-center text-sm text-secondary-em">
        <p className="mb-2">Agent local hors ligne.</p>
        <p className="text-xs text-muted-em">Agent local requis.</p>
        {externalPreview?.path && (
          <div className="mt-6">
            <SquarePreviewFrame
              kind="text"
              text={previewTextSnippet(externalPreview.preview)}
              title={externalPreview.path.split("/").pop()}
              subtitle={externalPreview.path}
              testId="file-preview-offline"
            />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-1 px-3 py-2 border-b border-white/5 text-xs">
        <button onClick={cdUp} className="p-1 rounded hover:bg-white/10" data-testid="cd-up-btn">
          <ArrowUp size={12} />
        </button>
        <code className="flex-1 font-code text-[11px] text-secondary-em truncate" data-testid="fs-cwd">{cwd}</code>
        <button onClick={() => refresh(cwd)} className="p-1 rounded hover:bg-white/10" data-testid="fs-refresh-btn">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {previewPath && (
        <div className="flex-shrink-0 p-3 border-b border-white/5">
          <SquarePreviewFrame
            kind={previewIsImage ? "empty" : "text"}
            text={previewIsImage ? undefined : previewTextSnippet(previewContent, 1200)}
            title={previewPath.split(/[/\\]/).pop()}
            subtitle={previewPath}
            emptyLabel={previewIsImage ? "Fichier image — éditeur ci-dessous" : "Fichier vide"}
            testId="file-square-preview"
          />
        </div>
      )}

      <div className="flex-1 overflow-hidden flex min-h-0">
        <div className="w-44 flex-shrink-0 border-r border-white/5 overflow-y-auto scrollbar-thin py-1.5" data-testid="file-tree">
          {listing.dirs.map((d) => (
            <button
              key={`d-${d}`}
              onClick={() => refresh(`${cwd}/${d}`)}
              className="w-full flex items-center gap-1.5 px-3 py-1 text-xs hover:bg-white/[0.05] text-secondary-em"
              data-testid={`fs-dir-${d}`}
            >
              <Folder size={11} className="opacity-70 flex-shrink-0" style={{ color: "var(--mode-color)" }} />
              <span className="truncate">{d}</span>
            </button>
          ))}
          {listing.files.map((f) => (
            <button
              key={`f-${f}`}
              onClick={() => openFile(f)}
              className="w-full flex items-center gap-1.5 px-3 py-1 text-xs hover:bg-white/[0.05]"
              data-testid={`fs-file-${f}`}
              style={{ color: currentFile?.endsWith("/" + f) || currentFile?.endsWith("\\" + f) ? "#fff" : "var(--emo-text-secondary)" }}
            >
              <FileIcon size={11} className="opacity-50 flex-shrink-0" />
              <span className="truncate">{f}</span>
            </button>
          ))}
          {listing.files.length === 0 && listing.dirs.length === 0 && !loading && (
            <p className="text-[10px] text-muted-em px-3 py-2">vide</p>
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          {currentFile ? (
            <>
              <div className="flex items-center justify-between px-3 py-1.5 text-[11px] border-b border-white/5">
                <code className="font-code text-secondary-em truncate" data-testid="editor-path">{currentFile}</code>
                <button
                  onClick={saveFile}
                  disabled={!dirty}
                  data-testid="editor-save-btn"
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] transition disabled:opacity-30"
                  style={{
                    background: dirty ? "var(--mode-color)" : "transparent",
                    color: dirty ? "#0A0510" : "var(--emo-text-muted)",
                  }}
                >
                  <Save size={10} /> {dirty ? "save" : "saved"}
                </button>
              </div>
              <div className="flex-1 min-h-0">
                <Editor
                  height="100%"
                  language={detectLang(currentFile)}
                  value={content}
                  onChange={(v) => setContent(v ?? "")}
                  theme="vs-dark"
                  loading={<div className="p-4 text-xs text-muted-em">Chargement…</div>}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 12,
                    fontFamily: "JetBrains Mono, monospace",
                    fontLigatures: true,
                    scrollBeyondLastLine: false,
                    padding: { top: 8, bottom: 8 },
                    wordWrap: "on",
                  }}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-muted-em">
              {editorLoading ? "Chargement…" : "Sélectionne un fichier"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
