#!/usr/bin/env python3
"""
TRUE 24/7 BOT - CLOUD READY VERSION
Runs independently without browser dependency
"""

import sys
import subprocess
import importlib
import time
import threading
import datetime
import requests
import os
import logging
from collections import deque
from urllib.parse import urlparse

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('24_7_bot_cloud.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('24_7_BOT')

# Install dependencies
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except Exception as e:
        logger.error(f"Failed to install {package}: {e}")
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
            logger.info(f"✓ {package_name} available")
        except ImportError:
            logger.info(f"Installing {package_name}...")
            if not install_package(pip_name):
                logger.error(f"Failed to install {package_name}")
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

# Global stats
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
    'restart_count': 0,
    'cloud_mode': True
}

# Default websites
WEBSITES = [
    "https://highly-pledge-achieving-allows.trycloudflare.com/vnc.html?autoconnect=true&password=123456",
    "https://studio.firebase.google.com/jja-06712545",
    "https://bot-1-hvtn.onrender.com",
    "https://bot-2-cta8.onrender.com",
    "https://dashboard.render.com/web/srv-d3ktd0c9c44c738su29g/deploys/dep-d3ktd1k9c44c738su3l0",
    "https://bot-for-web.onrender.com",
    "https://dashboard.render.com/web/srv-d3ktdqb3fgac73a3rkt0/deploys/dep-d3ktdrr3fgac73a3rlmg"
]

stats['website_list'] = WEBSITES.copy()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

class True247Bot:
    def __init__(self):
        self.websites = WEBSITES.copy()
        self.running = True
        self.sessions = {}
        self.threads = {}
        self.health_check_thread = None
        self.last_health_check = datetime.datetime.now()
        
        logger.info("🤖 TRUE 24/7 BOT INITIALIZED - CLOUD READY")
        
        # Start health monitoring
        self.start_health_monitor()

    def start_health_monitor(self):
        """Monitor bot health and auto-restart failed sessions"""
        def health_monitor():
            while self.running:
                try:
                    current_time = datetime.datetime.now()
                    
                    # Check each website session every 2 minutes
                    for website in self.websites:
                        if website in self.sessions and self.sessions[website]:
                            try:
                                # Simple health check - get current URL
                                driver = self.sessions[website]
                                driver.current_url
                                stats['bot_status'][website] = 'healthy'
                            except Exception as e:
                                logger.warning(f"Health check failed for {website}: {e}")
                                stats['bot_status'][website] = 'unhealthy'
                                # Auto-restart unhealthy session
                                self.restart_website_session(website)
                        else:
                            # Session doesn't exist, start it
                            if website not in self.threads or not self.threads[website].is_alive():
                                self.start_website(website)
                    
                    self.last_health_check = current_time
                    time.sleep(0)  # Check every 2 minutes
                    
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(60)
        
        self.health_check_thread = threading.Thread(target=health_monitor, daemon=True)
        self.health_check_thread.start()
        logger.info("✅ Health monitor started")

    def restart_website_session(self, website):
        """Restart a specific website session"""
        logger.info(f"🔄 Restarting session for: {website}")
        
        # Clean up old session
        if website in self.sessions and self.sessions[website]:
            try:
                self.sessions[website].quit()
            except:
                pass
            self.sessions[website] = None
        
        # Remove from instances
        if website in stats['browser_instances']:
            del stats['browser_instances'][website]
        
        # Start new session
        self.start_website(website)
        stats['restart_count'] += 1
        self.record_activity("SYSTEM", f"Auto-restarted session for: {website}")

    def create_browser(self):
        """Create browser with cloud-optimized settings"""
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            
            # Cloud-optimized settings
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")  # Save bandwidth
            options.add_argument("--disable-javascript")  # For simple sites
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Set timeouts
            driver.set_page_load_timeout(45)
            driver.implicitly_wait(10)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Browser created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Browser creation failed: {e}")
            return None

    def maintain_session(self, website):
        """Maintain 24/7 session with enhanced resilience"""
        session_start_time = datetime.datetime.now()
        visit_count = 0
        
        logger.info(f"🚀 Starting 24/7 session for: {website}")
        
        while self.running:
            driver = None
            try:
                # Create browser instance
                driver = self.create_browser()
                if not driver:
                    logger.error(f"Failed to create browser for {website}")
                    time.sleep(60)
                    continue
                
                self.sessions[website] = driver
                stats['browser_instances'][website] = {
                    'start_time': datetime.datetime.now(),
                    'last_activity': 'Starting visit',
                    'visit_count': visit_count
                }
                stats['active_sessions'] = len([s for s in self.sessions.values() if s])
                self.update_stats()
                
                # Visit website
                logger.info(f"🌐 Visiting: {website} (Visit #{visit_count + 1})")
                start_visit = datetime.datetime.now()
                
                driver.get(website)
                
                # Wait for page load
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                visit_duration = (datetime.datetime.now() - start_visit).total_seconds()
                page_title = driver.title
                current_url = driver.current_url
                
                visit_count += 1
                stats['total_visits'] += 1
                stats['successful_visits'] += 1
                
                # Update session info
                stats['browser_instances'][website].update({
                    'last_activity': datetime.datetime.now().strftime("%H:%M:%S"),
                    'current_url': current_url,
                    'page_title': page_title,
                    'visit_count': visit_count,
                    'last_visit_duration': f"{visit_duration:.1f}s"
                })
                
                self.record_activity(website, f"✅ Visit #{visit_count} - {page_title} ({visit_duration:.1f}s)")
                logger.info(f"✅ Successful visit #{visit_count} to {website}")
                
                # Stay on page for a while (simulate real user)
                stay_time = 9999999999999999999999999999999999999999  # 2 minutes
                logger.info(f"💤 Staying on {website} for {stay_time} seconds")
                
                stay_start = datetime.datetime.now()
                while self.running and (datetime.datetime.now() - stay_start).seconds < stay_time:
                    # Update session age periodically
                    session_age = datetime.datetime.now() - session_start_time
                    stats['browser_instances'][website]['age'] = self.format_time(session_age)
                    stats['browser_instances'][website]['session_duration'] = self.format_time(session_age)
                    
                    self.update_stats()
                    time.sleep(10)
                
                # Close browser and prepare for next visit
                try:
                    driver.quit()
                    self.sessions[website] = None
                except:
                    pass
                
                # Wait before next visit
                wait_time = 0  # 30 seconds between sessions
                logger.info(f"⏳ Waiting {wait_time} seconds before next visit to {website}")
                time.sleep(wait_time)
                
            except TimeoutException:
                stats['failed_visits'] += 1
                self.record_activity(website, f"❌ Visit #{visit_count + 1} - Timeout")
                logger.warning(f"⏰ Timeout visiting {website}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                time.sleep(30)
                
            except Exception as e:
                stats['failed_visits'] += 1
                self.record_activity(website, f"❌ Visit #{visit_count + 1} - {str(e)}")
                logger.error(f"💥 Error visiting {website}: {e}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                time.sleep(30)

    def start_website(self, website):
        """Start a session for a website"""
        if website in self.threads and self.threads[website].is_alive():
            logger.info(f"Session already running for: {website}")
            return False
        
        thread = threading.Thread(target=self.maintain_session, args=(website,), daemon=True)
        self.threads[website] = thread
        thread.start()
        logger.info(f"✅ Started session thread for: {website}")
        return True

    def start_all_websites(self):
        """Start all sessions"""
        logger.info("🚀 STARTING ALL 24/7 SESSIONS...")
        
        for website in self.websites:
            try:
                self.start_website(website)
                logger.info(f"✅ Started: {website}")
                time.sleep(5)  # Stagger startup
            except Exception as e:
                logger.error(f"❌ Failed to start {website}: {e}")
        
        self.record_activity("SYSTEM", f"All {len(self.websites)} sessions started")
        logger.info(f"🎯 Total websites: {len(self.websites)}")

    def record_activity(self, website, action):
        activity = {
            'website': website,
            'timestamp': datetime.datetime.now().strftime("%H:%M:%S"),
            'action': action
        }
        stats['visit_history'].appendleft(activity)
        socketio.emit('activity', activity)

    def update_stats(self):
        """Update statistics"""
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
            'process_id': stats.get('process_id', os.getpid()),
            'cloud_mode': True
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
bot = True24_7Bot()

@app.route('/')
def dashboard():
    # Simple dashboard HTML
    return """
    <html>
    <head><title>24/7 Bot - Cloud Mode</title></head>
    <body>
        <h1>🤖 24/7 Bot - Cloud Mode</h1>
        <p>✅ Running independently on server</p>
        <p>🌐 Websites being visited: {}</p>
        <p>🕒 Uptime: {}</p>
        <p>📊 Total Visits: {}</p>
        <a href="/api/stats">View Detailed Stats</a>
    </body>
    </html>
    """.format(len(WEBSITES), bot.format_time(datetime.datetime.now() - stats['start_time']), stats['total_visits'])

@app.route('/api/stats')
def api_stats():
    return jsonify(stats)

@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'websites_active': len([s for s in bot.sessions.values() if s]),
        'total_websites': len(WEBSITES)
    })

def main():
    print("=" * 70)
    print("🤖 TRUE 24/7 BOT - CLOUD READY VERSION")
    print("=" * 70)
    print("✅ Features:")
    print("  • Runs independently on cloud/server")
    print("  • Survives browser closure")
    print("  • Auto-restart on failures")
    print("  • Health monitoring")
    print("  • No local machine dependency")
    print("=" * 70)
    print("🌐 Websites to maintain:")
    for i, website in enumerate(WEBSITES, 1):
        print(f"   {i}. {website}")
    print("=" * 70)
    
    # Start all sessions
    bot.start_all_websites()
    
    # Get port from environment (for cloud hosting)
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    
    print(f"🚀 Starting server on {host}:{port}")
    print("💡 Deploy to Render/Heroku for true 24/7 operation")
    
    try:
        socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        # Auto-restart
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()