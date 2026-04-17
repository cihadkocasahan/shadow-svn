import os
import subprocess
import json
import shutil
import time
import threading
from urllib.parse import urlparse
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- ENCRYPTED .ENV READER (v3.1) ---
# Reads data/.secret.key and transparently decrypts env vars set by setup scripts.
# Falls back gracefully to plain-text values if no key exists.
def _load_fernet():
    key_path = "/data/.secret.key"
    if not os.path.exists(key_path):
        return None
    try:
        from cryptography.fernet import Fernet
        with open(key_path, "rb") as f:
            return Fernet(f.read())
    except Exception:
        return None

def _decrypt_env(name):
    """Return decrypted value of an env variable, or the raw value if not encrypted."""
    raw = os.environ.get(name, "")
    if not raw:
        return raw
    fernet = _load_fernet()
    if fernet is None:
        return raw
    try:
        return fernet.decrypt(raw.encode()).decode()
    except Exception:
        return raw  # plain-text fallback

_FERNET = _load_fernet()  # load once at startup

# --- PORTABLE CONFIG & PATHS (v2.7) ---
DATA_ROOT = "/data"
REPO_ROOT = os.path.join(DATA_ROOT, "svn")
CONFIG_FILE = os.path.join(DATA_ROOT, "config.json")
ACTIVE_SYNCS = set() # Track running tasks globally
from datetime import datetime

os.makedirs(REPO_ROOT, exist_ok=True)
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"projects": {}, "credentials": {}, "dashboard_pass": ""}, f, indent=4)

config_lock = threading.Lock()

# v3.1.0 - Shadow SVN [Encrypted .env + Security]
scheduler = BackgroundScheduler()
scheduler.start()

def load_config():
    with config_lock:
        if not os.path.exists(CONFIG_FILE): return {"projects": {}, "credentials": {}, "dashboard_pass": ""}
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                data.setdefault("projects", {})
                data.setdefault("credentials", {})
                data.setdefault("dashboard_pass", "")
                return data
        except: return {"projects": {}, "credentials": {}, "dashboard_pass": ""}

def save_config(config):
    with config_lock:
        try:
            with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)
        except: pass

def get_domain(url):
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    except: return url

def get_credentials(project_cfg, config):
    url = project_cfg.get("url", "")
    domain = get_domain(url)
    # Decrypt env vars transparently
    env_user = _decrypt_env("SVN_USER")
    env_pass = _decrypt_env("SVN_PASS")
    u = project_cfg.get("username") or config.get("credentials", {}).get(domain, {}).get("u") or env_user
    p = project_cfg.get("password") or config.get("credentials", {}).get(domain, {}).get("p") or env_pass
    return u, p

@app.before_request
def check_auth():
    if request.path in ['/login', '/api/auth/login'] or request.path.startswith('/static'): return
    config = load_config()
    if not config.get('dashboard_pass'): return  # No password set = open access
    if not session.get('authorized'):
        return redirect(url_for('login_page'))

@app.route('/login')
def login_page(): return render_template_string(LOGIN_TEMPLATE)

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    config = load_config()
    data = request.json
    if data.get('password') == config.get('dashboard_pass'):
        session['authorized'] = True
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Geçersiz Şifre'}), 401

@app.route('/api/auth/logout')
def api_logout():
    session.pop('authorized', None)
    return redirect(url_for('login_page'))

# --- CORE API ---

def get_local_info(project_name):
    path = os.path.join(REPO_ROOT, project_name)
    if not os.path.exists(path): return "---", "...", "---"
    try:
        url = f"file://{path}"
        info = subprocess.check_output(["svn", "info", url]).decode()
        l_rev = [l for l in info.split('\n') if l.startswith("Last Changed Rev: ")][0].split(": ")[1]
        msg = subprocess.check_output(["svnlook", "log", path, "-r", l_rev]).decode().strip()
        auth = [l for l in info.split('\n') if l.startswith("Last Changed Author: ")][0].split(": ")[1].strip()
        return l_rev, msg, auth
    except: return "---", "...", "---"

def ensure_project_repo(name, url, user=None, pwd=None):
    path = os.path.join(REPO_ROOT, name)
    if not os.path.exists(path):
        try:
            print(f"[Shadow SVN] Init: {name}")
            subprocess.run(["svnadmin", "create", path], check=True)
            hook = os.path.join(path, "hooks/pre-revprop-change")
            with open(hook, 'w') as f: f.write("#!/bin/sh\nexit 0")
            os.chmod(hook, 0o755)
            u, p = user, pwd
            if not u or not p:
                config = load_config()
                u, p = get_credentials({"url": url}, config)
            subprocess.run(["svnsync", "init", f"file://{path}", url, "--source-username", u, "--source-password", p, "--non-interactive", "--trust-server-cert"], check=True)
            return True
        except:
            if os.path.exists(path): shutil.rmtree(path)
            return False
    return True

def run_sync_task(name):
    if name in ACTIVE_SYNCS: return # Skip if already running
    config = load_config(); p_cfg = config["projects"].get(name)
    if not p_cfg: return
    ACTIVE_SYNCS.add(name)
    try:
        u, p = get_credentials(p_cfg, config); path = os.path.join(REPO_ROOT, name)
        subprocess.check_output(["svnsync", "sync", f"file://{path}", "--source-username", u, "--source-password", p, "--non-interactive", "--trust-server-cert"], stderr=subprocess.STDOUT)
        rev, msg, auth = get_local_info(name)
        p_cfg.update({"last_local_rev": rev, "last_msg": msg, "local_author": auth})
        save_config(config)
    except subprocess.CalledProcessError as e:
        if "lock" in e.output.decode().lower(): subprocess.run(["svn", "propdel", "svn:sync-lock", "--revprop", "-r", "0", f"file://{path}", "--non-interactive"])
    finally:
        ACTIVE_SYNCS.remove(name) if name in ACTIVE_SYNCS else None

def update_scheduler():
    config = load_config(); current_jobs = {job.id: job for job in scheduler.get_jobs()}
    for name, p in config["projects"].items():
        job_id = f"sync_{name}"
        if p.get("enabled"):
            interval = int(p['interval'])
            if job_id not in current_jobs:
                # New or just enabled: trigger immediately + schedule
                scheduler.add_job(id=job_id, func=run_sync_task, args=[name], trigger=IntervalTrigger(seconds=interval), next_run_time=datetime.now(), replace_existing=True)
            elif current_jobs[job_id].trigger.interval.total_seconds() != interval:
                # Interval changed: update trigger
                scheduler.reschedule_job(job_id, trigger=IntervalTrigger(seconds=interval))
        else:
            # Disabled: remove if exists
            if job_id in current_jobs: scheduler.remove_job(job_id)

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/projects', methods=['GET', 'POST'])
def api_projects_manager():
    config = load_config()
    if request.method == 'GET':
        out = []
        for name, p in config["projects"].items():
            l_rev, l_msg, l_auth = get_local_info(name)
            now = time.time(); ttl = 60; last_check = p.get("last_remote_check", 0)
            r_rev = p.get("last_remote_rev", "---"); r_auth = p.get("remote_author", "---")
            is_synced = (l_auth == r_auth) and (l_auth != "---")
            is_running = name in ACTIVE_SYNCS
            # If disabled, we still want to show the status but we don't fetch remote info automatically
            if not p.get("enabled"):
                out.append({"id": name, "url": p["url"], "enabled": False, "interval": p["interval"], "local": p.get("last_local_rev", "---"), "remote": r_rev, "message": p.get("last_msg", "..."), "is_synced": is_synced, "is_running": is_running, "check_age": int(now - last_check), "checkout_url": f"svn://{request.host.split(':')[0]}:13080/{name}"})
                continue

            if now - last_check > ttl or r_rev == "---":
                try:
                    u, pw = get_credentials(p, config)
                    r_info = subprocess.check_output(["svn", "info", p["url"], "--username", u, "--password", pw, "--non-interactive", "--trust-server-cert"]).decode()
                    r_rev = [l for l in r_info.split('\n') if l.startswith("Last Changed Rev: ")][0].split(": ")[1]
                    r_auth = [l for l in r_info.split('\n') if l.startswith("Last Changed Author: ")][0].split(": ")[1].strip()
                    p.update({"last_remote_rev": r_rev, "last_remote_check": now, "remote_author": r_auth})
                    save_config(config)
                except: pass
            is_synced = (l_auth == r_auth) and (l_auth != "---")
            is_running = name in ACTIVE_SYNCS
            display_rev = r_rev if is_synced else l_rev
            out.append({"id": name, "url": p["url"], "enabled": p["enabled"], "interval": p["interval"], "local": display_rev, "remote": r_rev, "message": l_msg, "is_synced": is_synced, "is_running": is_running, "check_age": int(now - p.get("last_remote_check", 0)), "checkout_url": f"svn://{request.host.split(':')[0]}:13080/{name}"})
        return jsonify(out)
    else:
        data = request.json
        name = data["name"].strip().replace(" ", "_"); url = data["url"].strip()
        if not name or not url: return jsonify({"error": "Geçersiz Veri"}), 400
        is_new = name not in config["projects"]
        if data.get("username") and data.get("password"):
            domain = get_domain(url)
            config.setdefault("credentials", {})[domain] = {"u": data["username"], "p": data["password"]}
        config["projects"][name] = {"url": url, "interval": int(data.get("interval", 3600)), "enabled": data.get("enabled", True), "username": data.get("username", ""), "password": data.get("password", "")}
        if is_new:
            success = ensure_project_repo(name, url, data.get("username"), data.get("password"))
            if not success: return jsonify({"error": "Repo Oluşturulamadı"}), 500
        save_config(config); update_scheduler(); return jsonify({"status": "ok"})

@app.route('/api/projects/<name>/toggle', methods=['POST'])
def api_toggle_project(name):
    config = load_config()
    if name in config["projects"]:
        config["projects"][name]["enabled"] = not config["projects"][name].get("enabled", True)
        save_config(config); update_scheduler(); return jsonify({"status": "ok", "enabled": config["projects"][name]["enabled"]})
    return jsonify({"error": "Not Found"}), 404

@app.route('/api/projects/<name>', methods=['PUT', 'DELETE'])
def api_edit_delete_project(name):
    config = load_config()
    if name not in config["projects"]: return jsonify({"error": "Not Found"}), 404
    
    if request.method == 'PUT':
        data = request.json
        p = config["projects"][name]
        p["interval"] = int(data.get("interval", p["interval"]))
        if data.get("username") and data.get("password"):
            domain = get_domain(p["url"])
            config.setdefault("credentials", {})[domain] = {"u": data["username"], "p": data["password"]}
            p["username"] = data["username"]
            p["password"] = data["password"]
        save_config(config); update_scheduler(); return jsonify({"status": "updated"})
    
    # DELETE logic
    del config["projects"][name]; path = os.path.join(REPO_ROOT, name)
    save_config(config); update_scheduler()
    
    # Run slow file deletion in background
    def safe_remove(p):
        if os.path.exists(p): shutil.rmtree(p)
    threading.Thread(target=safe_remove, args=(path,)).start()
    
    return jsonify({"status": "deleted"})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    config = load_config()
    if request.method == 'GET':
        return jsonify({"dashboard_pass_set": bool(config.get("dashboard_pass"))})
    else:
        data = request.json
        new_pass = data.get("dashboard_pass", "").strip()
        config["dashboard_pass"] = new_pass
        save_config(config)
        # Clear session if password removed (open access restored)
        if not new_pass:
            session.pop('authorized', None)
        return jsonify({"status": "saved", "pass_set": bool(new_pass)})

@app.route('/api/sync/manual', methods=['POST'])
def api_manual_sync():
    name = request.args.get('name')
    if name: threading.Thread(target=run_sync_task, args=(name,)).start()
    return jsonify({"status": "Triggered"})

# --- UI TEMPLATES (v2.7 Security & Optional Auth) ---

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'><title>Shadow SVN - Login</title>
    <style>
        body { font-family: 'Inter', sans-serif; background: #F0F4F8; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 400px; text-align: center; }
        h1 { color: #01579B; font-weight: 900; margin-bottom: 8px; }
        .hint { font-size: 11px; color: #90A4AE; font-weight: 700; margin-bottom: 28px; }
        input { width: 100%; padding: 14px; margin-bottom: 16px; border-radius: 12px; border: 2px solid #E2EBF1; font-size: 16px; box-sizing: border-box; }
        button { width: 100%; padding: 14px; background: #0288D1; color: white; border: none; border-radius: 12px; font-weight: 900; cursor: pointer; font-size: 14px; }
        .err { color: #dc2626; font-size: 12px; margin-top: 10px; font-weight: 700; display: none; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>Shadow SVN</h1>
        <p class="hint">Bu dashboard şifre korumalıdır.</p>
        <input type="password" id="pw" placeholder="Şifre" onkeydown="if(event.key==='Enter') login()">
        <button onclick="login()">GİRİŞ YAP</button>
        <div class="err" id="err">❌ Geçersiz şifre</div>
    </div>
    <script>
        async function login() {
            const res = await fetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({password: document.getElementById('pw').value}) });
            if(res.ok) location.href='/';
            else { document.getElementById('err').style.display='block'; }
        }
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang='tr'>
<head>
    <meta charset='UTF-8'><title>Shadow SVN Dashboard</title>
    <style>
        :root { --brand-primary: #0288D1; --brand-deep: #01579B; --page-bg: #F0F4F8; --card-bg: #FFFFFF; --card-border: #D0DFE8; --text-main: #012B3D; --text-muted: #546E7A; --accent-fire: #FF5722; --synced-green: #2E7D32; }
        * { box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--page-bg); color: var(--text-main); margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { width: 100%; max-width: 1200px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid var(--card-border); padding-bottom: 15px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }
        .card { background: var(--card-bg); border-radius: 20px; border: 1px solid var(--card-border); padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); position: relative; transition: all 0.2s; }
        .card:hover { transform: translateY(-3px); }
        .card.disabled { border-style: dashed; border-color: #CFD8DC; }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .project-name { font-size: 18px; font-weight: 900; color: var(--brand-deep); text-transform: uppercase; }
        .scheduler-tag { font-size: 9px; font-weight: 900; padding: 2px 6px; border-radius: 4px; margin-top: 4px; display: inline-block; }
        .scheduler-on { background: #E3F2FD; color: #1976D2; border: 1px solid #BBDEFB; }
        .scheduler-off { background: #ECEFF1; color: #546E7A; border: 1px solid #CFD8DC; }
        .sync-badge { font-size: 10px; font-weight: 900; padding: 4px 10px; border-radius: 12px; background: #EEE; color: #777; }
        .synced { background: #E8F5E9; color: var(--synced-green); display: block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .spin { animation: spin 2s linear infinite; display: inline-block; }
        .stat-line { display: flex; justify-content: space-between; margin-bottom: 15px; align-items: baseline; }
        .val { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 900; color: var(--brand-primary); }
        .msg-box { background: #F8FAFC; border-radius: 10px; padding: 12px; font-size: 12px; height: 100px; overflow-y: auto; white-space: pre-wrap; margin-bottom: 15px; border: 1px solid #E2EBF1; color: var(--text-main); line-height: 1.4; }
        .url-row { font-size: 10px; font-family: monospace; background: #f1f5f9; padding: 10px; border-radius: 6px; margin-bottom: 15px; border-left: 3px solid var(--brand-primary); display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .url-text { text-overflow: ellipsis; overflow: hidden; white-space: nowrap; flex: 1; }
        .btn-copy { background: white; border: 1px solid #D0DFE8; padding: 4px 8px; border-radius: 4px; color: var(--brand-primary); font-size: 9px; cursor: pointer; font-weight: 800; }
        .btn-copy:hover { background: var(--brand-primary); color: white; }
        .ctrls { display: flex; gap: 10px; align-items: center; justify-content: space-between; }
        .add-card { border: 2px dashed var(--brand-primary); display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; background: rgba(2, 136, 209, 0.03); min-height: 400px; }
        button { border: none; padding: 10px; border-radius: 12px; cursor: pointer; font-weight: 800; font-size: 11px; text-transform: uppercase; white-space: nowrap; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
        .btn-fire { background: var(--accent-fire); color: white; width: 44px; height: 44px; }
        .btn-del { background: #fee2e2; color: #dc2626; width: 44px; height: 44px; }
        .btn-toggle { background: #EEE; color: #444; width: 44px; height: 44px; }
        .btn-gear { background: #F1F5F9; color: #475569; width: 44px; height: 44px; }
        button:hover { filter: brightness(0.9); transform: scale(1.05); }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        modal { display:none; position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:100; align-items:center; justify-content:center; backdrop-filter: blur(4px); }
        .modal-content { background: white; padding: 40px; border-radius: 24px; width: 700px; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
        .form-group { margin-bottom: 20px; text-align: left; }
        .form-label { font-size: 12px; font-weight: 900; color: var(--brand-deep); margin-bottom: 8px; display: block; text-transform: uppercase; }
        input { width: 100%; padding: 14px; border-radius: 12px; border: 2px solid #E2EBF1; font-weight: 600; font-size: 14px; }
        .modal-footer { display:flex; gap:10px; margin-top:20px; }
        /* Toast */
        #toast { position:fixed; bottom:30px; left:50%; transform:translateX(-50%) translateY(20px); background:#1e293b; color:white; padding:12px 24px; border-radius:12px; font-size:13px; font-weight:700; opacity:0; transition:all 0.3s; z-index:999; pointer-events:none; }
        #toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
        /* Confirm Modal */
        #confirm-modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:200; align-items:center; justify-content:center; }
        #confirm-modal .box { background:white; border-radius:20px; padding:30px; width:360px; text-align:center; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        #confirm-modal h3 { margin:0 0 8px; color:#012B3D; font-weight:900; }
        #confirm-modal p { color:#546E7A; font-size:13px; margin-bottom:24px; }
        #confirm-modal .actions { display:flex; gap:10px; }
        #confirm-modal .actions button { flex:1; padding:12px; border-radius:10px; font-weight:800; font-size:12px; border:none; cursor:pointer; }
    </style>
</head>
<body>
    <div class="container header">
        <a href="/" style="text-decoration:none;"><h1 style="font-weight:900; color:var(--brand-deep); margin:0; cursor:pointer;">Shadow SVN <span style="font-size:12px; opacity:0.6;">v0.1.1</span></h1></a>
        <div style="font-size: 11px; font-weight:900; color:var(--text-muted); text-align:right; display: flex; align-items: center; gap: 10px;" id="header-actions">
            <span id="status-dot">● ACTIVE</span>
            <button onclick="openSettings()" style="padding:4px 8px; font-size:9px; background:#EEE;">AYARLAR ⚙️</button>
            <button id="btn-logout" onclick="location.href='/api/auth/logout'" style="padding:4px 8px; font-size:9px; background:#FEE2E2; color:#DC2626; display:none;">ÇIKIŞ</button>
        </div>
    </div>
    <div id="toast"></div>
    <div id="confirm-modal"><div class="box"><h3 id="confirm-title">Emin misiniz?</h3><p id="confirm-msg"></p><div class="actions"><button id="confirm-btn" onclick="confirmAction()" style="background:#dc2626;color:white;">SİL</button><button onclick="document.getElementById('confirm-modal').style.display='none'" style="background:#EEE;">VAZGEÇ</button></div></div></div>
    <div class="container grid" id="project-grid"></div>

    <modal id="add-modal">
        <div class="modal-content">
            <h2 style="margin-top:0; font-weight:900; color:var(--brand-deep);">Yeni Mirror Ekle</h2>
            <div class="form-group"><label class="form-label">PROJE ADI</label><input type="text" id="p-name" placeholder="Örn: Master_Root"></div>
            <div class="form-group"><label class="form-label">UZAK SVN URL</label><input type="text" id="p-url" placeholder="https://svn.example.com/repo/trunk"></div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                <div class="form-group"><label class="form-label">SVN KULLANICI ADI</label><input type="text" id="p-user" placeholder="Kullanıcı adı"></div>
                <div class="form-group"><label class="form-label">SVN ŞİFRESİ</label><input type="password" id="p-pass" placeholder="Şifre"></div>
            </div>
            <div class="form-group"><label class="form-label">GÜNCELLEME SIKLIĞI (DAKİKA)</label><input type="number" id="p-interval" value="20" min="1"></div>
            <p style="font-size:11px; color:#90A4AE; font-weight:700;">* Kullanıcı adı ve şifre girilmezse .env (SVN_USER/SVN_PASS) değerleri kullanılır.</p>
            <div class="modal-footer"><button onclick="saveProject()" style="background:var(--brand-primary); color:white; flex:2; height:50px;">BAŞLAT</button><button onclick="closeModal('add-modal')" style="background:#EEE; flex:1;">İPTAL</button></div>
        </div>
    </modal>

    <modal id="settings-modal">
        <div class="modal-content">
            <h2 style="margin-top:0; font-weight:900; color:var(--brand-deep);">Shadow SVN Ayarları</h2>
            <div class="form-group">
                <label class="form-label">DASHBOARD ŞİFRESİ</label>
                <input type="password" id="s-pass" placeholder="Şifre girin (boş = şifresiz açık erişim)">
            </div>
            <p style="font-size:11px; color:#90A4AE; font-weight:700;">* Boş bırakırsanız login ekranı devre dışı kalır, dashboard herkese açık olur.</p>
            <div class="modal-footer"><button onclick="saveSettings()" style="background:var(--brand-primary); color:white; flex:1; height:50px;">AYARLARI KAYDET</button><button onclick="closeModal('settings-modal')" style="background:#EEE; flex:1;">KAPAT</button></div>
        </div>
    </modal>

    <modal id="edit-modal">
        <div class="modal-content">
            <h2 style="margin-top:0; font-weight:900; color:var(--brand-deep);">Proje Ayarlarını Düzenle</h2>
            <input type="hidden" id="e-id">
            <div class="form-group"><label class="form-label">GÜNCELLEME SIKLIĞI (DAKİKA)</label><input type="number" id="e-interval" min="1"></div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                <div class="form-group"><label class="form-label">SVN KULLANICI ADI</label><input type="text" id="e-user" placeholder="Değiştirmece boş bırak"></div>
                <div class="form-group"><label class="form-label">SVN ŞİFRESİ</label><input type="password" id="e-pass" placeholder="Değiştirmece boş bırak"></div>
            </div>
            <div class="modal-footer"><button onclick="saveEdit()" style="background:var(--brand-primary); color:white; flex:2; height:50px;">GÜNCELLE</button><button onclick="closeModal('edit-modal')" style="background:#EEE; flex:1;">İPTAL</button></div>
        </div>
    </modal>

    <script>
        function showToast(msg, duration=3000) {
            const t = document.getElementById('toast');
            t.textContent = msg; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), duration);
        }
        function copyTo(txt) {
            navigator.clipboard.writeText(txt).then(() => showToast('📋 Kopyalandı!'));
        }
        async function loadProjects() {
            try {
                const res = await fetch('/api/projects'); if(!res.ok) return;
                const data = await res.json(); const grid = document.getElementById('project-grid'); grid.innerHTML = '';
                data.forEach(p => {
                    const runningIcon = p.is_running ? '<svg class="spin" style="width:12px;height:12px;margin-right:5px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>' : '';
                    grid.innerHTML += `
                        <div class="card ${p.enabled ? '' : 'disabled'}">
                            <div class="card-header">
                                <div>
                                    <span class="project-name">${p.id}</span>
                                    <div style="font-size:9px; color:#999; max-width:250px; overflow:hidden; text-overflow:ellipsis;">${p.url}</div>
                                    <div class="scheduler-tag ${p.enabled ? 'scheduler-on' : 'scheduler-off'}">
                                        ${p.enabled ? '⏱️ OTOMATİK AKTİF' : '❌ OTOMATİK KAPALI'}
                                    </div>
                                    <div style="font-size:9px; font-weight:900; color:var(--brand-primary); margin-top:4px;">⏱️ Her ${p.interval/60} dk bir.</div>
                                </div>
                                <span class="sync-badge ${p.is_synced ? 'synced' : ''}">${runningIcon} ${p.is_synced ? '✓ GÜNCEL' : 'SYNC...'}</span>
                            </div>
                            <div class="stat-line">
                                <div><span style="font-size:10px; font-weight:900; color:#AAA;">LOKAL</span><div class="val">${p.local}</div></div>
                                <div style="text-align:right;"><span style="font-size:10px; font-weight:900; color:#AAA;">UZAK</span><div class="val">${p.remote}</div></div>
                            </div>
                            <div class="msg-box">${p.message}</div>
                            <div class="url-row">
                                <span class="url-text">${p.checkout_url}</span>
                                <button class="btn-copy" onclick="copyTo('${p.checkout_url}')" title="Kopyala"><svg style="width:14px;height:14px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></button>
                            </div>
                            <div class="ctrls">
                                <button class="btn-fire" onclick="manualSync('${p.id}')" ${p.is_running ? 'disabled' : ''} title="Hemen Sync">
                                    <svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
                                </button>
                                <button class="btn-toggle" style="background:${p.enabled ? '#ff9800' : '#4caf50'}; color:white;" onclick="toggleProject('${p.id}')" title="${p.enabled ? 'Duraklat' : 'Devam Et'}">
                                    ${p.enabled ? '<svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>' : '<svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 3l14 9-14 9V3z"></path></svg>'}
                                </button>
                                <button class="btn-gear" onclick="openEdit('${p.id}', ${p.interval/60})" title="Ayarlar">
                                    <svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                                </button>
                                <button class="btn-del" onclick="deleteProject('${p.id}')" title="Sil">
                                    <svg style="width:20px;height:20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                                </button>
                            </div>
                        </div>`;
                });
                grid.innerHTML += `<div class="card add-card" onclick="openAdd()"><div style="font-size:60px; color:var(--brand-primary)">+</div><div style="font-weight:900; color:var(--brand-primary);">YENİ MİRROR EKLE</div></div>`;
                
                // Adaptive refresh: faster when sync is running
                const anyRunning = data.some(p => p.is_running);
                clearTimeout(window.refreshTimer);
                window.refreshTimer = setTimeout(loadProjects, anyRunning ? 3000 : 30000);
            } catch(e) { window.refreshTimer = setTimeout(loadProjects, 30000); }
        }
        function openAdd() {
            ['p-name','p-url','p-user','p-pass'].forEach(id => document.getElementById(id).value = '');
            document.getElementById('p-interval').value = 20;
            document.getElementById('add-modal').style.display='flex';
        }
        function openSettings() { document.getElementById('settings-modal').style.display='flex'; }
        function openEdit(id, currentInterval) {
            document.getElementById('e-id').value = id;
            document.getElementById('e-interval').value = currentInterval;
            document.getElementById('e-user').value = '';
            document.getElementById('e-pass').value = '';
            document.getElementById('edit-modal').style.display='flex';
        }
        function closeModal(id) { document.getElementById(''+id).style.display='none'; }
        async function saveEdit() {
            const id = document.getElementById('e-id').value;
            const payload = {
                interval: document.getElementById('e-interval').value * 60,
                username: document.getElementById('e-user').value,
                password: document.getElementById('e-pass').value
            };
            const res = await fetch(`/api/projects/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
            if(res.ok) { closeModal('edit-modal'); showToast('✅ Ayarlar güncellendi.'); loadProjects(); }
            else { showToast('❌ Güncelleme başarısız.'); }
        }

        async function saveProject() {
            const payload = {
                name: document.getElementById('p-name').value,
                url: document.getElementById('p-url').value,
                interval: document.getElementById('p-interval').value * 60,
                username: document.getElementById('p-user').value,
                password: document.getElementById('p-pass').value
            };
            if (!payload.name || !payload.url) { showToast('⚠️ Proje adı ve URL zorunludur.'); return; }
            const res = await fetch('/api/projects', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
            if(res.ok) { closeModal('add-modal'); showToast('✅ Proje eklendi, senkronizasyon başlıyor...'); loadProjects(); }
            else {
                const err = await res.json();
                showToast('❌ ' + (err.error || 'SVN URL ve kimlik bilgilerini kontrol edin.'));
            }
        }
        async function saveSettings() {
            const newPass = document.getElementById('s-pass').value;
            const res = await fetch('/api/settings', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({dashboard_pass: newPass}) });
            const result = await res.json();
            closeModal('settings-modal');
            showToast(newPass ? '✅ Şifre kaydedildi.' : '✅ Şifre kaldırıldı, dashboard açık.');
            setTimeout(() => location.reload(), 1000);
        }
        // Init: show logout only if password is set
        fetch('/api/settings').then(r=>r.json()).then(s=>{
            document.getElementById('btn-logout').style.display = s.dashboard_pass_set ? 'inline-block' : 'none';
        });
        async function toggleProject(id) {
            await fetch(`/api/projects/${id}/toggle`, { method:'POST' });
            loadProjects();
        }
        async function manualSync(id) {
            await fetch('/api/sync/manual?name=' + id, { method:'POST' });
            showToast('⚡ Senkronizasyon tetiklendi: ' + id);
        }
        let _confirmCb = null;
        function askConfirm(title, msg, cb, btnText='SİL') {
            document.getElementById('confirm-title').textContent = title;
            document.getElementById('confirm-msg').textContent = msg;
            document.getElementById('confirm-btn').textContent = btnText;
            _confirmCb = cb;
            document.getElementById('confirm-modal').style.display = 'flex';
        }
        function confirmAction() {
            document.getElementById('confirm-modal').style.display = 'none';
            if(_confirmCb) _confirmCb();
        }
        async function deleteProject(id) {
            askConfirm('Projeyi Sil', id + ' projesi ve tüm yerel verileri silinecek. Emin misiniz?', async () => {
                await fetch('/api/projects/'+id, { method:'DELETE' });
                showToast('🗑️ ' + id + ' silindi.');
                loadProjects();
            });
        }
        loadProjects();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    update_scheduler(); app.run(host='0.0.0.0', port=80)
