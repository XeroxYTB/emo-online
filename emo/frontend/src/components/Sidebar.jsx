import React from "react";
import { Plus, MessageSquare, Trash2, Pencil, LogOut, ChevronLeft, ChevronRight, User as UserIcon, Settings } from "lucide-react";
import EmoLogo from "./EmoLogo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";

export const Sidebar = ({
  conversations,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
  user,
  onLogout,
  collapsed,
  onToggleCollapsed,
  onOpenProfile,
  mobile = false,
}) => {
  const groups = groupByDate(conversations);

  if (collapsed) {
    return (
      <aside
        data-testid="sidebar-collapsed"
        className={`w-14 flex-shrink-0 h-full ${mobile ? "flex" : "hidden md:flex"} flex-col items-center py-4 glass-panel`}
        style={{ borderRight: "1px solid var(--emo-border)", borderRadius: 0 }}
      >
        <button
          data-testid="sidebar-expand-btn"
          onClick={onToggleCollapsed}
          className="p-2 rounded-lg em-hover text-muted-em transition mb-3"
          title="Déplier"
        >
          <ChevronRight size={16} />
        </button>
        <EmoLogo size="sm" showText={false} className="mb-3" />
        <button
          data-testid="new-conversation-mini-btn"
          onClick={onNew}
          className="p-2 rounded-lg mb-2 transition border"
          style={{ borderColor: "var(--emo-border)", color: "var(--emo-text-secondary)" }}
          title="Nouvelle conversation"
        >
          <Plus size={16} />
        </button>
        <div className="flex-1" />
        <button
          data-testid="user-menu-mini-btn"
          onClick={onOpenProfile}
          className="p-1 rounded-full hover:scale-105 transition"
        >
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
          ) : (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium"
              style={{ background: "var(--emo-accent-soft)", color: "var(--mode-color)" }}
            >
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
          )}
        </button>
      </aside>
    );
  }

  return (
    <aside
      data-testid="sidebar-container"
      className={`w-72 flex-shrink-0 h-full ${mobile ? "flex" : "hidden md:flex"} flex-col glass-panel`}
      style={{ borderRight: "1px solid var(--emo-border)", borderRadius: 0 }}
    >
      <div className="px-4 py-3 flex items-center justify-between border-b" style={{ borderColor: "var(--emo-border)" }}>
        <EmoLogo size="sm" showSubtitle={false} />
        <div className="flex items-center gap-1">
          <button
            data-testid="sidebar-collapse-btn"
            onClick={onToggleCollapsed}
            className="p-1.5 rounded em-hover text-muted-em transition"
            title="Replier"
          >
            <ChevronLeft size={14} />
          </button>
        </div>
      </div>

      <div className="px-3">
        <button
          data-testid="new-conversation-btn"
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium border transition-colors em-hover-subtle"
          style={{ borderColor: "var(--emo-border)" }}
        >
          <Plus size={16} className="text-muted-em" />
          <span>Nouvelle conversation</span>
        </button>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto scrollbar-thin px-2 pb-3">
        {Object.keys(groups).length === 0 && (
          <p className="text-xs text-muted-em px-3 mt-6">Aucune conversation</p>
        )}
        {Object.entries(groups).map(([label, items]) => (
          <div key={label} className="mt-3">
            <p className="text-[10px] tracking-[0.2em] uppercase text-muted-em px-3 mb-1">{label}</p>
            {items.map((c) => (
              <ConversationRow
                key={c.conversation_id}
                conv={c}
                active={c.conversation_id === activeId}
                onSelect={() => onSelect(c.conversation_id)}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="p-3 border-t" style={{ borderColor: "var(--emo-border)" }}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              data-testid="user-menu-btn"
              className="w-full flex items-center gap-3 px-2 py-2 rounded-xl em-hover-subtle transition"
            >
              {user?.picture ? (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium"
                  style={{ background: "var(--emo-accent-soft)", color: "var(--mode-color)" }}
                >
                  {user?.name?.[0]?.toUpperCase() || "?"}
                </div>
              )}
              <div className="flex-1 text-left">
                <p className="text-sm truncate">{user?.name || "Anonyme"}</p>
                <p className="text-[11px] text-muted-em truncate">{user?.email}</p>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56" style={{ background: "var(--emo-surface)", borderColor: "var(--emo-border)" }}>
            <DropdownMenuItem data-testid="open-profile-btn" onClick={onOpenProfile} className="cursor-pointer">
              <Settings size={14} className="mr-2" />
              Profil & abonnement
            </DropdownMenuItem>
            <DropdownMenuItem data-testid="logout-btn" onClick={onLogout} className="cursor-pointer">
              <LogOut size={14} className="mr-2" />
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
};

const ConversationRow = ({ conv, active, onSelect, onRename, onDelete }) => {
  return (
    <div
      data-testid={`conv-row-${conv.conversation_id}`}
      onClick={onSelect}
      className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition ${
        active ? "em-active" : "em-hover-subtle"
      }`}
    >
      <MessageSquare size={14} className="opacity-50 flex-shrink-0" />
      <span className="flex-1 truncate" style={{ color: active ? "var(--emo-text)" : "var(--emo-text-secondary)" }}>
        {conv.title || "Sans titre"}
      </span>
      <div className="hidden group-hover:flex items-center gap-1">
        <button
          data-testid={`rename-${conv.conversation_id}`}
          onClick={(e) => {
            e.stopPropagation();
            const t = window.prompt("Nouveau titre :", conv.title || "");
            if (t && t.trim()) onRename(conv.conversation_id, t.trim());
          }}
          className="p-1 hover:text-[var(--emo-text)] text-muted-em"
        >
          <Pencil size={12} />
        </button>
        <button
          data-testid={`delete-${conv.conversation_id}`}
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm("Supprimer cette conversation ?")) onDelete(conv.conversation_id);
          }}
          className="p-1 hover:text-red-400 text-muted-em"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
};

function groupByDate(items) {
  const groups = {};
  const today = new Date();
  for (const c of items) {
    const d = new Date(c.updated_at || c.created_at);
    const diff = Math.floor((today - d) / (1000 * 60 * 60 * 24));
    let label;
    if (diff <= 0) label = "Aujourd'hui";
    else if (diff <= 1) label = "Hier";
    else if (diff <= 7) label = "Cette semaine";
    else if (diff <= 30) label = "Ce mois-ci";
    else label = "Plus ancien";
    (groups[label] = groups[label] || []).push(c);
  }
  return groups;
}

export default Sidebar;
