import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { MessageSquare, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function FeedbackSessionsPanel() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await http.get("/admin/feedback-sessions");
      setSessions(r.data?.sessions || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Chargement impossible");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <RefreshCw size={18} className="animate-spin text-muted-em" />
      </div>
    );
  }

  if (!sessions.length) {
    return (
      <p className="text-xs text-muted-em py-4">
        Aucune session de retours pour l&apos;instant. Les réponses apparaîtront ici chaque mois.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-em">Sessions mensuelles — ~50 % des utilisateurs sollicités.</p>
        <button type="button" onClick={load} className="p-1.5 rounded em-hover text-muted-em">
          <RefreshCw size={14} />
        </button>
      </div>
      {sessions.map((s) => (
        <div
          key={s.month}
          className="rounded-xl p-3 space-y-2"
          style={{ background: "var(--emo-subtle-bg)", border: "1px solid var(--emo-border)" }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <MessageSquare size={14} style={{ color: "var(--emo-accent)" }} />
              <span className="text-sm font-medium" style={{ color: "var(--emo-text)" }}>
                {s.month}
              </span>
            </div>
            <span className="text-[10px] text-muted-em whitespace-nowrap">
              {s.total_responses} rép. · {s.total_shown} sollicités
            </span>
          </div>
          <p className="text-xs text-secondary-em">{s.summary}</p>
          {s.sample_responses?.length > 0 && (
            <ul className="space-y-1.5 pt-1">
              {s.sample_responses.map((resp, i) => (
                <li
                  key={i}
                  className="text-[11px] px-2.5 py-2 rounded-lg font-code leading-relaxed"
                  style={{ background: "var(--emo-surface)", color: "var(--emo-text-secondary)" }}
                >
                  « {resp.length > 200 ? `${resp.slice(0, 200)}…` : resp} »
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
