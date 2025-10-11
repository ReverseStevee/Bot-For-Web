#!/usr/bin/env python3
"""
24/7 Auto-Start Website Bot - ENHANCED 24/7 VERSION
- Runs continuously even after tab/browser closure
- Auto-restart on failures
- Persistent session management
- Background process capabilities
"""

import sys
import subprocess
import importlib
import time
import threading
import datetime
import requests
import os
import signal
import atexit
from collections import deque
from urllib.parse import urlparse
import logging


# Install dependencies
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except:
        return False

def check_dependencies():
    packages = {
        'selenium': 'selenium',
        'flask': 'flask', 
        'webdriver_manager': 'webdriver-manager',
        'flask_socketio': 'flask-socketio'
    }
    
    for package_name, pip_name in packages.items():
        try:
            importlib.import_module(package_name)
        except ImportError:
            logging.info(f"Installing {package_name}...")
            if not install_package(pip_name):
                return False
    return True

if not check_dependencies():
    sys.exit(1)

# Import after installation
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from flask import Flask, render_template_string, jsonify
from flask_socketio import SocketIO

# Global stats with persistence
stats = {
    'total_visits': 0,
    'successful_visits': 0,
    'failed_visits': 0,
    'start_time': datetime.datetime.now(),
    'active_sessions': 0,
    'browser_instances': {},
    'scanned_websites': {},
    'custom_websites': [],
    'visit_history': deque(maxlen=100),
    'bot_status': {},
    'website_list': [],
    'process_id': os.getpid(),
    'restart_count': 0
}

# Default websites - FIXED URLs
WEBSITES = [
    "https://studio.firebase.google.com/vps123-74546702",
    "https://operating-fountain-removed-frost.trycloudflare.com/vnc.html?autoconnect=true&password=123456",
    "https://bot-1-hvtn.onrender.com",
    "https://bot-2-cta8.onrender.com",
    "https://dashboard.render.com/web/srv-d3ktd0c9c44c738su29g/deploys/dep-d3ktd1k9c44c738su3l0",
    "https://dashboard.render.com/web/srv-d3ktdqb3fgac73a3rkt0/deploys/dep-d3ktdrr3fgac73a3rlmg"
]

# Initialize website list
stats['website_list'] = WEBSITES.copy()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# HTML TEMPLATE - Enhanced with 24/7 features
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Uptime Bot 🥱</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: #1e1e1e; 
            color: white; 
            margin: 0; 
            padding: 20px; 
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            padding: 20px; 
            background: #2d2d2d; 
            border-radius: 10px; 
            border: 2px solid #4CAF50;
        }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
            margin-bottom: 20px; 
        }
        .stat-card { 
            background: #2d2d2d; 
            padding: 20px; 
            border-radius: 8px; 
            text-align: center; 
        }
        .stat-number { 
            font-size: 28px; 
            font-weight: bold; 
            margin: 10px 0; 
        }
        .success { color: #4CAF50; }
        .warning { color: #FF9800; }
        .error { color: #f44336; }
        .info { color: #2196F3; }
        
        .control-panel { 
            background: #2d2d2d; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
            text-align: center;
            border: 1px solid #4CAF50;
        }
        .btn { 
            background: #4CAF50; 
            color: white; 
            border: none; 
            padding: 12px 24px; 
            margin: 5px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
        }
        .btn-scan { background: #2196F3; }
        .btn-refresh { background: #FF9800; }
        .btn-restart { background: #9C27B0; }
        
        .section { 
            background: #2d2d2d; 
            padding: 20px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
        }
        .session-item, .scan-item, .status-item, .website-item { 
            background: #3d3d3d; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 5px; 
        }
        .online { border-left: 4px solid #4CAF50; }
        .offline { border-left: 4px solid #f44336; }
        .warning-status { border-left: 4px solid #FF9800; }
        
        .input-group { 
            display: flex; 
            gap: 10px; 
            margin: 15px 0; 
        }
        .url-input { 
            flex: 1; 
            padding: 12px; 
            border-radius: 5px; 
            border: 1px solid #555; 
            background: #3d3d3d; 
            color: white; 
            font-size: 16px; 
        }
        .activity-item {
            background: #3d3d3d;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            font-size: 14px;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-active { background: #4CAF50; }
        .status-inactive { background: #f44336; }
        .status-warning { background: #FF9800; }
        .website-url {
            font-family: monospace;
            font-size: 12px;
            color: #aaa;
            word-break: break-all;
        }
        .24-7-badge {
            background: #4CAF50;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Beta Test Version</h1>
            <p>The First Experimental Bot in Github</p>
            <div class="24-7-badge">24/7 MODE: ACTIVE</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div>Active Sessions</div>
                <div class="stat-number info" id="activeSessions">0</div>
            </div>
            <div class="stat-card">
                <div>Total Websites</div>
                <div class="stat-number info" id="totalWebsites">0</div>
            </div>
            <div class="stat-card">
                <div>Websites Online</div>
                <div class="stat-number success" id="scannedOnline">0</div>
            </div>
            <div class="stat-card">
                <div>Uptime</div>
                <div class="stat-number info" id="uptime">0s</div>
            </div>
            <div class="stat-card">
                <div>Restart Count</div>
                <div class="stat-number warning" id="restartCount">0</div>
            </div>
            <div class="stat-card">
                <div>Process ID</div>
                <div class="stat-number info" id="processId">0</div>
            </div>
        </div>

        <div class="control-panel">
            <h3>Bot Status: <span style="color: #4CAF50;">🟢 RUNNING 24/7</span></h3>
            <p>This bot runs continuously in background and auto-restarts on failures</p>
            <button class="btn btn-scan" onclick="scanAll()">🔍 Scan All Websites</button>
            <button class="btn btn-refresh" onclick="refreshStats()">🔄 Refresh Stats</button>
            <button class="btn btn-restart" onclick="restartSessions()">🔄 Restart All Sessions</button>
        </div>

        <div class="section">
            <h3>➕ Add New Website</h3>
            <div class="input-group">
                <input type="url" class="url-input" id="newUrl" placeholder="https://example.com">
                <button class="btn" onclick="addWebsite()">Add Website</button>
            </div>
            <div id="message"></div>
        </div>

        <div class="section">
            <h3>📋 Website List</h3>
            <div id="websiteList">
                <div style="text-align: center; padding: 20px; color: #888;">
                    Loading websites...
                </div>
            </div>
        </div>

        <div class="section">
            <h3>🖥️ Active Browser Sessions</h3>
            <div id="sessionsList">
                <div style="text-align: center; padding: 20px; color: #888;">
                    Starting sessions...
                </div>
            </div>
        </div>

        <div class="section">
            <h3>🔍 Website Scanner Results</h3>
            <div id="scannerResults">
                <div style="text-align: center; padding: 20px; color: #888;">
                    Click "Scan All Websites" to check status
                </div>
            </div>
        </div>

        <div class="section">
            <h3>📈 Activity Log</h3>
            <div id="activityLog">
                <div style="text-align: center; padding: 20px; color: #888;">
                    Activity will appear here...
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        
        socket.on('stats_update', function(data) {
            console.log('Stats update received:', data);
            document.getElementById('activeSessions').textContent = data.active_sessions;
            document.getElementById('totalWebsites').textContent = data.total_websites;
            document.getElementById('scannedOnline').textContent = data.scanned_online;
            document.getElementById('uptime').textContent = data.uptime;
            document.getElementById('restartCount').textContent = data.restart_count || 0;
            document.getElementById('processId').textContent = data.process_id || 'N/A';
            
            updateWebsiteList(data.website_list);
            updateSessions(data.sessions);
            updateScanner(data.scanned_websites);
        });
        
        socket.on('activity', function(activity) {
            addActivity(activity);
        });

        socket.on('add_result', function(result) {
            showMessage(result.message, result.success);
        });

        socket.on('restart_complete', function(data) {
            showMessage('All sessions restarted successfully!', true);
        });

        function updateWebsiteList(websites) {
            const container = document.getElementById('websiteList');
            if (!websites || websites.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #888;">No websites configured</div>';
                return;
            }
            
            let html = '';
            websites.forEach(website => {
                html += `
                    <div class="website-item online">
                        <strong>🌐 ${website}</strong>
                        <div class="website-url">${website}</div>
                        <div>Status: ✅ In Bot List • 24/7 Active</div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        function updateSessions(sessions) {
            const container = document.getElementById('sessionsList');
            if (!sessions || Object.keys(sessions).length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #888;">No active sessions yet</div>';
                return;
            }
            
            let html = '';
            for (const [website, session] of Object.entries(sessions)) {
                html += `
                    <div class="session-item online">
                        <strong>${website}</strong>
                        <div class="website-url">${website}</div>
                        <div>🕒 Session Age: ${session.age || '0s'}</div>
                        <div>📊 Status: ✅ ACTIVE & VISITING 24/7</div>
                        <div>Last Activity: ${session.last_activity || 'Just now'}</div>
                    </div>
                `;
            }
            container.innerHTML = html;
        }

        function updateScanner(websites) {
            const container = document.getElementById('scannerResults');
            if (!websites || Object.keys(websites).length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #888;">No scan results yet</div>';
                return;
            }
            
            let html = '';
            for (const [url, scan] of Object.entries(websites)) {
                const statusClass = scan.status === 'online' ? 'online' : 'offline';
                const statusText = scan.status === 'online' ? '✅ ONLINE' : '❌ OFFLINE';
                const statusCode = scan.status_code ? ` (HTTP ${scan.status_code})` : '';
                
                html += `
                    <div class="scan-item ${statusClass}">
                        <strong>${url}</strong>
                        <div class="website-url">${url}</div>
                        <div>Status: ${statusText}${statusCode}</div>
                        <div>Last checked: ${scan.last_checked}</div>
                        ${scan.error ? `<div style="color: #f44336;">Error: ${scan.error}</div>` : ''}
                    </div>
                `;
            }
            container.innerHTML = html;
        }

        function addActivity(activity) {
            const log = document.getElementById('activityLog');
            const item = document.createElement('div');
            item.className = 'activity-item';
            item.innerHTML = `
                <strong>${activity.website}</strong>
                <div>🕒 ${activity.timestamp} - ${activity.action}</div>
            `;
            
            if (log.firstChild && log.firstChild.style.textAlign === 'center') {
                log.innerHTML = '';
            }
            
            log.insertBefore(item, log.firstChild);
            
            if (log.children.length > 15) {
                log.removeChild(log.lastChild);
            }
        }

        function showMessage(message, isSuccess) {
            const messageDiv = document.getElementById('message');
            const color = isSuccess ? '#4CAF50' : '#f44336';
            messageDiv.innerHTML = `<div style="color: ${color}; margin-top: 10px;">${message}</div>`;
            setTimeout(() => { messageDiv.innerHTML = ''; }, 5000);
        }

        function scanAll() { 
            socket.emit('scan_all'); 
            showMessage('Scanning all websites...', true);
        }
        
        function refreshStats() {
            showMessage('Refreshing statistics...', true);
        }
        
        function addWebsite() {
            const url = document.getElementById('newUrl').value.trim();
            if (url) {
                socket.emit('add_website', {url: url});
                document.getElementById('newUrl').value = '';
            } else {
                showMessage('Please enter a valid URL', false);
            }
        }

        function restartSessions() {
            socket.emit('restart_sessions');
            showMessage('Restarting all sessions...', true);
        }

        // Auto-reconnect for WebSocket
        socket.on('disconnect', function() {
            console.log('Disconnected from server, attempting to reconnect...');
        });

        socket.on('reconnect', function() {
            console.log('Reconnected to server');
            showMessage('Reconnected to bot server', true);
        });

        // Auto-refresh stats every 3 seconds
        setInterval(() => {
            // Stats are automatically updated via WebSocket
        }, 3000);

        // Initial load
        document.addEventListener('DOMContentLoaded', function() {
            showMessage('24/7 Bot Started - Running Continuously in Background', true);
        });

        // Handle page visibility changes
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                // Page became visible again, refresh stats
                refreshStats();
            }
        });
    </script>
</body>
</html>
"""

class WebsiteBot:
    def __init__(self):
        self.websites = WEBSITES.copy()
        self.running = True
        self.sessions = {}
        self.threads = {}
        self.restart_count = 0
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Register cleanup function
        atexit.register(self.cleanup)
        
        # Initialize bot status for all websites
        for website in self.websites:
            stats['bot_status'][website] = {
                'is_active': False,
                'last_visit': None,
                'visit_count': 0,
                'last_error': None,
                'restart_count': 0
            }

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, but continuing 24/7 operation...")
        # Don't stop - just log and continue

    def cleanup(self):
        """Cleanup function that runs on exit"""
        logging.info("Cleaning up resources...")
        self.running = False
        for website, driver in self.sessions.items():
            try:
                if driver:
                    driver.quit()
            except:
                pass

    def create_browser(self):
        """Create a resilient browser instance"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                options = Options()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--headless=new")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=0")
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Set page load timeout
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(10)
                
                logging.info(f"✅ Browser created successfully (attempt {attempt + 1})")
                return driver
                
            except Exception as e:
                logging.warning(f"Browser creation failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    logging.error("Failed to create browser after all retries")
                    return None

    def maintain_session(self, website):
        """Maintain continuous 24/7 session with auto-restart"""
        session_restarts = 0
        logging.info(f"🚀 Starting 24/7 session for: {website}")
        
        while self.running:
            try:
                # Create or recreate browser
                if website not in self.sessions or not self.sessions[website]:
                    self.sessions[website] = self.create_browser()
                    if not self.sessions[website]:
                        logging.error(f"❌ Failed to create browser for {website}")
                        time.sleep(30)
                        continue
                    
                    stats['browser_instances'][website] = {
                        'start_time': datetime.datetime.now(),
                        'last_activity': 'Just started',
                        'restart_count': session_restarts
                    }
                    stats['active_sessions'] = len([s for s in self.sessions.values() if s])
                    self.update_stats()
                    self.record_activity(website, "Browser session started")
                
                driver = self.sessions[website]
                
                # Load website with retry logic
                max_visit_retries = 0
                for visit_attempt in range(max_visit_retries):
                    try:
                        logging.info(f"🌐 Visiting: {website} (attempt {visit_attempt + 1})")
                        driver.get(website)
                        
                        WebDriverWait(driver, 45).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Get page info
                        page_title = driver.title
                        current_url = driver.current_url
                        
                        self.record_activity(website, f"✅ Successfully visiting - {page_title}")
                        logging.info(f"✅ ACTIVE: {website} - {page_title}")
                        
                        # Update session info
                        stats['browser_instances'][website]['last_activity'] = datetime.datetime.now().strftime("%H:%M:%S")
                        stats['browser_instances'][website]['current_url'] = current_url
                        stats['browser_instances'][website]['page_title'] = page_title
                        stats['browser_instances'][website]['restart_count'] = session_restarts
                        
                        break  # Success, break out of retry loop
                        
                    except TimeoutException:
                        if visit_attempt < max_visit_retries - 1:
                            logging.warning(f"Page load timeout for {website}, retrying...")
                            continue
                        else:
                            self.record_activity(website, "❌ Page load timeout after retries")
                            raise
                    except Exception as e:
                        if visit_attempt < max_visit_retries - 1:
                            logging.warning(f"Visit failed for {website}, retrying...: {e}")
                            time.sleep(5)
                            continue
                        else:
                            self.record_activity(website, f"❌ Visit failed: {str(e)}")
                            raise
                
                # Stay on website permanently with health checks
                consecutive_failures = 0
                while self.running and consecutive_failures < 3:
                    try:
                        # Update session age
                        current_time = datetime.datetime.now()
                        session_age = current_time - stats['browser_instances'][website]['start_time']
                        stats['browser_instances'][website]['age'] = self.format_time(session_age)
                        
                        # Health check - verify browser is responsive
                        driver.current_url
                        
                        # Update stats periodically
                        self.update_stats()
                        
                        # Reset failure counter on success
                        consecutive_failures = 0
                        time.sleep(15)  # Check more frequently
                        
                    except WebDriverException as e:
                        consecutive_failures += 1
                        logging.warning(f"Browser health check failed for {website} (failure {consecutive_failures}): {e}")
                        if consecutive_failures >= 3:
                            break
                        time.sleep(5)
                    except Exception as e:
                        consecutive_failures += 1
                        logging.warning(f"Session health check failed for {website} (failure {consecutive_failures}): {e}")
                        if consecutive_failures >= 3:
                            break
                        time.sleep(5)
                
                # Cleanup broken session
                self.cleanup_session(website)
                session_restarts += 1
                stats['restart_count'] = session_restarts
                self.record_activity(website, f"🔄 Session restarted (total restarts: {session_restarts})")
                
                # Brief pause before restarting
                time.sleep(10)
                    
            except Exception as e:
                logging.error(f"💥 Critical error for {website}: {e}")
                self.cleanup_session(website)
                time.sleep(30)

    def cleanup_session(self, website):
        """Clean up a specific session"""
        if website in self.sessions:
            try:
                self.sessions[website].quit()
            except:
                pass
            finally:
                self.sessions[website] = None
                if website in stats['browser_instances']:
                    del stats['browser_instances'][website]
                stats['active_sessions'] = len([s for s in self.sessions.values() if s])
                self.update_stats()

    def restart_all_sessions(self):
        """Restart all sessions"""
        logging.info("🔄 Restarting all sessions...")
        self.record_activity("SYSTEM", "Restarting all browser sessions")
        
        # Clean up all sessions
        for website in list(self.sessions.keys()):
            self.cleanup_session(website)
        
        # Restart all websites
        self.start_all_websites()
        
        stats['restart_count'] += 1
        self.update_stats()
        socketio.emit('restart_complete', {'message': 'All sessions restarted'})

    def scan_website(self, url):
        """Scan a single website with improved error handling"""
        try:
            logging.info(f"🔍 Scanning: {url}")
            
            # Update status to scanning
            stats['scanned_websites'][url] = {
                'status': 'scanning',
                'last_checked': datetime.datetime.now().strftime("%H:%M:%S")
            }
            self.update_stats()
            
            # Make the request with proper headers and timeout
            response = requests.get(
                url, 
                timeout=15, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                },
                verify=False,
                allow_redirects=True
            )
            
            # Determine status
            status = 'online' if response.status_code < 400 else 'offline'
            
            stats['scanned_websites'][url] = {
                'status': status,
                'last_checked': datetime.datetime.now().strftime("%H:%M:%S"),
                'status_code': response.status_code,
                'response_time': round(response.elapsed.total_seconds() * 1000, 2),
                'content_length': len(response.content)
            }
            
            self.update_stats()
            self.record_activity("SCANNER", f"Scanned {url}: {status} (HTTP {response.status_code})")
            logging.info(f"✅ Scan result for {url}: {status}")
            return True
            
        except Exception as e:
            stats['scanned_websites'][url] = {
                'status': 'offline',
                'last_checked': datetime.datetime.now().strftime("%H:%M:%S"),
                'error': str(e)
            }
            self.update_stats()
            self.record_activity("SCANNER", f"Scan failed {url}: {str(e)}")
            logging.error(f"❌ Scan failed for {url}: {e}")
            return False

    def scan_all_websites(self):
        """Scan all websites with improved threading"""
        def scan_thread():
            logging.info("🔄 Starting comprehensive website scan...")
            all_websites = stats['website_list']
            
            for website in all_websites:
                if not self.running:
                    break
                self.scan_website(website)
                time.sleep(0)  # Reduced delay for faster scanning
            
            logging.info("✅ Website scan completed")
        
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
        return thread

    def add_website(self, url):
        """Add a new website with validation"""
        try:
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL format. Please use http:// or https://"
            
            # Check if already exists
            if url in stats['website_list']:
                return False, "Website already in list"
            
            # Add to website list
            stats['website_list'].append(url)
            stats['custom_websites'].append(url)
            
            # Start session immediately
            self.start_website(url)
            
            self.record_activity("SYSTEM", f"Added new website: {url}")
            self.update_stats()
            
            return True, f"Website added successfully: {url}"
            
        except Exception as e:
            logging.error(f"Error adding website {url}: {e}")
            return False, f"Error adding website: {str(e)}"

    def start_website(self, website):
        """Start a session for a website"""
        if website in self.threads and self.threads[website].is_alive():
            logging.info(f"Session already running for: {website}")
            return False
        
        thread = threading.Thread(target=self.maintain_session, args=(website,), daemon=True)
        self.threads[website] = thread
        thread.start()
        logging.info(f"Started session thread for: {website}")
        return True

    def start_all_websites(self):
        """Start all sessions automatically with improved error handling"""
        logging.info("🚀 AUTO-STARTING ALL 24/7 SESSIONS...")
        
        for website in stats['website_list']:
            try:
                self.start_website(website)
                logging.info(f"✅ Started: {website}")
                time.sleep(2)  # Stagger startup to avoid resource contention
            except Exception as e:
                logging.error(f"❌ Failed to start {website}: {e}")
        
        self.record_activity("SYSTEM", f"All {len(stats['website_list'])} sessions auto-started")
        logging.info(f"🎯 Total websites: {len(stats['website_list'])}")

    def record_activity(self, website, action):
        stats['total_visits'] += 1
        stats['successful_visits'] += 1
        
        activity = {
            'website': website,
            'timestamp': datetime.datetime.now().strftime("%H:%M:%S"),
            'action': action
        }
        stats['visit_history'].appendleft(activity)
        socketio.emit('activity', activity)
        logging.info(f"ACTIVITY: {website} - {action}")

    def update_stats(self):
        """Update all statistics"""
        current_stats = {
            'active_sessions': stats['active_sessions'],
            'total_visits': stats['total_visits'],
            'total_websites': len(stats['website_list']),
            'scanned_online': sum(1 for s in stats['scanned_websites'].values() if s.get('status') == 'online'),
            'uptime': self.format_time(datetime.datetime.now() - stats['start_time']),
            'sessions': stats['browser_instances'],
            'scanned_websites': stats['scanned_websites'],
            'website_list': stats['website_list'],
            'restart_count': stats.get('restart_count', 0),
            'process_id': stats.get('process_id', os.getpid())
        }
        socketio.emit('stats_update', current_stats)

    def format_time(self, td):
        seconds = td.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"

# Create bot instance
bot = WebsiteBot()

# Flask routes
@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    return jsonify(stats)

@app.route('/api/websites')
def api_websites():
    return jsonify({'websites': stats['website_list']})

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'uptime': bot.format_time(datetime.datetime.now() - stats['start_time']),
        'active_sessions': stats['active_sessions']
    })

# SocketIO events
@socketio.on('connect')
def handle_connect():
    logging.info("📱 Client connected to dashboard")
    bot.update_stats()

@socketio.on('scan_all')
def handle_scan_all():
    logging.info("🔍 Client requested to scan all websites")
    bot.scan_all_websites()

@socketio.on('add_website')
def handle_add_website(data):
    url = data['url']
    logging.info(f"➕ Client requested to add website: {url}")
    success, message = bot.add_website(url)
    socketio.emit('add_result', {'success': success, 'message': message})

@socketio.on('restart_sessions')
def handle_restart_sessions():
    logging.info("🔄 Client requested session restart")
    bot.restart_all_sessions()

def daemonize():
    """Make the process run in background (Unix-like systems)"""
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        logging.error(f"Fork failed: {e}")
        sys.exit(1)

def main():
    print("=" * 70)
    print("🚀 24/7 AUTO-START WEBSITE BOT - ENHANCED 24/7 VERSION")
    print("=" * 70)
    print("🌐 ENHANCED FEATURES:")
    print("  • True 24/7 operation - survives closures")
    print("  • Auto-restart on failures")
    print("  • Resilient browser sessions")
    print("  • Background process capable")
    print("  • Comprehensive logging")
    print("  • Health monitoring")
    print("=" * 70)
    print("📊 Dashboard: http://localhost:5000")
    print("📋 Websites in bot:")
    for i, website in enumerate(WEBSITES, 1):
        print(f"   {i}. {website}")
    print("")
    print("🔄 Auto-starting all 24/7 sessions...")
    print("=" * 70)
    
    # Auto-start all sessions
    bot.start_all_websites()
    
    # Start periodic scanning every 5 minutes
    def periodic_scanner():
        while True:
            time.sleep(0)  # 5 minutes
            if bot.running:
                logging.info("🔄 Periodic website scan started")
                bot.scan_all_websites()
    
    scanner_thread = threading.Thread(target=periodic_scanner, daemon=True)
    scanner_thread.start()
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logging.info("Bot interrupted but designed to continue running...")
    except Exception as e:
        logging.error(f"Server error: {e}")
        # Don't exit - the bot should keep running
        time.sleep(60)
        main()  # Restart main function

if __name__ == "__main__":
    main()