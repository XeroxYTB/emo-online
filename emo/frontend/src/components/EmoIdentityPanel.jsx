import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { toast } from "sonner";
import { History, RotateCcw, Sparkles, ChevronDown, ChevronRight } from "lucide-react";

export default function EmoIdentityPanel() {
  const [loading, setLoading] = useState(true);
  const [sections, setSections] = useState({});
  const [editable, setEditable] = useState([]);
  const [limits, setLimits] = useState({});
  const [versions, setVersions] = useState([]);
  const [openSection, setOpenSection] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [cur, saves] = await Promise.all([
        http.get("/admin/emo-identity"),
        http.get("/admin/emo-identity/versions"),
      ]);
      setSections(cur.data.sections || {});
      setEditable(cur.data.editable || []);
      setLimits(cur.data.limits || {});
      setVersions(saves.data.versions || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Chargement identité impossible");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const restore = async (versionId) => {
    if (!window.confirm("Restaurer cette version ? Une autobackup sera créée avant.")) return;
    try {
      await http.post("/admin/emo-identity/restore", { version_id: versionId });
      toast.success("Version restaurée");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Restauration échouée");
    }
  };

  if (loading) {
    return <p className="p-6 text-xs text-muted-em text-center">Chargement…</p>;
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-3 space-y-4" data-testid="emo-identity-panel">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-muted-em">
        <Sparkles size={12} style={{ color: "var(--mode-color)" }} />
        Auto-édition · {limits.max_edits_per_day || 12} max/jour
      </div>

      <div className="space-y-2">
        {editable.map((key) => {
          const meta = sections[key] || {};
          const isOpen = openSection === key;
          return (
            <div
              key={key}
              className="rounded-xl overflow-hidden"
              style={{ border: "1px solid rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.25)" }}
            >
              <button
                type="button"
                onClick={() => setOpenSection(isOpen ? null : key)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs hover:bg-white/[0.03]"
              >
                {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span className="font-code" style={{ color: "var(--mode-color)" }}>{key}</span>
                {meta.is_customized && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-200">custom</span>
                )}
                <span className="ml-auto text-[10px] text-muted-em">{meta.char_count || 0} chars</span>
              </button>
              {isOpen && meta.preview && (
                <pre className="px-3 pb-3 text-[10px] leading-relaxed whitespace-pre-wrap font-code text-secondary-em max-h-40 overflow-y-auto scrollbar-thin">
                  {meta.preview}
                </pre>
              )}
            </div>
          );
        })}
      </div>

      <div>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-em mb-2">
          <History size={12} />
          Sauvegardes ({versions.length})
        </div>
        <div className="space-y-1">
          {versions.length === 0 ? (
            <p className="text-[11px] text-muted-em px-1">Aucune sauvegarde pour l&apos;instant.</p>
          ) : (
            versions.map((v) => (
              <div
                key={v.version_id}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px]"
                style={{ background: "rgba(255,255,255,0.03)" }}
              >
                <span className="font-code text-[10px] truncate flex-1" title={v.reason}>
                  {v.kind} · {(v.reason || "").slice(0, 48)}
                </span>
                <span className="text-[9px] text-muted-em flex-shrink-0">
                  {v.created_at ? new Date(v.created_at).toLocaleString("fr-FR") : ""}
                </span>
                <button
                  type="button"
                  onClick={() => restore(v.version_id)}
                  className="p-1 rounded hover:bg-white/10 text-emerald-300 flex-shrink-0"
                  title="Restaurer"
                >
                  <RotateCcw size={11} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
