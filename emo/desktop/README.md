# Émo Desktop (Phase 1)

Application locale PyQt6 : chat, vocal, agent, 24 skills, dashboard mobile.

## Installation

```bash
cd "H:\Emo Online Final"
pip install -r emo/desktop/requirements.txt
```

Copiez `emo/desktop/config/api_keys.json.example` vers `emo/desktop/config/api_keys.json` et renseignez vos clés.

## Lancement

```bash
py -m emo.desktop
```

Le relais agent cloud démarre automatiquement si `agent_token` est configuré (ou `EMO_AGENT_TOKEN`).

## Modes

| Mode | Description |
|------|-------------|
| **CHAT** | Conversation texte (Gemini ou backend) |
| **VOCAL** | Voix Gemini Live (stub Phase 1 si pas de clé) |
| **AGENT** | Pipeline think→plan→execute + skills |

## Raccourcis

- **F4** — Couper/réactiver le micro (mode vocal)
- **ESC** — Interrompre l'agent

## Dashboard mobile (port 8000)

- `GET /pair` — code d'appairage
- `POST /command` — envoyer une commande texte
- `POST /upload` — upload fichier
- `WS /ws/log` — journal en direct

## Skills (24)

Chargés dynamiquement depuis `actions/`. Prioritaires : `file_controller`, `web_search`, `open_app`, `local_analyzer_skill`, `dev_agent_skill`.

## Phase 2 (prévu)

- Gemini Live streaming audio complet
- Vision écran (OpenCV)
- Intégration cloud frontend native
- SMS / notifications push
- Tests E2E PyQt6
