import React from "react";
import { Plus, MessageSquare, Trash2, Pencil, LogOut, ChevronLeft, ChevronRight, Settings, X } from "lucide-react";
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
        className={`emo-sidebar w-14 emo-panel-flat ${mobile ? "flex" : "hidden md:flex"} items-center py-4`}
      >
        <button
          data-testid="sidebar-expand-btn"
          onClick={onToggleCollapsed}
          className="emo-icon-btn mb-4"
          title="Déplier"
        >
          <ChevronRight size={16} />
        </button>
        <EmoLogo size="sm" showText={false} className="mb-4" />
        <button
          data-testid="new-conversation-mini-btn"
          onClick={onNew}
          className="emo-icon-btn mb-2"
          title="Nouvelle conversation"
        >
          <Plus size={16} />
        </button>
        <div className="flex-1" />
        <button
          data-testid="user-menu-mini-btn"
          onClick={onOpenProfile}
          className="rounded-full hover:scale-105 transition"
        >
          {user?.picture ? (
            <img src={user.picture} alt="" className="w-8 h-8 rounded-full ring-2 ring-transparent hover:ring-[var(--emo-accent-border)]" />
          ) : (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold"
              style={{ background: "var(--emo-accent-soft)", color: "var(--emo-accent)" }}
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
      className={`emo-sidebar w-72 emo-panel-flat ${mobile ? "flex emo-sidebar-mobile" : "hidden md:flex"}`}
    >
      <div className="px-4 py-3.5 flex items-center justify-between border-b" style={{ borderColor: "var(--emo-border)" }}>
        <EmoLogo size="sm" showSubtitle={false} />
        <button
          data-testid="sidebar-collapse-btn"
          onClick={onToggleCollapsed}
          className="emo-icon-btn"
          title={mobile ? "Fermer" : "Replier"}
          aria-label={mobile ? "Fermer le menu" : "Replier la barre latérale"}
        >
          {mobile ? <X size={16} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      <div className="px-3 pt-3">
        <button
          data-testid="new-conversation-btn"
          onClick={onNew}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium emo-btn-primary"
        >
          <Plus size={16} />
          <span>Nouvelle conversation</span>
        </button>
      </div>

      <div className="mt-3 flex-1 overflow-y-auto scrollbar-thin px-2 pb-3">
        {Object.keys(groups).length === 0 && (
          <p className="text-xs text-muted-em px-3 mt-8 text-center">Aucune conversation</p>
        )}
        {Object.entries(groups).map(([label, items]) => (
          <div key={label} className="mt-4">
            <p className="text-[10px] font-semibold tracking-wide uppercase text-muted-em px-3 mb-1.5">{label}</p>
            {items.map((c) => (
              <ConversationRow
                key={c.conversation_id}
                conv={c}
                active={c.conversation_id === activeId}
                onSelect={() => onSelect(c.conversation_id)}
                onRename={onRename}
                onDelete={onDelete}
                mobile={mobile}
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
              className="w-full flex items-center gap-3 px-2.5 py-2.5 rounded-xl em-hover-subtle transition"
            >
              {user?.picture ? (
                <img src={user.picture} alt="" className="w-9 h-9 rounded-xl object-cover" />
              ) : (
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold"
                  style={{ background: "var(--emo-accent-soft)", color: "var(--emo-accent)" }}
                >
                  {user?.name?.[0]?.toUpperCase() || "?"}
                </div>
              )}
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium truncate">{user?.name || "Anonyme"}</p>
                <p className="text-[11px] text-muted-em truncate">{user?.email}</p>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56" style={{ background: "var(--emo-surface)", borderColor: "var(--emo-border)" }}>
            <DropdownMenuItem data-testid="open-profile-btn" onClick={onOpenProfile} className="cursor-pointer">
              <Settings size={14} className="mr-2" />
              Paramètres
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

const ConversationRow = ({ conv, active, onSelect, onRename, onDelete, mobile = false }) => {
  return (
    <div
      data-testid={`conv-row-${conv.conversation_id}`}
      onClick={onSelect}
      className="relative group flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer text-sm transition mb-0.5"
      style={{
        background: active ? "var(--emo-active-bg)" : "transparent",
        color: active ? "var(--emo-text)" : "var(--emo-text-secondary)",
        borderLeft: active ? "3px solid var(--mode-color)" : "3px solid transparent",
      }}
    >
      <MessageSquare size={14} className="opacity-50 flex-shrink-0" />
      <span className="flex-1 truncate">{conv.title || "Sans titre"}</span>
      <div className={`${mobile ? "flex" : "hidden group-hover:flex"} items-center gap-0.5 flex-shrink-0`}>
        <button
          data-testid={`rename-${conv.conversation_id}`}
          onClick={(e) => {
            e.stopPropagation();
            const t = window.prompt("Nouveau titre :", conv.title || "");
            if (t && t.trim()) onRename(conv.conversation_id, t.trim());
          }}
          className="emo-conv-action-btn em-hover-subtle text-muted-em"
          aria-label="Renommer"
        >
          <Pencil size={12} />
        </button>
        <button
          data-testid={`delete-${conv.conversation_id}`}
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm("Supprimer cette conversation ?")) onDelete(conv.conversation_id);
          }}
          className="emo-conv-action-btn em-hover-subtle text-muted-em hover:!text-red-400"
          aria-label="Supprimer"
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
