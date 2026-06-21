import React, { useState } from "react";
import { http } from "../lib/api";
import { MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function FeedbackPrompt({ open, onClose }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [skipping, setSkipping] = useState(false);

  if (!open) return null;

  const skip = async () => {
    setSkipping(true);
    try {
      await http.post("/feedback/skip");
      onClose?.();
    } catch {
      onClose?.();
    } finally {
      setSkipping(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    const value = text.trim();
    if (!value) {
      toast.error("Écris quelques mots ou passe cette étape");
      return;
    }
    setSubmitting(true);
    try {
      await http.post("/feedback", { response: value });
      toast.success("Merci pour ton retour !");
      onClose?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Erreur envoi");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      data-testid="feedback-prompt"
      className="fixed inset-0 z-[55] flex items-center justify-center px-4 overflow-y-auto py-8"
      style={{ background: "var(--emo-paywall-overlay)", backdropFilter: "blur(16px)" }}
    >
      <div
        className="w-full max-w-md glass-panel rounded-3xl p-7"
        style={{ animation: "fadeIn 0.4s ease" }}
        role="dialog"
        aria-labelledby="feedback-prompt-title"
      >
        <div className="flex items-center justify-center mb-4">
          <MessageSquare size={36} style={{ color: "var(--emo-accent)" }} />
        </div>
        <h2
          id="feedback-prompt-title"
          className="font-heading text-xl text-center font-medium"
          style={{ color: "var(--emo-text)" }}
        >
          Comment améliorerais-tu l&apos;app ?
        </h2>
        <p className="text-center text-secondary-em mt-2 text-sm">
          Une question rapide ce mois-ci — ton avis compte.
        </p>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <textarea
            data-testid="feedback-textarea"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            maxLength={5000}
            placeholder="Fonctionnalités, bugs, idées…"
            className="w-full px-3 py-2.5 rounded-xl text-sm em-input resize-none"
            autoFocus
          />
          <div className="flex flex-col-reverse sm:flex-row gap-2">
            <button
              type="button"
              data-testid="feedback-skip-btn"
              onClick={skip}
              disabled={submitting || skipping}
              className="flex-1 py-2.5 rounded-xl text-sm emo-btn-soft disabled:opacity-50"
            >
              {skipping ? <Loader2 size={14} className="animate-spin mx-auto" /> : "Passer"}
            </button>
            <button
              type="submit"
              data-testid="feedback-submit-btn"
              disabled={submitting || skipping}
              className="flex-1 py-2.5 rounded-xl text-sm font-medium emo-btn-primary disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {submitting ? <Loader2 size={14} className="animate-spin" /> : "Envoyer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
