import React, { useCallback, useEffect, useRef } from "react";
import { FileCode2, Globe } from "lucide-react";
import { basename } from "../lib/filePreview";

/** Mini-navigateur pour aperçu HTML live — chrome pro, iframe sandbox, mises à jour sans reload. */
export default function LiveHtmlPreview({ path = "", title, content = "", compact = false }) {
  const iframeRef = useRef(null);
  const lastWrittenRef = useRef("");
  const displayTitle = title || (path ? basename(path) : "Aperçu HTML");

  const writeContent = useCallback((html) => {
    const iframe = iframeRef.current;
    if (!iframe || html == null) return;
    if (html === lastWrittenRef.current) return;
    lastWrittenRef.current = html;
    try {
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc) return;
      doc.open();
      doc.write(html);
      doc.close();
    } catch {
      /* sandbox / cross-origin — ignore */
    }
  }, []);

  useEffect(() => {
    writeContent(content || "");
  }, [content, writeContent]);

  const handleIframeLoad = () => {
    if (content && content !== lastWrittenRef.current) {
      writeContent(content);
    }
  };

  return (
    <div
      className="rounded-xl overflow-hidden"
      data-testid="live-html-preview"
      style={{
        background: "var(--emo-surface)",
        border: "1px solid var(--emo-border)",
        boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
      }}
    >
      <div
        className="flex items-center gap-1.5 px-2 py-1.5"
        style={{
          borderBottom: "1px solid var(--emo-border)",
          background: "var(--emo-subtle-bg, var(--emo-surface))",
        }}
      >
        <FileCode2 size={12} className="flex-shrink-0" style={{ color: "var(--emo-text-muted)" }} />
        <div
          className="flex-1 min-w-0 flex items-center gap-1.5 px-2 py-0.5 rounded-full"
          style={{
            background: "var(--emo-surface)",
            border: "1px solid var(--emo-border)",
          }}
        >
          <Globe size={10} className="flex-shrink-0" style={{ color: "var(--emo-text-muted)" }} />
          <span
            className="flex-1 min-w-0 truncate text-[10px] font-code"
            style={{ color: "var(--emo-text)" }}
            title={path || displayTitle}
          >
            {displayTitle}
          </span>
        </div>
      </div>

      <div
        className="relative"
        style={{
          background: "var(--emo-preview-bg)",
          boxShadow: "inset 0 2px 8px rgba(0,0,0,0.08)",
        }}
      >
        <iframe
          ref={iframeRef}
          title={path || displayTitle}
          src="about:blank"
          onLoad={handleIframeLoad}
          className="w-full border-0 block"
          style={{
            height: compact ? 220 : 360,
            background: "#fff",
          }}
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      <p
        className="text-[9px] px-2 py-1 flex items-center gap-1"
        style={{ color: "var(--emo-text-muted)", borderTop: "1px solid var(--emo-border)" }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse"
          style={{ background: "var(--mode-color)" }}
          aria-hidden
        />
        Aperçu HTML en direct
        {path && (
          <span className="truncate opacity-70 font-code" title={path}>
            · {path}
          </span>
        )}
      </p>
    </div>
  );
}
