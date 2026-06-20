import React, { useState, useEffect } from "react";
import { Activity, FolderTree, Bot, X } from "lucide-react";
import FileExplorer from "./FileExplorer";
import AgentSettingsPanel from "./AgentSettingsPanel";
import AgentPermissionsPanel from "./AgentPermissionsPanel";

const TABS = [
  { id: "files", label: "Fichiers", icon: FolderTree },
  { id: "activity", label: "Activité", icon: Activity },
  { id: "agent", label: "Agent", icon: Bot },
];

export default function RightPanel({
  tools,
  agentOnline,
  onRefreshStatus,
  onClose,
  filePreview = null,
  activeTab,
  onTabChange,
}) {
  const [tab, setTab] = useState(activeTab || "activity");

  useEffect(() => {
    if (activeTab && activeTab !== tab) setTab(activeTab);
  }, [activeTab, tab]);

  const selectTab = (id) => {
    setTab(id);
    onTabChange?.(id);
  };

  return (
    <aside
      data-testid="right-panel"
      className="hidden lg:flex w-[400px] flex-shrink-0 h-full flex-col glass-panel"
      style={{ borderLeft: "1px solid var(--emo-border)", borderRadius: 0 }}
    >
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-white/5">
        <div className="flex items-center gap-1">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = t.id === tab;
            return (
              <button
                key={t.id}
                data-testid={`right-tab-${t.id}`}
                onClick={() => selectTab(t.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                style={{
                  color: active ? "#fff" : "var(--emo-text-muted)",
                  background: active ? "rgba(255,255,255,0.06)" : "transparent",
                }}
              >
                <Icon size={13} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
                {t.label}
              </button>
            );
          })}
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10 text-muted-em" data-testid="right-panel-close">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === "activity" && <ActivityTab tools={tools} agentOnline={agentOnline} />}
        {tab === "files" && <FileExplorer agentOnline={agentOnline} externalPreview={filePreview} />}
        {tab === "agent" && (
          <div className="p-4 overflow-y-auto h-full scrollbar-thin space-y-4">
            <AgentSettingsPanel agentOnline={agentOnline} onRefreshStatus={onRefreshStatus} />
            <AgentPermissionsPanel agentOnline={agentOnline} />
          </div>
        )}
      </div>
    </aside>
  );
}

const ActivityTab = ({ tools, agentOnline }) => (
  <div className="h-full overflow-y-auto scrollbar-thin p-3" data-testid="activity-tab">
    <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-muted-em mb-3 px-1">
      <div
        className={`w-1.5 h-1.5 rounded-full ${agentOnline ? "bg-emerald-400" : "bg-zinc-600"}`}
        style={{ boxShadow: agentOnline ? "0 0 6px #34d39988" : "none" }}
      />
      Agent {agentOnline ? "connecté" : "hors ligne"} · {tools.length} action{tools.length !== 1 ? "s" : ""}
    </div>
    {tools.length === 0 ? (
      <p className="text-xs text-muted-em text-center pt-8 px-4">
        Actions en direct pendant que Émo travaille.
      </p>
    ) : (
      <div className="space-y-1">
        {tools.map((t) => (
          <div key={t.id} className="text-xs px-2 py-1.5 rounded-lg" style={{ background: "rgba(255,255,255,0.03)" }}>
            <span className="font-code text-[11px]" style={{ color: "var(--mode-color)" }}>{t.tool}</span>
            <span className="text-muted-em ml-2">{t.state === "executing" ? "…" : "ok"}</span>
          </div>
        ))}
      </div>
    )}
  </div>
);
