import React, { useEffect, useState } from "react";
import { http, API, BACKEND_URL } from "../lib/api";
import { X, User as UserIcon, Sparkles, Palette, ShieldCheck, AlertTriangle, Trash2, LogOut, Save, Moon, Sun, Monitor, Package, Download } from "lucide-react";
import { toast } from "sonner";
import { SubscriptionSection } from "./SubscriptionPlans";

const THEME_OPTIONS = [
  { id: "dark", label: "Sombre", Icon: Moon },
  { id: "light", label: "Clair", Icon: Sun },
  { id: "system", label: "Système", Icon: Monitor },
];

export default function ProfileDrawer({ open, onClose, onLogout, onPreferencesChange }) {
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState("");
  const [addon, setAddon] = useState("");
  const [themeMode, setThemeMode] = useState("dark");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState("");

  useEffect(() => {
    if (!open) return;
    http.get("/profile").then((r) => {
      setProfile(r.data);
      setName(r.data.user.name || "");
      setAddon(r.data.preferences.custom_prompt_addon || "");
      setThemeMode(r.data.preferences.theme_mode || "dark");
    });
  }, [open]);

  const save = async () => {
    setSaving(true);
    try {
      await http.patch("/profile", {
        name, custom_prompt_addon: addon, theme_mode: themeMode,
      });
      onPreferencesChange?.({ theme_mode: themeMode });
      toast.success("Profil enregistré");
    } catch (e) {
      toast.error("Erreur");
    } finally {
      setSaving(false);
    }
  };

  const refreshProfile = async () => {
    const r = await http.get("/profile");
    setProfile(r.data);
  };

  const resetLicense = async () => {
    if (!window.confirm("Reset ta license active ? (admin only, pour test du paywall)")) return;
    await http.post("/profile/reset-license");
    toast.success("License reset");
    const r = await http.get("/profile");
    setProfile(r.data);
  };

  const deleteAccount = async () => {
    if (confirmDelete !== "SUPPRIMER") {
      toast.error("Tape SUPPRIMER pour confirmer");
      return;
    }
    await http.delete("/profile");
    onLogout();
  };

  if (!open) return null;

  return (
    <>
      <div
        data-testid="profile-overlay"
        onClick={onClose}
        className="fixed inset-0 z-40"
        style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
      />
      <aside
        data-testid="profile-drawer"
        className="fixed top-0 right-0 bottom-0 z-50 w-[480px] max-w-[95vw] glass-panel overflow-y-auto scrollbar-thin"
        style={{
          background: "rgba(7,4,10,0.92)",
          borderLeft: "1px solid var(--emo-border)",
          borderRadius: 0,
          boxShadow: "-20px 0 60px rgba(0,0,0,0.5)",
          animation: "slideInRight 0.25s ease",
        }}
      >
        <div className="sticky top-0 z-10 px-6 py-4 flex items-center justify-between glass-panel" style={{ borderBottom: "1px solid var(--emo-border)", borderRadius: 0 }}>
          <div className="flex items-center gap-2">
            <UserIcon size={16} style={{ color: "var(--mode-color)" }} />
            <h2 className="font-heading text-lg">Profil</h2>
          </div>
          <button data-testid="profile-close-btn" onClick={onClose} className="p-1.5 rounded hover:bg-white/10">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {profile && (
            <>
              {/* User card */}
              <Section icon={UserIcon} label="Compte">
                <div className="flex items-center gap-3">
                  {profile.user.picture ? (
                    <img src={profile.user.picture} alt="" className="w-12 h-12 rounded-full" />
                  ) : (
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-base font-medium"
                      style={{ background: "rgba(168,85,247,0.2)", color: "var(--mode-color)" }}
                    >
                      {(profile.user.name || profile.user.email)?.[0]?.toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{profile.user.email}</p>
                    <p className="text-[11px] text-muted-em">
                      {profile.user.auth_provider === "google" ? "Google" : "Email + password"}
                      {profile.license.is_admin && (
                        <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] px-1.5 py-0.5 rounded-full" style={{ background: "rgba(245,158,11,0.15)", color: "#fbbf24" }}>
                          <ShieldCheck size={9} /> admin
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                <Field label="Nom affiché">
                  <input
                    data-testid="profile-name-input"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-white/5 text-sm focus:outline-none focus:border-purple-500/40"
                  />
                </Field>
              </Section>

              {/* Abonnements */}
              <Section icon={Sparkles} label="Abonnements & IA">
                <SubscriptionSection
                  license={profile.license}
                  plans={profile.plans}
                  onRefresh={refreshProfile}
                  onReset={profile.license.is_admin ? resetLicense : null}
                />
              </Section>

              {/* Theme mode */}
              <Section icon={Palette} label="Apparence">
                <div className="flex gap-2">
                  {THEME_OPTIONS.map((opt) => {
                    const active = themeMode === opt.id;
                    const Icon = opt.Icon;
                    return (
                      <button
                        key={opt.id}
                        data-testid={`theme-${opt.id}-btn`}
                        onClick={() => {
                          setThemeMode(opt.id);
                          onPreferencesChange?.({ theme_mode: opt.id });
                        }}
                        className="flex-1 flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl text-xs transition"
                        style={{
                          background: active ? "rgba(168,85,247,0.15)" : "rgba(255,255,255,0.02)",
                          border: `1px solid ${active ? "rgba(168,85,247,0.45)" : "rgba(255,255,255,0.06)"}`,
                          color: active ? "var(--emo-text)" : "var(--emo-text-secondary)",
                        }}
                      >
                        <Icon size={16} />
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-[10px] text-muted-em">Choisis ton thème. &quot;Système&quot; suit les préférences de ton OS.</p>
              </Section>

              {/* Custom prompt */}
              <Section icon={Sparkles} label="Instructions perso pour Émo">
                <textarea
                  data-testid="custom-prompt-input"
                  value={addon}
                  onChange={(e) => setAddon(e.target.value)}
                  rows={5}
                  placeholder="Ex: Réponds toujours en français formel. Préfère TypeScript à JavaScript. Mes projets sont sous /home/hugo/dev/..."
                  className="w-full px-3 py-2.5 rounded-xl bg-black/40 border border-white/5 text-sm focus:outline-none focus:border-purple-500/40 resize-none font-code text-[13px]"
                  maxLength={4000}
                />
                <p className="text-[11px] text-muted-em mt-1">
                  Injecté dans chaque conversation. {addon.length}/4000 caractères.
                </p>
              </Section>

              {/* Stripe payouts — admin only */}
              {profile.license.is_admin && (
                <>
                  <Section icon={Package} label="Code source complet (self-hosting)">
                    <div className="p-3 rounded-xl text-xs space-y-2.5" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)" }}>
                      <p className="text-secondary-em leading-relaxed">
                        Télécharge tout le code source d&apos;Émo (backend + frontend + agent Go + doc) pour l&apos;héberger sur ton propre domaine et garder 100% des revenus.
                      </p>
                      <p className="text-muted-em text-[10px]">
                        Inclus : <code className="font-code">backend/</code>, <code className="font-code">frontend/</code>, <code className="font-code">agent-go/</code>, <code className="font-code">memory/</code>, <code className="font-code">SELF_HOSTING.md</code>. Les <code className="font-code">.env</code> sont sanitizés en <code className="font-code">.env.example</code> (clés à remettre).
                      </p>
                      <button
                        data-testid="download-source-btn"
                        onClick={() => {
                          const base = BACKEND_URL || window.location.origin;
                          const url = `${base}/api/admin/project-export`;
                          const w = window.open(url, "_blank");
                          if (!w) window.location.href = url;
                          toast.success("Téléchargement du code source lancé");
                        }}
                        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all hover:scale-[1.01]"
                        style={{ background: "#10B981", color: "#021F14", boxShadow: "0 0 18px rgba(16,185,129,0.35)" }}
                      >
                        <Download size={13} /> Télécharger emo-source.tar.gz
                      </button>
                      <p className="text-[10px] text-muted-em">
                        Lis <code className="font-code">SELF_HOSTING.md</code> dans l&apos;archive pour les étapes de déploiement (Vercel, Render, Railway, VPS, etc.).
                      </p>
                    </div>
                  </Section>

                  <Section icon={Package} label="Revenus Stripe">
                  <div className="p-3 rounded-xl text-xs space-y-2.5" style={{ background: "rgba(99,91,255,0.06)", border: "1px solid rgba(99,91,255,0.18)" }}>
                    <p className="text-secondary-em leading-relaxed">
                      Les paiements clients vont directement sur ton compte Stripe (celui dont la clé est dans <code className="font-code">STRIPE_API_KEY</code>).
                    </p>
                    <p className="text-muted-em leading-relaxed">
                      <strong>Mode actuel</strong> : <code className="font-code text-amber-300">test</code> (sk_test_emergent — paiements simulés, pas de vrais fonds).
                    </p>
                    <div className="space-y-1 pt-1">
                      <p className="text-muted-em">Pour encaisser pour de vrai :</p>
                      <ol className="ml-4 list-decimal space-y-1 text-secondary-em">
                        <li>Crée un compte sur <a href="https://stripe.com" target="_blank" rel="noreferrer" className="underline text-purple-300">stripe.com</a></li>
                        <li>Dashboard → Developers → API keys → copie ta <code className="font-code">sk_live_...</code></li>
                        <li>Remplace <code className="font-code">STRIPE_API_KEY</code> dans <code className="font-code">/app/backend/.env</code></li>
                        <li>Redémarre le backend</li>
                      </ol>
                    </div>
                    <div className="flex gap-2 pt-1">
                      <a
                        href="https://dashboard.stripe.com/payouts"
                        target="_blank"
                        rel="noreferrer"
                        data-testid="stripe-payouts-link"
                        className="flex-1 text-center px-3 py-2 rounded-lg text-[11px] font-medium"
                        style={{ background: "rgba(99,91,255,0.18)", color: "#a5b4fc" }}
                      >
                        Voir mes payouts →
                      </a>
                      <a
                        href="https://dashboard.stripe.com/payments"
                        target="_blank"
                        rel="noreferrer"
                        data-testid="stripe-payments-link"
                        className="flex-1 text-center px-3 py-2 rounded-lg text-[11px] font-medium"
                        style={{ background: "rgba(99,91,255,0.18)", color: "#a5b4fc" }}
                      >
                        Voir les paiements →
                      </a>
                    </div>
                    <p className="text-[10px] text-muted-em pt-1">
                      Sur Stripe, payouts vers ta banque toutes les 2-7 jours en auto (configurable). Tu peux aussi déclencher un payout manuel.
                    </p>
                  </div>
                </Section>
                </>
              )}

              {/* Save */}
              <button
                data-testid="profile-save-btn"
                onClick={save}
                disabled={saving}
                className="w-full py-3 rounded-2xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                style={{ background: "var(--mode-color)", color: "#0A0510", boxShadow: "0 0 16px var(--mode-glow)" }}
              >
                <Save size={13} /> {saving ? "Sauvegarde…" : "Enregistrer"}
              </button>

              {/* Danger zone */}
              <details className="border border-red-500/20 rounded-xl">
                <summary className="cursor-pointer px-4 py-2.5 text-xs text-red-300 hover:bg-red-500/5 rounded-xl">
                  <AlertTriangle size={11} className="inline mr-1.5" /> Zone dangereuse
                </summary>
                <div className="px-4 pb-4 pt-2 space-y-3 text-xs">
                  <button
                    onClick={onLogout}
                    data-testid="profile-logout-btn"
                    className="w-full py-2 rounded-lg flex items-center justify-center gap-2 text-secondary-em hover:bg-white/5"
                  >
                    <LogOut size={11} /> Se déconnecter
                  </button>
                  <div>
                    <p className="text-muted-em mb-1.5">Supprimer le compte (irréversible — toutes tes données partent) :</p>
                    <input
                      type="text"
                      placeholder='Tape "SUPPRIMER" pour confirmer'
                      value={confirmDelete}
                      onChange={(e) => setConfirmDelete(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-red-500/20 text-xs focus:outline-none focus:border-red-500/40"
                    />
                    <button
                      data-testid="profile-delete-btn"
                      onClick={deleteAccount}
                      className="w-full mt-2 py-2 rounded-lg flex items-center justify-center gap-2 text-xs"
                      style={{ background: "rgba(239,68,68,0.15)", color: "#fca5a5" }}
                    >
                      <Trash2 size={11} /> Supprimer définitivement
                    </button>
                  </div>
                </div>
              </details>
            </>
          )}
        </div>
      </aside>
    </>
  );
}

const Section = ({ icon: Icon, label, children }) => (
  <div className="space-y-3">
    <h3 className="text-xs uppercase tracking-[0.2em] text-muted-em flex items-center gap-1.5">
      <Icon size={11} /> {label}
    </h3>
    <div className="space-y-2.5">{children}</div>
  </div>
);

const Field = ({ label, children }) => (
  <div>
    <label className="block text-[11px] text-muted-em mb-1">{label}</label>
    {children}
  </div>
);
