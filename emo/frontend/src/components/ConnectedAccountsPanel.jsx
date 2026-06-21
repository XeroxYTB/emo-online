import React, { useCallback, useEffect, useState } from "react";
import { http, getActiveBase, BACKEND_URL, getSessionToken } from "../lib/api";
import { frontendUrl } from "../lib/paths";
import { Github, Link2, Unlink, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const PROVIDER_ICONS = {
  github: Github,
  google: () => (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
      />
      <path
        fill="currentColor"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="currentColor"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="currentColor"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  ),
};

export default function ConnectedAccountsPanel() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await http.get("/connections");
      setAccounts(r.data?.accounts || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Impossible de charger les comptes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connect = (provider) => {
    const base = (getActiveBase() || BACKEND_URL || "").replace(/\/$/, "");
    if (!base) {
      toast.error("Backend indisponible");
      return;
    }
    const returnUrl = frontendUrl("/auth/connections/callback");
    const qs = new URLSearchParams({ return_url: returnUrl });
    const session = getSessionToken();
    if (session) qs.set("session", session);
    window.location.href = `${base}/api/oauth/${provider}/start?${qs.toString()}`;
  };

  const disconnect = async (provider) => {
    if (!window.confirm(`Déconnecter ${provider} ?`)) return;
    setBusy(provider);
    try {
      await http.delete(`/connections/${provider}`);
      toast.success("Compte déconnecté");
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Erreur");
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="dot-loading"><span /><span /><span /></div>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="connected-accounts-panel">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-em">
          Lie GitHub ou Google pour qu&apos;Émo agisse avec tes comptes (tokens côté serveur uniquement).
        </p>
        <button type="button" onClick={load} className="p-1.5 rounded em-hover text-muted-em" aria-label="Actualiser">
          <RefreshCw size={14} />
        </button>
      </div>

      {accounts.map((acc) => {
        const Icon = PROVIDER_ICONS[acc.provider] || Link2;
        const connected = acc.connected;
        const configured = acc.configured;
        const display = acc.profile?.display || acc.profile?.login;
        return (
          <div key={acc.provider} className="emo-settings-card flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "var(--emo-subtle-bg)", color: "var(--emo-text-secondary)" }}
            >
              <Icon size={18} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium" style={{ color: "var(--emo-text)" }}>
                {acc.label || acc.provider}
              </p>
              {connected && display ? (
                <p className="text-xs text-muted-em truncate">Connecté en tant que {display}</p>
              ) : configured ? (
                <p className="text-xs text-muted-em">Non connecté</p>
              ) : (
                <p className="text-xs" style={{ color: "var(--emo-warning-text)" }}>
                  {acc.message || "Configure keys on server"}
                </p>
              )}
            </div>
            <div className="flex-shrink-0">
              {connected ? (
                <button
                  type="button"
                  data-testid={`disconnect-${acc.provider}`}
                  disabled={busy === acc.provider}
                  onClick={() => disconnect(acc.provider)}
                  className="emo-btn-ghost px-3 py-2 rounded-lg text-xs flex items-center gap-1.5"
                >
                  <Unlink size={12} /> Déconnecter
                </button>
              ) : (
                <button
                  type="button"
                  data-testid={`connect-${acc.provider}`}
                  disabled={!configured || busy === acc.provider}
                  onClick={() => connect(acc.provider)}
                  className="emo-btn-primary px-3 py-2 rounded-lg text-xs flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Link2 size={12} /> Connecter
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
