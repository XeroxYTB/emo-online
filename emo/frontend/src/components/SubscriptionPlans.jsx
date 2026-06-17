import React, { useState } from "react";
import { http } from "../lib/api";
import {
  Check, Zap, Crown, Sparkles, Loader2, RefreshCw, Clock, ShieldCheck,
  Infinity as InfinityIcon, AlertTriangle, RotateCcw,
} from "lucide-react";
import { toast } from "sonner";

const TIER_ICONS = { free: Clock, basic: Sparkles, premium: Zap, ultra: Crown };
const TIER_RANK = { free: 0, basic: 1, premium: 2, ultra: 3 };

export function SubscriptionSection({ license, plans, onRefresh, onReset }) {
  const [loading, setLoading] = useState(null);
  const [checking, setChecking] = useState(false);
  const currentTier = license?.tier || "free";
  const planList = plans || [];

  const subscribe = async (tier) => {
    setLoading(tier);
    try {
      const r = await http.post("/license/checkout", {
        origin_url: window.location.origin,
        tier,
      });
      if (r.data.already_paid) {
        toast.success(`Tu es déjà abonné ${r.data.tier}`);
        onRefresh?.();
        return;
      }
      if (r.data.url) window.location.href = r.data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Erreur Stripe");
    } finally {
      setLoading(null);
    }
  };

  const checkPayment = async () => {
    setChecking(true);
    try {
      const r = await http.post("/license/claim-payment");
      if (r.data.paid) {
        toast.success(`Abonnement ${r.data.tier} activé !`);
        onRefresh?.();
      } else {
        toast.info(r.data.message || "Paiement pas encore reçu — réessaie dans 30s");
      }
    } catch (_) {
      toast.error("Erreur vérification");
    } finally {
      setChecking(false);
    }
  };

  if (license?.is_admin && license?.source === "admin_grant") {
    return (
      <div className="p-3 rounded-xl text-sm" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)" }}>
        <div className="flex items-center gap-2">
          <Crown size={14} style={{ color: "#fbbf24" }} />
          <strong style={{ color: "#fbbf24" }}>Ultra Admin · illimité</strong>
        </div>
        <p className="text-[11px] text-secondary-em mt-1">Accès complet, tous les modèles IA.</p>
        {onReset && (
          <button onClick={onReset} className="mt-2 text-[11px] flex items-center gap-1 text-muted-em hover:text-amber-400">
            <RotateCcw size={10} /> Reset license (test)
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {currentTier !== "free" && license?.active && (
        <div className="p-3 rounded-xl text-sm" style={{ background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.25)" }}>
          <div className="flex items-center gap-2">
            <ShieldCheck size={14} style={{ color: "#34d399" }} />
            <strong style={{ color: "#34d399" }}>
              {license.tier_name || currentTier} actif
            </strong>
          </div>
          <p className="text-[11px] text-secondary-em mt-1">
            Modèle : {license.model_label || "—"}
            {license.valid_until && (
              <> · renouvellement {new Date(license.valid_until).toLocaleDateString("fr-FR")}</>
            )}
          </p>
        </div>
      )}

      {currentTier === "free" && (
        <div className="p-3 rounded-xl text-sm" style={{ background: "rgba(168,85,247,0.08)", border: "1px solid rgba(168,85,247,0.25)" }}>
          <div className="flex items-center gap-2">
            <Clock size={14} style={{ color: "var(--mode-color)" }} />
            <strong style={{ color: "var(--mode-color)" }}>Gratuit · IA open-source</strong>
          </div>
          <p className="text-[11px] text-secondary-em mt-1">
            {license?.messages_left_today ?? 0} / {license?.messages_per_day ?? 15} messages restants aujourd&apos;hui
            {license?.model_label && <> · {license.model_label}</>}
          </p>
        </div>
      )}

      <div className="grid gap-2.5">
        {planList.filter((p) => p.id !== "free").map((plan) => {
          const Icon = TIER_ICONS[plan.id] || Zap;
          const isCurrent = currentTier === plan.id && license?.active;
          const canUpgrade = !isCurrent && (TIER_RANK[plan.id] ?? 0) > (TIER_RANK[currentTier] ?? 0);
          const cardStyle =
            plan.id === "ultra"
              ? { bg: "rgba(245,158,11,0.06)", border: "rgba(245,158,11,0.25)", accent: "#fbbf24" }
              : plan.id === "basic"
                ? { bg: "rgba(99,102,241,0.06)", border: "rgba(99,102,241,0.25)", accent: "#a5b4fc" }
                : { bg: "rgba(168,85,247,0.06)", border: "rgba(168,85,247,0.25)", accent: "var(--mode-color)" };
          return (
            <div
              key={plan.id}
              className="p-4 rounded-xl space-y-2.5"
              style={{
                background: cardStyle.bg,
                border: `1px solid ${cardStyle.border}`,
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={16} style={{ color: cardStyle.accent }} />
                  <span className="font-medium text-sm">{plan.name}</span>
                </div>
                <span className="text-sm font-heading">
                  {plan.price_eur} €<span className="text-[10px] text-muted-em">/mois</span>
                </span>
              </div>
              <ul className="space-y-1">
                {plan.features?.slice(0, 4).map((f) => (
                  <li key={f} className="text-[11px] text-secondary-em flex items-start gap-1.5">
                    <Check size={10} className="mt-0.5 flex-shrink-0" style={{ color: cardStyle.accent }} />
                    {f}
                  </li>
                ))}
              </ul>
              {plan.models?.length > 0 && (
                <p className="text-[10px] text-muted-em">
                  IA : {plan.models.slice(0, 3).join(" · ")}
                </p>
              )}
              {isCurrent ? (
                <div className="text-[11px] text-center py-2 rounded-lg" style={{ background: "rgba(52,211,153,0.1)", color: "#34d399" }}>
                  Plan actuel
                </div>
              ) : canUpgrade || currentTier === "free" ? (
                <button
                  data-testid={`subscribe-${plan.id}-btn`}
                  onClick={() => subscribe(plan.id)}
                  disabled={loading === plan.id}
                  className="w-full py-2.5 rounded-xl text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                  style={{
                    background: plan.id === "ultra" ? "#fbbf24" : plan.id === "basic" ? "#818cf8" : "var(--mode-color)",
                    color: "#0A0510",
                  }}
                >
                  {loading === plan.id ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                  {TIER_RANK[currentTier] >= TIER_RANK[plan.id] ? `S'abonner ${plan.name}` : `Passer ${plan.name}`}
                </button>
              ) : null}
            </div>
          );
        })}
      </div>

      <button
        onClick={checkPayment}
        disabled={checking}
        className="w-full py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 text-secondary-em hover:text-white hover:bg-white/5 disabled:opacity-50"
      >
        {checking ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
        J&apos;ai payé · vérifier mon abonnement
      </button>
      <p className="text-[10px] text-muted-em text-center flex items-center justify-center gap-1">
        <ShieldCheck size={10} /> Paiement sécurisé Stripe · Annulable à tout moment
      </p>
    </div>
  );
}

export default function Paywall({ info, plans, onPaid }) {
  const [loading, setLoading] = useState(null);
  const [checking, setChecking] = useState(false);
  const expired = info?.status === "expired";
  const planList = plans || info?.plans || [];

  const subscribe = async (tier) => {
    setLoading(tier);
    try {
      const r = await http.post("/license/checkout", { origin_url: window.location.origin, tier });
      if (r.data.already_paid) { onPaid?.(); return; }
      if (r.data.url) window.location.href = r.data.url;
    } catch (_) {
      setLoading(null);
    }
  };

  const checkPayment = async () => {
    setChecking(true);
    try {
      const r = await http.post("/license/claim-payment");
      if (r.data.paid) onPaid?.();
      else {
        const lic = await http.get("/license/status");
        if (lic.data.active && lic.data.tier !== "free") onPaid?.();
        else alert(r.data.message || "Pas encore reçu. Patiente 30s puis réessaie.");
      }
    } catch (_) { /* ignore */ }
    finally { setChecking(false); }
  };

  return (
    <div
      data-testid="paywall-screen"
      className="fixed inset-0 z-[60] flex items-center justify-center px-4 mode-creatif overflow-y-auto py-8"
      style={{ background: "rgba(7,4,10,0.85)", backdropFilter: "blur(16px)" }}
    >
      <div className="w-full max-w-lg glass-panel rounded-3xl p-8" style={{ animation: "fadeIn 0.5s ease" }}>
        <div className="flex items-center justify-center mb-5">
          <InfinityIcon size={48} style={{ color: "var(--mode-color)", filter: "drop-shadow(0 0 14px var(--mode-glow))" }} />
        </div>
        <h2 className="font-heading text-2xl text-center font-medium">
          {expired ? "Abonnement expiré" : "Quota du jour atteint"}
        </h2>
        <p className="text-center text-secondary-em mt-2 text-sm">
          {expired
            ? "Renouvelle ton abonnement pour continuer."
            : <>Tu as utilisé tes <strong>{info?.messages_per_day || 15} messages gratuits</strong>. Passe <strong>Basique</strong> pour des IA gratuites illimitées, ou Premium / Ultra pour de meilleurs modèles.</>}
        </p>

        <div className="mt-6 space-y-3">
          {planList.filter((p) => p.id !== "free").map((plan) => (
            <button
              key={plan.id}
              data-testid={`paywall-${plan.id}-btn`}
              onClick={() => subscribe(plan.id)}
              disabled={!!loading}
              className="w-full p-4 rounded-2xl text-left transition hover:scale-[1.01] disabled:opacity-50"
              style={{
                background: plan.id === "ultra" ? "rgba(245,158,11,0.12)" : "rgba(168,85,247,0.12)",
                border: `1px solid ${plan.id === "ultra" ? "rgba(245,158,11,0.3)" : "rgba(168,85,247,0.3)"}`,
              }}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium">{plan.name}</span>
                <span className="font-heading">{plan.price_eur} €/mois</span>
              </div>
              <p className="text-[11px] text-muted-em mt-1">{plan.label}</p>
            </button>
          ))}
        </div>

        <button
          onClick={checkPayment}
          disabled={checking}
          className="w-full mt-4 py-2 rounded-xl text-xs flex items-center justify-center gap-1.5 text-secondary-em hover:bg-white/5 disabled:opacity-50"
        >
          {checking ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
          J&apos;ai payé · vérifier
        </button>
      </div>
    </div>
  );
}
