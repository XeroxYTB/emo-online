# Agent local Emo

Deux modes d'exécution :

## Agent relais seul (léger)

```bash
pip install httpx
export EMO_BACKEND_URL=https://votre-app.onrender.com
export EMO_AGENT_TOKEN=xxx   # depuis l'UI Emo > Parametres agent
python emo-agent.py
```

## Application desktop complète (Phase 1)

```bash
pip install -r emo/desktop/requirements.txt
py -m emo.desktop
```

L'app PyQt6 inclut CHAT / VOCAL / AGENT, 24 skills, dashboard mobile (:8000) et démarre le relais agent automatiquement si `agent_token` est configuré dans Paramètres.

Téléchargement zip depuis l'UI Emo (fallback si binaire Go absent) — extrait `emo/` et lance `start.bat` / `start.sh`.

Windows : double-clic via `start.bat` après extraction du zip.
