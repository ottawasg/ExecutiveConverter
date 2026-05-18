import sys
import subprocess
import shutil
import tkinter as tk

# ── Dependency installer splash ───────────────────────────────────
REQUIRED_PY = [
    ("customtkinter", "customtkinter"),
    ("PIL",           "Pillow"),
    ("yt_dlp",        "yt-dlp"),
    ("requests",      "requests"),
]

def _check_missing_py():
    missing = []
    for import_name, pkg_name in REQUIRED_PY:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg_name)
    return missing

def _ffmpeg_installed():
    return shutil.which("ffmpeg") is not None

def _refresh_path():
    """Pull updated PATH from registry so newly installed tools are found."""
    try:
        import winreg, os
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
            sys_path, _ = winreg.QueryValueEx(k, "Path")
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                usr_path, _ = winreg.QueryValueEx(k, "Path")
        except FileNotFoundError:
            usr_path = ""
        os.environ["PATH"] = sys_path + ";" + usr_path + ";" + os.environ.get("PATH", "")
    except Exception:
        pass

def _install_ffmpeg():
    result = subprocess.run(
        ["winget", "install", "--id", "Gyan.FFmpeg", "-e",
         "--accept-source-agreements", "--accept-package-agreements", "--silent"],
        capture_output=True
    )
    _refresh_path()  # update PATH immediately after install
    return result.returncode == 0

def _run_splash_installer():
    """Install missing deps via console output before any GUI is created."""
    missing_py  = _check_missing_py()
    need_ffmpeg = not _ffmpeg_installed()
    if not missing_py and not need_ffmpeg:
        return

    print("=" * 50)
    print("  Executive Converter — Setup")
    print("=" * 50)

    for pkg in missing_py:
        print(f"  Installing {pkg}...", end=" ", flush=True)
        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                           capture_output=True)
        print("OK" if r.returncode == 0 else "FAILED")

    if need_ffmpeg:
        print("  Installing ffmpeg via winget (may take a minute)...", end=" ", flush=True)
        ok = _install_ffmpeg()
        print("OK" if (ok and _ffmpeg_installed()) else "FAILED")

    still_missing = _check_missing_py()
    still_no_ff   = not _ffmpeg_installed()

    if still_missing or still_no_ff:
        print()
        print("  ERROR: Some dependencies could not be installed:")
        if still_missing:
            print(f"    Python: {', '.join(still_missing)}")
            print(f"    Run: python -m pip install {' '.join(still_missing)}")
        if still_no_ff:
            print("    ffmpeg: not found")
            print("    Download from: https://ffmpeg.org/download.html")
        print()
        input("  Press Enter to exit...")
        sys.exit(1)

    print("  All dependencies ready.")
    print()

_run_splash_installer()

# ── Imports ───────────────────────────────────────────────────────
import customtkinter as ctk
import threading
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── App directory (works both as .py and frozen .exe) ─────────────
import sys as _sys
APP_DIR = Path(_sys.executable).parent if getattr(_sys, "frozen", False) else Path(__file__).parent

# ── Config ────────────────────────────────────────────────────────
_CONFIG_FILE = APP_DIR / "config.json"
_CONFIG_DEFAULTS = {
    "ROBLOX_API_KEY":    "",
    "ROBLOX_USER_ID":    "",
    "DOWNLOADS_FOLDER":  "downloads",
    "UPLOAD_JSON":       "upload.json",
    "SPEED":             2.3,
    "AMPLIFY_DB":        -4,
    "LICENSE_KEY":       "",
    "LICENSE_VALID_UNTIL": "",
    "LICENSE_TIER":      "",
    "LICENSE_EXPIRES_AT": "",
}

LICENSE_API     = "https://vercel-api-three-rho.vercel.app"
_LICENSE_SECRET = "2ffc6cc3c180782978ce6cf33dde044541af114d9e24bd80"

def _validate_license(key: str) -> dict:
    import requests as _req
    try:
        r = _req.post(
            f"{LICENSE_API}/api/validate",
            headers={"x-api-secret": _LICENSE_SECRET, "Content-Type": "application/json"},
            json={"license_key": key}, timeout=10,
        )
        return r.json() if r.status_code == 200 else {"valid": False, "message": f"Server error ({r.status_code})"}
    except Exception as e:
        return {"valid": False, "message": f"Network error: {e}"}

def load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return {**_CONFIG_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_CONFIG_DEFAULTS)

def save_config(cfg: dict):
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

if not _CONFIG_FILE.exists():
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_old", APP_DIR / "config.py")
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        save_config({
            "ROBLOX_API_KEY":   getattr(mod, "ROBLOX_API_KEY",  ""),
            "ROBLOX_USER_ID":   getattr(mod, "ROBLOX_USER_ID",  ""),
            "DOWNLOADS_FOLDER": getattr(mod, "DOWNLOADS_FOLDER", "downloads"),
            "UPLOAD_JSON":      getattr(mod, "UPLOAD_JSON",      "upload.json"),
            "SPEED":            getattr(mod, "SPEED",            2.3),
            "AMPLIFY_DB":       getattr(mod, "AMPLIFY_DB",       -4),
        })
    except Exception:
        save_config(dict(_CONFIG_DEFAULTS))

CFG              = load_config()
SPEED            = CFG["SPEED"]
AMPLIFY_DB       = CFG["AMPLIFY_DB"]
# Always resolve relative paths against APP_DIR so .exe finds them next to itself
_dl = CFG["DOWNLOADS_FOLDER"]
DOWNLOADS_FOLDER = str(APP_DIR / _dl) if not Path(_dl).is_absolute() else _dl

import cfg as _cfg_mod  # keep other scripts in sync

# ── Theme ─────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# VS Code / Figma inspired palette
BG        = "#0d0f14"   # deepest background
SB        = "#111318"   # sidebar
CARD      = "#161b22"   # card / input bg
CARD2     = "#1c2130"   # slightly lighter card
BORDER    = "#21262d"   # border
ACCENT    = "#2f81f7"   # blue accent
ACCENT_H  = "#1f6feb"
GREEN     = "#238636"
GREEN_H   = "#2ea043"
PURPLE    = "#6e40c9"
PURPLE_H  = "#5a32a3"
TEXT      = "#e6edf3"
TEXT_DIM  = "#7d8590"
TEXT_MUT  = "#3d444d"
DANGER    = "#da3633"

# ── FA Icon renderer ──────────────────────────────────────────────
_FA_TTF = APP_DIR / "fa-solid-900.ttf"
if not _FA_TTF.exists():
    import site
    for _sp in site.getsitepackages():
        _c = Path(_sp) / "fontawesome-free/static/fontawesome_free/webfonts/fa-solid-900.ttf"
        if _c.exists():
            _FA_TTF = _c
            break

_FA_ICONS = {
    "download":   "",
    "upload":     "",
    "search":     "",
    "save":       "",
    "trash":      "",
    "sync":       "",
    "globe":      "",
    "cog":        "",
    "file-audio": "",
    "list":       "",
    "check":      "",
    "times":      "",
    "key":        "",
    "user":       "",
    "sign-out":   "",
}
_icon_cache: dict = {}

def fa_icon(name: str, size: int = 13, color: str = "#ffffff"):
    key = (name, size, color)
    if key in _icon_cache:
        return _icon_cache[key]
    if not _FA_TTF.exists():
        return None
    ch = _FA_ICONS.get(name)
    if not ch:
        return None
    try:
        pad = max(2, size // 6)
        c   = size + pad * 2
        img  = Image.new("RGBA", (c, c), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(str(_FA_TTF), size)
        bbox = draw.textbbox((0, 0), ch, font=font)
        x = (c - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = (c - (bbox[3] - bbox[1])) // 2 - bbox[1]
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        draw.text((x, y), ch, font=font, fill=(r, g, b, 255))
        ci = ctk.CTkImage(light_image=img, dark_image=img, size=(c, c))
        _icon_cache[key] = ci
        return ci
    except Exception:
        return None

# ── Roblox helpers ────────────────────────────────────────────────
def _fetch_roblox_profile(user_id: str):
    import requests as req
    from io import BytesIO
    info = req.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=8).json()
    dn   = info.get("displayName") or info.get("name", user_id)
    thumb = req.get(
        "https://thumbnails.roblox.com/v1/users/avatar-headshot",
        params={"userIds": user_id, "size": "150x150", "format": "Png", "isCircular": "false"},
        timeout=8,
    ).json()
    img_url = thumb["data"][0]["imageUrl"]
    avatar  = Image.open(BytesIO(req.get(img_url, timeout=8).content)).convert("RGBA")
    return dn, avatar

def _make_circle_avatar(img: Image.Image, size: int) -> ctk.CTkImage:
    img  = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return ctk.CTkImage(light_image=out, dark_image=out, size=(size, size))


# ═══════════════════════════════════════════════════════════════════
#  APP
# ═══════════════════════════════════════════════════════════════════
def _apply_taskbar_visibility(title: str):
    """Force the frameless window to show in the Windows taskbar."""
    import ctypes
    GWL_EXSTYLE      = -20
    WS_EX_APPWINDOW  = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080
    u32 = ctypes.windll.user32
    hwnd = u32.FindWindowW(None, title)
    if not hwnd:
        return
    style = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
    u32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    u32.ShowWindow(hwnd, 0)   # SW_HIDE
    u32.ShowWindow(hwnd, 9)   # SW_RESTORE


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Executive Converter")
        self.overrideredirect(True)   # remove OS title bar
        self.geometry("820x560")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - 820) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"820x560+{x}+{y}")
        self._drag_x = self._drag_y = 0
        # Make window appear in taskbar despite overrideredirect
        self.after(50, lambda: _apply_taskbar_visibility(self.title()))

        self._active_page   = None
        self._sidebar_btns  = {}
        self._pages         = {}
        self._user_id       = None
        self._display_name  = None
        self._avatar_img    = None

        if not self._license_ok():
            self._show_license_screen()
        else:
            self._after_license()

    # ── Thread-safe log ──────────────────────────────────────────
    def log(self, msg: str):
        self.after(0, self._log_ui, msg)

    def _log_ui(self, msg: str):
        try:
            self._log_box.configure(state="normal")
            self._log_box.insert("end", msg)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _log_clear(self):
        try:
            self._log_box.configure(state="normal")
            self._log_box.delete("1.0", "end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _redirect_stdout(self):
        import io, threading as _th
        app = self

        class _Writer(io.TextIOBase):
            def __init__(self_):
                self_._buf       = []
                self_._lock      = _th.Lock()
                self_._scheduled = False
            def write(self_, s):
                if not s:
                    return 0
                with self_._lock:
                    self_._buf.append(s)
                    if not self_._scheduled:
                        self_._scheduled = True
                        app.after(250, self_._flush)
                return len(s)
            def _flush(self_):
                with self_._lock:
                    text = "".join(self_._buf)
                    self_._buf.clear()
                    self_._scheduled = False
                if text:
                    app.log(text)
            def flush(self_):
                self_._flush()

        class _Ctx:
            def __enter__(self_):
                self_._w   = _Writer()
                self_._old = sys.stdout
                sys.stdout = self_._w
                return self_
            def __exit__(self_, *_):
                sys.stdout = self_._old
                self_._w.flush()
        return _Ctx()

    # ── License gate ─────────────────────────────────────────────
    def _license_ok(self) -> bool:
        import datetime
        key   = CFG.get("LICENSE_KEY", "").strip()
        until = CFG.get("LICENSE_VALID_UNTIL", "").strip()
        if not key:
            return False
        try:
            return datetime.date.fromisoformat(until) >= datetime.date.today()
        except ValueError:
            return False

    def _show_license_screen(self):
        self._lic_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._lic_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        wrap = ctk.CTkFrame(self._lic_frame, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrap, text="Executive Converter",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"),
                     text_color=TEXT).pack(padx=48, pady=(36, 4))
        ctk.CTkLabel(wrap, text="Enter your license key to continue",
                     font=ctk.CTkFont("Segoe UI", 12),
                     text_color=TEXT_DIM).pack(pady=(0, 24))

        self._lic_entry = ctk.CTkEntry(
            wrap, width=320, height=42,
            placeholder_text="XXXX-XXXX-XXXX-XXXX",
            font=ctk.CTkFont("Consolas", 13),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8,
        )
        saved = CFG.get("LICENSE_KEY", "")
        if saved:
            self._lic_entry.insert(0, saved)
        self._lic_entry.pack(pady=(0, 8))

        self._lic_status = ctk.CTkLabel(wrap, text="",
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=DANGER)
        self._lic_status.pack(pady=(0, 8))

        self._lic_btn = ctk.CTkButton(
            wrap, text="Activate", width=320, height=42,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_H, corner_radius=8,
            command=self._do_activate,
        )
        self._lic_btn.pack(pady=(0, 36))
        self._lic_entry.bind("<Return>", lambda _: self._do_activate())
        self._lic_entry.focus()

    def _do_activate(self):
        key = self._lic_entry.get().strip().upper()
        if len(key) < 4:
            self._lic_status.configure(text="Enter a valid license key.")
            return
        self._lic_btn.configure(state="disabled", text="Checking…")
        self._lic_status.configure(text="")
        threading.Thread(target=self._check_license, args=(key,), daemon=True).start()

    def _check_license(self, key: str):
        import datetime
        result = _validate_license(key)
        if result.get("valid"):
            CFG["LICENSE_KEY"]        = key
            CFG["LICENSE_VALID_UNTIL"] = datetime.date.today().isoformat()
            CFG["LICENSE_TIER"]       = result.get("tier", "")
            CFG["LICENSE_EXPIRES_AT"] = result.get("expires_at") or ""
            save_config(CFG)
            self.after(0, self._on_license_ok)
        else:
            msg = result.get("message", "Invalid license.")
            self.after(0, lambda: self._lic_btn.configure(state="normal", text="Activate"))
            self.after(0, lambda: self._lic_status.configure(text=msg, text_color=DANGER))

    def _on_license_ok(self):
        self._lic_frame.destroy()
        self._after_license()

    def _after_license(self):
        threading.Thread(target=self._revalidate_bg, daemon=True).start()
        threading.Thread(target=self._check_for_update, daemon=True).start()
        saved_uid = CFG.get("SAVED_USER_ID", "").strip()
        if saved_uid:
            self._build_ui()
            self._show_page("download")
            threading.Thread(target=self._auto_login, args=(saved_uid,), daemon=True).start()
        else:
            self._show_login_screen()

    def _revalidate_bg(self):
        import datetime
        key = CFG.get("LICENSE_KEY", "").strip()
        if not key:
            return
        result = _validate_license(key)
        if result.get("valid"):
            CFG["LICENSE_VALID_UNTIL"] = datetime.date.today().isoformat()
            CFG["LICENSE_TIER"]        = result.get("tier", CFG.get("LICENSE_TIER", ""))
            CFG["LICENSE_EXPIRES_AT"]  = result.get("expires_at") or CFG.get("LICENSE_EXPIRES_AT", "")
            save_config(CFG)
            self.after(0, self._refresh_license_badge)
        else:
            CFG["LICENSE_VALID_UNTIL"] = ""
            save_config(CFG)
            self.after(0, self._force_license_screen)

    # ── Auto-updater ─────────────────────────────────────────────
    _CURRENT_VERSION = "1.0.0"
    _GITHUB_USER     = ""   # filled after gh auth
    _GITHUB_REPO     = "ExecutiveConverter"

    def _check_for_update(self):
        import urllib.request, json as _json
        try:
            vf = APP_DIR / "version.json"
            current = self._CURRENT_VERSION
            if vf.exists():
                current = _json.loads(vf.read_text()).get("version", current)

            # resolve github user from gh cli if blank
            user = self._GITHUB_USER
            if not user:
                r = __import__("subprocess").run(
                    "gh api user --jq .login", shell=True, capture_output=True, text=True)
                user = r.stdout.strip()
            if not user:
                return

            api_url = f"https://api.github.com/repos/{user}/{self._GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "ExecutiveConverter"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = _json.loads(resp.read())

            latest    = data.get("tag_name", "").lstrip("v")
            changelog = data.get("body", "")
            dl_url    = next(
                (a["browser_download_url"] for a in data.get("assets", [])
                 if a["name"].endswith(".exe")), data.get("html_url", "")
            )

            if latest and latest != current:
                self.after(0, lambda: self._show_update_banner(latest, changelog, dl_url))
        except Exception:
            pass

    def _show_update_banner(self, version, changelog, url):
        banner = ctk.CTkFrame(self, fg_color="#1c2a1c", corner_radius=0,
                               border_width=0, height=38)
        banner.pack(side="bottom", fill="x")
        banner.pack_propagate(False)

        ctk.CTkLabel(banner, text=f"  🔔  Update tersedia: v{version}  —  {changelog[:60]}",
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color="#3fb950").pack(side="left", padx=(10, 0))

        def _download():
            import webbrowser
            webbrowser.open(url)

        ctk.CTkButton(banner, text="Download", width=90, height=26,
                      font=ctk.CTkFont("Segoe UI", 11, "bold"),
                      fg_color=GREEN, hover_color=GREEN_H, corner_radius=5,
                      command=_download).pack(side="right", padx=8, pady=6)
        ctk.CTkButton(banner, text="✕", width=28, height=26,
                      font=ctk.CTkFont("Segoe UI", 12),
                      fg_color="transparent", hover_color=CARD2,
                      text_color=TEXT_DIM, corner_radius=5,
                      command=banner.destroy).pack(side="right", padx=(0, 4), pady=6)

    def _force_license_screen(self):
        for w in self.winfo_children():
            w.destroy()
        self._active_page = None
        self._sidebar_btns = {}
        self._pages = {}
        self._show_license_screen()
        self._lic_status.configure(text="Your license has expired.", text_color="#f59e0b")

    # ── Roblox login screen ───────────────────────────────────────
    def _show_login_screen(self):
        self._login_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        wrap = ctk.CTkFrame(self._login_frame, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrap, text="Executive Converter",
                     font=ctk.CTkFont("Segoe UI", 22, "bold"), text_color=TEXT).pack(padx=48, pady=(36, 4))
        ctk.CTkLabel(wrap, text="Connect your Roblox account",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=TEXT_DIM).pack(pady=(0, 24))

        self._login_entry = ctk.CTkEntry(
            wrap, width=320, height=42,
            placeholder_text="Roblox User ID",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=CARD2, border_color=BORDER, border_width=1,
            text_color=TEXT, corner_radius=8,
        )
        self._login_entry.pack(pady=(0, 8))

        self._login_status = ctk.CTkLabel(wrap, text="",
                                          font=ctk.CTkFont("Segoe UI", 11),
                                          text_color=DANGER)
        self._login_status.pack(pady=(0, 8))

        self._login_btn = ctk.CTkButton(
            wrap, text="Connect", width=320, height=42,
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_H, corner_radius=8,
            command=self._do_login,
        )
        self._login_btn.pack(pady=(0, 36))
        self._login_entry.bind("<Return>", lambda _: self._do_login())
        self._login_entry.focus()

    def _do_login(self):
        uid = self._login_entry.get().strip()
        if not uid.isdigit():
            self._login_status.configure(text="User ID must be numbers only.")
            return
        self._login_btn.configure(state="disabled", text="Connecting…")
        self._login_status.configure(text="")
        threading.Thread(target=self._verify_login, args=(uid,), daemon=True).start()

    def _verify_login(self, uid: str):
        try:
            dn, av = _fetch_roblox_profile(uid)
            self._user_id      = uid
            self._display_name = dn
            self._avatar_img   = av
            self.after(0, self._on_login_ok)
        except Exception as e:
            self.after(0, lambda: self._login_btn.configure(state="normal", text="Connect"))
            self.after(0, lambda: self._login_status.configure(text=f"Failed: {e}"))

    def _on_login_ok(self):
        CFG["SAVED_USER_ID"] = self._user_id
        save_config(CFG)
        self._build_ui()
        self._show_page("download")
        self._update_profile()
        self._slide_out(self._login_frame)

    def _auto_login(self, uid: str):
        try:
            dn, av = _fetch_roblox_profile(uid)
            self._user_id = uid; self._display_name = dn; self._avatar_img = av
            self.after(0, self._update_profile)
        except Exception:
            pass

    def _slide_out(self, frame, rely: float = 0.0):
        rely -= 0.08
        if rely < -1:
            frame.destroy(); return
        frame.place(relx=0, rely=rely, relwidth=1, relheight=1)
        self.after(14, lambda: self._slide_out(frame, rely))

    # ── Drag helpers ──────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _minimize(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._on_restore)

    def _on_restore(self, _event):
        self.unbind("<Map>")
        self.overrideredirect(True)
        self.lift()
        self.after(50, lambda: _apply_taskbar_visibility(self.title()))

    # ── Main UI ───────────────────────────────────────────────────
    def _build_ui(self):
        # ── Custom title bar ──────────────────────────────────────
        self._titlebar = ctk.CTkFrame(self, height=32, fg_color=SB, corner_radius=0)
        self._titlebar.pack(side="top", fill="x")
        self._titlebar.pack_propagate(False)

        ctk.CTkLabel(self._titlebar, text="Executive Converter",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=TEXT_DIM).pack(side="left", padx=14)

        # Close button
        _close = tk.Button(
            self._titlebar, text="×", bd=0, relief="flat", padx=0, pady=0,
            font=("Segoe UI", 15), cursor="hand2",
            bg=SB, fg=TEXT_DIM, activebackground=DANGER, activeforeground="#ffffff",
            command=self.destroy,
        )
        _close.pack(side="right", ipadx=10, ipady=2)
        _close.bind("<Enter>", lambda _: _close.configure(bg=DANGER, fg="#ffffff"))
        _close.bind("<Leave>", lambda _: _close.configure(bg=SB, fg=TEXT_DIM))

        # Minimize button
        _mini = tk.Button(
            self._titlebar, text="−", bd=0, relief="flat", padx=0, pady=0,
            font=("Segoe UI", 13), cursor="hand2",
            bg=SB, fg=TEXT_DIM, activebackground=CARD2, activeforeground=TEXT,
            command=self._minimize,
        )
        _mini.pack(side="right", ipadx=8, ipady=2)
        _mini.bind("<Enter>", lambda _: _mini.configure(bg=CARD2, fg=TEXT))
        _mini.bind("<Leave>", lambda _: _mini.configure(bg=SB, fg=TEXT_DIM))

        # Drag to move
        self._titlebar.bind("<ButtonPress-1>",   self._drag_start)
        self._titlebar.bind("<B1-Motion>",        self._drag_move)
        for child in self._titlebar.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.bind("<ButtonPress-1>", self._drag_start)
                child.bind("<B1-Motion>",     self._drag_move)

        ctk.CTkFrame(self, height=1, fg_color=BORDER, corner_radius=0).pack(side="top", fill="x")

        # ── Body row (sidebar + content) ─────────────────────────
        self._body = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._body.pack(side="top", fill="both", expand=True)

        # ── Sidebar ───────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self._body, width=200, fg_color=SB, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # App name
        hdr = ctk.CTkFrame(self.sidebar, fg_color=SB, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Executive Converter",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=TEXT).pack(side="left", padx=16, pady=14)

        self._divider(self.sidebar)

        # Profile card
        self._profile_card = ctk.CTkFrame(self.sidebar, fg_color=CARD2,
                                          corner_radius=10, border_width=1, border_color=BORDER)
        self._profile_card.pack(fill="x", padx=10, pady=(10, 6))

        av_row = ctk.CTkFrame(self._profile_card, fg_color="transparent")
        av_row.pack(fill="x", padx=12, pady=(12, 6))

        self._avatar_label = ctk.CTkLabel(av_row, text="", width=40)
        self._avatar_label.pack(side="left")

        info = ctk.CTkFrame(av_row, fg_color="transparent")
        info.pack(side="left", padx=(8, 0), fill="x", expand=True)
        self._name_label = ctk.CTkLabel(info, text="Not connected",
                                        font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                        text_color=TEXT_DIM, anchor="w")
        self._name_label.pack(anchor="w")
        self._uid_label = ctk.CTkLabel(info, text="",
                                       font=ctk.CTkFont("Segoe UI", 10),
                                       text_color=TEXT_MUT, anchor="w")
        self._uid_label.pack(anchor="w")

        # License badge
        self._lic_badge = ctk.CTkLabel(
            self._profile_card, text="",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_DIM, anchor="w",
        )
        self._lic_badge.pack(anchor="w", padx=12, pady=(0, 4))
        self._refresh_license_badge()

        self._switch_btn = ctk.CTkButton(
            self._profile_card, text="Switch Account",
            height=28, corner_radius=6,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=CARD, hover_color=CARD2,
            text_color=TEXT_DIM, border_width=1, border_color=BORDER,
            command=self._open_switch_account,
        )
        self._switch_btn.pack(padx=10, pady=(0, 10), fill="x")

        self._divider(self.sidebar)

        # Nav
        nav_items = [
            ("download", "Download",    "download"),
            ("upload",   "Upload",      "upload"),
            ("status",   "Check Status","search"),
            ("logs",     "Logs",        "list"),
            ("config",   "Settings",    "cog"),
        ]
        self._nav_wrap = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self._nav_wrap.pack(fill="x", padx=8, pady=8)
        for key, label, icon_name in nav_items:
            self._make_nav_btn(key, label, icon_name)

        # Bottom version
        self._divider(self.sidebar, side="bottom")
        ctk.CTkLabel(self.sidebar, text="v1.0  ·  Executive Converter",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXT_MUT).pack(side="bottom", pady=8)

        # ── Content area ──────────────────────────────────────────
        self.content = ctk.CTkFrame(self._body, fg_color=BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self._build_download_page()
        self._build_upload_page()
        self._build_status_page()
        self._build_logs_page()
        self._build_config_page()

    def _make_nav_btn(self, key, label, icon_name):
        ico = fa_icon(icon_name, size=13, color=TEXT_DIM)
        btn = ctk.CTkButton(
            self._nav_wrap, text=f"  {label}", anchor="w",
            image=ico, compound="left",
            height=36, corner_radius=6,
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color="transparent", hover_color=CARD2,
            text_color=TEXT_DIM, border_width=0,
            command=lambda k=key: self._show_page(k),
        )
        btn.pack(fill="x", pady=1)
        self._sidebar_btns[key] = (btn, icon_name)

    def _divider(self, parent, side=None):
        kw = {"side": side} if side else {}
        ctk.CTkFrame(parent, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x", **kw)

    # ── Profile ───────────────────────────────────────────────────
    def _update_profile(self):
        if self._avatar_img:
            av = _make_circle_avatar(self._avatar_img, 40)
            self._avatar_label.configure(image=av, text="")
            self._avatar_label._ctk_image = av
        self._name_label.configure(text=self._display_name or "Unknown", text_color=TEXT)
        self._uid_label.configure(text=f"ID: {self._user_id}")

    def _refresh_license_badge(self):
        import datetime
        tier    = CFG.get("LICENSE_TIER", "")
        expires = CFG.get("LICENSE_EXPIRES_AT", "")
        t_map   = {"7d": "7 Days", "30d": "30 Days", "lifetime": "Lifetime"}
        ts      = t_map.get(tier, tier or "Licensed")
        if tier == "lifetime" or not expires:
            self._lic_badge.configure(text=f"  License: {ts}", text_color="#3fb950")
        else:
            try:
                dt   = datetime.datetime.fromisoformat(expires.replace("Z", "+00:00"))
                left = (dt - datetime.datetime.now(datetime.timezone.utc)).days
                exp  = dt.strftime("%b %d %Y")
                if left < 0:
                    self._lic_badge.configure(text=f"  License: Expired", text_color=DANGER)
                elif left <= 3:
                    self._lic_badge.configure(text=f"  License: {ts} · {left}d left", text_color="#f0883e")
                else:
                    self._lic_badge.configure(text=f"  License: {ts} · {exp}", text_color="#3fb950")
            except Exception:
                self._lic_badge.configure(text=f"  License: {ts}", text_color="#3fb950")

    def _open_switch_account(self):
        overlay = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()

        wrap = ctk.CTkFrame(overlay, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDER)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrap, text="Switch Account",
                     font=ctk.CTkFont("Segoe UI", 18, "bold"), text_color=TEXT).pack(padx=48, pady=(32, 4))
        ctk.CTkLabel(wrap, text="Enter new Roblox User ID",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_DIM).pack(pady=(0, 20))

        entry = ctk.CTkEntry(wrap, width=300, height=40,
                             placeholder_text="User ID",
                             font=ctk.CTkFont("Segoe UI", 13),
                             fg_color=CARD2, border_color=BORDER, border_width=1,
                             text_color=TEXT, corner_radius=8)
        entry.pack(pady=(0, 8))
        entry.focus()

        status = ctk.CTkLabel(wrap, text="", font=ctk.CTkFont("Segoe UI", 11), text_color=DANGER)
        status.pack(pady=(0, 8))

        def cancel():
            overlay.destroy()

        btn_row = ctk.CTkFrame(wrap, fg_color="transparent")
        btn_row.pack(pady=(0, 28))

        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=140, height=38,
                                   fg_color=CARD2, hover_color=CARD, text_color=TEXT_DIM,
                                   border_width=1, border_color=BORDER, corner_radius=8,
                                   command=cancel)
        cancel_btn.pack(side="left", padx=(0, 8))

        def _switch():
            uid = entry.get().strip()
            if not uid.isdigit():
                status.configure(text="User ID must be numbers only.")
                return
            ok_btn.configure(state="disabled", text="Connecting…")
            status.configure(text="")
            def _verify():
                try:
                    dn, av = _fetch_roblox_profile(uid)
                    self._user_id = uid; self._display_name = dn; self._avatar_img = av
                    CFG["SAVED_USER_ID"] = uid
                    save_config(CFG)
                    self.after(0, self._update_profile)
                    self.after(0, overlay.destroy)
                except Exception as e:
                    self.after(0, lambda: ok_btn.configure(state="normal", text="Connect"))
                    self.after(0, lambda: status.configure(text=f"Failed: {e}"))
            threading.Thread(target=_verify, daemon=True).start()

        ok_btn = ctk.CTkButton(btn_row, text="Connect", width=140, height=38,
                               fg_color=ACCENT, hover_color=ACCENT_H, corner_radius=8,
                               font=ctk.CTkFont("Segoe UI", 12, "bold"),
                               command=_switch)
        ok_btn.pack(side="left")
        entry.bind("<Return>", lambda _: _switch())

    # ── Page navigation ───────────────────────────────────────────
    def _show_page(self, key):
        if self._active_page == key:
            return
        for f in self._pages.values():
            f.pack_forget()
        for k, (btn, icon_name) in self._sidebar_btns.items():
            active = k == key
            col    = TEXT if active else TEXT_DIM
            btn.configure(
                fg_color=CARD2 if active else "transparent",
                text_color=col,
                font=ctk.CTkFont("Segoe UI", 13, "bold" if active else "normal"),
                image=fa_icon(icon_name, 13, col),
            )
        self._pages[key].pack(fill="both", expand=True, padx=20, pady=18)
        self._active_page = key
        if key == "upload":
            self._refresh_upload_list()

    # ── Widget helpers ────────────────────────────────────────────
    def _section_title(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 14))

    def _field_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_DIM).pack(anchor="w", pady=(0, 4))

    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8,
                            border_width=1, border_color=BORDER, **kw)

    def _entry(self, parent, **kw):
        return ctk.CTkEntry(parent, fg_color=CARD2, border_color=BORDER, border_width=1,
                            text_color=TEXT, corner_radius=6, height=36,
                            font=ctk.CTkFont("Segoe UI", 12), **kw)

    def _primary_btn(self, parent, text, cmd, icon=None, color=ACCENT, hover=ACCENT_H, **kw):
        ico = fa_icon(icon, 13, "#ffffff") if icon else None
        return ctk.CTkButton(parent, text=f"  {text}" if ico else text,
                             image=ico, compound="left",
                             height=38, font=ctk.CTkFont("Segoe UI", 13, "bold"),
                             fg_color=color, hover_color=hover, corner_radius=7,
                             command=cmd, **kw)

    def _ghost_btn(self, parent, text, cmd, icon=None, **kw):
        ico = fa_icon(icon, 12, TEXT_DIM) if icon else None
        return ctk.CTkButton(parent, text=f"  {text}" if ico else text,
                             image=ico, compound="left",
                             height=34, font=ctk.CTkFont("Segoe UI", 11),
                             fg_color=CARD, hover_color=CARD2,
                             text_color=TEXT_DIM, corner_radius=6,
                             border_width=1, border_color=BORDER,
                             command=cmd, **kw)

    def _progress_bar(self, parent):
        pb = ctk.CTkProgressBar(parent, height=3, corner_radius=2,
                                fg_color=BORDER, progress_color=ACCENT)
        pb.set(0)
        return pb

    # ════════════════════════════════════════════════════════════
    #  PAGE 1 — DOWNLOAD
    # ════════════════════════════════════════════════════════════
    def _build_download_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        self._pages["download"] = page

        self._section_title(page, "Download & Convert")

        # Source row
        src_row = ctk.CTkFrame(page, fg_color="transparent")
        src_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(src_row, text="Source",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=TEXT_DIM).pack(side="left", padx=(0, 12))
        self.source_var = ctk.StringVar(value="YouTube")
        ctk.CTkOptionMenu(
            src_row, values=["YouTube", "SoundCloud"],
            variable=self.source_var, width=160, height=34,
            fg_color=CARD, button_color=CARD2, button_hover_color=BORDER,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT,
            text_color=TEXT, font=ctk.CTkFont("Segoe UI", 12),
            corner_radius=6, command=self._on_source_change,
        ).pack(side="left")

        # URL box
        url_card = self._card(page)
        url_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(url_card, text="URLs  (one per line)",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_DIM).pack(anchor="w", padx=14, pady=(10, 4))
        self.url_textbox = ctk.CTkTextbox(
            url_card, height=130,
            font=ctk.CTkFont("Consolas", 11),
            fg_color=CARD2, text_color=TEXT, border_width=0, corner_radius=0,
        )
        self.url_textbox.pack(fill="x", padx=1, pady=(0, 1))
        self._load_urls_to_box()

        # Buttons
        btn_row = ctk.CTkFrame(page, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))
        self.btn_download = self._primary_btn(btn_row, "Download & Convert",
                                              self._start_download, icon="download")
        self.btn_download.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self._ghost_btn(btn_row, "Save", self._save_urls, icon="save", width=80).pack(side="left")

        # Progress
        self.dl_progress = self._progress_bar(page)
        self.dl_progress.pack(fill="x", pady=(0, 2))
        self.dl_status_lbl = ctk.CTkLabel(page, text="",
                                          font=ctk.CTkFont("Segoe UI", 10),
                                          text_color=TEXT_DIM)
        self.dl_status_lbl.pack(anchor="w")

    def _on_source_change(self, _=None):
        self._load_urls_to_box()

    def _get_url_file(self):
        return "urls_youtube.txt" if self.source_var.get() == "YouTube" else "urls_soundcloud.txt"

    def _load_urls_to_box(self):
        path = Path(self._get_url_file())
        self.url_textbox.delete("1.0", "end")
        if path.exists():
            lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.url_textbox.insert("1.0", "\n".join(lines))

    def _save_urls(self):
        raw  = self.url_textbox.get("1.0", "end").strip()
        urls = [l.strip() for l in raw.splitlines() if l.strip()]
        Path(self._get_url_file()).write_text("\n".join(urls), encoding="utf-8")
        self.log(f"Saved {len(urls)} URL(s) to {self._get_url_file()}\n")

    def _start_download(self):
        raw  = self.url_textbox.get("1.0", "end").strip()
        urls = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not urls:
            self.log("No URLs found.\n")
            return
        self._save_urls()
        self.btn_download.configure(state="disabled", text="  Downloading…")
        self.dl_progress.set(0)
        self.dl_status_lbl.configure(text="")
        threading.Thread(target=self._download_worker, args=(urls,), daemon=True).start()

    def _ensure_ffmpeg(self) -> bool:
        if _ffmpeg_installed():
            return True
        self.log("⚙ ffmpeg not found — installing via winget, please wait…\n")
        ok = _install_ffmpeg()
        if ok:
            # Refresh PATH in this process so shutil.which can find it
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
                    sys_path, _ = winreg.QueryValueEx(k, "Path")
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Environment") as k:
                    try:
                        usr_path, _ = winreg.QueryValueEx(k, "Path")
                    except FileNotFoundError:
                        usr_path = ""
                import os
                os.environ["PATH"] = sys_path + ";" + usr_path + ";" + os.environ.get("PATH", "")
            except Exception:
                pass
        if _ffmpeg_installed():
            self.log("✓ ffmpeg installed successfully.\n")
            return True
        self.log("✗ ffmpeg install failed. Install it manually from https://ffmpeg.org/download.html\n")
        return False

    def _download_worker(self, urls):
        from main import download_and_convert
        total = len(urls)
        success = failed = 0
        self.log(f"▶ Starting {total} download(s) [{self.source_var.get()}]\n")
        if not self._ensure_ffmpeg():
            self.after(0, self.btn_download.configure, {"state": "normal", "text": "  Download & Convert"})
            return
        with self._redirect_stdout():
            for i, url in enumerate(urls, 1):
                self.log(f"\n[{i}/{total}] {url}\n")
                self.after(0, self.dl_status_lbl.configure, {"text": f"{i}/{total} downloading…"})
                try:
                    ok = download_and_convert(url)
                except Exception as e:
                    ok = False
                    self.log(f"  Error: {e}\n")
                if ok: success += 1
                else:  failed  += 1
                self.after(0, self.dl_progress.set, i / total)
        self.log(f"\n✓ Done — {success} ok, {failed} failed\n")
        self.after(0, self.dl_status_lbl.configure, {"text": f"Done — {success} ok, {failed} failed"})
        self.after(0, self.btn_download.configure, {"state": "normal", "text": "  Download & Convert"})

    # ════════════════════════════════════════════════════════════
    #  PAGE 2 — UPLOAD
    # ════════════════════════════════════════════════════════════
    def _build_upload_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        self._pages["upload"] = page

        self._section_title(page, "Upload to Roblox")

        # Header row
        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 6))
        self.up_info_lbl = ctk.CTkLabel(hdr, text="Click Refresh to scan",
                                        font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_DIM)
        self.up_info_lbl.pack(side="left")
        self._ghost_btn(hdr, "Refresh", self._refresh_upload_list, icon="sync", width=90).pack(side="right")
        self._ghost_btn(hdr, "Permissions", self._open_permissions,
                        icon="globe", width=110).pack(side="right", padx=(0, 6))

        # Scrollable file list
        self._up_scroll = ctk.CTkScrollableFrame(page, fg_color=CARD,
                                                  corner_radius=8,
                                                  border_width=1, border_color=BORDER,
                                                  height=240)
        self._up_scroll.pack(fill="both", expand=True, pady=(0, 8))
        self._up_rows: list = []   # (frame, filepath, btn, status_lbl)

        # Status bar
        self.up_status_lbl = ctk.CTkLabel(page, text="",
                                          font=ctk.CTkFont("Segoe UI", 10),
                                          text_color=TEXT_DIM)
        self.up_status_lbl.pack(anchor="w")

    def _refresh_upload_list(self):
        from upload import load_uploaded, extract_song_title
        folder   = Path(DOWNLOADS_FOLDER)
        files    = sorted(folder.glob("*.ogg")) if folder.exists() else []
        uploaded = load_uploaded()

        # Clear old rows
        for row, *_ in self._up_rows:
            row.destroy()
        self._up_rows.clear()

        if not files:
            self.up_info_lbl.configure(text="No OGG files found")
            empty = ctk.CTkLabel(self._up_scroll, text="  (empty)",
                                 font=ctk.CTkFont("Segoe UI", 11), text_color=TEXT_MUT)
            empty.pack(anchor="w", padx=14, pady=10)
            self._up_rows.append((empty, None, None, None))
            return

        self.up_info_lbl.configure(text=f"{len(files)} OGG file(s) ready")

        for f in files:
            mb    = f.stat().st_size / (1024 * 1024)
            title = extract_song_title(f.stem)
            done  = f.stem in uploaded

            # Row card
            row = ctk.CTkFrame(self._up_scroll, fg_color=CARD2,
                               corner_radius=8, border_width=1, border_color=BORDER)
            row.pack(fill="x", padx=4, pady=3)
            row.columnconfigure(0, weight=1)

            # Left — icon dot + text stack
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=10)

            # Colored dot indicator
            dot_color = "#3fb950" if done else ACCENT
            dot = ctk.CTkFrame(left, width=6, height=6, corner_radius=3, fg_color=dot_color)
            dot.pack(side="left", padx=(0, 8))

            info = ctk.CTkFrame(left, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(info, text=title[:52],
                         font=ctk.CTkFont("Segoe UI", 12, "bold" if not done else "normal"),
                         text_color=TEXT if not done else TEXT_DIM,
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{f.name}  ·  {mb:.1f} MB",
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=TEXT_MUT, anchor="w").pack(anchor="w")

            # Right — status chip + button
            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=10, pady=10)

            status_lbl = ctk.CTkLabel(
                right,
                text="✓ Uploaded" if done else "",
                font=ctk.CTkFont("Segoe UI", 10),
                text_color="#3fb950", width=80, anchor="e",
            )
            status_lbl.pack(side="left", padx=(0, 8))

            btn = ctk.CTkButton(
                right, text="Upload", width=86, height=30,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                fg_color=GREEN if not done else CARD,
                hover_color=GREEN_H if not done else CARD,
                text_color=TEXT if not done else TEXT_MUT,
                border_width=1 if done else 0,
                border_color=BORDER,
                corner_radius=6,
                state="normal" if not done else "disabled",
                command=lambda _f=f, _sl=status_lbl: self._upload_single(_f, _btn_ref[0], _sl),
            )
            _btn_ref = [btn]
            btn.pack(side="left")

            self._up_rows.append((row, f, btn, status_lbl))

    def _upload_single(self, filepath: Path, btn: ctk.CTkButton, status_lbl: ctk.CTkLabel):
        btn.configure(state="disabled", text="…", fg_color=CARD2)
        status_lbl.configure(text="Uploading…", text_color=TEXT_DIM)
        self.up_status_lbl.configure(text=f"Uploading {filepath.name[:40]}…")
        threading.Thread(target=self._upload_single_worker,
                         args=(filepath, btn, status_lbl), daemon=True).start()

    def _upload_single_worker(self, filepath: Path, btn: ctk.CTkButton, status_lbl: ctk.CTkLabel):
        from upload import upload_to_roblox, load_uploaded, save_uploaded, extract_song_title
        title = extract_song_title(filepath.stem)
        self.log(f"\n▶ Uploading: {title}\n")
        with self._redirect_stdout():
            try:
                asset_id, status = upload_to_roblox(filepath)
            except Exception as e:
                self.log(f"  Error: {e}\n")
                asset_id, status = None, "exception"

        if asset_id:
            uploaded = load_uploaded()
            uploaded[filepath.stem] = {
                "_filename": filepath.stem, "playlistId": "6989936f04a6c8e0cdc770de",
                "title": title, "soundId": f"rbxassetid://{asset_id}",
                "genre": "koplo", "playbackSpeed": 0.45,
                "thumbnail": "", "duration": 0,
            }
            save_uploaded(uploaded)
            dest = Path(DOWNLOADS_FOLDER) / ".." / "uploaded"
            dest.mkdir(exist_ok=True)
            try:
                filepath.rename(dest / filepath.name)
                self.log("  Moved to uploaded/\n")
            except Exception:
                pass
            self.after(0, lambda: btn.configure(state="disabled", text="Upload",
                                                fg_color=CARD2, text_color=TEXT_MUT))
            self.after(0, lambda: status_lbl.configure(text="✓ Done", text_color="#3fb950"))
            self.after(0, lambda: self.up_status_lbl.configure(text=f"✓ {title[:40]} uploaded"))
            self.log(f"  ✓ Asset ID: {asset_id}\n")
        else:
            self.log(f"  ✗ Failed — {status}\n")
            self.after(0, lambda: btn.configure(state="normal", text="Upload",
                                                fg_color=GREEN, hover_color=GREEN_H, text_color=TEXT))
            self.after(0, lambda: status_lbl.configure(text="✗ Failed", text_color=DANGER))
            self.after(0, lambda: self.up_status_lbl.configure(text=f"✗ Failed: {title[:35]}"))

    def _open_permissions(self):
        def _run():
            with self._redirect_stdout():
                __import__("open_permissions").main()
        threading.Thread(target=_run, daemon=True).start()

    # ════════════════════════════════════════════════════════════
    #  PAGE 3 — STATUS
    # ════════════════════════════════════════════════════════════
    def _build_status_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        self._pages["status"] = page

        self._section_title(page, "Asset Status")

        # Badge row
        badge_row = ctk.CTkFrame(page, fg_color="transparent")
        badge_row.pack(fill="x", pady=(0, 14))
        self.badge_approved  = self._badge(badge_row, "Approved",  "—", "#1a4731", "#3fb950")
        self.badge_reviewing = self._badge(badge_row, "Reviewing", "—", "#2d2210", "#d29922")
        self.badge_rejected  = self._badge(badge_row, "Rejected",  "—", "#3b1219", "#f85149")
        for b in (self.badge_approved, self.badge_reviewing, self.badge_rejected):
            b.pack(side="left", expand=True, fill="x", padx=(0, 8))

        # Button
        self.btn_check = self._primary_btn(page, "Check All Assets",
                                           self._start_check, icon="search",
                                           color=PURPLE, hover=PURPLE_H)
        self.btn_check.pack(fill="x")

    def _badge(self, parent, label, value, bg, fg):
        f = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8,
                         border_width=1, border_color=BORDER)
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_DIM).pack(pady=(10, 2))
        lbl = ctk.CTkLabel(f, text=value,
                           font=ctk.CTkFont("Segoe UI", 28, "bold"),
                           text_color=fg)
        lbl.pack(pady=(0, 10))
        f._count_label = lbl
        return f

    def _start_check(self):
        self.btn_check.configure(state="disabled", text="  Checking…")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        import json as _json
        from check_status import check_asset
        from cfg import UPLOAD_JSON as _UJ
        _uj  = Path(_UJ)
        path = APP_DIR / _uj if not _uj.is_absolute() else _uj
        if not path.exists():
            self.log("upload.json not found.\n")
            self.after(0, self.btn_check.configure, {"state": "normal", "text": "  Check All Assets"})
            return
        with open(path) as f:
            assets = _json.load(f)
        if not assets:
            self.log("No assets in upload.json.\n")
            self.after(0, self.btn_check.configure, {"state": "normal", "text": "  Check All Assets"})
            return
        self.log(f"▶ Checking {len(assets)} asset(s)…\n\n")
        approved = reviewing = rejected = errors = 0
        STATE_MAP = {
            "MODERATION_STATE_APPROVED":  ("✓", True,  False, False),
            "Approved":                   ("✓", True,  False, False),
            "MODERATION_STATE_REVIEWING": ("·", False, True,  False),
            "Reviewing":                  ("·", False, True,  False),
            "MODERATION_STATE_REJECTED":  ("✗", False, False, True),
            "Rejected":                   ("✗", False, False, True),
        }
        with self._redirect_stdout():
            for i, entry in enumerate(assets, 1):
                title    = entry.get("title", "?")
                asset_id = entry.get("soundId", "").replace("rbxassetid://", "")
                if not asset_id:
                    self.log(f"  [{i:2d}] ?  {title} — no ID\n"); errors += 1; continue
                state = check_asset(asset_id)
                ico, is_ok, is_rev, is_rej = STATE_MAP.get(state, ("?", False, False, False))
                self.log(f"  [{i:2d}] {ico}  {title[:40]:<40s}  {state}\n")
                if is_ok:    approved  += 1
                elif is_rev: reviewing += 1
                elif is_rej: rejected  += 1
                else:        errors    += 1
        self.log(f"\nApproved: {approved}  Reviewing: {reviewing}  Rejected: {rejected}\n")
        self.after(0, self.badge_approved._count_label.configure,  {"text": str(approved)})
        self.after(0, self.badge_reviewing._count_label.configure, {"text": str(reviewing)})
        self.after(0, self.badge_rejected._count_label.configure,  {"text": str(rejected)})
        self.after(0, self.btn_check.configure, {"state": "normal", "text": "  Check All Assets"})

    # ════════════════════════════════════════════════════════════
    #  PAGE 4 — LOGS
    # ════════════════════════════════════════════════════════════
    def _build_logs_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        self._pages["logs"] = page

        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="Logs", font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXT).pack(side="left")
        self._ghost_btn(hdr, "Clear", self._log_clear, icon="trash", width=80).pack(side="right")

        self._log_box = ctk.CTkTextbox(
            page, font=ctk.CTkFont("Consolas", 11),
            fg_color=CARD, text_color=TEXT_DIM,
            border_width=1, border_color=BORDER, corner_radius=8,
        )
        self._log_box.pack(fill="both", expand=True)
        self._log_box.configure(state="disabled")

    # ════════════════════════════════════════════════════════════
    #  PAGE 5 — SETTINGS
    # ════════════════════════════════════════════════════════════
    def _build_config_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        self._pages["config"] = page

        self._section_title(page, "Settings")

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        def _field(parent, label, key, placeholder="", show=""):
            ctk.CTkLabel(parent, text=label, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXT_DIM).pack(anchor="w", pady=(8, 2))
            e = self._entry(parent, placeholder_text=placeholder, show=show)
            e.pack(fill="x")
            val = CFG.get(key, "")
            if val: e.insert(0, str(val))
            return e

        # Credentials
        cred = self._card(scroll)
        cred.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(cred, text="Roblox Credentials",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkFrame(cred, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(6, 0))
        inner = ctk.CTkFrame(cred, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(0, 14))
        self._cfg_api_key = _field(inner, "API Key", "ROBLOX_API_KEY",
                                   placeholder="Paste Roblox API key", show="•")
        key_row = ctk.CTkFrame(inner, fg_color="transparent")
        key_row.pack(fill="x", pady=(4, 0))
        def _toggle():
            cur = self._cfg_api_key.cget("show")
            self._cfg_api_key.configure(show="" if cur == "•" else "•")
            self._toggle_btn.configure(text="Hide" if cur == "•" else "Show")
        self._toggle_btn = self._ghost_btn(key_row, "Show", _toggle, width=70)
        self._toggle_btn.pack(anchor="e")
        self._cfg_user_id = _field(inner, "User ID", "ROBLOX_USER_ID", placeholder="e.g. 10507308421")

        # Audio
        audio = self._card(scroll)
        audio.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(audio, text="Audio Settings",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkFrame(audio, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(6, 0))
        sl = ctk.CTkFrame(audio, fg_color="transparent")
        sl.pack(fill="x", padx=14, pady=(4, 14))
        sl.columnconfigure(1, weight=1)

        ctk.CTkLabel(sl, text="Speed (x)", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_DIM).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        self._spd_lbl = ctk.CTkLabel(sl, text=f"{CFG['SPEED']:.1f}x",
                                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                                     text_color=ACCENT, width=40)
        self._spd_lbl.grid(row=0, column=2, padx=(8, 0))
        self._cfg_speed = ctk.CTkSlider(sl, from_=0.5, to=4.0, number_of_steps=35,
                                        fg_color=BORDER, progress_color=ACCENT, button_color=ACCENT,
                                        command=lambda v: self._spd_lbl.configure(text=f"{v:.1f}x"))
        self._cfg_speed.set(CFG["SPEED"])
        self._cfg_speed.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(sl, text="Amplify (dB)", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=TEXT_DIM).grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        self._amp_lbl = ctk.CTkLabel(sl, text=f"{CFG['AMPLIFY_DB']:+d}dB",
                                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                                     text_color=ACCENT, width=40)
        self._amp_lbl.grid(row=1, column=2, padx=(8, 0))
        self._cfg_amp = ctk.CTkSlider(sl, from_=-12, to=12, number_of_steps=24,
                                      fg_color=BORDER, progress_color=ACCENT, button_color=ACCENT,
                                      command=lambda v: self._amp_lbl.configure(text=f"{int(v):+d}dB"))
        self._cfg_amp.set(CFG["AMPLIFY_DB"])
        self._cfg_amp.grid(row=1, column=1, sticky="ew")

        # Paths
        paths = self._card(scroll)
        paths.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(paths, text="Paths", font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkFrame(paths, height=1, fg_color=BORDER).pack(fill="x", padx=14, pady=(6, 0))
        pi = ctk.CTkFrame(paths, fg_color="transparent")
        pi.pack(fill="x", padx=14, pady=(0, 14))
        self._cfg_dl_folder   = _field(pi, "Downloads Folder", "DOWNLOADS_FOLDER", placeholder="downloads")
        self._cfg_upload_json = _field(pi, "Upload JSON",      "UPLOAD_JSON",       placeholder="upload.json")

        # Save
        self._cfg_status = ctk.CTkLabel(scroll, text="",
                                        font=ctk.CTkFont("Segoe UI", 11), text_color="#3fb950")
        self._cfg_status.pack(anchor="w")
        self._primary_btn(scroll, "Save Settings", self._save_config, icon="save").pack(fill="x", pady=(6, 0))

    def _save_config(self):
        global CFG, SPEED, AMPLIFY_DB, DOWNLOADS_FOLDER
        new_cfg = {
            **CFG,
            "ROBLOX_API_KEY":   self._cfg_api_key.get().strip(),
            "ROBLOX_USER_ID":   self._cfg_user_id.get().strip(),
            "SPEED":            round(self._cfg_speed.get(), 2),
            "AMPLIFY_DB":       int(self._cfg_amp.get()),
            "DOWNLOADS_FOLDER": self._cfg_dl_folder.get().strip() or "downloads",
            "UPLOAD_JSON":      self._cfg_upload_json.get().strip() or "upload.json",
        }
        save_config(new_cfg)
        CFG = new_cfg; SPEED = new_cfg["SPEED"]
        AMPLIFY_DB = new_cfg["AMPLIFY_DB"]
        DOWNLOADS_FOLDER = new_cfg["DOWNLOADS_FOLDER"]
        self._cfg_status.configure(text="Settings saved.")
        self.after(2000, lambda: self._cfg_status.configure(text=""))


if __name__ == "__main__":
    app = App()
    app.mainloop()
