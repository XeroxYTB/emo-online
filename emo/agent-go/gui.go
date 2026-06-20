package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"
)

type guiState struct {
	mu          sync.Mutex
	backend     string
	token       string
	userName    string
	userEmail   string
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
			"backend":     st.backend,
			"token_set":   st.token != "",
			"user_name":   st.userName,
			"user_email":  st.userEmail,
			"running":     st.running,
			"connected":   st.connected,
			"error":       st.lastError,
			"permissions": st.perms,
			"site_url":    "https://xeroxytb.com/chat",
		})
	}))
	mux.HandleFunc("/api/login", withCORS(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, map[string]interface{}{"ok": false, "error": "JSON invalide"})
			return
		}
		st.mu.Lock()
		backend := st.backend
		st.mu.Unlock()
		if backend == "" {
			backend = resolveBackend("")
		}
		sess, name, email, err := st.loginToBackend(backend, strings.TrimSpace(body.Email), body.Password)
		if err != nil {
			writeJSON(w, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		agentTok, err := st.fetchAgentToken(backend, sess)
		if err != nil {
			writeJSON(w, map[string]interface{}{"ok": false, "error": err.Error()})
			return
		}
		st.mu.Lock()
		st.backend = backend
		st.token = agentTok
		st.userName = name
		st.userEmail = email
		st.lastError = ""
		_ = os.WriteFile(filepath.Join(appDataDir(), "token.txt"), []byte(agentTok), 0600)
		_ = os.WriteFile(filepath.Join(appDataDir(), "backend.txt"), []byte(backend+"\n"), 0600)
		st.mu.Unlock()
		writeJSON(w, map[string]interface{}{"ok": true, "name": name, "email": email})
	}))
	mux.HandleFunc("/api/logout", withCORS(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method", http.StatusMethodNotAllowed)
			return
		}
		st.mu.Lock()
		if st.cancel != nil {
			st.cancel()
		}
		st.token = ""
		st.userName = ""
		st.userEmail = ""
		st.running = false
		st.connected = false
		st.mu.Unlock()
		_ = os.Remove(filepath.Join(appDataDir(), "token.txt"))
		writeJSON(w, map[string]bool{"ok": true})
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
	guiURL := "http://" + addr

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		if guiAlreadyRunning(guiURL) {
			openBrowser(guiURL)
			return
		}
		fmt.Fprintf(os.Stderr, "[emo-agent] Port %s occupé (aucune GUI Emo détectée): %v\n", addr, err)
		os.Exit(1)
	}

	srv := &http.Server{Handler: mux}
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)

	serverErr := make(chan error, 1)
	go func() {
		if err := srv.Serve(ln); err != nil && err != http.ErrServerClosed {
			serverErr <- err
		}
	}()

	time.Sleep(350 * time.Millisecond)

	if runtime.GOOS == "windows" {
		go showNativeUI(guiURL)
		select {
		case <-sigCh:
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = srv.Shutdown(ctx)
		case err := <-serverErr:
			fmt.Fprintf(os.Stderr, "[emo-agent] GUI server failed: %v\n", err)
			os.Exit(1)
		}
		return
	}

	openBrowser(guiURL)
	select {
	case <-sigCh:
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(ctx)
	case err := <-serverErr:
		fmt.Fprintf(os.Stderr, "[emo-agent] GUI server failed: %v\n", err)
		os.Exit(1)
	}
}

func guiAlreadyRunning(guiURL string) bool {
	client := &http.Client{Timeout: 800 * time.Millisecond}
	resp, err := client.Get(guiURL)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
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

func (st *guiState) loginToBackend(backend, email, password string) (session, name, userEmail string, err error) {
	payload, _ := json.Marshal(map[string]string{"email": email, "password": password})
	req, err := http.NewRequest(http.MethodPost, backend+"/api/auth/login", bytes.NewReader(payload))
	if err != nil {
		return "", "", "", err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := httpClient.Do(req)
	if err != nil {
		return "", "", "", fmt.Errorf("API injoignable")
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		var er struct {
			Detail string `json:"detail"`
		}
		_ = json.Unmarshal(body, &er)
		if er.Detail != "" {
			return "", "", "", fmt.Errorf(er.Detail)
		}
		return "", "", "", fmt.Errorf("connexion refusée (%d)", resp.StatusCode)
	}
	var data struct {
		SessionToken string `json:"session_token"`
		Name         string `json:"name"`
		Email        string `json:"email"`
	}
	if err := json.Unmarshal(body, &data); err != nil {
		return "", "", "", err
	}
	return data.SessionToken, data.Name, data.Email, nil
}

func (st *guiState) fetchAgentToken(backend, session string) (string, error) {
	req, err := http.NewRequest(http.MethodGet, backend+"/api/agent/token", nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+session)
	resp, err := httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("token agent indisponible")
	}
	var data struct {
		AgentToken string `json:"agent_token"`
	}
	if err := json.Unmarshal(body, &data); err != nil {
		return "", err
	}
	if data.AgentToken == "" {
		return "", fmt.Errorf("token agent vide")
	}
	return data.AgentToken, nil
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
<title>Émo Agent</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Segoe UI,system-ui,sans-serif;background:#07040a;color:#f3e8ff;min-height:100vh}
.wrap{max-width:480px;margin:0 auto;padding:32px 20px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.brand svg{width:44px;height:44px}
.brand h1{margin:0;font-size:1.5rem;font-weight:600}
.sub{color:#a89bbd;font-size:13px;line-height:1.55;margin:0 0 22px}
.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:20px;margin-bottom:14px}
.card h2{margin:0 0 12px;font-size:13px;text-transform:uppercase;letter-spacing:.14em;color:#a89bbd}
.field{margin-bottom:12px}
.field label{display:block;font-size:12px;color:#a89bbd;margin-bottom:6px}
.field input{width:100%;padding:11px 13px;border-radius:12px;border:1px solid rgba(255,255,255,.1);background:#0f0818;color:#fff;font-size:14px}
.status{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:14px;padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.03)}
.dot{width:9px;height:9px;border-radius:50%;background:#71717a;flex-shrink:0}
.dot.on{background:#34d399;box-shadow:0 0 10px #34d39999}
.perm label{display:flex;align-items:center;gap:10px;padding:7px 0;font-size:14px;cursor:pointer}
.btn{width:100%;padding:14px;border:none;border-radius:14px;font-weight:600;font-size:14px;cursor:pointer;margin-top:8px;transition:transform .12s}
.btn:active{transform:scale(.98)}
.btn-primary{background:linear-gradient(135deg,#a855f7,#7c3aed);color:#0a0510;box-shadow:0 0 24px rgba(168,85,247,.35)}
.btn-ghost{background:rgba(255,255,255,.06);color:#e9d5ff;border:1px solid rgba(255,255,255,.08)}
.btn-danger{background:rgba(239,68,68,.12);color:#fca5a5;border:1px solid rgba(239,68,68,.25)}
.note{font-size:11px;color:#6d5f82;line-height:1.55;margin-top:14px}
.hidden{display:none!important}
.userline{font-size:14px;margin:0 0 4px}.useremail{font-size:12px;color:#a89bbd;margin:0 0 12px}
a.link{color:#c4b5fd}
</style></head><body><div class="wrap">
<div class="brand"><svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg"><rect x="8" y="17" width="14" height="14" rx="4.5" fill="#8b5cf6"/><rect x="26" y="17" width="14" height="14" rx="4.5" fill="#8b5cf6"/></svg><h1>Émo Agent</h1></div>
<p class="sub">Interface locale — même compte que sur <a class="link" href="https://xeroxytb.com/chat" target="_blank">xeroxytb.com</a>. Pilote ton PC depuis n&apos;importe quel appareil.</p>

<div id="loginView">
<div class="card"><h2>Connexion</h2>
<div class="field"><label>Email</label><input type="email" id="loginEmail" autocomplete="username"/></div>
<div class="field"><label>Mot de passe</label><input type="password" id="loginPass" autocomplete="current-password"/></div>
<button class="btn btn-primary" id="loginBtn">Se connecter</button>
<p id="loginErr" class="note" style="color:#fca5a5"></p>
</div></div>

<div id="dashView" class="hidden">
<div class="status"><span class="dot" id="dot"></span><span id="statusText">Hors ligne</span></div>
<p class="userline" id="userName"></p><p class="useremail" id="userEmail"></p>
<div class="card perm"><h2>Permissions locales</h2>
<label><input type="checkbox" id="p_shell"/> Commandes shell</label>
<label><input type="checkbox" id="p_read"/> Lire / lister fichiers</label>
<label><input type="checkbox" id="p_grep"/> Recherche (grep)</label>
<label><input type="checkbox" id="p_write"/> Écrire / modifier</label>
<label><input type="checkbox" id="p_delete"/> Supprimer</label>
</div>
<button class="btn btn-primary" id="startBtn">Démarrer l&apos;agent</button>
<button class="btn btn-ghost" id="stopBtn">Arrêter</button>
<button class="btn btn-danger" id="logoutBtn">Se déconnecter</button>
<p class="note">L&apos;agent doit rester actif pour exécuter des actions depuis le site web (téléphone, tablette, autre PC).</p>
</div>
</div>
<script>
const loginView=document.getElementById('loginView'),dashView=document.getElementById('dashView');
async function refresh(){
  const r=await fetch('/api/state');const s=await r.json();
  const logged=s.token_set;
  loginView.classList.toggle('hidden',logged); dashView.classList.toggle('hidden',!logged);
  if(!logged)return;
  userName.textContent=s.user_name||'Compte Émo'; userEmail.textContent=s.user_email||'';
  const p=s.permissions||{};
  p_shell.checked=p.allow_shell!==false; p_read.checked=p.allow_read!==false;
  p_grep.checked=p.allow_grep!==false; p_write.checked=!!p.allow_write; p_delete.checked=!!p.allow_delete;
  dot.className='dot'+(s.running&&s.connected?' on':'');
  statusText.textContent=s.running?(s.connected?'En ligne — prêt pour le site':'Connexion…'):'Hors ligne';
  if(s.error)statusText.textContent=s.error;
}
async function savePerms(){
  await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
    permissions:{allow_shell:p_shell.checked,allow_read:p_read.checked,allow_grep:p_grep.checked,allow_write:p_write.checked,allow_delete:p_delete.checked,enabled:true}
  })});
}
loginBtn.onclick=async()=>{
  loginErr.textContent=''; loginBtn.disabled=true;
  try{
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:loginEmail.value,password:loginPass.value})});
    const d=await r.json(); if(!d.ok)throw new Error(d.error||'Erreur');
    await savePerms(); await fetch('/api/start',{method:'POST'}); refresh();
  }catch(e){loginErr.textContent=e.message||'Erreur';}finally{loginBtn.disabled=false;}
};
loginPass.addEventListener('keydown',e=>{if(e.key==='Enter')loginBtn.click();});
startBtn.onclick=async()=>{await savePerms();await fetch('/api/start',{method:'POST'});refresh();};
stopBtn.onclick=async()=>{await fetch('/api/stop',{method:'POST'});refresh();};
logoutBtn.onclick=async()=>{await fetch('/api/logout',{method:'POST'});refresh();};
setInterval(refresh,2000);refresh();
</script></body></html>`
