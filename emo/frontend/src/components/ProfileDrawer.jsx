import React, { useEffect, useState } from "react";
import { http, API, BACKEND_URL } from "../lib/api";
import { X, User as UserIcon, Sparkles, Palette, ShieldCheck, AlertTriangle, Trash2, LogOut, Save, Moon, Sun, Monitor, Package, Download, Shield } from "lucide-react";
import { toast } from "sonner";
import { SubscriptionSection } from "./SubscriptionPlans";
import AgentPermissionsPanel from "./AgentPermissionsPanel";

const THEME_OPTIONS = [
  { id: "dark", label: "Sombre", Icon: Moon },
  { id: "light", label: "Clair", Icon: Sun },
  { id: "system", label: "Système", Icon: Monitor },
];

export default function ProfileDrawer({ open, onClose, onLogout, onPreferencesChange, agentOnline }) {
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
    if (!window.confirm("Réinitialiser la licence ?")) return;
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

              {/* Agent local — permissions */}
              <Section icon={Shield} label="Agent local">
                <AgentPermissionsPanel agentOnline={agentOnline} />
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
              </Section>

              {/* Custom prompt */}
              <Section icon={Sparkles} label="Instructions">
                <textarea
                  data-testid="custom-prompt-input"
                  value={addon}
                  onChange={(e) => setAddon(e.target.value)}
                  rows={5}
                  placeholder="Instructions optionnelles"
                  className="w-full px-3 py-2.5 rounded-xl bg-black/40 border border-white/5 text-sm focus:outline-none focus:border-purple-500/40 resize-none font-code text-[13px]"
                  maxLength={4000}
                />
              </Section>

              {/* Stripe payouts — admin only */}
              {profile.license.is_admin && (
                <>
                  <Section icon={Package} label="Code source">
                    <div className="p-3 rounded-xl text-xs space-y-2.5" style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)" }}>
                      <button
                        data-testid="download-source-btn"
                        onClick={() => {
                          const base = BACKEND_URL || window.location.origin;
                          const url = `${base}/api/admin/project-export`;
                          const w = window.open(url, "_blank");
                          if (!w) window.location.href = url;
                          toast.success("Téléchargement lancé");
                        }}
                        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all hover:scale-[1.01]"
                        style={{ background: "#10B981", color: "#021F14", boxShadow: "0 0 18px rgba(16,185,129,0.35)" }}
                      >
                        <Download size={13} /> emo-source.tar.gz
                      </button>
                    </div>
                  </Section>

                  <Section icon={Package} label="Stripe">
                  <div className="p-3 rounded-xl text-xs space-y-2.5" style={{ background: "rgba(99,91,255,0.06)", border: "1px solid rgba(99,91,255,0.18)" }}>
                    <div className="flex gap-2">
                      <a
                        href="https://dashboard.stripe.com/payouts"
                        target="_blank"
                        rel="noreferrer"
                        data-testid="stripe-payouts-link"
                        className="flex-1 text-center px-3 py-2 rounded-lg text-[11px] font-medium"
                        style={{ background: "rgba(99,91,255,0.18)", color: "#a5b4fc" }}
                      >
                        Payouts
                      </a>
                      <a
                        href="https://dashboard.stripe.com/payments"
                        target="_blank"
                        rel="noreferrer"
                        data-testid="stripe-payments-link"
                        className="flex-1 text-center px-3 py-2 rounded-lg text-[11px] font-medium"
                        style={{ background: "rgba(99,91,255,0.18)", color: "#a5b4fc" }}
                      >
                        Paiements
                      </a>
                    </div>
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
