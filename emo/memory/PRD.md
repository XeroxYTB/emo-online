# Émo — PRD

## Pricing (final)
- **Gratuit** : 10 messages / jour (reset à minuit UTC), illimité dans le temps
- **Lifetime** : 20 € one-shot via Stripe → messages illimités
- **Admin lifetime auto** : emails dans `EMO_ADMIN_EMAILS` env (CSV) — `hugo@example.com` + `huglostalatac@gmail.com` par défaut

## Architecture
- LLM : Claude Sonnet 4.5 (function calling) via Emergent LLM Key
- Backend : FastAPI + Motor + Stripe + SSE + agent long-polling + BeautifulSoup pour web
- Agent natif Go : 5 binaires cross-compilés + `--install` natif (registre Windows / LaunchAgent macOS / systemd user Linux)
- Frontend : React 19 + Monaco + Tailwind + Shadcn

## Tools de Claude
### Locaux (via agent)
- `exec_shell`, `read_file`, `write_file`, `list_dir`
### Web (backend, pas besoin d'agent)
- `web_search(query, limit)` — DuckDuckGo HTML, retourne title/url/snippet
- `web_fetch(url, max_chars)` — texte propre + liens + URLs d'images

## Itération 7 — Freeze fix + Tech-by-default + Mobile (Feb 2026)
- [x] **BUG CRITIQUE FIXÉ** : freeze d'Emo causé par stdout massif (`dir /s` sur tout un disque) qui saturait le SSE.
  - Backend `agent_relay.py` : truncation 64 KB max sur stdout/stderr/content (defense-in-depth, marche même avec vieux binaires agent)
  - Go agent `main.go` : truncation 64 KB côté agent (garde la fin où les erreurs sont)
  - **Tous les binaires rebuild** (5 plateformes) — l'utilisateur doit télécharger la nouvelle version
- [x] **4 modes retirés du header** : plus de top-bar ModeSelector
- [x] **Sélecteur de mode déplacé dans le composer** (style DeepSeek) — bouton subtil avec icône + menu dropdown
- [x] **Tech = défaut + intégré dans la persona de base** : plus de mode "normal", Tech est toujours actif. Modes restants : Tech / Créatif / Brutal (Créatif et Brutal sont des overrides).
- [x] **Persona** : "Hugo" only (jamais "hugo catala"). Suppression des références spontanées à "je suis l'IA de Hugo / je viens de DeskBuddy" — Emo répond au sujet pas à son lore.
- [x] **Debug console** : admin only (UI cache le bouton Bug pour les non-admins)
- [x] **Mobile responsive** : hamburger menu + sidebar drawer + composer/header compacts
- [x] **Light theme contrast** : header utilise `var(--emo-glass-bg)`, dropdown sidebar utilise `var(--emo-surface)`
- [x] Suppression de `ModeSelector.jsx` (obsolète)
- [x] Migration legacy : `mode == "normal"` en DB → traité comme "tech" côté backend

## Itération 6 — Webhook Stripe + UI simplifiée (Feb 2026)
- [x] **Webhook Stripe vérifié** via curl simulation : `checkout.session.completed` avec `client_reference_id` → user.paid=true OK
- [x] **Fix webhook bug** : `licenses.update_one` ajouté `upsert=True` pour gérer les users qui paient avant d'avoir un doc license initialisé
- [x] Webhook fallback email : si `client_reference_id` absent, recherche par `customer_email` → user upgrade OK
- [x] **UI custom simplifiée** : suppression de density / reduce-motion / grain-toggle / accent colors
- [x] **Thème dark/light/system** : seul choix UI restant. Détection `prefers-color-scheme` pour "system", persistance localStorage + backend (`theme_mode`)
- [x] CSS light theme : palette claire avec glass-panels translucides white, grain réduit, gradients atténués
- [x] **Téléchargement code source** : déjà admin-only (403 pour non-admin, 200 + tarball pour admin) — confirmé
- [x] Logs webhook : warning si paiement sans user_id matchable

## Itération 5 — Polish + Web tools
- [x] **Quota daily 10 msg/jour** (au lieu de trial 7j) — reset minuit UTC via `daily_day` field
- [x] Pill "X / 10 aujourd'hui" remplace l'ancien essai
- [x] Paywall réécrit pour "Quota du jour atteint"
- [x] **Compte admin `huglostalatac@gmail.com`** ajouté en lifetime auto
- [x] **Web tools** : `web_search` (DDG) + `web_fetch` (BS4) intégrés à Émo
- [x] Persona enrichi : Émo sait chercher modèles 3D (Sketchfab, OpenGameArt, free3d, Poly Haven), docs, code, etc.
- [x] **UI customizable++** :
  - Densité de texte : Compact / Normal / Grand
  - Animations réduites (toggle)
  - Grain en fond (toggle)
  - Couleur d'accent (5 thèmes)
  - Instructions perso pour Émo
- [x] **Fix download** : passage de `<a href download>` à `fetch + blob` (résout les pbs cross-domain et `download` ignoré)
- [x] ToolCallCard supporte les nouveaux tools (icônes Search vert, Globe bleu) + résultats formatés (titres/URLs pour search, text+liens+images pour fetch)

## Tests
- 14/14 pytest backend ✅
- Web search testé live : "pygame documentation" → 3 résultats valides incluant pygame.org
- Web fetch testé live : titre + 25 liens extraits
- Émo end-to-end : `web_search "raylib official documentation"` → synthèse propre avec vraies URLs
- Admin lifetime auto : `huglostalatac@gmail.com` signup → status `admin_grant`, paid=true

## Comptes
- `hugo@example.com` / `emo-test-2026` (admin lifetime)
- `huglostalatac@gmail.com` / `emo2026` (admin lifetime)
- Tout autre signup → 10 msg/jour gratuits → paiement €20 → lifetime payé

## Backlog
### P1
- Tool `web_screenshot` (capture visuelle de page) — nécessite Playwright headless
- Installateur Windows graphique (.exe Inno Setup) avec UAC
- macOS notarization + .dmg
- Streaming live des sorties shell
- Tool `apply_diff` + vue diff Monaco
- Refactor `server.py` (>1200 lignes) en routers FastAPI (`routes/auth.py`, `routes/chat.py`, `routes/admin.py`, etc.)
- Test paiement Stripe live de bout en bout (mode test puis mode live)

### P2
- Voice in/out (Whisper + TTS)
- Bridge DeskBuddy (OLED SSD1306)
- Ollama provider
- CDN binaires
- Multi-projets / workspaces
