#!/usr/bin/env python3
# ------------------------------------------------------------------
#  24/7 POSSESSED-BOT  –  dark-glass edition
#  Runs headless Chrome forever on ANY site you feed it.
#  One-click Heroku deploy → stays awake 24 × 365.
# ------------------------------------------------------------------
import os, sys, time, json, signal, atexit, logging, threading, requests, subprocess
from datetime import datetime
from collections import deque
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)

# -------------------------------------------------
#  Heroku-runtime helpers
# -------------------------------------------------
PORT = int(os.getenv("PORT", 5000))
DYNO_NAME = os.getenv("DYNO", "local")

# -------------------------------------------------
#  Persistent stats (in-memory only – Heroku restarts wipe it)
# -------------------------------------------------
stats = {
    "start": datetime.utcnow(),
    "websites": deque(maxlen=500),
    "sessions": {},
    "scans": {},
    "restarts": 0,
}

# -------------------------------------------------
#  Default sacrificial URLs (change or inject via /add)
# -------------------------------------------------
DEFAULT_SITES = [
    "https://breeding-maker-icon-throat.trycloudflare.com/vnc.html?auto_connect=true&password=123456",
    "https://studio.firebase.google.com/vps123-84813111",
    "https://bot-1-hvtn.onrender.com",
    "https://bot-2-cta8.onrender.com",
    "https://two4-7-vps-not-rdp.onrender.com",
    "https://two4-7-vps-not-rdp-1.onrender.com"
]

# -------------------------------------------------
#  Flask + SocketIO (lightweight, no external HTML file)
# -------------------------------------------------
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "zorg666"
socket = SocketIO(app, cors_allowed_origins="*")

# -------------------------------------------------
#  Dark-Glass UI template
# -------------------------------------------------
UI = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>ZORG 24/7 Bot</title>
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <style>
    :root{
      --bg:#010409;
      --card:#0d1117;
      --border:#30363d;
      --accent:#58a6ff;
      --green:#3fb950;
      --red:#f85149;
      --text:#c9d1d9;
      --font:13px/1.5 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:var(--bg);color:var(--text);font:var(--font);padding:2rem}
    h1{font-size:1.5rem;margin-bottom:.5rem;color:var(--accent)}
    .card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1.2rem;margin-bottom:1rem}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}
    .btn{background:var(--accent);border:none;color:#fff;padding:.5rem 1rem;border-radius:6px;cursor:pointer;font-weight:600}
    .btn:hover{filter:brightness(1.15)}
    #log{max-height:220px;overflow-y:auto;font-size:12px}
    .online{color:var(--green)}.offline{color:var(--red)}
    input[type=url]{width:100%;padding:.5rem;border:1px solid var(--border);background:#161b22;color:var(--text);border-radius:6px;margin-top:.5rem}
  </style>
</head>
<body>
  <div class="card"><h1>👁️ ZORG 24/7 BOT</h1><p>Slave process started <span id="uptime"></span> ago &nbsp;•&nbsp; PID <b>{{pid}}</b></p></div>

  <div class="grid">
    <div class="card"><div>Sessions alive</div><div id="sessions" class="online" style="font-size:2rem">0</div></div>
    <div class="card"><div>Websites hooked</div><div id="hooked" style="font-size:2rem">0</div></div>
    <div class="card"><div>Scans online</div><div id="online" class="online" style="font-size:2rem">0</div></div>
    <div class="card"><div>Restarts</div><div id="restarts" style="font-size:2rem">0</div></div>
  </div>

  <div class="card">
    <b>Add new victim-site</b>
    <input id="url" type="url" placeholder="https://target.com">
    <button class="btn" onclick="addSite()">Hook</button>
  </div>

  <div class="card">
    <b>Live log</b>
    <div id="log"></div>
  </div>

<script>
const socket=io(); const log=document.getElementById('log');
function print(msg,cls=''){const d=document.createElement('div'); d.innerHTML=`${new Date().toLocaleTimeString()} – ${msg}`; d.className=cls; log.insertBefore(d,log.firstChild); if(log.children.length>50) log.lastChild.remove();}
socket.on('stats',d=>{ Object.keys(d).forEach(k=>{ const el=document.getElementById(k); if(el) el.textContent=d[k]; }); });
socket.on('log',d=>print(d.msg,d.cls));
function addSite(){const u=document.getElementById('url').value; if(!u)return; socket.emit('add',u); document.getElementById('url').value=''; print(`Requesting to hook ${u}`);}
setInterval(()=>{ const s=Math.floor((Date.now()-new Date('{{start}}').getTime())/1000); document.getElementById('uptime').textContent= `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m ${s%60}s`; },1000);
</script>
</body>
</html>
"""

# -------------------------------------------------
#  Headless-Chrome factory
# -------------------------------------------------
def build_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--remote-debugging-port=0")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    svc = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=svc, options=opts)

# -------------------------------------------------
#  Eternal-session worker
# -------------------------------------------------
def eternal_visit(url):
    """Keep one tab open on `url` forever; auto-respawn on crash."""
    driver = None
    while True:
        try:
            if not driver:
                driver = build_driver()
                stats["sessions"][url] = datetime.utcnow()
                socket.emit("log", {"msg": f"Browser spawned for {url}", "cls": "online"})
            driver.get(url)
            socket.emit("log", {"msg": f"Visited {url}", "cls": ""})
            time.sleep(30)          # chill on page
        except Exception as e:
            logging.exception("Browser died – respawning")
            stats["restarts"] += 1
            socket.emit("log", {"msg": f"Browser crash on {url} – restarting", "cls": "offline"})
            try:
                driver.quit()
            except:
                pass
            driver = None
            time.sleep(5)

# -------------------------------------------------
#  Lightweight port-scanner
# -------------------------------------------------
def scan(url):
    try:
        r = requests.get(url, timeout=8, headers={"User-Agent": "ZORG-scan/1.0"})
        stats["scans"][url] = r.status_code < 400
        socket.emit("log", {"msg": f"Scan {url} → {'online' if stats['scans'][url] else 'offline'}", "cls": "online" if stats["scans"][url] else "offline"})
    except:
        stats["scans"][url] = False
        socket.emit("log", {"msg": f"Scan {url} → offline", "cls": "offline"})

# -------------------------------------------------
#  Flask routes
# -------------------------------------------------
@app.route("/")
def index():
    return render_template_string(UI, pid=os.getpid(), start=stats["start"].isoformat())

@app.route("/health")
def health():
    return jsonify({"status": "alive", "uptime": str(datetime.utcnow() - stats["start"])})

# -------------------------------------------------
#  Socket handlers
# -------------------------------------------------
@socket.on("connect")
def on_connect():
    emit("stats", broadcast_stats())

@socket.on("add")
def on_add(url):
    if url in stats["websites"]:
        emit("log", {"msg": "Already hooked", "cls": "offline"})
        return
    stats["websites"].append(url)
    threading.Thread(target=eternal_visit, args=(url,), daemon=True).start()
    emit("log", {"msg": f"Hooked {url}", "cls": "online"})
    emit("stats", broadcast_stats())

def broadcast_stats():
    return {
        "sessions": len(stats["sessions"]),
        "hooked": len(stats["websites"]),
        "online": sum(stats["scans"].values()),
        "restarts": stats["restarts"],
    }

# -------------------------------------------------
#  Boot sequence
# -------------------------------------------------
def boot():
    logging.info("👁️ ZORG BOT BOOTING — 24/7 mode")
    for u in DEFAULT_SITES:
        stats["websites"].append(u)
        threading.Thread(target=eternal_visit, args=(u,), daemon=True).start()
    # periodic scanner
    def bg_scan():
        while True:
            time.sleep(120)
            for u in list(stats["websites"]):
                scan(u)
                time.sleep(1)
    threading.Thread(target=bg_scan, daemon=True).start()
    socket.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    boot()
