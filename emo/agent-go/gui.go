package main

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type guiState struct {
	mu          sync.Mutex
	backend     string
	token       string
	perms       Permissions
	running     bool
	cancel      context.CancelFunc
	lastError   string
	connected   bool
}

func runGUI(initialBackend, initialToken string) {
	st := &guiState{
		backend: initialBackend,
		token:   initialToken,
		perms:   loadPermissions(),
	}
	if st.backend == "" {
		st.backend = resolveBackend("")
	}
	if st.token == "" {
		st.token = resolveToken("")
	}

	withCORS := func(h http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin == "https://xeroxytb.com" || origin == "https://www.xeroxytb.com" ||
				origin == "https://xeroxytb.github.io" ||
				strings.HasPrefix(origin, "http://127.0.0.1") || strings.HasPrefix(origin, "http://localhost") {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			}
			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}
			h(w, r)
		}
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write([]byte(guiHTML))
	})
	mux.HandleFunc("/api/state", withCORS(func(w http.ResponseWriter, r *http.Request) {
		st.mu.Lock()
		defer st.mu.Unlock()
		writeJSON(w, map[string]interface{}{
			"backend":   st.backend,
			"token_set": st.token != "",
			"running":   st.running,
			"connected": st.connected,
			"error":     st.lastError,
			"permissions": st.perms,
		})
	}))
	mux.HandleFunc("/api/save", withCORS(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Backend     string      `json:"backend"`
			Token       string      `json:"token"`
			Permissions Permissions `json:"permissions"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		st.mu.Lock()
		if strings.TrimSpace(body.Backend) != "" {
			st.backend = strings.TrimRight(strings.TrimSpace(body.Backend), "/")
		}
		if strings.TrimSpace(body.Token) != "" {
			st.token = strings.TrimSpace(body.Token)
		}
		st.perms = body.Permissions
		st.perms.Enabled = true
		_ = savePermissions(st.perms)
		if st.token != "" {
			_ = os.WriteFile(filepath.Join(appDataDir(), "token.txt"), []byte(st.token), 0600)
		}
		if st.backend != "" {
			_ = os.WriteFile(filepath.Join(appDataDir(), "backend.txt"), []byte(st.backend+"\n"), 0600)
		}
		st.mu.Unlock()
		writeJSON(w, map[string]bool{"ok": true})
	}))
	mux.HandleFunc("/api/start", withCORS(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method", http.StatusMethodNotAllowed)
			return
		}
		st.mu.Lock()
		defer st.mu.Unlock()
		if st.token == "" {
			writeJSON(w, map[string]interface{}{"ok": false, "error": "Token requis (copie depuis le site Emo > Agent)"})
			return
		}
		if st.running {
			writeJSON(w, map[string]bool{"ok": true})
			return
		}
		ctx, cancel := context.WithCancel(context.Background())
		st.cancel = cancel
		st.running = true
		st.lastError = ""
		go st.runAgent(ctx)
		writeJSON(w, map[string]bool{"ok": true})
	}))
	mux.HandleFunc("/api/stop", withCORS(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method", http.StatusMethodNotAllowed)
			return
		}
		st.mu.Lock()
		if st.cancel != nil {
			st.cancel()
		}
		st.running = false
		st.connected = false
		st.mu.Unlock()
		writeJSON(w, map[string]bool{"ok": true})
	}))

	addr := "127.0.0.1:17841"
	go func() {
		_ = http.ListenAndServe(addr, mux)
	}()
	time.Sleep(300 * time.Millisecond)
	openBrowser("http://" + addr)
	select {}
}

func (st *guiState) runAgent(ctx context.Context) {
	st.mu.Lock()
	backend, token := st.backend, st.token
	st.mu.Unlock()

	defer func() {
		st.mu.Lock()
		st.running = false
		st.connected = false
		st.mu.Unlock()
	}()

	runWithStatus(ctx, backend, token, func(ok bool) {
		st.mu.Lock()
		st.connected = ok
		st.mu.Unlock()
	})
}

func (st *guiState) checkPermissions(tool string) bool {
	st.mu.Lock()
	defer st.mu.Unlock()
	return st.perms.allowsTool(tool)
}

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("cmd", "/c", "start", "", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

const guiHTML = `<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Emo Agent — Permissions locales</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:#07040a;color:#f3e8ff;min-height:100vh}
.wrap{max-width:520px;margin:0 auto;padding:28px 20px}
h1{font-size:1.4rem;margin:0 0 4px}p.sub{color:#a89bbd;font-size:13px;margin:0 0 24px;line-height:1.5}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px;margin-bottom:16px}
label{display:flex;align-items:center;gap:10px;padding:8px 0;font-size:14px;cursor:pointer}
input[type=text]{width:100%;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.1);background:#0f0818;color:#fff;margin-top:6px}
.status{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:16px}
.dot{width:8px;height:8px;border-radius:50%;background:#71717a}
.dot.on{background:#34d399;box-shadow:0 0 8px #34d39988}
.btn{width:100%;padding:14px;border:none;border-radius:14px;font-weight:600;font-size:14px;cursor:pointer;margin-top:8px}
.btn-primary{background:#a855f7;color:#0a0510}.btn-danger{background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid rgba(239,68,68,.3)}
.note{font-size:11px;color:#6d5f82;margin-top:16px;line-height:1.5}
</style></head><body><div class="wrap">
<h1>Emo Agent</h1>
<p class="sub">Contrôle local uniquement. Les LLM et paiements restent sur le site Emo en ligne.</p>
<div class="status"><span class="dot" id="dot"></span><span id="statusText">Hors ligne</span></div>
<div class="card">
<label>Backend (site Emo)</label>
<input type="text" id="backend" placeholder="https://votre-app.onrender.com"/>
<label style="margin-top:12px">Token agent (menu Agent du site)</label>
<input type="text" id="token" placeholder="Colle ton token ici"/>
</div>
<div class="card"><strong style="font-size:13px">Permissions locales</strong>
<label><input type="checkbox" id="p_shell"/> Commandes shell</label>
<label><input type="checkbox" id="p_read"/> Lire fichiers / lister</label>
<label><input type="checkbox" id="p_grep"/> Recherche (grep)</label>
<label><input type="checkbox" id="p_write"/> Écrire / modifier fichiers</label>
<label><input type="checkbox" id="p_delete"/> Supprimer fichiers</label>
</div>
<button class="btn btn-primary" id="startBtn">Démarrer l'agent</button>
<button class="btn btn-danger" id="stopBtn">Arrêter</button>
<p class="note">Ne ferme pas cette fenêtre tant que tu veux qu'Émo pilote ton PC. Tu peux minimiser le navigateur.</p>
</div>
<script>
async function refresh(){
  const r=await fetch('/api/state');const s=await r.json();
  backend.value=s.backend||''; if(!token.value&&s.token_set) token.placeholder='(token enregistré)';
  const p=s.permissions||{};
  p_shell.checked=p.allow_shell!==false; p_read.checked=p.allow_read!==false;
  p_grep.checked=p.allow_grep!==false; p_write.checked=!!p.allow_write; p_delete.checked=!!p.allow_delete;
  dot.className='dot'+(s.running&&s.connected?' on':'');
  statusText.textContent=s.running?(s.connected?'Connecté au site Emo':'Connexion…'):'Hors ligne';
  if(s.error) statusText.textContent=s.error;
}
async function save(){
  await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    backend:backend.value, token:token.value,
    permissions:{allow_shell:p_shell.checked,allow_read:p_read.checked,allow_grep:p_grep.checked,allow_write:p_write.checked,allow_delete:p_delete.checked,enabled:true}
  })});
}
startBtn.onclick=async()=>{await save();await fetch('/api/start',{method:'POST'});refresh();};
stopBtn.onclick=async()=>{await fetch('/api/stop',{method:'POST'});refresh();};
setInterval(refresh,2000);refresh();
</script></body></html>`
