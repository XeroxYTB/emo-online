# Agent local Emo

Même API que le site en ligne. Lance sur le PC de l'utilisateur.

```bash
pip install httpx
export EMO_BACKEND_URL=https://votre-app.onrender.com
export EMO_AGENT_TOKEN=xxx   # depuis l'UI Emo > Parametres agent
python emo-agent.py
```

Ou :

```bash
python emo-agent.py --backend https://votre-app.onrender.com --token xxx
```

Windows : double-clic possible via `run-agent.bat` (a creer localement, non versionne).
