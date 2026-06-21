import React, { useState, useEffect } from "react";
import { Activity, FolderTree, Bot, X } from "lucide-react";
import FileExplorer from "./FileExplorer";
import AgentSettingsPanel from "./AgentSettingsPanel";
import AgentPermissionsPanel from "./AgentPermissionsPanel";
import BrowserPanel from "./BrowserPanel";

const TABS = [
  { id: "activity", label: "Activité", icon: Activity },
  { id: "files", label: "Fichiers", icon: FolderTree },
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
  onBrowserFrameUpdate,
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
      className="hidden md:flex w-[min(460px,38vw)] min-w-[360px] flex-shrink-0 h-full flex-col emo-panel-flat"
      style={{ borderLeft: "1px solid var(--emo-border)", background: "var(--emo-surface)" }}
    >
      <div className="emo-panel-tabs flex-shrink-0">
        <div className="flex items-center gap-1 flex-1">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = t.id === tab;
            return (
              <button
                key={t.id}
                data-testid={`right-tab-${t.id}`}
                onClick={() => selectTab(t.id)}
                className="emo-panel-tab"
                data-active={active ? "true" : "false"}
              >
                <Icon size={13} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
                {t.label}
              </button>
            );
          })}
        </div>
        {onClose && (
          <button onClick={onClose} className="emo-icon-btn ml-1" data-testid="right-panel-close">
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
            onBrowserFrameUpdate={onBrowserFrameUpdate}
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

const ActivityTab = ({ tools, agentOnline, browserFrames, reflectNotes, onBrowserFrameUpdate }) => (
  <div className="h-full flex flex-col overflow-hidden" data-testid="activity-tab">
    <div
      className="flex-shrink-0 flex items-center gap-2 text-[10px] uppercase tracking-wide font-medium text-muted-em px-4 py-2.5"
      style={{ borderBottom: "1px solid var(--emo-border)", background: "var(--emo-bg-subtle)" }}
    >
      <div
        className={`w-2 h-2 rounded-full ${agentOnline ? "emo-status-dot-online" : "emo-status-dot-offline"}`}
      />
      Agent {agentOnline ? "connecté" : "hors ligne"}
      {tools.length > 0 && (
        <span className="normal-case tracking-normal opacity-70 font-normal">
          · {tools.length} action{tools.length !== 1 ? "s" : ""}
        </span>
      )}
    </div>

    <div className="flex-1 min-h-0">
      <BrowserPanel frames={browserFrames} reflectNotes={reflectNotes} onFrameUpdate={onBrowserFrameUpdate} />
    </div>

    {tools.length > 0 && (
      <div
        className="flex-shrink-0 max-h-32 overflow-y-auto scrollbar-thin p-2.5 space-y-1.5"
        style={{ borderTop: "1px solid var(--emo-border)", background: "var(--emo-bg-subtle)" }}
      >
        {tools.slice(-8).map((t) => (
          <div
            key={t.id}
            className="text-xs px-3 py-2 rounded-xl flex items-center justify-between"
            style={{ background: "var(--emo-surface)", border: "1px solid var(--emo-border)" }}
          >
            <span className="font-code text-[11px] font-medium" style={{ color: "var(--mode-color)" }}>{t.tool}</span>
            <span className="text-muted-em text-[10px]">
              {t.state === "executing" ? "en cours…" : t.state === "error" ? "erreur" : "ok"}
            </span>
          </div>
        ))}
      </div>
    )}
  </div>
);
