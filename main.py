# ============================================================
#  SynaAI Test App  —  main.py
#  Single-file Kivy + pyjnius Android automation test app
#  Compatible with: Pydroid 3 / Buildozer APK build
# ============================================================

# ── Colour palette ───────────────────────────────────────────
# BG_DARK   #0D0F14   app background
# BG_CARD   #161B25   card / section surface
# BG_ELEM   #1E2535   input / button base
# ACCENT    #4F8EF7   primary blue
# ACCENT2   #A259FF   purple accent
# SUCCESS   #27AE60
# WARNING   #F39C12
# DANGER    #E74C3C
# TEXT_PRI  #F0F4FF
# TEXT_SEC  #8892AA
# ─────────────────────────────────────────────────────────────

import os
import sys
import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.utils import platform

# ── Platform guard ───────────────────────────────────────────
IS_ANDROID = platform == "android"

if IS_ANDROID:
    try:
        from jnius import autoclass, cast
        from android.permissions import request_permissions, Permission
        JNIUS_OK = True
    except Exception as _e:
        JNIUS_OK = False
        print(f"[SynaAI] pyjnius import error: {_e}")
else:
    JNIUS_OK = False
    print("[SynaAI] Running on non-Android platform — Android features disabled.")

# ─────────────────────────────────────────────────────────────
#  Logging helper
# ─────────────────────────────────────────────────────────────
_log_label = None   # filled in after UI build

def log(msg, level="INFO"):
    tag = {"INFO": "✅", "WARN": "⚠️", "ERROR": "❌", "ACTION": "🔵"}.get(level, "•")
    full = f"{tag}  {msg}"
    print(f"[SynaAI/{level}] {msg}")
    if _log_label is not None:
        existing = _log_label.text
        lines = existing.split("\n")
        lines.insert(0, full)
        _log_label.text = "\n".join(lines[:40])   # keep last 40 lines


# ─────────────────────────────────────────────────────────────
#  Android helper – lazy-load Java classes
# ─────────────────────────────────────────────────────────────
def _get_context():
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity

def _get_audio_manager():
    Context = autoclass("android.content.Context")
    ctx = _get_context()
    return ctx.getSystemService(Context.AUDIO_SERVICE)

def _get_window_manager():
    ctx = _get_context()
    return ctx.getSystemService("window")

def _settings_can_write():
    Settings = autoclass("android.provider.Settings")
    ctx = _get_context()
    return Settings.System.canWrite(ctx)

def _request_write_settings():
    try:
        Intent   = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri      = autoclass("android.net.Uri")
        ctx      = _get_context()
        intent   = Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS)
        intent.setData(Uri.parse(f"package:{ctx.getPackageName()}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
        log("WRITE_SETTINGS permission page opened.", "ACTION")
    except Exception as e:
        log(f"Could not open WRITE_SETTINGS page: {e}", "ERROR")


# ─────────────────────────────────────────────────────────────
#  1.  APP LAUNCHER
# ─────────────────────────────────────────────────────────────
APP_PACKAGES = {
    "youtube":   "com.google.android.youtube",
    "spotify":   "com.spotify.music",
    "chrome":    "com.android.chrome",
    "whatsapp":  "com.whatsapp",
    "settings":  "com.android.settings",
    "instagram": "com.instagram.android",
    "telegram":  "org.telegram.messenger",
    "maps":      "com.google.android.apps.maps",
    "gmail":     "com.google.android.gm",
    "camera":    "com.android.camera2",
}

def open_app(app_name: str):
    """Launch an installed Android app by friendly name or package name."""
    if not IS_ANDROID or not JNIUS_OK:
        log(f"open_app('{app_name}') — not on Android, skipping.", "WARN")
        return
    try:
        ctx          = _get_context()
        pkg_manager  = ctx.getPackageManager()
        Intent       = autoclass("android.content.Intent")

        key = app_name.strip().lower()
        package = APP_PACKAGES.get(key, app_name.strip())   # fallback: treat input as package

        launch_intent = pkg_manager.getLaunchIntentForPackage(package)
        if launch_intent is None:
            log(f"App not found: '{app_name}' (tried package '{package}')", "ERROR")
            return
        launch_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(launch_intent)
        log(f"Launched: {app_name} ({package})", "INFO")
    except Exception as e:
        log(f"open_app error: {e}", "ERROR")


# ─────────────────────────────────────────────────────────────
#  2.  VOLUME CONTROL
# ─────────────────────────────────────────────────────────────
def volume_up():
    if not IS_ANDROID or not JNIUS_OK:
        log("volume_up — not on Android.", "WARN"); return
    try:
        AudioManager = autoclass("android.media.AudioManager")
        am = _get_audio_manager()
        am.adjustStreamVolume(
            AudioManager.STREAM_MUSIC,
            AudioManager.ADJUST_RAISE,
            AudioManager.FLAG_SHOW_UI
        )
        log("Volume raised.", "INFO")
    except Exception as e:
        log(f"volume_up error: {e}", "ERROR")

def volume_down():
    if not IS_ANDROID or not JNIUS_OK:
        log("volume_down — not on Android.", "WARN"); return
    try:
        AudioManager = autoclass("android.media.AudioManager")
        am = _get_audio_manager()
        am.adjustStreamVolume(
            AudioManager.STREAM_MUSIC,
            AudioManager.ADJUST_LOWER,
            AudioManager.FLAG_SHOW_UI
        )
        log("Volume lowered.", "INFO")
    except Exception as e:
        log(f"volume_down error: {e}", "ERROR")

_is_muted = False

def toggle_mute():
    global _is_muted
    if not IS_ANDROID or not JNIUS_OK:
        log("toggle_mute — not on Android.", "WARN"); return
    try:
        AudioManager = autoclass("android.media.AudioManager")
        am = _get_audio_manager()
        if not _is_muted:
            am.setStreamVolume(AudioManager.STREAM_MUSIC, 0, AudioManager.FLAG_SHOW_UI)
            _is_muted = True
            log("Muted.", "INFO")
        else:
            max_vol = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
            am.setStreamVolume(AudioManager.STREAM_MUSIC, max_vol // 2, AudioManager.FLAG_SHOW_UI)
            _is_muted = False
            log("Unmuted (50%).", "INFO")
    except Exception as e:
        log(f"toggle_mute error: {e}", "ERROR")

def mute_volume_silent():
    """Mute without UI — used internally by sleep mode."""
    if not IS_ANDROID or not JNIUS_OK:
        return
    try:
        AudioManager = autoclass("android.media.AudioManager")
        am = _get_audio_manager()
        am.setStreamVolume(AudioManager.STREAM_MUSIC, 0, 0)
    except Exception as e:
        log(f"mute_volume_silent error: {e}", "ERROR")


# ─────────────────────────────────────────────────────────────
#  3.  BRIGHTNESS CONTROL
# ─────────────────────────────────────────────────────────────
def _set_brightness(value: int):
    """
    value: 0–255  (Settings.System expects 0-255)
    Requires WRITE_SETTINGS permission on Android 6+.
    """
    if not IS_ANDROID or not JNIUS_OK:
        log(f"set_brightness({value}) — not on Android.", "WARN"); return
    try:
        Settings = autoclass("android.provider.Settings")
        if not _settings_can_write():
            log("WRITE_SETTINGS permission needed — opening settings page.", "WARN")
            _request_write_settings()
            return
        ctx      = _get_context()
        resolver = ctx.getContentResolver()
        Settings.System.putInt(
            resolver,
            Settings.System.SCREEN_BRIGHTNESS_MODE,
            Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL
        )
        Settings.System.putInt(
            resolver,
            Settings.System.SCREEN_BRIGHTNESS,
            max(0, min(255, value))
        )
        # Apply to current window as well
        WindowManager = autoclass("android.view.WindowManager")
        LayoutParams  = autoclass("android.view.WindowManager$LayoutParams")
        activity      = _get_context()
        window        = activity.getWindow()
        lp            = window.getAttributes()
        lp.screenBrightness = max(0.0, min(1.0, value / 255.0))
        window.setAttributes(lp)
        log(f"Brightness set to {value}/255.", "INFO")
    except Exception as e:
        log(f"set_brightness error: {e}", "ERROR")

def brightness_up():
    if not IS_ANDROID or not JNIUS_OK:
        log("brightness_up — not on Android.", "WARN"); return
    try:
        Settings = autoclass("android.provider.Settings")
        ctx      = _get_context()
        resolver = ctx.getContentResolver()
        current  = Settings.System.getInt(resolver, Settings.System.SCREEN_BRIGHTNESS, 128)
        _set_brightness(min(255, current + 25))
    except Exception as e:
        log(f"brightness_up error: {e}", "ERROR")

def brightness_down():
    if not IS_ANDROID or not JNIUS_OK:
        log("brightness_down — not on Android.", "WARN"); return
    try:
        Settings = autoclass("android.provider.Settings")
        ctx      = _get_context()
        resolver = ctx.getContentResolver()
        current  = Settings.System.getInt(resolver, Settings.System.SCREEN_BRIGHTNESS, 128)
        _set_brightness(max(10, current - 25))
    except Exception as e:
        log(f"brightness_down error: {e}", "ERROR")

def brightness_low():    _set_brightness(30)
def brightness_medium(): _set_brightness(128)
def brightness_max():    _set_brightness(255)

def set_brightness_silent(value: int):
    """Used internally — same as _set_brightness but no repeated logs."""
    _set_brightness(value)


# ─────────────────────────────────────────────────────────────
#  4.  SETTINGS SHORTCUTS
# ─────────────────────────────────────────────────────────────
def _open_settings_action(action_name: str):
    if not IS_ANDROID or not JNIUS_OK:
        log(f"open_settings({action_name}) — not on Android.", "WARN"); return
    try:
        Intent   = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        ctx      = _get_context()
        action   = getattr(Settings, action_name, None)
        if action is None:
            log(f"Unknown settings action: {action_name}", "ERROR"); return
        intent = Intent(action)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
        log(f"Opened settings: {action_name}", "INFO")
    except Exception as e:
        log(f"open_settings error: {e}", "ERROR")

def open_wifi_settings():       _open_settings_action("ACTION_WIFI_SETTINGS")
def open_bluetooth_settings():  _open_settings_action("ACTION_BLUETOOTH_SETTINGS")
def open_display_settings():    _open_settings_action("ACTION_DISPLAY_SETTINGS")
def open_sound_settings():      _open_settings_action("ACTION_SOUND_SETTINGS")
def open_app_settings():
    if not IS_ANDROID or not JNIUS_OK:
        log("open_app_settings — not on Android.", "WARN"); return
    try:
        Intent   = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        Uri      = autoclass("android.net.Uri")
        ctx      = _get_context()
        intent   = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        intent.setData(Uri.parse(f"package:{ctx.getPackageName()}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
        log("Opened app settings.", "INFO")
    except Exception as e:
        log(f"open_app_settings error: {e}", "ERROR")


# ─────────────────────────────────────────────────────────────
#  5.  SLEEP MODE
# ─────────────────────────────────────────────────────────────
def activate_sleep_mode():
    log("🌙 Sleep Mode activating…", "ACTION")
    mute_volume_silent()
    log("  • Volume muted.", "INFO")
    set_brightness_silent(20)
    log("  • Brightness lowered to minimum.", "INFO")
    open_display_settings()
    log("  • Display settings opened.", "INFO")
    log("🌙 Sleep Mode active.", "ACTION")


# ─────────────────────────────────────────────────────────────
#  UI COMPONENTS
# ─────────────────────────────────────────────────────────────

# ── Theme colours (Kivy RGBA 0–1 floats) ─────────────────────
C_BG_DARK  = (0.051, 0.059, 0.078, 1)
C_BG_CARD  = (0.086, 0.106, 0.145, 1)
C_BG_ELEM  = (0.118, 0.145, 0.208, 1)
C_ACCENT   = (0.310, 0.557, 0.969, 1)
C_ACCENT2  = (0.635, 0.349, 1.000, 1)
C_SUCCESS  = (0.153, 0.682, 0.376, 1)
C_WARNING  = (0.953, 0.612, 0.071, 1)
C_DANGER   = (0.906, 0.298, 0.235, 1)
C_SLEEP    = (0.400, 0.200, 0.800, 1)
C_TEXT_PRI = (0.941, 0.957, 1.000, 1)
C_TEXT_SEC = (0.533, 0.573, 0.667, 1)


class CardBox(BoxLayout):
    """A BoxLayout that draws a rounded dark card behind its children."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding     = [dp(16), dp(14), dp(16), dp(14)]
        self.spacing     = dp(10)
        
        # ----- FIX: make the card size itself to its content -----
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        # ---------------------------------------------------------
        
        with self.canvas.before:
            Color(*C_BG_CARD)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size


class SynaButton(Button):
    """Styled rounded button with configurable accent colour."""
    def __init__(self, accent=None, **kwargs):
        self._accent = accent or C_ACCENT
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(46))
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("color", C_TEXT_PRI)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*self._accent)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        if not hasattr(self, "_bg_rect"):
            return
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size


def _section_title(text):
    lbl = Label(
        text=text,
        font_size=sp(16),
        bold=True,
        color=C_TEXT_PRI,
        size_hint_y=None,
        height=dp(30),
        halign="left",
        text_size=(None, None),
    )
    lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
    return lbl


def _sub_label(text):
    lbl = Label(
        text=text,
        font_size=sp(12),
        color=C_TEXT_SEC,
        size_hint_y=None,
        height=dp(20),
        halign="left",
    )
    lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
    return lbl


def _spacer(h=10):
    w = Widget(size_hint_y=None, height=dp(h))
    return w


def _hrow(*widgets, spacing=8):
    row = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(46),
        spacing=dp(spacing),
    )
    for w in widgets:
        row.add_widget(w)
    return row


# ─────────────────────────────────────────────────────────────
#  SECTION BUILDERS
# ─────────────────────────────────────────────────────────────

def build_launcher_section():
    card = CardBox()
    card.add_widget(_section_title("📱  App Launcher"))
    card.add_widget(_sub_label("Type an app name or package and press Open App"))

    ti = TextInput(
        hint_text="e.g. youtube  /  spotify  /  chrome  /  com.example.app",
        size_hint_y=None,
        height=dp(46),
        multiline=False,
        font_size=sp(14),
        foreground_color=C_TEXT_PRI,
        hint_text_color=C_TEXT_SEC,
        background_normal="",
        background_active="",
        background_color=C_BG_ELEM,
        padding=[dp(12), dp(12), dp(12), dp(12)],
        cursor_color=C_ACCENT,
    )
    card.add_widget(ti)

    btn = SynaButton(text="▶  Open App", accent=C_ACCENT)
    def on_open(_):
        name = ti.text.strip()
        if not name:
            log("App Launcher: enter an app name first.", "WARN")
            return
        open_app(name)
    btn.bind(on_release=on_open)
    card.add_widget(btn)

    card.add_widget(_sub_label("Quick launch:"))
    quick_row1 = _hrow(
        *[SynaButton(text=n.capitalize(), accent=C_BG_ELEM,
                     on_release=lambda _, a=n: open_app(a))
          for n in ["youtube", "spotify", "chrome"]]
    )
    quick_row2 = _hrow(
        *[SynaButton(text=n.capitalize(), accent=C_BG_ELEM,
                     on_release=lambda _, a=n: open_app(a))
          for n in ["whatsapp", "settings"]]
    )
    card.add_widget(quick_row1)
    card.add_widget(quick_row2)
    return card


def build_volume_section():
    card = CardBox()
    card.add_widget(_section_title("🔊  Volume Control"))
    card.add_widget(_sub_label("Uses Android AudioManager"))

    row = _hrow(
        SynaButton(text="🔊  Vol Up",   accent=C_SUCCESS,  on_release=lambda _: volume_up()),
        SynaButton(text="🔉  Vol Down", accent=C_WARNING,  on_release=lambda _: volume_down()),
        SynaButton(text="🔇  Mute",     accent=C_DANGER,   on_release=lambda _: toggle_mute()),
    )
    card.add_widget(row)
    return card


def build_brightness_section():
    card = CardBox()
    card.add_widget(_section_title("☀️  Brightness Control"))
    card.add_widget(_sub_label("Requires WRITE_SETTINGS — will prompt if needed"))

    row1 = _hrow(
        SynaButton(text="🔆 Up",      accent=C_SUCCESS, on_release=lambda _: brightness_up()),
        SynaButton(text="🔅 Down",    accent=C_WARNING, on_release=lambda _: brightness_down()),
    )
    row2 = _hrow(
        SynaButton(text="🌑 Low",     accent=C_BG_ELEM,  on_release=lambda _: brightness_low()),
        SynaButton(text="🌓 Medium",  accent=C_BG_ELEM,  on_release=lambda _: brightness_medium()),
        SynaButton(text="🌕 Max",     accent=C_ACCENT,   on_release=lambda _: brightness_max()),
    )
    card.add_widget(row1)
    card.add_widget(row2)
    return card


def build_settings_section():
    card = CardBox()
    card.add_widget(_section_title("⚙️  Settings Shortcuts"))
    card.add_widget(_sub_label("Opens Android system settings screens"))

    row1 = _hrow(
        SynaButton(text="📶 WiFi",       accent=C_ACCENT,  on_release=lambda _: open_wifi_settings()),
        SynaButton(text="🦷 Bluetooth",  accent=C_ACCENT2, on_release=lambda _: open_bluetooth_settings()),
    )
    row2 = _hrow(
        SynaButton(text="🖥 Display",    accent=C_BG_ELEM,  on_release=lambda _: open_display_settings()),
        SynaButton(text="🔔 Sound",      accent=C_BG_ELEM,  on_release=lambda _: open_sound_settings()),
    )
    row3 = _hrow(
        SynaButton(text="📋 App Info",   accent=C_BG_ELEM,  on_release=lambda _: open_app_settings()),
    )
    card.add_widget(row1)
    card.add_widget(row2)
    card.add_widget(row3)
    return card


def build_sleep_section():
    card = CardBox()
    card.add_widget(_section_title("🌙  Sleep Mode"))
    card.add_widget(_sub_label("Mutes volume + lowers brightness + opens display settings"))

    btn = SynaButton(
        text="🌙  Activate Sleep Mode",
        accent=C_SLEEP,
        height=dp(52),
        font_size=sp(15),
        on_release=lambda _: activate_sleep_mode(),
    )
    card.add_widget(btn)
    return card


def build_log_section():
    global _log_label
    card = CardBox()
    card.add_widget(_section_title("📋  Activity Log"))
    card.add_widget(_sub_label("Recent actions appear here"))

    _log_label = Label(
        text="— Log is empty —",
        font_size=sp(12),
        color=C_TEXT_SEC,
        size_hint_y=None,
        halign="left",
        valign="top",
        markup=True,
    )
    _log_label.bind(texture_size=lambda i, v: setattr(i, "height", max(v[1], dp(60))))
    _log_label.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))

    inner_scroll = ScrollView(size_hint=(1, None), height=dp(160))
    inner_scroll.add_widget(_log_label)
    card.add_widget(inner_scroll)

    clear_btn = SynaButton(
        text="🗑  Clear Log",
        accent=C_BG_ELEM,
        height=dp(38),
        font_size=sp(12),
        on_release=lambda _: setattr(_log_label, "text", "— Log cleared —"),
    )
    card.add_widget(clear_btn)
    return card


# ─────────────────────────────────────────────────────────────
#  MAIN LAYOUT
# ─────────────────────────────────────────────────────────────

class SynaRootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Draw app background
        with self.canvas.before:
            Color(*C_BG_DARK)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos))
        self.bind(size=lambda *_: setattr(self._bg, "size", self.size))

        # ── Header ──────────────────────────────────────────
        header = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(72),
            padding=[dp(20), dp(12), dp(20), dp(0)],
        )
        with header.canvas.before:
            Color(*C_BG_CARD)
            self._hdr_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *_: setattr(self._hdr_rect, "pos", header.pos))
        header.bind(size=lambda *_: setattr(self._hdr_rect, "size", header.size))

        title_lbl = Label(
            text="[b]SynaAI[/b] Test App",
            markup=True,
            font_size=sp(22),
            color=C_TEXT_PRI,
            halign="left",
            size_hint_y=None,
            height=dp(34),
        )
        title_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))

        sub_lbl = Label(
            text="Android Automation Sandbox",
            font_size=sp(12),
            color=C_ACCENT,
            halign="left",
            size_hint_y=None,
            height=dp(20),
        )
        sub_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))

        header.add_widget(title_lbl)
        header.add_widget(sub_lbl)
        self.add_widget(header)

        # ── Scrollable content ───────────────────────────────
        scroll = ScrollView(do_scroll_x=False)

        content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(14), dp(14), dp(14), dp(20)],
            spacing=dp(14),
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(build_launcher_section())
        content.add_widget(build_volume_section())
        content.add_widget(build_brightness_section())
        content.add_widget(build_settings_section())
        content.add_widget(build_sleep_section())
        content.add_widget(build_log_section())

        # ── Platform notice ──────────────────────────────────
        notice_text = (
            "✅  Running on Android — features enabled."
            if IS_ANDROID else
            "⚠️  Non-Android platform detected.\n"
            "Android features are disabled.\n"
            "Install on device or build APK for full functionality."
        )
        notice_color = C_SUCCESS if IS_ANDROID else C_WARNING
        notice = Label(
            text=notice_text,
            font_size=sp(11),
            color=notice_color,
            size_hint_y=None,
            height=dp(48),
            halign="center",
        )
        notice.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        content.add_widget(notice)

        scroll.add_widget(content)
        self.add_widget(scroll)


# ─────────────────────────────────────────────────────────────
#  APP ENTRY
# ─────────────────────────────────────────────────────────────

class SynaAIApp(App):
    def build(self):
        self.title = "SynaAI Test App"
        Window.clearcolor = C_BG_DARK

        if IS_ANDROID and JNIUS_OK:
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.WRITE_SETTINGS,
                    Permission.MODIFY_AUDIO_SETTINGS,
                ])
            except Exception as e:
                log(f"Permission request error: {e}", "WARN")

        return SynaRootWidget()

    def on_start(self):
        log("SynaAI Test App started.", "INFO")
        if not IS_ANDROID:
            log("Running in desktop/Pydroid preview mode.", "WARN")

    def on_stop(self):
        log("SynaAI Test App stopped.", "INFO")


if __name__ == "__main__":
    SynaAIApp().run()