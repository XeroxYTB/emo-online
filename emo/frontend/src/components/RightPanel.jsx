import React, { useState, useEffect } from "react";
import { Activity, FolderTree, Brain, Settings, X, Globe, KeyRound, Compass, Sparkles } from "lucide-react";
import FileExplorer from "./FileExplorer";
import MemoryPanel from "./MemoryPanel";
import AgentSettingsPanel from "./AgentSettingsPanel";
import LLMKeysPanel from "./LLMKeysPanel";
import BrowserPanel from "./BrowserPanel";
import EmoIdentityPanel from "./EmoIdentityPanel";
import SquarePreviewFrame from "./SquarePreviewFrame";
import ToolCallCard from "./ToolCallCard";

const BASE_TABS = [
  { id: "site", label: "Site", icon: Globe },
  { id: "browser", label: "Web", icon: Compass },
  { id: "keys", label: "Clés IA", icon: KeyRound },
  { id: "activity", label: "Activité", icon: Activity },
  { id: "files", label: "Fichiers", icon: FolderTree },
  { id: "memory", label: "Mémoire", icon: Brain },
  { id: "settings", label: "Agent", icon: Settings },
];

export default function RightPanel({
  tools,
  agentOnline,
  onRefreshStatus,
  onClose,
  browserFrames = [],
  reflectNotes = [],
  filePreview = null,
  isAdmin = false,
  activeTab,
  onTabChange,
}) {
  const [tab, setTab] = useState(activeTab || "site");
  const TABS = isAdmin
    ? [...BASE_TABS.slice(0, 3), { id: "emo", label: "Émo", icon: Sparkles }, ...BASE_TABS.slice(3)]
    : BASE_TABS;

  useEffect(() => {
    if (activeTab && activeTab !== tab) setTab(activeTab);
  }, [activeTab]);

  const selectTab = (id) => {
    setTab(id);
    onTabChange?.(id);
  };

  return (
    <aside
      data-testid="right-panel"
      className="hidden lg:flex w-[420px] flex-shrink-0 h-full flex-col glass-panel"
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
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition"
                style={{
                  color: active ? "#fff" : "var(--emo-text-muted)",
                  background: active ? "rgba(255,255,255,0.06)" : "transparent",
                }}
              >
                <Icon size={12} style={{ color: active ? "var(--mode-color)" : "currentColor" }} />
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
        {tab === "site" && (
          <div className="h-full overflow-y-auto scrollbar-thin p-4 flex flex-col items-center justify-center">
            <SquarePreviewFrame
              kind="iframe"
              url="https://xeroxytb.com"
              title="Emo Online"
              subtitle="https://xeroxytb.com"
              testId="site-preview-iframe"
            />
          </div>
        )}
        {tab === "browser" && <BrowserPanel frames={browserFrames} reflectNotes={reflectNotes} />}
        {tab === "emo" && isAdmin && <EmoIdentityPanel />}
        {tab === "keys" && <LLMKeysPanel />}
        {tab === "activity" && <ActivityTab tools={tools} agentOnline={agentOnline} />}
        {tab === "files" && <FileExplorer agentOnline={agentOnline} externalPreview={filePreview} />}
        {tab === "memory" && <MemoryPanel />}
        {tab === "settings" && (
          <div className="p-4 overflow-y-auto h-full scrollbar-thin">
            <AgentSettingsPanel agentOnline={agentOnline} onRefreshStatus={onRefreshStatus} />
          </div>
        )}
      </div>
    </aside>
  );
}

const ActivityTab = ({ tools, agentOnline }) => {
  return (
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
          Quand Émo utilise un outil (fichiers, shell, web…), l&apos;activité s&apos;affiche ici en direct.
        </p>
      ) : (
        <div className="space-y-1">
          {tools.map((t) => <ToolCallCard key={t.id} event={t} />)}
        </div>
      )}
    </div>
  );
};
