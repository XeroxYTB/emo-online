import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { Brain, Trash2, Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function MemoryPanel() {
  const [memories, setMemories] = useState([]);
  const [adding, setAdding] = useState(false);
  const [newContent, setNewContent] = useState("");

  const refresh = async () => {
    const r = await http.get("/memories");
    setMemories(r.data);
  };

  useEffect(() => { refresh(); }, []);

  const create = async () => {
    if (!newContent.trim()) return;
    await http.post("/memories", { content: newContent.trim() });
    setNewContent("");
    setAdding(false);
    refresh();
  };

  const remove = async (id) => {
    await http.delete(`/memories/${id}`);
    refresh();
    toast.success("Mémoire supprimée");
  };

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 space-y-3" data-testid="memory-panel">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={14} style={{ color: "var(--mode-color)" }} />
          <h3 className="font-heading text-sm">Mémoire long-terme</h3>
          <span className="text-[10px] text-muted-em">{memories.length}</span>
        </div>
        <button
          data-testid="add-memory-btn"
          onClick={() => setAdding(!adding)}
          className="p-1 rounded hover:bg-white/10"
        >
          <Plus size={14} />
        </button>
      </div>

      {adding && (
        <div className="space-y-2 p-3 rounded-xl glass-card">
          <textarea
            data-testid="memory-input"
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            rows={2}
            placeholder="Mémoire"
            className="w-full bg-black/40 border border-white/5 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-purple-500/40 resize-none"
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => { setAdding(false); setNewContent(""); }} className="text-xs text-muted-em px-2 py-1">
              annuler
            </button>
            <button
              data-testid="memory-save-btn"
              onClick={create}
              className="text-xs px-3 py-1 rounded-lg"
              style={{ background: "var(--mode-color)", color: "#0A0510" }}
            >
              ajouter
            </button>
          </div>
        </div>
      )}

      {memories.length === 0 && !adding && (
        <p className="text-xs text-muted-em text-center pt-8">
          Aucune mémoire enregistrée. Émo apprendra de tes conversations automatiquement.
        </p>
      )}

      {memories.map((m) => (
        <div
          key={m.memory_id}
          data-testid={`memory-${m.memory_id}`}
          className="group p-3 rounded-xl glass-card text-xs flex items-start gap-2"
        >
          {m.source === "auto" ? (
            <Sparkles size={11} className="mt-0.5 flex-shrink-0" style={{ color: "var(--mode-color)" }} />
          ) : (
            <Brain size={11} className="mt-0.5 flex-shrink-0 opacity-50" />
          )}
          <p className="flex-1 leading-relaxed text-secondary-em">{m.content}</p>
          <button
            data-testid={`memory-delete-${m.memory_id}`}
            onClick={() => remove(m.memory_id)}
            className="opacity-0 group-hover:opacity-100 transition p-0.5 text-muted-em hover:text-red-400"
          >
            <Trash2 size={11} />
          </button>
        </div>
      ))}
    </div>
  );
}
