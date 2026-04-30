import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import webbrowser
import requests
from bs4 import BeautifulSoup
import threading
import os
import json
import re
import time
import math
from io import BytesIO
from PIL import Image, ImageTk
from concurrent.futures import ThreadPoolExecutor

SETTINGS_FILE = "mediafolder_settings.json"
APP_VERSION = "2.0.0"
LOGO_URL = "https://apizutool.one/images/logoz/dwnld/mediafire.png"
GITHUB_URL = "https://github.com/Hexadecinull/MediaFolderPro"


class MediaFolderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaFolder Pro")
        self.root.geometry("1200x870")

        self.is_dark = True
        self.file_data = {}
        self.speed_history = [0] * 50
        self.current_speed = 0
        self.peak_speed = 0
        self.is_downloading = False
        self.is_paused = False
        self.abort_requested = False
        self.icon_img = None
        self.total_size_to_download = 0
        self.total_downloaded_so_far = 0
        self.total_files_count = 0
        self.files_completed = 0
        self.files_failed = 0
        self.fetch_file_count = 0
        self.fetch_folder_count = 0
        self.dl_start_time = None
        self._fetch_active = False
        self._fetch_abort = False
        self._fetch_canvas_w = 1
        self._fetch_canvas_h = 30
        self._fetch_shimmer_x = 0.0
        self.checked_nodes = set()
        self._dl_lock = threading.Lock()
        self.failed_files = []
        self._console_lines = []

        self.themes = {
            "dark": {
                "bg": "#111111", "sidebar": "#181818", "content": "#1e1e1e",
                "text": "#eeeeee", "accent": "#007acc", "stop": "#d32f2f",
                "field": "#252526", "border": "#333333", "subtext": "#888888",
            },
            "light": {
                "bg": "#f3f3f3", "sidebar": "#e8e8e8", "content": "#ffffff",
                "text": "#111111", "accent": "#005fb8", "stop": "#c62828",
                "field": "#f0f0f0", "border": "#cccccc", "subtext": "#666666",
            }
        }

        self.style = ttk.Style()
        self.setup_ui()
        self.apply_theme()

        last_path = self.load_settings()
        if last_path:
            self.path_entry.insert(0, last_path)

        threading.Thread(target=self._load_app_icon, daemon=True).start()

    def _load_app_icon(self):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(LOGO_URL, headers=headers, timeout=10)
            res.raise_for_status()
            img = Image.open(BytesIO(res.content)).resize((32, 32), Image.Resampling.LANCZOS)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            self.icon_img = ImageTk.PhotoImage(img)
            self.root.after(0, self._apply_icon)
        except Exception as e:
            print(f"Icon load error: {e}")

    def _apply_icon(self):
        if self.icon_img:
            self.root.iconphoto(True, self.icon_img)
            self.logo_canvas.delete("all")
            self.logo_canvas.create_image(16, 16, image=self.icon_img)

    def setup_ui(self):
        self.sidebar = tk.Frame(self.root, width=300)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.header_f = tk.Frame(self.sidebar)
        self.header_f.pack(pady=(28, 8), fill="x", padx=10)

        self.logo_canvas = tk.Canvas(self.header_f, width=32, height=32, highlightthickness=0)
        self.logo_canvas.pack(side="left", padx=(10, 6))

        self.logo_lbl = tk.Label(self.header_f, text="MEDIAFOLDER", font=("Segoe UI", 14, "bold"), bd=0)
        self.logo_lbl.pack(side="left")

        self.stats_f = tk.Frame(self.sidebar)
        self.stats_f.pack(fill="x", padx=25, pady=(6, 2))

        self.speed_val = tk.Label(self.stats_f, text="0.00 KB/s", font=("Consolas", 15, "bold"), bd=0)
        self.speed_val.pack(anchor="w")
        self.eta_lbl = tk.Label(self.stats_f, text="ETA: --:--:--", font=("Segoe UI", 9), bd=0)
        self.eta_lbl.pack(anchor="w")
        self.rem_lbl = tk.Label(self.stats_f, text="Remaining: 0 B", font=("Segoe UI", 9), bd=0)
        self.rem_lbl.pack(anchor="w")
        self.elapsed_lbl = tk.Label(self.stats_f, text="Elapsed: --:--:--", font=("Segoe UI", 9), bd=0)
        self.elapsed_lbl.pack(anchor="w")
        self.peak_lbl = tk.Label(self.stats_f, text="Peak: 0 B/s", font=("Segoe UI", 9), bd=0)
        self.peak_lbl.pack(anchor="w")
        self.dl_progress_lbl = tk.Label(self.stats_f, text="Downloaded: 0 B / 0 B", font=("Segoe UI", 9), bd=0)
        self.dl_progress_lbl.pack(anchor="w")
        self.cur_file_lbl = tk.Label(self.stats_f, text="", font=("Segoe UI", 8), bd=0, wraplength=240, justify="left")
        self.cur_file_lbl.pack(anchor="w", pady=(4, 0))

        self.graph_canvas = tk.Canvas(self.sidebar, height=75, highlightthickness=0)
        self.graph_canvas.pack(fill="x", padx=20, pady=(10, 6))

        self.prog_f = tk.Frame(self.sidebar)
        self.prog_f.pack(fill="x", padx=25)

        self.file_status = tk.Label(self.prog_f, text="Idle", font=("Segoe UI", 8), anchor="w", bd=0)
        self.file_status.pack(fill="x")
        self.p1 = ttk.Progressbar(self.prog_f, mode="determinate")
        self.p1.pack(fill="x", pady=(2, 8))

        self.total_status = tk.Label(self.prog_f, text="Overall: 0%", font=("Segoe UI", 8), anchor="w", bd=0)
        self.total_status.pack(fill="x")
        self.p2 = ttk.Progressbar(self.prog_f, mode="determinate")
        self.p2.pack(fill="x", pady=2)

        self.info_f = tk.Frame(self.sidebar)
        self.info_f.pack(fill="x", padx=25, pady=(12, 0))

        self.counter_lbl = tk.Label(self.info_f, text="Files: 0 / 0", font=("Segoe UI", 9, "bold"), bd=0, anchor="w")
        self.counter_lbl.pack(fill="x")
        self.failed_lbl = tk.Label(self.info_f, text="Failed: 0", font=("Segoe UI", 8), bd=0, anchor="w")
        self.failed_lbl.pack(fill="x")
        self.size_lbl = tk.Label(self.info_f, text="Total size: —", font=("Segoe UI", 8), bd=0, anchor="w")
        self.size_lbl.pack(fill="x")
        self.folders_lbl = tk.Label(self.info_f, text="Folders: 0", font=("Segoe UI", 8), bd=0, anchor="w")
        self.folders_lbl.pack(fill="x")
        self.sel_lbl = tk.Label(self.info_f, text="Selected: 0 files", font=("Segoe UI", 8), bd=0, anchor="w")
        self.sel_lbl.pack(fill="x", pady=(2, 0))

        self.console_header_f = tk.Frame(self.sidebar)
        self.console_header_f.pack(fill="x", padx=20, pady=(10, 0))
        self.console_lbl = tk.Label(self.console_header_f, text="Console", font=("Segoe UI", 7, "bold"), bd=0, anchor="w")
        self.console_lbl.pack(side="left")
        self.clear_console_btn = tk.Button(
            self.console_header_f, text="Clear", font=("Segoe UI", 7),
            relief="flat", bd=0, cursor="hand2", padx=6, pady=1,
            command=self._clear_console
        )
        self.clear_console_btn.pack(side="right")

        self.console = tk.Text(
            self.sidebar, font=("Consolas", 7), relief="flat",
            state="disabled", wrap="word", bd=0, height=1
        )
        self.console.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.console.tag_config("info",  foreground="#888888")
        self.console.tag_config("ok",    foreground="#4caf50")
        self.console.tag_config("warn",  foreground="#ff9800")
        self.console.tag_config("error", foreground="#f44336")

        self.btn_stack = tk.Frame(self.sidebar)
        self.btn_stack.pack(side="bottom", fill="x", padx=20, pady=20)

        self.view_failed_btn = tk.Button(
            self.btn_stack, text="VIEW FAILED FILES", font=("Segoe UI", 8),
            relief="flat", bd=0, cursor="hand2", pady=4, command=self.show_failed_files,
            state="disabled"
        )
        self.view_failed_btn.pack(fill="x", pady=(0, 6))

        self.pause_btn = tk.Button(
            self.btn_stack, text="PAUSE", font=("Segoe UI", 10, "bold"),
            relief="flat", state="disabled", command=self.toggle_pause, bd=0, cursor="hand2", pady=6
        )
        self.pause_btn.pack(fill="x", pady=(0, 6))

        self.dl_btn = tk.Button(
            self.btn_stack, text="START DOWNLOAD", font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2", command=self.handle_dl_trigger, bd=0, pady=6
        )
        self.dl_btn.pack(fill="x")

        self.main_area = tk.Frame(self.root)
        self.main_area.pack(side="right", fill="both", expand=True)

        self.top_btns_f = tk.Frame(self.main_area)
        self.top_btns_f.pack(fill="x", padx=10, pady=(8, 0))

        self.about_btn = tk.Button(
            self.top_btns_f, text="About", font=("Segoe UI", 7),
            relief="flat", bd=0, cursor="hand2", command=self.show_about, padx=6, pady=3
        )
        self.about_btn.pack(side="right", padx=(0, 4))

        self.theme_btn = tk.Button(
            self.top_btns_f, text="Toggle Theme", font=("Segoe UI", 7),
            relief="flat", bd=0, cursor="hand2", command=self.toggle_theme, padx=6, pady=3
        )
        self.theme_btn.pack(side="right", padx=(0, 4))

        self.top_bar = tk.Frame(self.main_area)
        self.top_bar.pack(fill="x", padx=20, pady=(8, 6))

        self.url_lbl = tk.Label(self.top_bar, text="Source URL", font=("Segoe UI", 8, "bold"), bd=0)
        self.url_lbl.grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.url_entry = tk.Entry(self.top_bar, font=("Segoe UI", 10), relief="flat", bd=0)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10), ipady=5)

        self.dl_loc_lbl = tk.Label(self.top_bar, text="Download Location", font=("Segoe UI", 8, "bold"), bd=0)
        self.dl_loc_lbl.grid(row=2, column=0, sticky="w", pady=(0, 2))

        self.path_f = tk.Frame(self.top_bar)
        self.path_f.grid(row=3, column=0, sticky="ew")
        self.path_entry = tk.Entry(self.path_f, font=("Segoe UI", 10), relief="flat", bd=0)
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.br_btn = tk.Button(
            self.path_f, text="Browse", relief="flat", bd=0,
            cursor="hand2", command=self.browse_directory, padx=10, pady=5
        )
        self.br_btn.pack(side="right", padx=(8, 0))
        self.top_bar.columnconfigure(0, weight=1)

        self.action_f = tk.Frame(self.main_area)
        self.action_f.pack(fill="x", padx=20, pady=(4, 6))

        self.fetch_canvas = tk.Canvas(self.action_f, height=30, highlightthickness=0, cursor="hand2")
        self.fetch_canvas.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.fetch_canvas.bind("<Button-1>", self._on_fetch_click)
        self.fetch_canvas.bind("<Configure>", self._on_fetch_configure)

        self.clear_btn = tk.Button(
            self.action_f, text="CLEAR", font=("Segoe UI", 9, "bold"),
            relief="flat", command=self.clear_list, bd=0, cursor="hand2", width=10
        )
        self.clear_btn.pack(side="right", fill="y")

        self.tree = ttk.Treeview(self.main_area, columns=("check", "size"), selectmode="none")
        self.tree.heading("#0", text="  Item Name")
        self.tree.heading("check", text="Selection")
        self.tree.heading("size", text="Size")
        self.tree.column("#0", minwidth=200)
        self.tree.column("check", width=110, anchor="center", minwidth=80)
        self.tree.column("size", width=130, anchor="e", minwidth=80)
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tree.bind("<Button-1>", self.handle_click)
        self.tree.bind("<Double-Button-1>", self.handle_double_click)

    def apply_theme(self):
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        self.root.configure(bg=c["bg"])

        for w in [self.sidebar, self.header_f, self.stats_f, self.prog_f, self.btn_stack, self.info_f]:
            w.configure(bg=c["sidebar"])

        for w in [self.main_area, self.top_bar, self.path_f, self.action_f, self.top_btns_f]:
            w.configure(bg=c["content"])

        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            background=c["field"], foreground=c["text"],
            fieldbackground=c["field"], borderwidth=0, rowheight=26
        )
        self.style.configure(
            "Treeview.Heading",
            background=c["content"], foreground=c["text"],
            relief="flat", borderwidth=0, font=("Segoe UI", 9, "bold")
        )
        self.style.map("Treeview.Heading", background=[("active", c["field"])])
        self.style.map(
            "Treeview",
            background=[("selected", c["accent"])],
            foreground=[("selected", "white")]
        )
        self.style.configure("TProgressbar", troughcolor=c["field"], background=c["accent"], borderwidth=0)

        for lbl in [self.logo_lbl, self.speed_val, self.eta_lbl, self.rem_lbl,
                    self.file_status, self.total_status, self.counter_lbl, self.failed_lbl,
                    self.size_lbl, self.folders_lbl, self.sel_lbl, self.cur_file_lbl,
                    self.elapsed_lbl, self.peak_lbl, self.dl_progress_lbl]:
            lbl.configure(bg=c["sidebar"], fg=c["text"])

        self.console_header_f.configure(bg=c["sidebar"])
        self.console_lbl.configure(bg=c["sidebar"], fg=c["subtext"])
        self.clear_console_btn.configure(
            bg=c["sidebar"], fg=c["subtext"],
            activebackground=c["field"], activeforeground=c["text"]
        )
        self.console.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.view_failed_btn.configure(
            bg=c["field"], fg=c["text"],
            activebackground=c["border"], activeforeground=c["text"]
        )
        self.logo_canvas.configure(bg=c["sidebar"])
        self.graph_canvas.configure(bg=c["field"])

        self.url_lbl.configure(bg=c["content"], fg=c["text"])
        self.dl_loc_lbl.configure(bg=c["content"], fg=c["text"])
        self.url_entry.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.path_entry.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])

        self.fetch_canvas.configure(bg=c["field"])
        self._draw_fetch_btn()
        self.pause_btn.configure(
            bg="#888888" if not self.is_dark else c["field"],
            fg="white" if not self.is_dark else c["text"],
            activebackground="#666666" if not self.is_dark else c["border"],
            activeforeground="white" if not self.is_dark else c["text"]
        )
        self.clear_btn.configure(
            bg=c["stop"], fg="white",
            activebackground="#b71c1c", activeforeground="white"
        )
        self.dl_btn.configure(
            bg=c["stop"] if self.is_downloading else c["accent"], fg="white",
            activebackground=c["stop"] if self.is_downloading else "#005a9e",
            activeforeground="white"
        )
        self.pause_btn.configure(
            bg="#888888" if not self.is_dark else c["field"],
            fg="white" if not self.is_dark else c["text"],
            activebackground="#666666" if not self.is_dark else c["border"],
            activeforeground="white" if not self.is_dark else c["text"]
        )
        self.theme_btn.configure(
            bg=c["content"], fg=c["subtext"],
            activebackground=c["field"], activeforeground=c["text"]
        )
        self.about_btn.configure(
            bg=c["content"], fg=c["subtext"],
            activebackground=c["field"], activeforeground=c["text"]
        )
        self.br_btn.configure(
            bg=c["field"], fg=c["text"],
            activebackground=c["border"], activeforeground=c["text"]
        )

    def _on_fetch_configure(self, event):
        self._fetch_canvas_w = event.width
        self._fetch_canvas_h = event.height
        self._draw_fetch_btn()

    def _on_fetch_click(self, event):
        if self._fetch_active:
            stop_zone = self._fetch_canvas_w - 36
            if event.x >= stop_zone:
                self.abort_fetch()
        else:
            self.start_load_thread()

    def _draw_fetch_btn(self):
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        w = self._fetch_canvas_w
        h = self._fetch_canvas_h
        self.fetch_canvas.delete("all")
        self.fetch_canvas.create_rectangle(0, 0, w, h, fill=c["field"], outline="")
        if self._fetch_active:
            self.fetch_canvas.create_rectangle(0, 0, w - 36, h, fill="#1a5f8a", outline="")
            sx = int(self._fetch_shimmer_x * (w - 36))
            shimmer_w = max(60, (w - 36) // 5)
            x0 = sx - shimmer_w // 2
            x1 = sx + shimmer_w // 2
            self.fetch_canvas.create_rectangle(max(0, x0), 0, min(w - 36, x1), h, fill="#4d9eca", outline="")
            stop_x = w - 36
            self.fetch_canvas.create_rectangle(stop_x, 0, w, h, fill="#d32f2f", outline="")
            self.fetch_canvas.create_text(stop_x + 18, h // 2, text="✕", font=("Segoe UI", 10, "bold"), fill="white")
            label_x = (w - 36) // 2
            self.fetch_canvas.create_text(label_x, h // 2, text="FETCHING CONTENT...", font=("Segoe UI", 9, "bold"), fill="#eeeeee")
        else:
            self.fetch_canvas.create_text(w // 2, h // 2, text="FETCH CONTENT", font=("Segoe UI", 9, "bold"), fill=c["text"])

    def _animate_fetch(self):
        if not self._fetch_active:
            return
        self._fetch_shimmer_x = (self._fetch_shimmer_x + 0.015) % 1.1
        self._draw_fetch_btn()
        self.root.after(30, self._animate_fetch)

    def _complete_fetch_anim(self):
        self._fetch_active = False
        self._fetch_abort = False
        self._fetch_shimmer_x = 0.0
        self._draw_fetch_btn()

    def abort_fetch(self):
        self._fetch_abort = True
        self.file_status.config(text="Fetch cancelled")
        self._complete_fetch_anim()
        self.clear_list()


        col = self.tree.identify_column(event.x)
        if col == "#1":
            return "break"

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def _clear_console(self):
        self._console_lines.clear()
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def log(self, msg, level="info"):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._console_lines.append((line, level))
        if len(self._console_lines) > 300:
            self._console_lines.pop(0)
        self.console.configure(state="normal")
        self.console.insert("end", line, level)
        self.console.see("end")
        self.console.configure(state="disabled")

    def show_about(self):
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        win = tk.Toplevel(self.root)
        win.title("About MediaFolder Pro")
        win.geometry("460x560")
        win.configure(bg=c["content"])
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)

        tk.Label(
            win, text="MediaFolder Pro", font=("Segoe UI", 17, "bold"),
            bg=c["content"], fg=c["accent"]
        ).pack(pady=(28, 2))
        tk.Label(
            win, text=f"Version {APP_VERSION}", font=("Segoe UI", 9),
            bg=c["content"], fg=c["subtext"]
        ).pack()

        tk.Frame(win, height=1, bg=c["border"]).pack(fill="x", padx=30, pady=12)

        creator_f = tk.Frame(win, bg=c["content"])
        creator_f.pack(anchor="w", padx=30)
        tk.Label(creator_f, text="Creator: ", font=("Segoe UI", 9), bg=c["content"], fg=c["text"]).pack(side="left")
        tk.Label(creator_f, text="SSMG4", font=("Segoe UI", 9, "bold"), bg=c["content"], fg=c["text"]).pack(side="left")

        gh_f = tk.Frame(win, bg=c["content"])
        gh_f.pack(anchor="w", padx=30, pady=(6, 0))
        tk.Label(gh_f, text="GitHub: ", font=("Segoe UI", 9), bg=c["content"], fg=c["text"]).pack(side="left")
        gh_link = tk.Label(
            gh_f, text=GITHUB_URL, font=("Segoe UI", 9, "underline"),
            bg=c["content"], fg=c["accent"], cursor="hand2"
        )
        gh_link.pack(side="left")
        gh_link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_URL))

        lic_f = tk.Frame(win, bg=c["content"])
        lic_f.pack(anchor="w", padx=30, pady=(6, 0))
        tk.Label(lic_f, text="License: ", font=("Segoe UI", 9), bg=c["content"], fg=c["text"]).pack(side="left")
        lic_link = tk.Label(
            lic_f, text="GNU General Public License v3.0", font=("Segoe UI", 9, "underline"),
            bg=c["content"], fg=c["accent"], cursor="hand2"
        )
        lic_link.pack(side="left")
        lic_link.bind("<Button-1>", lambda e: webbrowser.open("https://www.gnu.org/licenses/gpl-3.0.html"))

        tk.Frame(win, height=1, bg=c["border"]).pack(fill="x", padx=30, pady=12)

        features = (
            "MediaFolder Pro lets you browse and bulk-download\n"
            "entire MediaFire folders with ease.\n\n"
            "  ◆  Recursive folder tree browsing\n"
            "  ◆  Per-file & overall download progress\n"
            "  ◆  Real-time speed graph with ETA & peak speed\n"
            "  ◆  Pause / Resume / Abort support\n"
            "  ◆  Parallel downloads (3 threads)\n"
            "  ◆  Selective file toggle via checkboxes\n"
            "  ◆  Failed file tracking\n"
            "  ◆  Saves last download directory\n"
            "  ◆  Dark & Light theme"
        )
        tk.Label(
            win, text=features, font=("Segoe UI", 9),
            bg=c["content"], fg=c["text"], justify="left"
        ).pack(padx=30, anchor="w")

        tk.Frame(win, height=1, bg=c["border"]).pack(fill="x", padx=30, pady=12)

        tk.Label(
            win, text="Built with Python & tkinter",
            font=("Segoe UI", 8), bg=c["content"], fg=c["subtext"]
        ).pack()

        tk.Button(
            win, text="Close", font=("Segoe UI", 9, "bold"),
            bg=c["accent"], fg="white", relief="flat", bd=0,
            cursor="hand2", command=win.destroy, padx=24, pady=6
        ).pack(pady=10)

    def handle_click(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or col != "#1":
            return
        current = self.tree.set(item, "check")
        new_state = "☐" if current == "☑" else "☑"
        self.update_node(item, new_state)
        self.propagate_down(item, new_state)
        self.refresh_selection_count()

    def handle_double_click(self, event):
        col = self.tree.identify_column(event.x)
        if col == "#1":
            return "break"

    def retry_failed(self):
        if not self.failed_files:
            messagebox.showinfo("Retry", "No failed downloads to retry.")
            return
        if self.is_downloading:
            messagebox.showwarning("Busy", "A download is already in progress.")
            return
        dest = self.path_entry.get().strip()
        if not dest:
            messagebox.showwarning("Warning", "Please choose a destination folder first.")
            return
        to_retry = list(self.failed_files)
        self.failed_files.clear()
        self.log(f"Retrying {len(to_retry)} failed file(s)…", "warn")
        for f in to_retry:
            f["resolved_path"] = os.path.join(dest, self.get_path_string(f["parent"]))
        self.is_downloading = True
        self.abort_requested = False
        self.peak_speed = 0
        self.dl_start_time = time.time()
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        self.dl_btn.config(text="STOP", bg=c["stop"], activebackground="#b71c1c")
        self.pause_btn.config(state="normal")
        self.total_size_to_download = sum(f["size"] for f in to_retry)
        self.total_downloaded_so_far = 0
        self.total_files_count = len(to_retry)
        self.files_completed = 0
        self.files_failed = 0
        self.p1["value"] = 0
        self.p2["value"] = 0
        self.failed_lbl.config(text="Failed: 0")
        self.file_status.config(text="Retrying failed downloads…")
        self.total_status.config(text="Overall: 0%")
        self.dl_progress_lbl.config(text=f"Downloaded: 0 B / {self.format_size(self.total_size_to_download)}")
        self.elapsed_lbl.config(text="Elapsed: 00:00:00")
        threading.Thread(target=self.run_downloads, args=(to_retry, dest), daemon=True).start()
        self._last_graph_bytes = 0
        self._last_graph_time = time.time()
        self.root.after(500, self.update_graph)

    def show_failed_files(self):
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        win = tk.Toplevel(self.root)
        win.title("Failed Downloads")
        win.geometry("520x420")
        win.configure(bg=c["content"])
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win, text="Failed Downloads", font=("Segoe UI", 13, "bold"),
            bg=c["content"], fg=c["stop"]
        ).pack(pady=(18, 4))

        if not self.failed_files:
            tk.Label(
                win, text="No failed downloads.", font=("Segoe UI", 10),
                bg=c["content"], fg=c["subtext"]
            ).pack(pady=20)
        else:
            tk.Label(
                win, text=f"{len(self.failed_files)} file(s) failed:",
                font=("Segoe UI", 9), bg=c["content"], fg=c["subtext"]
            ).pack(anchor="w", padx=20, pady=(0, 4))

            outer = tk.Frame(win, bg=c["field"])
            outer.pack(fill="both", expand=True, padx=20, pady=(0, 8))

            canvas = tk.Canvas(outer, bg=c["field"], highlightthickness=0)
            sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            rows_frame = tk.Frame(canvas, bg=c["field"])
            canvas_window = canvas.create_window((0, 0), window=rows_frame, anchor="nw")

            def _on_rows_configure(e):
                canvas.configure(scrollregion=canvas.bbox("all"))
            def _on_canvas_configure(e):
                canvas.itemconfig(canvas_window, width=e.width)
            rows_frame.bind("<Configure>", _on_rows_configure)
            canvas.bind("<Configure>", _on_canvas_configure)

            def _retry_one(file_entry, row_widget):
                self.failed_files.remove(file_entry)
                row_widget.destroy()
                dest = self.path_entry.get().strip()
                if not dest:
                    messagebox.showwarning("Warning", "No download location set.", parent=win)
                    return
                file_entry["resolved_path"] = os.path.join(dest, self.get_path_string(file_entry["parent"]))
                self.log(f"Retrying: {file_entry['name']}", "warn")
                if not self.is_downloading:
                    self.is_downloading = True
                    self.abort_requested = False
                    self.peak_speed = 0
                    self.dl_start_time = time.time()
                    col2 = self.themes["dark"] if self.is_dark else self.themes["light"]
                    self.dl_btn.config(text="STOP", bg=col2["stop"], activebackground="#b71c1c")
                    self.pause_btn.config(state="normal")
                    self.total_size_to_download = file_entry["size"]
                    self.total_downloaded_so_far = 0
                    self.total_files_count = 1
                    self.files_completed = 0
                    self.files_failed = 0
                    self.p1["value"] = 0
                    self.p2["value"] = 0
                    threading.Thread(target=self.run_downloads, args=([file_entry], dest), daemon=True).start()
                    self._last_graph_bytes = 0
                    self._last_graph_time = time.time()
                    self.root.after(500, self.update_graph)
                else:
                    threading.Thread(target=self.download_single_file, args=(file_entry, dest), daemon=True).start()

            for f in list(self.failed_files):
                row = tk.Frame(rows_frame, bg=c["field"])
                row.pack(fill="x", pady=1, padx=2)
                tk.Label(
                    row, text=f"  {f['name']}  ({self.format_size(f['size'])})",
                    font=("Consolas", 8), bg=c["field"], fg=c["text"],
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)
                tk.Button(
                    row, text="Retry", font=("Segoe UI", 7, "bold"),
                    bg=c["accent"], fg="white", relief="flat", bd=0,
                    cursor="hand2", padx=8, pady=3,
                    command=lambda fe=f, r=row: _retry_one(fe, r)
                ).pack(side="right", padx=(0, 4))

        btn_row = tk.Frame(win, bg=c["content"])
        btn_row.pack(pady=12)
        tk.Button(
            btn_row, text="Retry All", font=("Segoe UI", 9, "bold"),
            bg=c["accent"], fg="white", relief="flat", bd=0,
            cursor="hand2", padx=18, pady=6,
            command=lambda: [win.destroy(), self.retry_failed()]
        ).pack(side="left", padx=8)
        tk.Button(
            btn_row, text="Close", font=("Segoe UI", 9),
            bg=c["field"], fg=c["text"], relief="flat", bd=0,
            cursor="hand2", padx=18, pady=6, command=win.destroy
        ).pack(side="left", padx=8)

    def update_node(self, item, state):
        self.tree.set(item, "check", state)
        if state == "☑":
            self.checked_nodes.add(item)
        else:
            self.checked_nodes.discard(item)

    def propagate_down(self, item, state):
        for child in self.tree.get_children(item):
            self.update_node(child, state)
            self.propagate_down(child, state)

    def refresh_selection_count(self):
        checked_files = [n for n in self.file_data if n in self.checked_nodes]
        count = len(checked_files)
        sel_size = sum(self.file_data[n]["size"] for n in checked_files)
        self.sel_lbl.config(text=f"Selected: {count} files")
        self.size_lbl.config(text=f"Selected size: {self.format_size(sel_size)}")

    def clear_list(self):
        self.tree.delete(*self.tree.get_children())
        self.file_data.clear()
        self.checked_nodes.clear()
        self.failed_files.clear()
        self._console_lines.clear()
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.view_failed_btn.config(state="disabled")
        self.fetch_file_count = 0
        self.fetch_folder_count = 0
        self.counter_lbl.config(text="Files: 0 / 0")
        self.failed_lbl.config(text="Failed: 0")
        self.size_lbl.config(text="Selected size: —")
        self.folders_lbl.config(text="Folders: 0")
        self.sel_lbl.config(text="Selected: 0 files")
        self.file_status.config(text="Idle")

    def handle_dl_trigger(self):
        if not self.file_data:
            messagebox.showwarning("Warning", "Please fetch a MediaFire folder first.")
            return
        if not self.is_downloading:
            self.start_download_thread()
        else:
            if messagebox.askyesno("Abort", "Stop all active downloads?"):
                self.abort_requested = True
                self.is_paused = False
                self.file_status.config(text="Aborting...")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_btn.config(text="RESUME" if self.is_paused else "PAUSE")
        self.file_status.config(text="Paused — click Resume to continue" if self.is_paused else "Downloading...")

    def start_download_thread(self):
        dest = self.path_entry.get().strip()
        selected = [self.file_data[n] for n in self.file_data if n in self.checked_nodes]
        if not selected:
            messagebox.showwarning("Warning", "No files selected. Toggle selections in the list first.")
            return
        if not dest:
            messagebox.showwarning("Warning", "Please choose a destination folder first.")
            return

        self.is_downloading = True
        self.abort_requested = False
        self.peak_speed = 0
        self.dl_start_time = time.time()

        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        self.dl_btn.config(text="STOP", bg=c["stop"], activebackground="#b71c1c")
        self.pause_btn.config(state="normal")

        self.total_size_to_download = sum(f["size"] for f in selected)
        self.total_downloaded_so_far = 0
        self.total_files_count = len(selected)
        self.files_completed = 0
        self.files_failed = 0

        for f in selected:
            f["resolved_path"] = os.path.join(dest, self.get_path_string(f["parent"]))

        self.p1["value"] = 0
        self.p2["value"] = 0
        self.file_status.config(text="Starting downloads…")
        self.total_status.config(text="Overall: 0%")
        self.cur_file_lbl.config(text="")
        self.failed_lbl.config(text="Failed: 0")
        self.peak_lbl.config(text="Peak: 0 B/s")
        self.dl_progress_lbl.config(text=f"Downloaded: 0 B / {self.format_size(self.total_size_to_download)}")
        self.elapsed_lbl.config(text="Elapsed: 00:00:00")
        self.log(f"Starting download of {len(selected)} file(s) → {dest}", "info")

        threading.Thread(target=self.run_downloads, args=(selected, dest), daemon=True).start()
        self._last_graph_bytes = 0
        self._last_graph_time = time.time()
        self.root.after(500, self.update_graph)

    def run_downloads(self, files, base):
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for file in files:
                while self.is_paused and not self.abort_requested:
                    time.sleep(0.3)
                if self.abort_requested:
                    break
                futures.append(executor.submit(self.download_single_file, file, base))
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Future error: {e}")

        self.is_downloading = False
        self.root.after(0, self.reset_ui)
        if not self.abort_requested:
            elapsed = int(time.time() - self.dl_start_time) if self.dl_start_time else 0
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            fc = self.files_completed
            ff = self.files_failed
            td = self.total_downloaded_so_far
            summary = f"Done — {fc} downloaded, {ff} failed, {self.format_size(td)}, {h:02d}:{m:02d}:{s:02d}"
            self.root.after(0, lambda msg=summary: self.log(msg, "ok" if ff == 0 else "warn"))
            self.root.after(
                100,
                lambda: messagebox.showinfo(
                    "Download Complete",
                    f"All done!\n\n"
                    f"Files downloaded:   {fc}\n"
                    f"Files failed:            {ff}\n"
                    f"Total downloaded:  {self.format_size(td)}\n"
                    f"Time elapsed:        {h:02d}:{m:02d}:{s:02d}\n\n"
                    f"Saved to:\n{base}"
                )
            )

    def download_single_file(self, file, base):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            name = file["name"]
            dest_path = file["resolved_path"]

            self.root.after(0, lambda n=name: self.cur_file_lbl.config(text=f"Resolving: {n}"))
            self.root.after(0, lambda n=name: self.file_status.config(text=f"Resolving: {n[:26]}…"))
            self.root.after(0, lambda n=name: self.log(f"Resolving: {n}", "info"))

            response = requests.get(
                f"https://www.mediafire.com/file/{file['key']}",
                headers=headers, timeout=15
            )
            soup = BeautifulSoup(response.text, "html.parser")
            d_btn = soup.find("a", {"id": "downloadButton"})

            if d_btn and d_btn.get("href"):
                self.root.after(0, lambda n=name: self.file_status.config(text=f"↓ {n[:28]}…"))
                self.root.after(0, lambda n=name: self.cur_file_lbl.config(text=f"↓ {n}"))
                self.root.after(0, lambda n=name: self.log(f"↓ Downloading: {n}", "info"))

                with requests.get(d_btn["href"], stream=True, headers=headers, timeout=30) as r:
                    os.makedirs(dest_path, exist_ok=True)
                    filepath = os.path.join(dest_path, name)
                    file_size = int(r.headers.get("content-length", 0))
                    downloaded = 0

                    with open(filepath, "wb") as f:
                        for chunk in r.iter_content(chunk_size=512 * 1024):
                            while self.is_paused and not self.abort_requested:
                                time.sleep(0.3)
                            if self.abort_requested:
                                return
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                with self._dl_lock:
                                    self.total_downloaded_so_far += len(chunk)
                                if file_size > 0:
                                    pct = int((downloaded / file_size) * 100)
                                    self.root.after(0, lambda p=pct: self.p1.__setitem__("value", p))
                                self.root.after(0, self.update_counters)

                with self._dl_lock:
                    self.files_completed += 1
                self.root.after(0, lambda n=name, s=self.format_size(file["size"]): self.log(f"✓ Done: {n}  ({s})", "ok"))
            else:
                self.root.after(0, lambda n=name: self.file_status.config(text=f"⚠ Failed: {n[:24]}"))
                self.root.after(0, lambda n=name: self.log(f"⚠ No download link: {n}", "warn"))
                with self._dl_lock:
                    self.files_failed += 1
                    self.files_completed += 1
                    self.failed_files.append(dict(file))
                ff = self.files_failed
                self.root.after(0, lambda v=ff: self.failed_lbl.config(text=f"Failed: {v}"))
                self.root.after(0, lambda: self.view_failed_btn.config(state="normal"))

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda n=file["name"], err=err_msg: self.log(f"✗ Error [{n}]: {err}", "error"))
            print(f"Download error [{file['name']}]: {e}")
            with self._dl_lock:
                self.files_failed += 1
                self.files_completed += 1
                self.failed_files.append(dict(file))
            ff = self.files_failed
            self.root.after(0, lambda v=ff: self.failed_lbl.config(text=f"Failed: {v}"))
            self.root.after(0, lambda: self.view_failed_btn.config(state="normal"))

    def update_counters(self):
        with self._dl_lock:
            done = self.total_downloaded_so_far
            total = self.total_size_to_download
            completed = self.files_completed
            total_files = self.total_files_count
        if total > 0:
            p = min(100, (done / total) * 100)
            self.p2["value"] = p
            self.total_status.config(text=f"Overall: {int(p)}%")
        self.counter_lbl.config(text=f"Files: {completed} / {total_files}")
        rem = max(0, total - done)
        self.rem_lbl.config(text=f"Remaining: {self.format_size(rem)}")
        self.dl_progress_lbl.config(
            text=f"Downloaded: {self.format_size(done)} / {self.format_size(total)}"
        )

    def reset_ui(self):
        c = self.themes["dark"] if self.is_dark else self.themes["light"]
        self.dl_btn.config(text="START DOWNLOAD", bg=c["accent"], activebackground="#005a9e")
        self.pause_btn.config(state="disabled", text="PAUSE")
        self.p1["value"] = 0
        self.cur_file_lbl.config(text="")
        if self.abort_requested:
            self.p2["value"] = 0
            self.file_status.config(text="Aborted")
            self.total_status.config(text="Aborted")
            self.log("Download aborted by user", "warn")
        else:
            self.file_status.config(text="Done ✓")
            self.total_status.config(text="Overall: 100%")
        self.is_paused = False
        self.speed_val.config(text="0.00 KB/s")
        self.eta_lbl.config(text="ETA: --:--:--")

    def format_size(self, b):
        if b <= 0:
            return "0 B"
        s_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(b, 1024)))
        i = min(i, len(s_name) - 1)
        return f"{round(b / math.pow(1024, i), 2)} {s_name[i]}"

    def get_path_string(self, node):
        p = []
        curr = node
        while curr:
            text = self.tree.item(curr, "text")
            if text:
                p.insert(0, text.strip().replace("📁 ", ""))
            curr = self.tree.parent(curr)
        return os.path.join(*p) if p else ""

    def start_load_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a MediaFire folder URL.")
            return
        self._fetch_active = True
        self._fetch_abort = False
        self._fetch_shimmer_x = 0.0
        self._draw_fetch_btn()
        self.root.after(30, self._animate_fetch)
        self.clear_list()
        self.log(f"Fetching: {url}", "info")
        self.file_status.config(text="Fetching folder tree…")
        threading.Thread(target=self.fetch_tree, args=(url,), daemon=True).start()

    def fetch_tree(self, url):
        try:
            m = re.search(r"folder/([a-zA-Z0-9]+)", url)
            if m:
                self.recursive_api(m.group(1), "")
                total_size = sum(f["size"] for f in self.file_data.values())
                self.root.after(0, lambda ts=total_size: self.size_lbl.config(text=f"Selected size: {self.format_size(ts)}"))
                self.root.after(0, lambda: self.folders_lbl.config(text=f"Folders: {self.fetch_folder_count}"))
                self.root.after(0, lambda: self.counter_lbl.config(text=f"Files: 0 / {self.fetch_file_count}"))
                self.root.after(0, lambda: self.sel_lbl.config(text=f"Selected: {self.fetch_file_count} files"))
                msg = f"Fetch complete — {self.fetch_file_count} files, {self.fetch_folder_count} folders"
                self.root.after(0, lambda: self.file_status.config(text=f"Ready — {self.fetch_file_count} file(s) found"))
                self.root.after(0, lambda m=msg: self.log(m, "ok"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Invalid URL", "Could not find a MediaFire folder key in the given URL."))
                self.root.after(0, lambda: self.file_status.config(text="Idle"))
                self.root.after(0, lambda: self.log("Invalid MediaFire URL", "error"))
        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("Error", str(err)))
            self.root.after(0, lambda: self.file_status.config(text="Error during fetch"))
            self.root.after(0, lambda err=str(e): self.log(f"Fetch error: {err}", "error"))
        self.root.after(0, self._complete_fetch_anim)

    def recursive_api(self, key, parent):
        if self._fetch_abort:
            return
        try:
            res = requests.get(
                "https://www.mediafire.com/api/1.4/folder/get_content.php",
                params={"content_type": "folders", "folder_key": key, "response_format": "json"},
                timeout=15
            ).json()

            for f in res.get("response", {}).get("folder_content", {}).get("folders", []):
                self.fetch_folder_count += 1
                cnt = self.fetch_folder_count
                self.root.after(0, lambda c=cnt: self.folders_lbl.config(text=f"Folders: {c}"))
                self.root.after(0, lambda n=f["name"]: self.file_status.config(text=f"Found folder: {n[:28]}…"))
                self.root.after(0, lambda n=f["name"]: self.log(f"📁 Folder: {n}", "info"))
                node = self.tree.insert(
                    parent, "end", text=f"📁 {f['name']}",
                    values=("☑", ""), open=False
                )
                self.recursive_api(f["folderkey"], node)

            res = requests.get(
                "https://www.mediafire.com/api/1.4/folder/get_content.php",
                params={"content_type": "files", "folder_key": key, "response_format": "json"},
                timeout=15
            ).json()

            for f in res.get("response", {}).get("folder_content", {}).get("files", []):
                sz = int(f.get("size", 0))
                self.fetch_file_count += 1
                cnt = self.fetch_file_count
                self.root.after(0, lambda c=cnt: self.counter_lbl.config(text=f"Files: 0 / {c}"))
                self.root.after(0, lambda n=f["filename"], s=self.format_size(sz): self.log(f"📄 {n}  ({s})", "info"))
                node = self.tree.insert(
                    parent, "end", text=f"📄 {f['filename']}",
                    values=("☑", self.format_size(sz))
                )
                self.checked_nodes.add(node)
                self.file_data[node] = {
                    "key": f["quickkey"],
                    "name": f["filename"],
                    "size": sz,
                    "parent": parent
                }
        except Exception as e:
            print(f"API error: {e}")
            self.root.after(0, lambda err=str(e): self.log(f"API error: {err}", "error"))

    def update_graph(self):
        if not self.is_downloading:
            return

        now = time.time()
        with self._dl_lock:
            current_bytes = self.total_downloaded_so_far

        elapsed_tick = max(0.001, now - self._last_graph_time)
        speed = max(0, (current_bytes - self._last_graph_bytes) / elapsed_tick)
        self._last_graph_bytes = current_bytes
        self._last_graph_time = now

        self.speed_history.pop(0)
        self.speed_history.append(speed)
        self.speed_val.config(text=f"{self.format_size(speed)}/s")

        if speed > self.peak_speed:
            self.peak_speed = speed
            self.peak_lbl.config(text=f"Peak: {self.format_size(self.peak_speed)}/s")

        if self.dl_start_time:
            elapsed = int(time.time() - self.dl_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.elapsed_lbl.config(text=f"Elapsed: {h:02d}:{m:02d}:{s:02d}")

        if speed > 0 and self.total_size_to_download > 0:
            with self._dl_lock:
                done = self.total_downloaded_so_far
            rem = max(0, self.total_size_to_download - done)
            eta_sec = int(rem / speed)
            h, m, s = eta_sec // 3600, (eta_sec % 3600) // 60, eta_sec % 60
            self.eta_lbl.config(text=f"ETA: {h:02d}:{m:02d}:{s:02d}")

        self.graph_canvas.delete("all")
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        if w > 1 and h > 1:
            mv = max(self.speed_history) or 1
            fill_pts = [0, h]
            line_pts = []
            for i, sv in enumerate(self.speed_history):
                x = i * (w / (len(self.speed_history) - 1))
                y = h - (sv / mv * h * 0.85)
                fill_pts.extend([x, y])
                line_pts.extend([x, y])
            fill_pts.extend([w, h])
            self.graph_canvas.create_polygon(fill_pts, fill="#1a5f8a", outline="")
            if len(line_pts) >= 4:
                self.graph_canvas.create_line(line_pts, fill="#007acc", width=2, smooth=True)

        if self.is_downloading:
            self.root.after(500, self.update_graph)

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f).get("last_path", "")
        except Exception:
            return ""

    def browse_directory(self):
        p = filedialog.askdirectory()
        if p:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, p)
            try:
                with open(SETTINGS_FILE, "w") as f:
                    json.dump({"last_path": p}, f)
            except Exception:
                pass


if __name__ == "__main__":
    root = tk.Tk()
    app = MediaFolderApp(root)
    root.mainloop()
