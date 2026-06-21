import React, { useEffect, useState } from "react";
import { http, BACKEND_URL } from "../lib/api";
import { KeyRound, RefreshCw, Save, Sparkles, Brain, Bug, Package, Download, ShieldCheck, CreditCard, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import EmoIdentityPanel from "./EmoIdentityPanel";
import MemoryPanel from "./MemoryPanel";
import DebugWindow from "./DebugWindow";
import FeedbackSessionsPanel from "./FeedbackSessionsPanel";

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
  const [stripe, setStripe] = useState({});
  const [stripeDraft, setStripeDraft] = useState({});
  const [stripeLoading, setStripeLoading] = useState(false);
  const [stripeSaving, setStripeSaving] = useState(false);

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

  const loadStripe = async () => {
    setStripeLoading(true);
    try {
      const r = await http.get("/admin/settings");
      setStripe(r.data || {});
      setStripeDraft({});
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Chargement Stripe impossible");
    } finally {
      setStripeLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "stripe") loadStripe();
  }, [tab]);

  const saveStripe = async () => {
    if (!Object.keys(stripeDraft).length) return;
    setStripeSaving(true);
    try {
      await http.patch("/admin/settings", stripeDraft);
      toast.success("Liens Stripe enregistrés");
      setStripeDraft({});
      await loadStripe();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Erreur");
    } finally {
      setStripeSaving(false);
    }
  };

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
    { id: "stripe", label: "Stripe", icon: CreditCard },
    { id: "feedback", label: "Retours utilisateurs", icon: MessageSquare },
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
                background: active ? "var(--emo-admin-bg)" : "var(--emo-subtle-bg)",
                color: active ? "var(--emo-admin-text)" : "var(--emo-text-secondary)",
                border: `1px solid ${active ? "var(--emo-warning-border)" : "var(--emo-border)"}`,
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
            <button type="button" onClick={loadKeys} className="p-1.5 rounded em-hover text-muted-em">
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
                  className="w-full px-3 py-2 rounded-lg text-xs font-code em-input focus:border-amber-500/40"
                />
              </div>
            );
          })}
          <button
            type="button"
            onClick={saveKeys}
            disabled={saving || !Object.keys(draft).length}
            className="w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 emo-alert-warning"
          >
            <Save size={14} /> {saving ? "Enregistrement…" : "Enregistrer les clés"}
          </button>
        </div>
      )}

      {tab === "stripe" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-em">Liens Payment Links Stripe par offre (Basic / Premium / Ultra).</p>
            <button type="button" onClick={loadStripe} className="p-1.5 rounded em-hover text-muted-em">
              <RefreshCw size={14} className={stripeLoading ? "animate-spin" : ""} />
            </button>
          </div>
          {[
            { id: "stripe_basic_link", label: "Basic", hint: "https://buy.stripe.com/..." },
            { id: "stripe_premium_link", label: "Premium", hint: "https://buy.stripe.com/..." },
            { id: "stripe_ultra_link", label: "Ultra", hint: "https://buy.stripe.com/..." },
            { id: "stripe_payment_link", label: "Paiement unique (legacy)", hint: "Optionnel" },
            { id: "stripe_subscription_link", label: "Abonnement (legacy)", hint: "Optionnel" },
          ].map((row) => (
            <div key={row.id} className="space-y-1">
              <label className="text-[11px] text-muted-em">{row.label}</label>
              <input
                type="url"
                placeholder={stripe[row.id] || row.hint}
                value={stripeDraft[row.id] ?? ""}
                onChange={(e) => setStripeDraft((d) => ({ ...d, [row.id]: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg text-xs font-code em-input focus:border-amber-500/40"
              />
              {stripe[row.id] && !stripeDraft[row.id] && (
                <p className="text-[10px] text-muted-em truncate">Actuel : {stripe[row.id]}</p>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={saveStripe}
            disabled={stripeSaving || !Object.keys(stripeDraft).length}
            className="w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 emo-btn-soft"
          >
            <Save size={14} /> {stripeSaving ? "Enregistrement…" : "Enregistrer les liens Stripe"}
          </button>
        </div>
      )}

      {tab === "feedback" && <FeedbackSessionsPanel />}

      {tab === "emo" && <EmoIdentityPanel />}
      {tab === "memory" && <MemoryPanel />}
      {tab === "system" && (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setDebugOpen(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm emo-btn-soft"
            style={{ color: "var(--emo-link)" }}
          >
            <Bug size={14} /> Console debug LLM / agent
          </button>
          <button
            type="button"
            onClick={() => {
              const base = BACKEND_URL || window.location.origin;
              window.open(`${base}/api/admin/project-export`, "_blank");
            }}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm emo-alert-success"
          >
            <Download size={14} /> Export code source
          </button>
          <div className="flex gap-2">
            <a href="https://dashboard.stripe.com/payments" target="_blank" rel="noreferrer" className="flex-1 text-center py-2 rounded-lg text-[11px] emo-btn-soft">Stripe</a>
            <a href="https://huggingface.co/spaces/Xroxx/emo-online-api/settings" target="_blank" rel="noreferrer" className="flex-1 text-center py-2 rounded-lg text-[11px] emo-btn-soft">HF Space</a>
          </div>
        </div>
      )}

      {debugOpen && (
        <DebugWindow events={debugEvents || []} onClose={() => setDebugOpen(false)} onClearEvents={onClearDebugEvents} />
      )}
    </div>
  );
}
