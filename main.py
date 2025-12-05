import os
import sys
import json
import time
import requests
import threading
import webbrowser
import subprocess
import getpass
from PyQt6 import QtWidgets, QtCore, QtGui
from flask import Flask, request

# -------------------------
# Paths
# -------------------------
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)  # EXE path
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_DIR = os.path.join(BASE_DIR, "config")
TOKEN_DIR = os.path.join(BASE_DIR, "token")
AVATAR_DIR = os.path.join(BASE_DIR, "avatar")
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(TOKEN_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_FILE = os.path.join(TOKEN_DIR, "token.json")
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# -------------------------
# Flask OAuth
# -------------------------
app = Flask(__name__)

# -------------------------
# WinCord Main App
# -------------------------
class WinCordApp(QtWidgets.QMainWindow):
    REDIRECT_URI = "http://localhost:8000/callback"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    API_URL = "https://discord.com/api/users/@me"

    def __init__(self):
        super().__init__()
        WinCordApp.instance = self
        self.setWindowTitle("WinCord")
        self.setFixedSize(550, 400)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowMaximizeButtonHint)

        # Load config
        self.cfg = self.load_config()
        self.client_id = self.cfg.get("client_id", "")
        self.client_secret = self.cfg.get("client_secret", "")

        # UI
        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        self.client_id_input = QtWidgets.QLineEdit(self.client_id)
        self.client_id_input.setPlaceholderText("Enter Discord Client ID")
        form.addRow("Client ID:", self.client_id_input)

        self.client_secret_input = QtWidgets.QLineEdit(self.client_secret)
        self.client_secret_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.client_secret_input.setPlaceholderText("Enter Discord Client Secret")
        form.addRow("Client Secret:", self.client_secret_input)

        layout.addLayout(form)

        btn_layout = QtWidgets.QHBoxLayout()
        self.save_btn = QtWidgets.QPushButton("Save Config")
        self.save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(self.save_btn)

        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.clicked.connect(self.start_discord_auth)
        btn_layout.addWidget(self.connect_btn)

        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_watching)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Variables
        self.access_token = None
        self.last_avatar_url = None
        self.watching = False

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_avatar)
        self.timer.start(30000)

        # System tray
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon())
        self.tray.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.setVisible(True)
        menu = QtWidgets.QMenu()
        menu.addAction("Open WinCord", self.show_window)
        menu.addAction("Stop Watching", self.stop_watching)
        menu.addAction("Exit Completely", self.exit_app)
        self.tray.setContextMenu(menu)

        # Load existing token.json
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                refresh_token = token_data.get("refresh_token")
                if refresh_token:
                    self.log("🔑 Found token.json, refreshing access token...")
                    self.access_token = self.refresh_access_token()
                    if self.access_token:
                        self.log("✅ Access token refreshed. Watching avatar...")
                        self.start_watching()
            except Exception as e:
                self.log(f"⚠ Failed to use token.json: {e}")

        # Add to startup silently in a thread
        threading.Thread(target=self.ensure_startup, daemon=True).start()

    # Logging
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.log_box.append(log_msg)
        print(log_msg)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")

    # Config
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_config(self):
        self.cfg["client_id"] = self.client_id_input.text()
        self.cfg["client_secret"] = self.client_secret_input.text()
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.cfg, f)
        self.client_id = self.cfg["client_id"]
        self.client_secret = self.cfg["client_secret"]
        self.log("💾 Config saved.")

    # Discord OAuth
    def start_discord_auth(self):
        if self.access_token:
            self.log("✅ Already connected with Discord.")
            return
        self.save_config()
        if not self.client_id or not self.client_secret:
            self.log("❌ Client ID or Secret is empty!")
            return
        auth_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={self.client_id}"
            f"&redirect_uri={self.REDIRECT_URI}&response_type=code&scope=identify"
        )
        threading.Thread(target=self.run_flask_server, daemon=True).start()
        time.sleep(1)
        webbrowser.open(auth_url)
        self.log("⌛ Waiting for Discord authorization...")

    def refresh_access_token(self):
        if not os.path.exists(TOKEN_FILE):
            return None
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return None
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post(self.TOKEN_URL, data=data, headers=headers)
        token_data = r.json()
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f)
        self.access_token = token_data.get("access_token")
        return self.access_token

    # Avatar
    def get_avatar_url(self):
        if not self.access_token:
            self.refresh_access_token()
        if not self.access_token:
            return None
        headers = {"Authorization": f"Bearer {self.access_token}"}
        r = requests.get(self.API_URL, headers=headers)
        user = r.json()
        avatar_hash = user.get("avatar")
        if not avatar_hash:
            return None
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_hash}.{ext}?size=512", ext

    def check_avatar(self):
        if not self.watching:
            return
        try:
            url_ext = self.get_avatar_url()
            if not url_ext:
                return
            url, ext = url_ext
            if url != self.last_avatar_url:
                self.last_avatar_url = url
                r = requests.get(url)
                if r.status_code == 200:
                    avatar_file = os.path.join(AVATAR_DIR, f"avatar.{ext}")
                    for f in os.listdir(AVATAR_DIR):
                        os.remove(os.path.join(AVATAR_DIR, f))
                    with open(avatar_file, "wb") as f:
                        f.write(r.content)
                    self.log(f"🔥 Avatar updated: {avatar_file}")
                    self.update_windows_avatar(avatar_file)
        except Exception as e:
            self.log(f"❌ Error: {e}")

    # Windows Avatar (PsExec)
    def update_windows_avatar(self, image_path):
        try:
            self.log("🔧 Updating Windows account picture silently...")
            username = getpass.getuser()
            cmd_sid = f'(New-Object System.Security.Principal.NTAccount("{username}")).Translate([System.Security.Principal.SecurityIdentifier]).Value'
            sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd_sid],
                                          creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
            psexec_path = os.path.join(BASE_DIR, "tools", "PsExec.exe")
            if not os.path.exists(psexec_path):
                self.log("❌ PsExec.exe not found in tools folder!")
                return

            sizes = ["Image96","Image448","Image32","Image40","Image48","Image192","Image240","Image64","Image208","Image424","Image1080"]
            reg_path = f'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AccountPicture\\Users\\{sid}'

            ps_payload = f'Set-StrictMode -Version Latest;$ErrorActionPreference="SilentlyContinue";'
            ps_payload += f'if(-not(Test-Path "{reg_path}")){{New-Item -Path "{reg_path}" -Force|Out-Null}};'
            for s in sizes:
                ps_payload += f'New-ItemProperty -Path "{reg_path}" -Name "{s}" -PropertyType String -Value "{image_path}" -Force|Out-Null;'

            subprocess.run([psexec_path, "-accepteula", "-s", "-d",
                            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_payload],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW, shell=False)
            self.log("✅ Windows account picture updated successfully.")
        except Exception as e:
            self.log(f"❌ Failed to update Windows avatar: {e}")

    # Start / Stop
    def stop_watching(self):
        self.watching = False
        self.log("⏹ Stopped watching.")

    def start_watching(self):
        self.watching = True
        self.log("▶ Started watching avatar.")

    # Tray
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("WinCord", "Application minimized to tray.", QtWidgets.QSystemTrayIcon.MessageIcon.Information)

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def exit_app(self):
        self.tray.hide()
        QtWidgets.QApplication.quit()

    def run_flask_server(self):
        app.run(port=8000, debug=False, use_reloader=False)

    # -------------------------
    # Startup Shortcut (pylnk3)
    # -------------------------
    def ensure_startup(self):
        try:
            import winshell
            import pythoncom
            from win32com.client import Dispatch
    
            startup_dir = winshell.startup()
            exe_path = sys.executable
            shortcut_path = os.path.join(startup_dir, "WinCord.lnk")
    
            if os.path.exists(shortcut_path):
                return
    
            pythoncom.CoInitialize()
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.Arguments = "--startup"  # ✅ إضافة الوسيط لتشغيل التطبيق في الخلفية
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.Description = "WinCord - Discord Avatar to Windows"
            shortcut.save()
    
            self.log("✅ Added WinCord to Startup folder with --startup (UAC may appear).")
        except Exception as e:
            self.log(f"❌ Failed to add to Startup: {e}")

# -------------------------
# Flask routes
# -------------------------
@app.route("/callback")
def callback():
    code = request.args.get("code")
    data = {
        "client_id": WinCordApp.instance.client_id,
        "client_secret": WinCordApp.instance.client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": WinCordApp.REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(WinCordApp.TOKEN_URL, data=data, headers=headers)
    token_data = r.json()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f)
    WinCordApp.instance.access_token = token_data.get("access_token")
    WinCordApp.instance.log("✅ Discord login successful!")
    WinCordApp.instance.start_watching()
    return "✅ Login successful! You can close this window."

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    qt_app = QtWidgets.QApplication(sys.argv)

    # تحقق إذا تم التشغيل من Startup
    STARTUP_MODE = "--startup" in sys.argv

    window = WinCordApp()

    if STARTUP_MODE:
        # تشغيل في الخلفية مباشرة (Tray) بدون فتح النافذة
        window.hide()
        window.log("🟢 Started in Tray (Startup mode). Right-click tray icon to open.")
    else:
        # تشغيل يدوي → أظهر النافذة
        window.show()

    sys.exit(qt_app.exec())