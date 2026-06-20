import React, { useState, useEffect } from "react";
import { Activity, FolderTree, Bot, X } from "lucide-react";
import FileExplorer from "./FileExplorer";
import AgentSettingsPanel from "./AgentSettingsPanel";
import AgentPermissionsPanel from "./AgentPermissionsPanel";
import BrowserPanel from "./BrowserPanel";

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
  browserFrames = [],
  reflectNotes = [],
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
      className="hidden lg:flex w-[min(460px,38vw)] min-w-[360px] flex-shrink-0 h-full flex-col glass-panel"
      style={{ borderLeft: "1px solid var(--emo-border)", borderRadius: 0 }}
    >
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 em-border-b">
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
                  color: active ? "var(--emo-text)" : "var(--emo-text-muted)",
                  background: active ? "var(--emo-tab-active-bg)" : "transparent",
                }}
              >
                <Icon size={13} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
                {t.label}
              </button>
            );
          })}
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 rounded em-hover text-muted-em" data-testid="right-panel-close">
            <X size={14} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === "activity" && (
          <ActivityTab
            tools={tools}
            agentOnline={agentOnline}
            browserFrames={browserFrames}
            reflectNotes={reflectNotes}
          />
        )}
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

const ActivityTab = ({ tools, agentOnline, browserFrames, reflectNotes }) => (
  <div className="h-full flex flex-col overflow-hidden" data-testid="activity-tab">
    <div className="flex-shrink-0 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-muted-em px-3 py-2 em-border-b">
      <div
        className={`w-1.5 h-1.5 rounded-full ${agentOnline ? "emo-status-dot-online" : "emo-status-dot-offline"}`}
      />
      Agent {agentOnline ? "connecté" : "hors ligne"}
      {tools.length > 0 && (
        <span className="normal-case tracking-normal opacity-70">
          · {tools.length} action{tools.length !== 1 ? "s" : ""}
        </span>
      )}
    </div>

    <div className="flex-1 min-h-0">
      <BrowserPanel frames={browserFrames} reflectNotes={reflectNotes} />
    </div>

    {tools.length > 0 && (
      <div className="flex-shrink-0 max-h-28 overflow-y-auto scrollbar-thin em-border-t p-2 space-y-1">
        {tools.slice(-8).map((t) => (
          <div key={t.id} className="text-xs px-2 py-1 rounded-lg" style={{ background: "var(--emo-subtle-bg)" }}>
            <span className="font-code text-[11px]" style={{ color: "var(--mode-color)" }}>{t.tool}</span>
            <span className="text-muted-em ml-2">
              {t.state === "executing" ? "…" : t.state === "error" ? "erreur" : "ok"}
            </span>
          </div>
        ))}
      </div>
    )}
  </div>
);
