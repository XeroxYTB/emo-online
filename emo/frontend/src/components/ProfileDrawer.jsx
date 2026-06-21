import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { X, User as UserIcon, Sparkles, Palette, ShieldCheck, AlertTriangle, Trash2, LogOut, Save, Moon, Sun, Monitor, Shield } from "lucide-react";
import { toast } from "sonner";
import { SubscriptionSection } from "./SubscriptionPlans";
import AgentPermissionsPanel from "./AgentPermissionsPanel";
import AdminPanel from "./AdminPanel";

const THEME_OPTIONS = [
  { id: "dark", label: "Sombre", Icon: Moon },
  { id: "light", label: "Clair", Icon: Sun },
  { id: "system", label: "Système", Icon: Monitor },
];

export default function ProfileDrawer({
  open,
  onClose,
  onLogout,
  themeMode,
  onThemeModeChange,
  agentOnline,
  debugEvents,
  onClearDebugEvents,
}) {
  const [profile, setProfile] = useState(null);
  const [section, setSection] = useState("profile");
  const [name, setName] = useState("");
  const [addon, setAddon] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState("");

  useEffect(() => {
    if (!open) return;
    setSection("profile");
    http.get("/profile").then((r) => {
      setProfile(r.data);
      setName(r.data.user.name || "");
      setAddon(r.data.preferences.custom_prompt_addon || "");
    });
  }, [open]);

  const save = async () => {
    setSaving(true);
    try {
      await http.patch("/profile", {
        name, custom_prompt_addon: addon, theme_mode: themeMode,
      });
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
    toast.success("Licence réinitialisée");
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
        style={{ background: "var(--emo-overlay)", backdropFilter: "blur(4px)" }}
      />
      <aside
        data-testid="profile-drawer"
        className="fixed top-0 right-0 bottom-0 z-50 w-[480px] max-w-[95vw] glass-panel overflow-y-auto scrollbar-thin emo-drawer"
        style={{
          background: "var(--emo-drawer-bg)",
          borderLeft: "1px solid var(--emo-border)",
          boxShadow: "var(--emo-drawer-shadow)",
        }}
      >
        <div className="sticky top-0 z-10 px-6 py-4 flex items-center justify-between glass-panel em-border-b">
          <div className="flex items-center gap-3">
            <UserIcon size={16} style={{ color: "var(--mode-color)" }} />
            <h2 className="font-heading text-lg" style={{ color: "var(--emo-text)" }}>Paramètres</h2>
          </div>
          <button data-testid="profile-close-btn" onClick={onClose} className="p-2 rounded-xl em-hover">
            <X size={16} />
          </button>
        </div>

        {profile?.license?.is_admin && (
          <div className="px-6 pt-4 flex gap-2">
            <button
              type="button"
              onClick={() => setSection("profile")}
              className="px-3 py-1.5 rounded-lg text-xs"
              style={{
                background: section === "profile" ? "var(--emo-accent-soft)" : "transparent",
                color: section === "profile" ? "var(--emo-accent)" : "var(--emo-text-muted)",
                border: `1px solid ${section === "profile" ? "var(--emo-accent-border)" : "transparent"}`,
              }}
            >
              Profil
            </button>
            <button
              type="button"
              onClick={() => setSection("admin")}
              className="px-3 py-1.5 rounded-lg text-xs"
              style={{
                background: section === "admin" ? "var(--emo-admin-bg)" : "transparent",
                color: section === "admin" ? "var(--emo-admin-text)" : "var(--emo-text-muted)",
                border: `1px solid ${section === "admin" ? "var(--emo-warning-border)" : "transparent"}`,
              }}
            >
              Admin
            </button>
          </div>
        )}

        <div className="p-6 space-y-6">
          {profile && section === "admin" && profile.license.is_admin && (
            <AdminPanel debugEvents={debugEvents} onClearDebugEvents={onClearDebugEvents} />
          )}

          {profile && section === "profile" && (
            <>
              {/* User card */}
              <Section icon={UserIcon} label="Compte">
                <div className="flex items-center gap-3">
                  {profile.user.picture ? (
                    <img src={profile.user.picture} alt="" className="w-12 h-12 rounded-full" />
                  ) : (
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-base font-medium"
                      style={{ background: "var(--emo-accent-soft)", color: "var(--mode-color)" }}
                    >
                      {(profile.user.name || profile.user.email)?.[0]?.toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: "var(--emo-text)" }}>{profile.user.email}</p>
                    <p className="text-[11px] text-muted-em">
                      {profile.user.auth_provider === "google" ? "Google" : "Email et mot de passe"}
                      {profile.license.is_admin && (
                        <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] px-1.5 py-0.5 rounded-full" style={{ background: "var(--emo-admin-bg)", color: "var(--emo-admin-text)" }}>
                          <ShieldCheck size={9} /> Admin
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
                    className="w-full px-3 py-2 rounded-xl em-input text-sm focus:border-purple-500/40"
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

              {/* Agent local — permissions (détail dans panneau Agent) */}
              <Section icon={Shield} label="Agent local">
                <p className="text-xs text-muted-em mb-2">Téléchargement et permissions dans le panneau Agent (à droite).</p>
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
                        onClick={() => onThemeModeChange?.(opt.id)}
                        className="flex-1 flex flex-col items-center gap-1.5 px-3 py-3 rounded-2xl text-xs font-medium transition emo-theme-btn"
                        data-active={active ? "true" : "false"}
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
                  placeholder="Instructions perso (priorité absolue sur le comportement par défaut). Clique Enregistrer."
                  className="w-full px-3 py-2.5 rounded-2xl em-input text-sm focus:border-purple-500/40 resize-none font-code text-[13px]"
                  maxLength={4000}
                />
              </Section>

              {/* Stripe / export — déplacés vers AdminPanel */}
              {profile.license.is_admin && (
                <p className="text-xs text-muted-em">
                  Clés IA, debug, export : onglet <strong style={{ color: "var(--emo-admin-text)" }}>Admin</strong>.
                </p>
              )}

              {/* Save */}
              <button
                data-testid="profile-save-btn"
                onClick={save}
                disabled={saving}
                className="w-full py-3 rounded-2xl text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50 transition-opacity"
                style={{
                  background: "var(--emo-accent)",
                  color: "var(--emo-on-accent)",
                  boxShadow: "0 4px 20px var(--emo-glow)",
                }}
              >
                <Save size={13} /> {saving ? "Sauvegarde…" : "Enregistrer"}
              </button>

              {/* Danger zone */}
              <details className="border border-red-500/20 rounded-2xl overflow-hidden">
                <summary className="cursor-pointer px-4 py-2.5 text-xs rounded-xl" style={{ color: "var(--emo-error-text)" }}>
                  <AlertTriangle size={11} className="inline mr-1.5" /> Zone dangereuse
                </summary>
                <div className="px-4 pb-4 pt-2 space-y-3 text-xs">
                  <button
                    onClick={onLogout}
                    data-testid="profile-logout-btn"
                    className="w-full py-2 rounded-lg flex items-center justify-center gap-2 text-secondary-em em-hover-subtle"
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
                      className="w-full px-3 py-1.5 rounded-lg em-input border-red-500/20 text-xs focus:border-red-500/40"
                    />
                    <button
                      data-testid="profile-delete-btn"
                      onClick={deleteAccount}
                      className="w-full mt-2 py-2 rounded-lg flex items-center justify-center gap-2 text-xs emo-alert-error"
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
