import React, { useState } from "react";
import { Activity, FolderTree, Brain, Settings, X } from "lucide-react";
import FileExplorer from "./FileExplorer";
import MemoryPanel from "./MemoryPanel";
import AgentSettingsPanel from "./AgentSettingsPanel";
import ToolCallCard from "./ToolCallCard";

const TABS = [
  { id: "activity", label: "Activité", icon: Activity },
  { id: "files", label: "Fichiers", icon: FolderTree },
  { id: "memory", label: "Mémoire", icon: Brain },
  { id: "settings", label: "Agent", icon: Settings },
];

export default function RightPanel({ tools, agentOnline, onRefreshStatus, onClose }) {
  const [tab, setTab] = useState("activity");

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
                onClick={() => setTab(t.id)}
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
        {tab === "activity" && <ActivityTab tools={tools} agentOnline={agentOnline} />}
        {tab === "files" && <FileExplorer agentOnline={agentOnline} />}
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
        Agent {agentOnline ? "en ligne" : "hors ligne"} · {tools.length} appels
      </div>
      {tools.length === 0 ? (
        <p className="text-xs text-muted-em text-center pt-8 px-4">
          Quand Émo utilise des outils (exec_shell, write_file…), ils apparaissent ici en temps réel.
        </p>
      ) : (
        <div className="space-y-1">
          {tools.map((t) => <ToolCallCard key={t.id} event={t} />)}
        </div>
      )}
    </div>
  );
};
