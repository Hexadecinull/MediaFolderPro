from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import StringProperty, BooleanProperty, NumericProperty
import threading
import requests
from bs4 import BeautifulSoup
import os
import re
import math
import time
import json
from concurrent.futures import ThreadPoolExecutor

APP_VERSION = "2.0.0"
GITHUB_URL = "https://github.com/Hexadecinull/MediaFolderPro"
SETTINGS_FILE = "mediafolder_settings.json"

DARK = {
    "bg": (0.07, 0.07, 0.07, 1),
    "card": (0.11, 0.11, 0.11, 1),
    "field": (0.15, 0.15, 0.15, 1),
    "accent": (0, 0.48, 0.8, 1),
    "stop": (0.83, 0.18, 0.18, 1),
    "text": (0.93, 0.93, 0.93, 1),
    "sub": (0.53, 0.53, 0.53, 1),
    "border": (0.22, 0.22, 0.22, 1),
}

LIGHT = {
    "bg": (0.95, 0.95, 0.95, 1),
    "card": (1, 1, 1, 1),
    "field": (0.94, 0.94, 0.94, 1),
    "accent": (0, 0.37, 0.72, 1),
    "stop": (0.78, 0.16, 0.16, 1),
    "text": (0.07, 0.07, 0.07, 1),
    "sub": (0.4, 0.4, 0.4, 1),
    "border": (0.8, 0.8, 0.8, 1),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (1,)


def fmt_size(b):
    if b <= 0:
        return "0 B"
    names = ("B", "KB", "MB", "GB", "TB")
    i = min(int(math.floor(math.log(b, 1024))), len(names) - 1)
    return f"{round(b / math.pow(1024, i), 2)} {names[i]}"


class ThemedButton(Button):
    def __init__(self, bg_color=None, text_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self._bg = bg_color or DARK["accent"]
        self._tc = text_color
        self.background_normal = ""
        self.background_color = self._bg
        self.color = self._tc
        self.bold = True
        self.font_size = sp(13)

    def set_theme(self, c):
        pass


class StyledInput(TextInput):
    def __init__(self, hint="", **kwargs):
        super().__init__(**kwargs)
        self.hint_text = hint
        self.background_normal = ""
        self.background_color = DARK["field"]
        self.foreground_color = DARK["text"]
        self.cursor_color = DARK["text"]
        self.hint_text_color = DARK["sub"]
        self.padding = [dp(10), dp(10)]
        self.font_size = sp(13)
        self.multiline = False

    def set_theme(self, c):
        self.background_color = c["field"]
        self.foreground_color = c["text"]
        self.cursor_color = c["text"]
        self.hint_text_color = c["sub"]


class FileRow(BoxLayout):
    def __init__(self, name, size_str, depth, is_folder, on_toggle, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(44)
        self.padding = [dp(8 + depth * 16), 0, dp(8), 0]
        self.spacing = dp(8)
        self._checked = True
        self._on_toggle = on_toggle
        self._is_folder = is_folder
        self._name = name
        self._depth = depth

        with self.canvas.before:
            Color(*DARK["card"])
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        icon = "📁" if is_folder else "📄"
        self.name_lbl = Label(
            text=f"{icon}  {name}", color=DARK["text"],
            font_size=sp(12), halign="left", valign="middle",
            size_hint_x=1, text_size=(None, None)
        )
        self.name_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self.name_lbl)

        self.size_lbl = Label(
            text=size_str, color=DARK["sub"],
            font_size=sp(11), size_hint_x=None, width=dp(72), halign="right"
        )
        self.add_widget(self.size_lbl)

        self.chk = CheckBox(
            active=True, size_hint=(None, None),
            size=(dp(32), dp(32)), color=DARK["accent"]
        )
        self.chk.bind(active=self._on_check)
        self.add_widget(self.chk)

    def _update_rect(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _on_check(self, chk, val):
        self._checked = val
        if self._on_toggle:
            self._on_toggle(self, val)

    def set_checked(self, val, fire_callback=True):
        self.chk.unbind(active=self._on_check)
        self.chk.active = val
        self._checked = val
        self.chk.bind(active=self._on_check)
        if fire_callback and self._on_toggle:
            self._on_toggle(self, val)

    def set_theme(self, c):
        self._bg_rect.__class__  # just access to trigger redraw
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*c["card"])
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.name_lbl.color = c["text"]
        self.size_lbl.color = c["sub"]
        self.chk.color = c["accent"]


class StatsPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(2)
        self.size_hint_y = None
        self.height = dp(160)

        with self.canvas.before:
            Color(*DARK["card"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        self.speed_lbl = Label(text="0.00 KB/s", bold=True, font_size=sp(18), color=DARK["text"], halign="left", size_hint_y=None, height=dp(28))
        self.speed_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self.add_widget(self.speed_lbl)

        for attr, default in [
            ("eta_lbl", "ETA: --:--:--"),
            ("rem_lbl", "Remaining: 0 B"),
            ("elapsed_lbl", "Elapsed: --:--:--"),
            ("peak_lbl", "Peak: 0 B/s"),
            ("dl_prog_lbl", "Downloaded: 0 B / 0 B"),
            ("status_lbl", "Idle"),
            ("files_lbl", "Files: 0 / 0"),
            ("sel_lbl", "Selected: 0 files"),
            ("sel_size_lbl", "Selected size: —"),
        ]:
            lbl = Label(
                text=default, font_size=sp(11), color=DARK["sub"],
                halign="left", size_hint_y=None, height=dp(16)
            )
            lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
            setattr(self, attr, lbl)
            self.add_widget(lbl)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_theme(self, c):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*c["card"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.speed_lbl.color = c["text"]
        for attr in ["eta_lbl", "rem_lbl", "elapsed_lbl", "peak_lbl",
                     "dl_prog_lbl", "status_lbl", "files_lbl", "sel_lbl", "sel_size_lbl"]:
            getattr(self, attr).color = c["sub"]


class MediaFolderAndroid(App):
    def build(self):
        self.c = DARK
        self.is_dark = True
        self.file_data = {}
        self.file_rows = []
        self.folder_rows = {}
        self.checked_nodes = set()
        self.fetch_file_count = 0
        self.fetch_folder_count = 0
        self._fetch_abort = False
        self._dl_lock = threading.Lock()
        self.failed_files = []
        self._console_lines = []
        self.is_downloading = False
        self.is_paused = False
        self.abort_requested = False
        self.total_size_to_download = 0
        self.total_downloaded_so_far = 0
        self.total_files_count = 0
        self.files_completed = 0
        self.files_failed = 0
        self.peak_speed = 0
        self.dl_start_time = None
        self.speed_history = [0] * 30
        self._shimmer_phase = 0.0
        self._fetch_active = False

        Window.clearcolor = self.c["bg"]

        root = BoxLayout(orientation="vertical", spacing=0)

        header = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(52),
            padding=[dp(14), dp(8)]
        )
        with header.canvas.before:
            Color(*self.c["card"])
            self._header_bg = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._upd_header, size=self._upd_header)

        self.title_lbl = Label(
            text="MEDIAFOLDER PRO", bold=True, font_size=sp(15),
            color=self.c["accent"], halign="left"
        )
        self.title_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        header.add_widget(self.title_lbl)

        self.theme_btn = ThemedButton(
            text="☀", bg_color=self.c["field"],
            text_color=self.c["text"], size_hint=(None, None),
            size=(dp(42), dp(36))
        )
        self.theme_btn.bind(on_press=self.toggle_theme)
        header.add_widget(self.theme_btn)

        self.about_btn_header = ThemedButton(
            text="ℹ", bg_color=self.c["field"],
            text_color=self.c["text"], size_hint=(None, None),
            size=(dp(42), dp(36))
        )
        self.about_btn_header.bind(on_press=self.show_about)
        header.add_widget(self.about_btn_header)

        root.add_widget(header)

        self.stats_panel = StatsPanel()
        root.add_widget(self.stats_panel)

        form = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(130),
            padding=[dp(12), dp(8)], spacing=dp(6)
        )
        with form.canvas.before:
            Color(*self.c["card"])
            self._form_bg = Rectangle(pos=form.pos, size=form.size)
        form.bind(pos=self._upd_form, size=self._upd_form)

        url_row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(56), spacing=dp(2))
        url_lbl = Label(text="Source URL", font_size=sp(10), color=self.c["sub"],
                        halign="left", size_hint_y=None, height=dp(14), bold=True)
        url_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self._url_lbl = url_lbl
        url_row.add_widget(url_lbl)
        self.url_input = StyledInput(hint="https://www.mediafire.com/folder/...")
        self.url_input.size_hint_y = None
        self.url_input.height = dp(38)
        url_row.add_widget(self.url_input)
        form.add_widget(url_row)

        path_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(6))
        path_lbl_col = BoxLayout(orientation="vertical", spacing=dp(2))
        path_lbl = Label(text="Download Location", font_size=sp(10), color=self.c["sub"],
                         halign="left", size_hint_y=None, height=dp(14), bold=True)
        path_lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self._path_lbl = path_lbl
        path_lbl_col.add_widget(path_lbl)
        self.path_input = StyledInput(hint="/sdcard/Downloads/MediaFolder")
        self.path_input.size_hint_y = None
        self.path_input.height = dp(38)
        path_lbl_col.add_widget(self.path_input)
        path_row.add_widget(path_lbl_col)
        form.add_widget(path_row)

        root.add_widget(form)

        actions = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(46),
            padding=[dp(12), dp(6)], spacing=dp(6)
        )
        with actions.canvas.before:
            Color(*self.c["bg"])
            self._actions_bg = Rectangle(pos=actions.pos, size=actions.size)
        actions.bind(pos=self._upd_actions, size=self._upd_actions)

        self.fetch_btn = ThemedButton(
            text="FETCH CONTENT", bg_color=self.c["field"],
            text_color=self.c["text"]
        )
        self.fetch_btn.bind(on_press=self.start_fetch)
        actions.add_widget(self.fetch_btn)

        self.stop_fetch_btn = ThemedButton(
            text="✕", bg_color=self.c["stop"],
            size_hint=(None, None), size=(dp(42), dp(34))
        )
        self.stop_fetch_btn.bind(on_press=lambda *_: self.abort_fetch())
        self.stop_fetch_btn.opacity = 0
        self.stop_fetch_btn.disabled = True
        actions.add_widget(self.stop_fetch_btn)

        self.clear_btn = ThemedButton(
            text="CLEAR", bg_color=self.c["stop"],
            size_hint=(None, None), size=(dp(80), dp(34))
        )
        self.clear_btn.bind(on_press=lambda *_: self.clear_list())
        actions.add_widget(self.clear_btn)

        root.add_widget(actions)

        self.file_list = GridLayout(
            cols=1, spacing=dp(1), size_hint_y=None
        )
        self.file_list.bind(minimum_height=self.file_list.setter("height"))

        self.scroll = ScrollView(size_hint=(1, 1))
        self.scroll.add_widget(self.file_list)
        root.add_widget(self.scroll)

        console_outer = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(110),
            padding=[dp(10), dp(4), dp(10), dp(0)]
        )
        with console_outer.canvas.before:
            Color(*self.c["card"])
            self._console_bg = Rectangle(pos=console_outer.pos, size=console_outer.size)
        console_outer.bind(pos=self._upd_console, size=self._upd_console)

        console_header = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(20)
        )
        self._console_title = Label(
            text="Console", font_size=sp(9), bold=True,
            color=self.c["sub"], halign="left", size_hint_x=1
        )
        self._console_title.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        console_header.add_widget(self._console_title)

        self._clear_console_btn = Button(
            text="Clear", font_size=sp(8), size_hint=(None, None),
            size=(dp(48), dp(18)), background_normal="",
            background_color=self.c["field"], color=self.c["sub"]
        )
        self._clear_console_btn.bind(on_press=lambda *_: self._clear_console())
        console_header.add_widget(self._clear_console_btn)
        console_outer.add_widget(console_header)

        self._console_scroll = ScrollView(size_hint=(1, 1))
        self._console_grid = GridLayout(cols=1, size_hint_y=None, spacing=0)
        self._console_grid.bind(minimum_height=self._console_grid.setter("height"))
        self._console_scroll.add_widget(self._console_grid)
        console_outer.add_widget(self._console_scroll)

        root.add_widget(console_outer)
        self._console_outer = console_outer

        dl_bar = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(56),
            padding=[dp(12), dp(8)], spacing=dp(6)
        )
        with dl_bar.canvas.before:
            Color(*self.c["card"])
            self._dlbar_bg = Rectangle(pos=dl_bar.pos, size=dl_bar.size)
        dl_bar.bind(pos=self._upd_dlbar, size=self._upd_dlbar)

        self.retry_btn = ThemedButton(
            text="RETRY FAILED", bg_color=self.c["accent"],
            size_hint_x=0.4
        )
        self.retry_btn.bind(on_press=lambda *_: self.retry_failed())
        dl_bar.add_widget(self.retry_btn)

        self.view_failed_btn = ThemedButton(
            text="VIEW FAILED", bg_color=self.c["field"],
            text_color=self.c["sub"], size_hint_x=0.3
        )
        self.view_failed_btn.disabled = True
        self.view_failed_btn.bind(on_press=lambda *_: self.show_failed_popup())
        dl_bar.add_widget(self.view_failed_btn)

        self.pause_btn = ThemedButton(
            text="PAUSE", bg_color=self.c["field"],
            text_color=self.c["sub"], size_hint_x=0.3
        )
        self.pause_btn.disabled = True
        self.pause_btn.bind(on_press=self.toggle_pause)
        dl_bar.add_widget(self.pause_btn)

        self.dl_btn = ThemedButton(
            text="START DOWNLOAD", bg_color=self.c["accent"],
            size_hint_x=0.7
        )
        self.dl_btn.bind(on_press=self.handle_dl_trigger)
        dl_bar.add_widget(self.dl_btn)

        root.add_widget(dl_bar)

        self._form = form
        self._header = header
        self._actions = actions
        self._dl_bar = dl_bar

        saved = self._load_settings()
        if saved:
            self.path_input.text = saved

        Clock.schedule_interval(self._animate_shimmer, 1 / 30)

        return root

    def _upd_header(self, w, *_): self._header_bg.pos = w.pos; self._header_bg.size = w.size
    def _upd_form(self, w, *_): self._form_bg.pos = w.pos; self._form_bg.size = w.size
    def _upd_actions(self, w, *_): self._actions_bg.pos = w.pos; self._actions_bg.size = w.size
    def _upd_dlbar(self, w, *_): self._dlbar_bg.pos = w.pos; self._dlbar_bg.size = w.size
    def _upd_console(self, w, *_): self._console_bg.pos = w.pos; self._console_bg.size = w.size

    def _animate_shimmer(self, dt):
        if not self._fetch_active:
            return
        self._shimmer_phase = (self._shimmer_phase + 0.015) % 1.1
        r, g, b, _ = self.c["accent"]
        phase = self._shimmer_phase
        blend = max(0, 1 - abs(phase - 0.5) * 3)
        rb = r + (1 - r) * blend * 0.4
        gb = g + (1 - g) * blend * 0.4
        bb = b + (1 - b) * blend * 0.4
        self.fetch_btn.background_color = (rb, gb, bb, 1)

    def log(self, msg, level="info"):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        colors = {
            "info":  (0.6, 0.6, 0.6, 1),
            "ok":    (0.3, 0.76, 0.31, 1),
            "warn":  (1, 0.6, 0, 1),
            "error": (0.96, 0.26, 0.21, 1),
        }
        col = colors.get(level, colors["info"])
        self._console_lines.append((line, col))
        if len(self._console_lines) > 200:
            self._console_lines.pop(0)
        lbl = Label(
            text=line, font_size=sp(9), color=col,
            halign="left", size_hint_y=None, height=dp(15)
        )
        lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        self._console_grid.add_widget(lbl)
        Clock.schedule_once(lambda dt: setattr(self._console_scroll, "scroll_y", 0), 0.05)

    def _clear_console(self):
        self._console_grid.clear_widgets()
        self._console_lines.clear()

    def retry_failed(self):
        if not self.failed_files:
            self._show_popup("Retry", "No failed downloads to retry.")
            return
        if self.is_downloading:
            self._show_popup("Busy", "A download is already in progress.")
            return
        dest = self.path_input.text.strip()
        if not dest:
            self._show_popup("Warning", "Set a download location first.")
            return
        to_retry = list(self.failed_files)
        self.failed_files.clear()
        self.view_failed_btn.disabled = True
        self.log(f"Retrying {len(to_retry)} failed file(s)…", "warn")
        for f in to_retry:
            f["resolved_path"] = os.path.join(dest, self._get_path_str(f.get("parent_id")))
        self.is_downloading = True
        self.abort_requested = False
        self.peak_speed = 0
        self.dl_start_time = time.time()
        self.total_size_to_download = sum(f["size"] for f in to_retry)
        self.total_downloaded_so_far = 0
        self.total_files_count = len(to_retry)
        self.files_completed = 0
        self.files_failed = 0
        self.dl_btn.text = "STOP"
        self.dl_btn.background_color = self.c["stop"]
        self.pause_btn.disabled = False
        self.stats_panel.dl_prog_lbl.text = f"Downloaded: 0 B / {fmt_size(self.total_size_to_download)}"
        self.stats_panel.status_lbl.text = "Retrying failed downloads…"
        threading.Thread(target=self._run_downloads, args=(to_retry, dest), daemon=True).start()
        Clock.schedule_interval(self._tick_graph, 0.5)

    def show_failed_popup(self):
        c = self.c
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))
        content.add_widget(Label(
            text=f"Failed Downloads ({len(self.failed_files)})",
            bold=True, font_size=sp(13), color=c["stop"],
            size_hint_y=None, height=dp(24)
        ))
        popup_ref = [None]

        if not self.failed_files:
            content.add_widget(Label(
                text="No failed downloads.", font_size=sp(11), color=c["sub"]
            ))
        else:
            sv = ScrollView(size_hint=(1, 1))
            gl = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
            gl.bind(minimum_height=gl.setter("height"))

            def _retry_one(file_entry, row_widget):
                if file_entry in self.failed_files:
                    self.failed_files.remove(file_entry)
                row_widget.parent.remove_widget(row_widget)
                dest = self.path_input.text.strip()
                if not dest:
                    self._show_popup("Warning", "Set a download location first.")
                    return
                file_entry["resolved_path"] = os.path.join(dest, self._get_path_str(file_entry.get("parent_id")))
                self.log(f"Retrying: {file_entry['name']}", "warn")
                threading.Thread(target=self._dl_file, args=(file_entry,), daemon=True).start()

            for f in list(self.failed_files):
                row = BoxLayout(
                    orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(6)
                )
                lbl = Label(
                    text=f"  {f['name']}  ({fmt_size(f['size'])})",
                    font_size=sp(10), color=c["text"], halign="left", size_hint_x=1
                )
                lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
                row.add_widget(lbl)
                retry_b = Button(
                    text="Retry", size_hint=(None, None), size=(dp(58), dp(28)),
                    background_normal="", background_color=c["accent"],
                    color=(1, 1, 1, 1), bold=True, font_size=sp(10)
                )
                retry_b.bind(on_press=lambda btn, fe=f, r=row: _retry_one(fe, r))
                row.add_widget(retry_b)
                gl.add_widget(row)

            sv.add_widget(gl)
            content.add_widget(sv)

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        retry_all_b = Button(
            text="Retry All", background_normal="",
            background_color=c["accent"], color=(1, 1, 1, 1),
            bold=True, font_size=sp(11)
        )
        close_b = Button(
            text="Close", background_normal="",
            background_color=c["field"], color=c["text"],
            font_size=sp(11)
        )
        btn_row.add_widget(retry_all_b)
        btn_row.add_widget(close_b)
        content.add_widget(btn_row)

        popup = Popup(
            title="Failed Files", content=content,
            size_hint=(0.92, 0.65), background_color=c["card"]
        )
        popup_ref[0] = popup
        retry_all_b.bind(on_press=lambda *_: [popup.dismiss(), self.retry_failed()])
        close_b.bind(on_press=popup.dismiss)
        popup.open()

    def toggle_theme(self, *_):
        self.is_dark = not self.is_dark
        self.c = DARK if self.is_dark else LIGHT
        Window.clearcolor = self.c["bg"]
        self._apply_theme()

    def _apply_theme(self):
        c = self.c
        self.title_lbl.color = c["accent"]
        self.theme_btn.background_color = c["field"]
        self.theme_btn.color = c["text"]
        self.about_btn_header.background_color = c["field"]
        self.about_btn_header.color = c["text"]
        self.stats_panel.set_theme(c)
        self.url_input.set_theme(c)
        self.path_input.set_theme(c)
        self._url_lbl.color = c["sub"]
        self._path_lbl.color = c["sub"]
        self.fetch_btn.background_color = c["field"]
        self.fetch_btn.color = c["text"]
        self.clear_btn.background_color = c["stop"]
        self.stop_fetch_btn.background_color = c["stop"]
        self.dl_btn.background_color = c["stop"] if self.is_downloading else c["accent"]
        self.pause_btn.background_color = c["field"]
        self.pause_btn.color = c["sub"]

        self._header_bg.__class__
        self._header.canvas.before.clear()
        with self._header.canvas.before:
            Color(*c["card"])
            self._header_bg = Rectangle(pos=self._header.pos, size=self._header.size)
        self._form.canvas.before.clear()
        with self._form.canvas.before:
            Color(*c["card"])
            self._form_bg = Rectangle(pos=self._form.pos, size=self._form.size)
        self._actions.canvas.before.clear()
        with self._actions.canvas.before:
            Color(*c["bg"])
            self._actions_bg = Rectangle(pos=self._actions.pos, size=self._actions.size)
        self._dl_bar.canvas.before.clear()
        with self._dl_bar.canvas.before:
            Color(*c["card"])
            self._dlbar_bg = Rectangle(pos=self._dl_bar.pos, size=self._dl_bar.size)

        for row in self.file_rows:
            row.set_theme(c)

    def show_about(self, *_):
        c = self.c
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))

        content.add_widget(Label(
            text="MediaFolder Pro", bold=True, font_size=sp(18),
            color=c["accent"], size_hint_y=None, height=dp(28)
        ))
        content.add_widget(Label(
            text=f"Version {APP_VERSION}  •  Android Edition",
            font_size=sp(11), color=c["sub"], size_hint_y=None, height=dp(18)
        ))
        content.add_widget(Label(
            text=f"Creator: SSMG4\nGitHub: {GITHUB_URL}\nLicense: GNU GPL v3.0",
            font_size=sp(11), color=c["text"], halign="left",
            size_hint_y=None, height=dp(52)
        ))
        content.add_widget(Label(
            text=(
                "◆ Recursive folder tree browsing\n"
                "◆ Per-file & overall progress\n"
                "◆ Real-time speed with ETA\n"
                "◆ Pause / Resume / Abort\n"
                "◆ Parallel downloads (3 threads)\n"
                "◆ Checkbox file selection\n"
                "◆ Dark & Light theme"
            ),
            font_size=sp(11), color=c["text"], halign="left",
            size_hint_y=None, height=dp(100)
        ))

        close_btn = Button(
            text="Close", size_hint_y=None, height=dp(40),
            background_normal="", background_color=c["accent"],
            color=(1, 1, 1, 1), bold=True
        )
        content.add_widget(close_btn)

        popup = Popup(
            title="About", content=content,
            size_hint=(0.88, None), height=dp(360),
            background_color=c["card"]
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def start_fetch(self, *_):
        url = self.url_input.text.strip()
        if not url:
            self._show_popup("Error", "Please enter a MediaFire folder URL.")
            return
        self._fetch_active = True
        self._fetch_abort = False
        self._shimmer_phase = 0.0
        self.fetch_btn.text = "FETCHING..."
        self.fetch_btn.disabled = True
        self.stop_fetch_btn.opacity = 1
        self.stop_fetch_btn.disabled = False
        self.clear_list()
        self.stats_panel.status_lbl.text = "Fetching folder tree…"
        self.log(f"Fetching: {url}", "info")
        threading.Thread(target=self._fetch_tree, args=(url,), daemon=True).start()

    def abort_fetch(self):
        self._fetch_abort = True
        Clock.schedule_once(self._finish_fetch_ui, 0)

    def _finish_fetch_ui(self, *_):
        self._fetch_active = False
        self._fetch_abort = False
        self.fetch_btn.text = "FETCH CONTENT"
        self.fetch_btn.background_color = self.c["field"]
        self.fetch_btn.disabled = False
        self.stop_fetch_btn.opacity = 0
        self.stop_fetch_btn.disabled = True
        self.stats_panel.status_lbl.text = "Idle"

    def _fetch_tree(self, url):
        try:
            m = re.search(r"folder/([a-zA-Z0-9]+)", url)
            if m:
                self._recursive_api(m.group(1), None)
                total = sum(f["size"] for f in self.file_data.values())
                sel_count = len(self.checked_nodes)
                Clock.schedule_once(lambda dt: self._update_fetch_done(total, sel_count), 0)
                msg = f"Fetch complete — {self.fetch_file_count} files, {self.fetch_folder_count} folders"
                Clock.schedule_once(lambda dt, m=msg: self.log(m, "ok"), 0)
            else:
                Clock.schedule_once(lambda dt: self._show_popup("Error", "Invalid MediaFire folder URL."), 0)
                Clock.schedule_once(lambda dt: self.log("Invalid MediaFire URL", "error"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt, err=e: self._show_popup("Error", str(err)), 0)
            Clock.schedule_once(lambda dt, err=str(e): self.log(f"Fetch error: {err}", "error"), 0)
        Clock.schedule_once(self._finish_fetch_ui, 0)

    def _update_fetch_done(self, total, sel_count):
        self.stats_panel.sel_size_lbl.text = f"Selected size: {fmt_size(total)}"
        self.stats_panel.sel_lbl.text = f"Selected: {sel_count} files"
        self.stats_panel.files_lbl.text = f"Files: 0 / {self.fetch_file_count}"
        self.stats_panel.status_lbl.text = f"Ready — {self.fetch_file_count} file(s) found"

    def _recursive_api(self, key, parent_id):
        if self._fetch_abort:
            return
        try:
            res = requests.get(
                "https://www.mediafire.com/api/1.4/folder/get_content.php",
                params={"content_type": "folders", "folder_key": key, "response_format": "json"},
                timeout=15
            ).json()
            for f in res.get("response", {}).get("folder_content", {}).get("folders", []):
                if self._fetch_abort:
                    return
                self.fetch_folder_count += 1
                node_id = f"folder_{f['folderkey']}"
                depth = self._get_depth(parent_id)
                Clock.schedule_once(
                    lambda dt, n=f["name"], nid=node_id, d=depth, pid=parent_id:
                    self._add_folder_row(n, nid, d, pid), 0
                )
                Clock.schedule_once(lambda dt, n=f["name"]: self.log(f"📁 Folder: {n}", "info"), 0)
                self._recursive_api(f["folderkey"], node_id)

            res = requests.get(
                "https://www.mediafire.com/api/1.4/folder/get_content.php",
                params={"content_type": "files", "folder_key": key, "response_format": "json"},
                timeout=15
            ).json()
            for f in res.get("response", {}).get("folder_content", {}).get("files", []):
                if self._fetch_abort:
                    return
                sz = int(f.get("size", 0))
                self.fetch_file_count += 1
                node_id = f"file_{f['quickkey']}"
                depth = self._get_depth(parent_id)
                self.file_data[node_id] = {
                    "key": f["quickkey"], "name": f["filename"],
                    "size": sz, "parent_id": parent_id
                }
                self.checked_nodes.add(node_id)
                cnt = self.fetch_file_count
                Clock.schedule_once(
                    lambda dt, fn=f["filename"], fs=fmt_size(sz), nid=node_id, d=depth, c=cnt:
                    self._add_file_row(fn, fs, nid, d, c), 0
                )
                Clock.schedule_once(lambda dt, n=f["filename"], s=fmt_size(sz): self.log(f"📄 {n}  ({s})", "info"), 0)
        except Exception as e:
            print(f"API error: {e}")

    def _get_depth(self, parent_id):
        if not parent_id:
            return 0
        d = 0
        pid = parent_id
        while pid and pid in self.folder_rows:
            pid = self.folder_rows[pid].get("parent")
            d += 1
        return d

    def _add_folder_row(self, name, node_id, depth, parent_id):
        row = FileRow(
            name=name, size_str="", depth=depth,
            is_folder=True, on_toggle=self._on_row_toggle
        )
        self.folder_rows[node_id] = {"row": row, "parent": parent_id}
        self.file_rows.append(row)
        self.file_list.add_widget(row)
        fc = self.fetch_folder_count
        self.stats_panel.status_lbl.text = f"Folders: {fc}…"

    def _add_file_row(self, name, size_str, node_id, depth, count):
        row = FileRow(
            name=name, size_str=size_str, depth=depth,
            is_folder=False, on_toggle=self._on_row_toggle
        )
        row._node_id = node_id
        self.file_rows.append(row)
        self.file_list.add_widget(row)
        self.stats_panel.files_lbl.text = f"Files: 0 / {count}"

    def _on_row_toggle(self, row, val):
        if hasattr(row, "_node_id"):
            if val:
                self.checked_nodes.add(row._node_id)
            else:
                self.checked_nodes.discard(row._node_id)
        self._refresh_selection()

    def _refresh_selection(self):
        checked = [n for n in self.file_data if n in self.checked_nodes]
        count = len(checked)
        sel_size = sum(self.file_data[n]["size"] for n in checked)
        self.stats_panel.sel_lbl.text = f"Selected: {count} files"
        self.stats_panel.sel_size_lbl.text = f"Selected size: {fmt_size(sel_size)}"

    def clear_list(self):
        self.file_list.clear_widgets()
        self.file_rows.clear()
        self.folder_rows.clear()
        self.file_data.clear()
        self.checked_nodes.clear()
        self.fetch_file_count = 0
        self.fetch_folder_count = 0
        self.stats_panel.files_lbl.text = "Files: 0 / 0"
        self.stats_panel.sel_lbl.text = "Selected: 0 files"
        self.stats_panel.sel_size_lbl.text = "Selected size: —"
        self.stats_panel.status_lbl.text = "Idle"

    def handle_dl_trigger(self, *_):
        if not self.file_data:
            self._show_popup("Warning", "Fetch a folder first.")
            return
        if not self.is_downloading:
            self._start_download()
        else:
            self.abort_requested = True
            self.is_paused = False
            self.stats_panel.status_lbl.text = "Aborting…"

    def toggle_pause(self, *_):
        self.is_paused = not self.is_paused
        self.pause_btn.text = "RESUME" if self.is_paused else "PAUSE"
        self.stats_panel.status_lbl.text = "Paused" if self.is_paused else "Downloading…"

    def _start_download(self):
        dest = self.path_input.text.strip()
        selected = [self.file_data[n] for n in self.file_data if n in self.checked_nodes]
        if not selected:
            self._show_popup("Warning", "No files selected.")
            return
        if not dest:
            self._show_popup("Warning", "Set a download location first.")
            return

        self.is_downloading = True
        self.abort_requested = False
        self.peak_speed = 0
        self.dl_start_time = time.time()
        self.total_size_to_download = sum(f["size"] for f in selected)
        self.total_downloaded_so_far = 0
        self.total_files_count = len(selected)
        self.files_completed = 0
        self.files_failed = 0

        for f in selected:
            f["resolved_path"] = os.path.join(dest, self._get_path_str(f["parent_id"]))

        self.dl_btn.text = "STOP"
        self.dl_btn.background_color = self.c["stop"]
        self.pause_btn.disabled = False
        self.stats_panel.dl_prog_lbl.text = f"Downloaded: 0 B / {fmt_size(self.total_size_to_download)}"

        threading.Thread(target=self._run_downloads, args=(selected, dest), daemon=True).start()
        self.log(f"Starting download of {len(selected)} file(s) → {dest}", "info")
        Clock.schedule_interval(self._tick_graph, 0.5)

    def _get_path_str(self, parent_id):
        parts = []
        pid = parent_id
        while pid and pid in self.folder_rows:
            row = self.folder_rows[pid]["row"]
            parts.insert(0, row._name)
            pid = self.folder_rows[pid]["parent"]
        return os.path.join(*parts) if parts else ""

    def _run_downloads(self, files, base):
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = []
            for f in files:
                while self.is_paused and not self.abort_requested:
                    time.sleep(0.3)
                if self.abort_requested:
                    break
                futures.append(ex.submit(self._dl_file, f))
            for fut in futures:
                try:
                    fut.result()
                except Exception as e:
                    print(f"Future error: {e}")

        self.is_downloading = False
        Clock.unschedule(self._tick_graph)

        if not self.abort_requested:
            elapsed = int(time.time() - self.dl_start_time) if self.dl_start_time else 0
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            fc, ff, td = self.files_completed, self.files_failed, self.total_downloaded_so_far
            summary = f"Done — {fc} downloaded, {ff} failed, {fmt_size(td)}, {h:02d}:{m:02d}:{s:02d}"
            Clock.schedule_once(lambda dt, msg=summary, level="ok" if ff == 0 else "warn":
                                 self.log(msg, level), 0)
            Clock.schedule_once(lambda dt: self._show_popup(
                "Download Complete",
                f"Files: {fc}  |  Failed: {ff}\n"
                f"Size: {fmt_size(td)}\n"
                f"Time: {h:02d}:{m:02d}:{s:02d}\n\nSaved to:\n{base}"
            ), 0)
        Clock.schedule_once(self._reset_dl_ui, 0)

    def _dl_file(self, file):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            name = file["name"]
            Clock.schedule_once(lambda dt, n=name: self.log(f"Resolving: {n}", "info"), 0)
            Clock.schedule_once(lambda dt, n=name: setattr(
                self.stats_panel.status_lbl, "text", f"Resolving: {n[:22]}…"), 0)

            r = requests.get(f"https://www.mediafire.com/file/{file['key']}", headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            btn = soup.find("a", {"id": "downloadButton"})

            if btn and btn.get("href"):
                Clock.schedule_once(lambda dt, n=name: self.log(f"↓ Downloading: {n}", "info"), 0)
                Clock.schedule_once(lambda dt, n=name: setattr(
                    self.stats_panel.status_lbl, "text", f"↓ {n[:24]}…"), 0)
                with requests.get(btn["href"], stream=True, headers=headers, timeout=30) as resp:
                    os.makedirs(file["resolved_path"], exist_ok=True)
                    filepath = os.path.join(file["resolved_path"], name)
                    downloaded = 0
                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=512 * 1024):
                            while self.is_paused and not self.abort_requested:
                                time.sleep(0.3)
                            if self.abort_requested:
                                return
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                with self._dl_lock:
                                    self.total_downloaded_so_far += len(chunk)
                                Clock.schedule_once(lambda dt: self._update_counters(), 0)
                with self._dl_lock:
                    self.files_completed += 1
                sz_str = fmt_size(file["size"])
                Clock.schedule_once(lambda dt, n=name, s=sz_str: self.log(f"✓ Done: {n}  ({s})", "ok"), 0)
            else:
                Clock.schedule_once(lambda dt, n=name: self.log(f"⚠ No download link: {n}", "warn"), 0)
                with self._dl_lock:
                    self.files_failed += 1
                    self.files_completed += 1
                    self.failed_files.append(dict(file))
                Clock.schedule_once(lambda dt: setattr(self.view_failed_btn, "disabled", False), 0)
        except Exception as e:
            err_msg = str(e)
            Clock.schedule_once(lambda dt, n=file["name"], err=err_msg: self.log(f"✗ Error [{n}]: {err}", "error"), 0)
            print(f"Download error [{file['name']}]: {e}")
            with self._dl_lock:
                self.files_failed += 1
                self.files_completed += 1
                self.failed_files.append(dict(file))
            Clock.schedule_once(lambda dt: setattr(self.view_failed_btn, "disabled", False), 0)

    def _update_counters(self):
        with self._dl_lock:
            done = self.total_downloaded_so_far
            total = self.total_size_to_download
            completed = self.files_completed
            total_f = self.total_files_count
            failed = self.files_failed
        rem = max(0, total - done)
        self.stats_panel.files_lbl.text = f"Files: {completed} / {total_f}"
        self.stats_panel.rem_lbl.text = f"Remaining: {fmt_size(rem)}"
        self.stats_panel.dl_prog_lbl.text = f"Downloaded: {fmt_size(done)} / {fmt_size(total)}"
        if failed > 0:
            self.stats_panel.status_lbl.text = f"Downloading… ({failed} failed)"

    def _tick_graph(self, dt):
        with self._dl_lock:
            last = self.total_downloaded_so_far
        time.sleep(0.45)
        with self._dl_lock:
            cur = self.total_downloaded_so_far
        speed = max(0, (cur - last) * 2)
        self.speed_history.pop(0)
        self.speed_history.append(speed)
        if speed > self.peak_speed:
            self.peak_speed = speed

        self.stats_panel.speed_lbl.text = f"{fmt_size(speed)}/s"
        self.stats_panel.peak_lbl.text = f"Peak: {fmt_size(self.peak_speed)}/s"
        if self.dl_start_time:
            elapsed = int(time.time() - self.dl_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.stats_panel.elapsed_lbl.text = f"Elapsed: {h:02d}:{m:02d}:{s:02d}"
        if speed > 0 and self.total_size_to_download > 0:
            with self._dl_lock:
                rem = max(0, self.total_size_to_download - self.total_downloaded_so_far)
            eta = int(rem / speed)
            h, m, s = eta // 3600, (eta % 3600) // 60, eta % 60
            self.stats_panel.eta_lbl.text = f"ETA: {h:02d}:{m:02d}:{s:02d}"

    def _reset_dl_ui(self, *_):
        self.dl_btn.text = "START DOWNLOAD"
        self.dl_btn.background_color = self.c["accent"]
        self.pause_btn.disabled = True
        self.pause_btn.text = "PAUSE"
        self.is_paused = False
        self.stats_panel.speed_lbl.text = "0.00 KB/s"
        self.stats_panel.eta_lbl.text = "ETA: --:--:--"
        if self.abort_requested:
            self.stats_panel.status_lbl.text = "Aborted"
            self.log("Download aborted by user", "warn")
        else:
            self.stats_panel.status_lbl.text = "Done ✓"

    def _show_popup(self, title, msg):
        c = self.c
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        content.add_widget(Label(
            text=msg, font_size=sp(12), color=c["text"],
            halign="left", valign="top"
        ))
        btn = Button(
            text="OK", size_hint_y=None, height=dp(40),
            background_normal="", background_color=c["accent"],
            color=(1, 1, 1, 1), bold=True
        )
        content.add_widget(btn)
        popup = Popup(title=title, content=content,
                      size_hint=(0.82, None), height=dp(200),
                      background_color=c["card"])
        btn.bind(on_press=popup.dismiss)
        popup.open()

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f).get("last_path", "")
        except Exception:
            return ""

    def _save_settings(self, path):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump({"last_path": path}, f)
        except Exception:
            pass

    def on_stop(self):
        path = self.path_input.text.strip()
        if path:
            self._save_settings(path)


if __name__ == "__main__":
    MediaFolderAndroid().run()
