import React, { useEffect, useState } from "react";
import { http, BACKEND_URL } from "../lib/api";
import { KeyRound, RefreshCw, Save, Sparkles, Brain, Bug, Package, Download, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import EmoIdentityPanel from "./EmoIdentityPanel";
import MemoryPanel from "./MemoryPanel";
import DebugWindow from "./DebugWindow";

const KEY_META = [
  { id: "groq", label: "Groq", hint: "Llama / Gemma gratuit" },
  { id: "openrouter", label: "OpenRouter", hint: "Modèles :free" },
  { id: "huggingface", label: "Hugging Face", hint: "HF_TOKEN" },
  { id: "gemini", label: "Gemini", hint: "Google AI Studio" },
  { id: "openai", label: "OpenAI", hint: "ChatGPT" },
  { id: "anthropic", label: "Anthropic", hint: "Claude" },
  { id: "deepseek", label: "DeepSeek", hint: "Chat / R1" },
];

export default function AdminPanel({ debugEvents, onClearDebugEvents }) {
  const [tab, setTab] = useState("keys");
  const [keys, setKeys] = useState({});
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);

  const loadKeys = async () => {
    setLoading(true);
    try {
      const r = await http.get("/admin/llm-keys");
      setKeys(r.data?.keys || {});
      setDraft({});
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Accès admin requis");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadKeys(); }, []);

  const saveKeys = async () => {
    if (!Object.keys(draft).length) return;
    setSaving(true);
    try {
      await http.patch("/admin/llm-keys", { keys: draft });
      toast.success("Clés enregistrées");
      setDraft({});
      await loadKeys();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Erreur");
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: "keys", label: "Clés IA", icon: KeyRound },
    { id: "emo", label: "Émo", icon: Sparkles },
    { id: "memory", label: "Mémoire", icon: Brain },
    { id: "system", label: "Système", icon: ShieldCheck },
  ];

  return (
    <div className="space-y-4" data-testid="admin-panel">
      <div className="flex flex-wrap gap-1.5">
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition"
              style={{
                background: active ? "rgba(245,158,11,0.15)" : "rgba(255,255,255,0.03)",
                color: active ? "#fbbf24" : "var(--emo-text-secondary)",
                border: `1px solid ${active ? "rgba(245,158,11,0.35)" : "rgba(255,255,255,0.06)"}`,
              }}
            >
              <Icon size={12} /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === "keys" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-em">Modifiables depuis le site — stockées chiffrées côté serveur.</p>
            <button type="button" onClick={loadKeys} className="p-1.5 rounded hover:bg-white/10 text-muted-em">
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
          {KEY_META.map((k) => {
            const row = keys[k.id] || {};
            const value = draft[k.id] ?? "";
            return (
              <div key={k.id} className="space-y-1">
                <label className="text-[11px] text-muted-em">{k.label}</label>
                <input
                  type="password"
                  placeholder={row.configured ? row.preview || "•••• configurée" : `Coller clé ${k.hint}`}
                  value={value}
                  onChange={(e) => setDraft((d) => ({ ...d, [k.id]: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg text-xs font-code bg-black/40 border border-white/10 focus:outline-none focus:border-amber-500/40"
                />
              </div>
            );
          })}
          <button
            type="button"
            onClick={saveKeys}
            disabled={saving || !Object.keys(draft).length}
            className="w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50"
            style={{ background: "rgba(245,158,11,0.2)", color: "#fbbf24", border: "1px solid rgba(245,158,11,0.35)" }}
          >
            <Save size={14} /> {saving ? "Enregistrement…" : "Enregistrer les clés"}
          </button>
        </div>
      )}

      {tab === "emo" && <EmoIdentityPanel />}
      {tab === "memory" && <MemoryPanel />}
      {tab === "system" && (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setDebugOpen(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm"
            style={{ background: "rgba(6,182,212,0.12)", border: "1px solid rgba(6,182,212,0.25)", color: "#67e8f9" }}
          >
            <Bug size={14} /> Debug LLM / agent
          </button>
          <button
            type="button"
            onClick={() => {
              const base = BACKEND_URL || window.location.origin;
              window.open(`${base}/api/admin/project-export`, "_blank");
            }}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm"
            style={{ background: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.25)", color: "#6ee7b7" }}
          >
            <Download size={14} /> Export code source
          </button>
          <div className="flex gap-2">
            <a href="https://dashboard.stripe.com/payments" target="_blank" rel="noreferrer" className="flex-1 text-center py-2 rounded-lg text-[11px]" style={{ background: "rgba(99,91,255,0.15)", color: "#a5b4fc" }}>Stripe</a>
            <a href="https://huggingface.co/spaces/Xroxx/emo-online-api/settings" target="_blank" rel="noreferrer" className="flex-1 text-center py-2 rounded-lg text-[11px]" style={{ background: "rgba(168,85,247,0.12)", color: "#d8b4fe" }}>HF Space</a>
          </div>
        </div>
      )}

      {debugOpen && (
        <DebugWindow events={debugEvents || []} onClose={() => setDebugOpen(false)} onClearEvents={onClearDebugEvents} />
      )}
    </div>
  );
}
