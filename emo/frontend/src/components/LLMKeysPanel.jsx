import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { ExternalLink, KeyRound, RefreshCw } from "lucide-react";

const KEY_LINKS = [
  { id: "openrouter", label: "OpenRouter", url: "https://openrouter.ai/keys", hint: "Modèles free (Llama, Gemma, Qwen)" },
  { id: "deepseek", label: "DeepSeek", url: "https://platform.deepseek.com/api_keys", hint: "Chat + R1 Reasoner" },
  { id: "groq", label: "Groq", url: "https://console.groq.com/keys", hint: "Llama / Gemma gratuit" },
  { id: "huggingface", label: "Hugging Face", url: "https://huggingface.co/settings/tokens", hint: "HF_TOKEN (Read)" },
  { id: "gemini", label: "Gemini", url: "https://aistudio.google.com/apikey", hint: "Google AI Studio" },
  { id: "openai", label: "OpenAI", url: "https://platform.openai.com/api-keys", hint: "GPT-4o mini" },
  { id: "anthropic", label: "Anthropic", url: "https://console.anthropic.com/settings/keys", hint: "Claude" },
];

export default function LLMKeysPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await http.get("/llm/status");
      setStatus(r.data);
    } catch (_) {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const live = status?.live || {};

  return (
    <div className="h-full overflow-y-auto scrollbar-thin p-4 space-y-4" data-testid="llm-keys-panel">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <KeyRound size={16} style={{ color: "var(--mode-color)" }} />
          <h3 className="text-sm font-semibold">Clés IA (prod)</h3>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="p-1.5 rounded-lg em-hover text-muted-em"
          title="Actualiser"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <p className="text-[11px] text-muted-em leading-relaxed">
        Configure localement avec{" "}
        <code className="text-[10px] px-1 rounded" style={{ background: "var(--emo-subtle-bg)" }}>scripts\setup-llm-keys.ps1</code>
        {" "}puis{" "}
        <code className="text-[10px] px-1 rounded" style={{ background: "var(--emo-subtle-bg)" }}>scripts\sync-hf-secrets.bat</code>
      </p>

      <div className="space-y-1.5">
        {KEY_LINKS.map((k) => {
          const configured = status?.[k.id];
          const row = live[k.id];
          const ok = configured && row?.ok === true;
          const bad = configured && row?.ok === false;
          const dot = !configured ? "emo-status-dot-offline" : ok ? "emo-status-dot-online" : bad ? "bg-red-500" : "bg-amber-500";
          return (
            <div
              key={k.id}
              className="flex items-center gap-2 px-2.5 py-2 rounded-xl text-xs"
              style={{ background: "var(--emo-subtle-bg)", border: "1px solid var(--emo-border)" }}
            >
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${dot}`} />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{k.label}</p>
                <p className="text-[10px] text-muted-em truncate">
                  {!configured ? "Clé absente sur HF" : bad ? (row.detail || "Erreur").slice(0, 60) : ok ? "Opérationnel" : "Clé présente"}
                </p>
              </div>
              <a
                href={k.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 rounded em-hover text-muted-em flex-shrink-0"
                title={k.hint}
              >
                <ExternalLink size={12} />
              </a>
            </div>
          );
        })}
      </div>

      <a
        href="https://huggingface.co/spaces/Xroxx/emo-online-api/settings"
        target="_blank"
        rel="noopener noreferrer"
        className="block text-center text-xs py-2.5 rounded-xl transition emo-btn-soft"
      >
        Ouvrir secrets HF Space →
      </a>
    </div>
  );
}
