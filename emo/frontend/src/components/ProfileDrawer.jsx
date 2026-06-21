import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import {
  X, User as UserIcon, Sparkles, Palette, ShieldCheck, AlertTriangle,
  Trash2, LogOut, Save, Moon, Sun, Monitor, Shield, CreditCard, FileText,
} from "lucide-react";
import { toast } from "sonner";
import { SubscriptionSection } from "./SubscriptionPlans";
import AgentPermissionsPanel from "./AgentPermissionsPanel";
import AdminPanel from "./AdminPanel";

const THEME_OPTIONS = [
  { id: "dark", label: "Sombre", Icon: Moon },
  { id: "light", label: "Clair", Icon: Sun },
  { id: "system", label: "Système", Icon: Monitor },
];

const NAV_ITEMS = [
  { id: "profile", label: "Profil", Icon: UserIcon },
  { id: "subscription", label: "Abonnement", Icon: CreditCard },
  { id: "appearance", label: "Apparence", Icon: Palette },
  { id: "instructions", label: "Instructions", Icon: FileText },
  { id: "agent", label: "Agent", Icon: Shield },
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

  const isAdmin = profile?.license?.is_admin;
  const navItems = isAdmin
    ? [...NAV_ITEMS, { id: "admin", label: "Admin", Icon: Sparkles }]
    : NAV_ITEMS;

  return (
    <>
      <div
        data-testid="profile-overlay"
        onClick={onClose}
        className="emo-drawer-overlay emo-profile-overlay"
      />
      <aside
        data-testid="profile-drawer"
        className="emo-drawer emo-profile-drawer flex flex-col overflow-hidden"
        style={{
          background: "var(--emo-drawer-bg)",
          borderLeft: "1px solid var(--emo-border)",
          boxShadow: "var(--emo-drawer-shadow)",
        }}
      >
        {/* Header */}
        <div className="flex-shrink-0 px-5 py-4 flex items-center justify-between border-b" style={{ borderColor: "var(--emo-border)" }}>
          <h2 className="font-heading text-lg font-semibold" style={{ color: "var(--emo-text)" }}>
            Paramètres
          </h2>
          <button data-testid="profile-close-btn" onClick={onClose} className="emo-icon-btn">
            <X size={16} />
          </button>
        </div>

        {!profile ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="dot-loading"><span /><span /><span /></div>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row flex-1 min-h-0">
            {/* Side nav */}
            <nav className="emo-settings-nav hidden sm:block">
              {navItems.map(({ id, label, Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSection(id)}
                  className="emo-settings-nav-btn mb-0.5"
                  data-active={section === id ? "true" : "false"}
                >
                  <Icon size={14} />
                  {label}
                </button>
              ))}
            </nav>

            {/* Mobile nav pills */}
            <div className="sm:hidden flex-shrink-0 emo-settings-nav-mobile scrollbar-thin">
              {navItems.map(({ id, label, Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSection(id)}
                  className="emo-segment-btn flex-shrink-0"
                  data-active={section === id ? "true" : "false"}
                >
                  <Icon size={14} />
                  <span className="whitespace-nowrap">{label}</span>
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="emo-settings-content scrollbar-thin flex-1">
              {section === "admin" && isAdmin && (
                <AdminPanel debugEvents={debugEvents} onClearDebugEvents={onClearDebugEvents} />
              )}

              {section === "profile" && (
                <>
                  <div className="emo-settings-section">
                    <h3 className="emo-settings-section-title">
                      <UserIcon size={12} /> Compte
                    </h3>
                    <div className="emo-settings-card space-y-4">
                      <div className="flex items-center gap-4">
                        {profile.user.picture ? (
                          <img src={profile.user.picture} alt="" className="w-14 h-14 rounded-2xl object-cover" />
                        ) : (
                          <div
                            className="w-14 h-14 rounded-2xl flex items-center justify-center text-lg font-semibold"
                            style={{ background: "var(--emo-accent-soft)", color: "var(--emo-accent)" }}
                          >
                            {(profile.user.name || profile.user.email)?.[0]?.toUpperCase()}
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate" style={{ color: "var(--emo-text)" }}>
                            {profile.user.email}
                          </p>
                          <p className="text-xs text-muted-em mt-0.5">
                            {profile.user.auth_provider === "google" ? "Google" : "Email et mot de passe"}
                            {isAdmin && (
                              <span className="ml-2 inline-flex items-center gap-1 text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full" style={{ background: "var(--emo-admin-bg)", color: "var(--emo-admin-text)" }}>
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
                          className="w-full px-3 py-2.5 rounded-xl em-input text-sm"
                        />
                      </Field>
                    </div>
                  </div>

                  <div className="emo-settings-section">
                    <details className="emo-settings-card border-red-500/20">
                      <summary className="cursor-pointer text-xs font-medium flex items-center gap-2" style={{ color: "var(--emo-error-text)" }}>
                        <AlertTriangle size={12} /> Zone dangereuse
                      </summary>
                      <div className="mt-4 pt-4 border-t space-y-3" style={{ borderColor: "var(--emo-border)" }}>
                        <button
                          onClick={onLogout}
                          data-testid="profile-logout-btn"
                          className="w-full py-2.5 rounded-xl flex items-center justify-center gap-2 text-sm emo-btn-ghost"
                        >
                          <LogOut size={14} /> Se déconnecter
                        </button>
                        <div>
                          <p className="text-xs text-muted-em mb-2">Supprimer le compte (irréversible) :</p>
                          <input
                            type="text"
                            placeholder='Tape "SUPPRIMER" pour confirmer'
                            value={confirmDelete}
                            onChange={(e) => setConfirmDelete(e.target.value)}
                            className="w-full px-3 py-2 rounded-xl em-input border-red-500/20 text-xs"
                          />
                          <button
                            data-testid="profile-delete-btn"
                            onClick={deleteAccount}
                            className="w-full mt-2 py-2.5 rounded-xl flex items-center justify-center gap-2 text-xs emo-alert-error font-medium"
                          >
                            <Trash2 size={12} /> Supprimer définitivement
                          </button>
                        </div>
                      </div>
                    </details>
                  </div>
                </>
              )}

              {section === "subscription" && (
                <div className="emo-settings-section">
                  <h3 className="emo-settings-section-title">
                    <CreditCard size={12} /> Abonnements & IA
                  </h3>
                  <div className="emo-settings-card">
                    <SubscriptionSection
                      license={profile.license}
                      plans={profile.plans}
                      onRefresh={refreshProfile}
                      onReset={isAdmin ? resetLicense : null}
                    />
                  </div>
                </div>
              )}

              {section === "appearance" && (
                <div className="emo-settings-section">
                  <h3 className="emo-settings-section-title">
                    <Palette size={12} /> Thème
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {THEME_OPTIONS.map((opt) => {
                      const active = themeMode === opt.id;
                      const Icon = opt.Icon;
                      return (
                        <button
                          key={opt.id}
                          data-testid={`theme-${opt.id}-btn`}
                          onClick={() => onThemeModeChange?.(opt.id)}
                          className="emo-theme-btn flex flex-col items-center gap-2 px-3 py-4 text-xs font-medium"
                          data-active={active ? "true" : "false"}
                        >
                          <Icon size={18} />
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-em mt-3">
                    Le thème est géré localement et synchronisé à l'enregistrement.
                  </p>
                </div>
              )}

              {section === "instructions" && (
                <div className="emo-settings-section">
                  <h3 className="emo-settings-section-title">
                    <FileText size={12} /> Instructions personnalisées
                  </h3>
                  <textarea
                    data-testid="custom-prompt-input"
                    value={addon}
                    onChange={(e) => setAddon(e.target.value)}
                    rows={8}
                    placeholder="Instructions perso (priorité absolue sur le comportement par défaut)."
                    className="w-full px-4 py-3 rounded-xl em-input text-sm resize-none font-code"
                    maxLength={4000}
                  />
                  <p className="text-xs text-muted-em mt-2">{addon.length}/4000 caractères</p>
                </div>
              )}

              {section === "agent" && (
                <div className="emo-settings-section">
                  <h3 className="emo-settings-section-title">
                    <Shield size={12} /> Agent local
                  </h3>
                  <div className="emo-settings-card">
                    <p className="text-xs text-muted-em mb-3">
                      Téléchargement et permissions détaillées dans le panneau Agent (à droite).
                    </p>
                    <AgentPermissionsPanel agentOnline={agentOnline} />
                  </div>
                </div>
              )}

              {section !== "admin" && (
                <button
                  data-testid="profile-save-btn"
                  onClick={save}
                  disabled={saving}
                  className="emo-btn-primary w-full py-3 rounded-xl text-sm flex items-center justify-center gap-2 mt-2"
                  style={{ boxShadow: "0 4px 20px var(--emo-glow)" }}
                >
                  <Save size={14} /> {saving ? "Sauvegarde…" : "Enregistrer"}
                </button>
              )}

              {isAdmin && section !== "admin" && (
                <p className="text-xs text-muted-em mt-4">
                  Clés IA, debug, export : onglet <strong style={{ color: "var(--emo-admin-text)" }}>Admin</strong>.
                </p>
              )}
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

const Field = ({ label, children }) => (
  <div>
    <label className="block text-xs text-muted-em mb-1.5 font-medium">{label}</label>
    {children}
  </div>
);
