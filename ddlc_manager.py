import os
import shutil
import json
import subprocess
import logging
import time
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from pypresence import Presence
import psutil
import ctypes
import sys
import webbrowser
import urllib.request

# PLEASE DO NOT TOUCH! I BEGGGG
__version__ = "1.1.1"
VERSION_CHECK_URL = "https://lachlanm05.com/ddmc_r/latest_version.txt"
GITHUB_URL = "https://github.com/LachlanM05/ddmc"
CHANGELOG_URL = "https://lachlanm05.com/ddmc_r/changelog.txt"
EXE_DOWNLOAD_BASE = "https://lachlanm05.com/ddmc_r/ddmc_manager.exe"
def parse_version(v):
    return [int(x) for x in v.strip().split(".") if x.isdigit()]


# Use a persistent folder in %APPDATA%
APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "DDLCModManager")
os.makedirs(APPDATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(APPDATA_DIR, "config.txt")


# Configure logging
LOG_PATH = os.path.join(APPDATA_DIR, "ddlc_manager.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# prune that thang
if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 200 * 1024 * 1024:
    os.remove(LOG_PATH)

# Constants
PATHS = {
    "VANILLA": os.path.join(APPDATA_DIR, "vanilla"),
    "MODS": os.path.join(APPDATA_DIR, "mods"),
    "PROFILES": os.path.join(APPDATA_DIR, "profiles"),
    "APPDATA": os.path.expandvars(r"%APPDATA%\\RenPy"),
    "BACKUPS": os.path.join(APPDATA_DIR, "appdata_backups")
}

for path in PATHS.values():
    os.makedirs(path, exist_ok=True)

DISCORD_CLIENT_ID = "1371433500745531472"

# Watchdog for playtime and Discord RPC
class SessionTimer:
    logging.info("Session Timer Tick")

    def __init__(self, rpc, profile_name, mod_name, start_time, on_end_callback):
        self.rpc = rpc
        self.profile_name = profile_name
        self.mod_name = mod_name
        self.start_time = start_time
        self.on_end_callback = on_end_callback
        self.running = True

        self.rpc.update(
            state=f"Playing {self.mod_name}",
            details=f"Profile: {self.profile_name}",
            start=self.start_time,
            large_image="modding_club",
            large_text="Doki Doki Modding Club",
            small_image="playing_a_mod",
            small_text="Playing"
        )

        self.start_tick = time.time()

    def stop(self):
        if self.running:
            self.running = False
            elapsed = int(time.time() - self.start_tick)
            self.rpc.update(
                state="Browsing Profiles",
                details="In Launcher",
                large_image="modding_club",
                large_text="Doki Doki Modding Club",
                small_image="in_launcher",
                small_text="In Launcher"
            )
            self.on_end_callback(elapsed)



# Utility: Get actual RenPy save folder for DDLC
def get_ddlc_save_path():
    if not os.path.exists(PATHS["APPDATA"]):
        return None
    for name in os.listdir(PATHS["APPDATA"]):
        if name.lower().startswith("ddlc"):
            return os.path.join(PATHS["APPDATA"], name)
    return None

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.showtip)
        self.widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack()

    def hidetip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class DDLCManager:
    logging.info("DDLCManager class loaded.")

    def __init__(self, root):
        start = time.time()
        self.root = root
        self.root.title("DDLC Mod Manager")
        self.root.geometry("900x800")
        self.load_config()
        self.root.after(3000, self.try_delete_old_exe)
        self.save_config()
        self.save_config()
        self.style = ttk.Style()
        self.enable_dark_mode()
    
        self.rpc = None
        self.watchdog = None
        self.session_timer = None
        self.init_discord_rpc()
        self.create_widgets()
        self.refresh_profiles()
        self.setup_bindings()
        if not self.config.get("disable_auto_update"):
            self.root.after(8000, lambda: self.check_for_updates(auto=True))
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        duration = time.time() -start
        logging.info(f"{duration:.2f}, huh? You're too slow!")
        

    def try_delete_old_exe(self):
        old_exe = self.config.get("old_exe")
        if not old_exe:
            return

        def delete_task():
            logging.info(f"Attempting to delete old EXE at: {old_path}")
            old_path = os.path.join(os.path.dirname(sys.argv[0]), old_exe)
            for i in range(5):
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        logging.info(f"Deleted old executable: {old_path}")
                    break
                except PermissionError:
                    logging.warning(f"Attempt {i+1}: Old EXE still in use. Retrying...")
                    time.sleep(1.5)
                except Exception as e:
                    logging.error(f"Unexpected error while deleting old exe: {e}")
                    break
            else:
                logging.warning("Could not delete old executable after retries.")

            # Clear config after retry attempt ends (success or not)
            self.config["old_exe"] = None
            self.save_config()

        Thread(target=delete_task, daemon=True).start()


    def load_config(self):
        logging.info("Loading Config")
        self.config = {
            "debug_enabled": False,
            "dark_mode": True,
            "ignored_update_version": None
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    lines = f.read().strip().splitlines()
                    for line in lines:
                        if line == "debug=true":
                            self.config["debug_enabled"] = True
                        elif line == "dark_mode=false":
                            self.config["dark_mode"] = False
                        if line.startswith("ignore_update="):
                            self.config["ignored_update_version"] = line.split("=")[1].strip()
                        elif line.startswith("old_exe="):
                            self.config["old_exe"] = line.split("=")[1].strip()
                        elif line == "disable_auto_update=true":
                            self.config["disable_auto_update"] = True
            except Exception as e:
                print("Failed to read config:", e)
                logging.error(f"Failed to read config {e}")





    def save_config(self):
        logging.info("Saving Config")
        try:
            with open(CONFIG_FILE, "w") as f:
                if self.config.get("debug_enabled"):
                    f.write("debug=true\n")
                f.write(f"dark_mode={'true' if self.config.get('dark_mode') else 'false'}\n")
                if self.config.get("ignored_update_version"):
                    f.write(f"ignore_update={self.config['ignored_update_version']}\n")
                if self.config.get("old_exe"):
                    f.write(f"old_exe={self.config['old_exe']}\n")
                if self.config.get("disable_auto_update"):
                    f.write("disable_auto_update=true\n")
        except Exception as e:
            print("Failed to write config:", e)
            logging.error(f"Failed to write config {e}")






    def enable_dark_mode(self):
        style = self.style
        if self.config.get("dark_mode", True):
            dark_bg = "#1e1e1e"
            dark_fg = "#dcdcdc"
            accent = "#3a3a3a"
        else:
            dark_bg = "#f0f0f0"
            dark_fg = "#000000"
            accent = "#d9d9d9"

        style.theme_use("clam")
        style.configure("TFrame", background=dark_bg)
        style.configure("TLabel", background=dark_bg, foreground=dark_fg)
        style.configure("TButton", background=accent, foreground=dark_fg)
        style.configure("Treeview", background=dark_bg, foreground=dark_fg, fieldbackground=dark_bg)
        style.configure("Treeview.Heading", background=accent, foreground=dark_fg)
        style.map("TButton", background=[("active", "#888" if not self.config["dark_mode"] else "#444")])
        self.root.configure(bg=dark_bg)

    def show_settings_window(self):
        win = Toplevel(self.root)
        win.title("Settings")
        win.resizable(False, False)

        
        content = ttk.Frame(win)
        content.pack(padx=20, pady=20)

        #Update
        ttk.Button(content, text="Check for Updates", command=lambda: self.check_for_updates(auto=False)).pack(pady=(10, 0))

        # Dark mode toggle
        dark_var = BooleanVar(value=self.config.get("dark_mode", True))
        def toggle_dark_mode():
            self.config["dark_mode"] = dark_var.get()
            self.save_config()
            self.enable_dark_mode()
            self.create_widgets()
            self.refresh_profiles()

        # Autoupdate toggle
        ttk.Checkbutton(content, text="Enable Dark Mode", variable=dark_var, command=toggle_dark_mode).pack(pady=5)
        update_var = BooleanVar(value=not self.config.get("disable_auto_update", False))
        def toggle_auto_update():
            self.config["disable_auto_update"] = not update_var.get()
            self.save_config()
        ttk.Checkbutton(content, text="Check for updates at launch", variable=update_var, command=toggle_auto_update).pack(pady=5)


        # Delete buttons
        ttk.Button(content, text="Delete Vanilla", command=self.delete_vanilla).pack(pady=2)
        ttk.Button(content, text="Delete Mods", command=self.delete_mods).pack(pady=2)
        ttk.Button(content, text="Delete Profiles", command=self.delete_profiles).pack(pady=2)

        # "CODE" button
        ttk.Button(content, text="Enter Code", command=self.open_code_entry).pack(pady=(10, 5))

        # Advanced tools (only shown if unlocked)
        if self.config.get("debug_enabled"):
            ttk.Separator(content).pack(fill=X, pady=10)
            ttk.Label(content, text="Advanced Tools:").pack(pady=(5, 2))
            ttk.Button(content, text="Open Profiles Folder", command=lambda: os.startfile(PATHS["PROFILES"])).pack(pady=2)
            ttk.Button(content, text="Open Mods Folder", command=lambda: os.startfile(PATHS["MODS"])).pack(pady=2)
            ttk.Button(content, text="Open Debug Log", command=self.show_debug_window).pack(pady=2)

            # Wipe config
            def wipe_config():
                if messagebox.askyesno("Confirm", "Delete config.txt and reset all settings?"):
                    logging.info("Wipe Config Prompting")
                    try:
                        logging.info("Config File Wiping")
                        os.remove(CONFIG_FILE)
                        messagebox.showinfo("Done", "Config wiped. Restarting app...")
                        logging.info("Config File Wiped, Restarting")
                        self.root.destroy()
                        os.execl(sys.executable, sys.executable, *sys.argv)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to delete config: {e}")
                        logging.error(f"Failed to wipe config {e}")

            ttk.Button(content, text="Wipe Settings", command=wipe_config).pack(pady=6)

            # Force quit
            def force_quit():
                logging.info("Force quitting. That hurts!")
                os._exit(1)

            ttk.Button(content, text="Force Quit", command=force_quit).pack(pady=2)

        # Signature label
        footer = ttk.Label(content, text="Made with love, by LachlanM05", foreground="#4ea3f2", cursor="hand2")
        footer.pack(pady=(10, 0))

        def open_creator_link(event):
            webbrowser.open_new("https://lachlanm05.com")

        footer.bind("<Button-1>", open_creator_link)



        ttk.Button(content, text="Close", command=win.destroy).pack(pady=10)

        sub_footer = ttk.Label(content, text=f"Version {__version__}", font=("Segoe UI", 6))
        sub_footer.pack(pady=(2, 10))

        # Dynamically size the window
        win.update_idletasks()
        win.geometry(f"{content.winfo_reqwidth() + 40}x{content.winfo_reqheight() + 40}")
    

    #Update Check Method
    def check_for_updates(self, auto=False):
        try:
            with urllib.request.urlopen(VERSION_CHECK_URL, timeout=5) as response:
                latest = response.read().decode("utf-8").strip()
            with urllib.request.urlopen(CHANGELOG_URL, timeout=5) as response:
                changelog = response.read().decode("utf-8").strip()

            if self.config.get("ignored_update_version") == latest:
                return  # User ignored this version

            current_parts = parse_version(__version__)
            latest_parts = parse_version(latest)

            if current_parts < latest_parts:
                def ignore_future():
                    self.config["ignored_update_version"] = latest
                    self.save_config()
                    update_win.destroy()

                def download_update():
                    exe_url = "https://lachlanm05.com/ddmc_r/ddlc_manager.exe"
                    exe_filename = f"ddlc_manager_{latest}.exe"
                    exe_path = os.path.join(os.path.dirname(sys.argv[0]), exe_filename)

                    cleanup_script = os.path.join(os.path.dirname(sys.argv[0]), "cleanup_old_exe.bat")
                    old_path = os.path.join(os.path.dirname(sys.argv[0]), self.config["old_exe"])
                    new_name = "ddlc_manager.exe"

                    try:
                        urllib.request.urlretrieve(exe_url, exe_path)
                        logging.info(f"Downloaded new version to {exe_path}")

                        self.config["old_exe"] = os.path.basename(sys.argv[0])
                        self.save_config()

                        # Write cleanup batch script
                        with open(cleanup_script, "w") as f:
                            f.write(f"""@echo off
timeout /t 3 > NUL
del /f /q "{old_path}"
rename "{exe_filename}" "{new_name}"
del /f /q "%~f0"
""")

                        subprocess.Popen([exe_path])
                        subprocess.Popen(["cmd", "/c", cleanup_script], creationflags=subprocess.CREATE_NO_WINDOW)
                        self.root.destroy()

                    except Exception as e:
                        messagebox.showerror("Download Failed", f"Could not download the update:\n{e}")
                        logging.error(f"Failed to download update: {e}")





                update_win = Toplevel(self.root)
                update_win.title("Update Available!")
                update_win.geometry("500x400")

                ttk.Label(update_win, text=f"A new version (v{latest}) is available!").pack(pady=10)
                text = Text(update_win, wrap="word", height=15, bg="#f4f4f4")
                text.insert(END, changelog)
                text.config(state=DISABLED)
                text.pack(padx=10, pady=5, fill=BOTH, expand=True)

                btn_frame = ttk.Frame(update_win)
                btn_frame.pack(pady=10)
                ttk.Button(btn_frame, text="Download and Launch", command=download_update).pack(side=LEFT, padx=5)
                ttk.Button(btn_frame, text="Ignore this version", command=ignore_future).pack(side=LEFT, padx=5)
                ttk.Button(btn_frame, text="Close", command=update_win.destroy).pack(side=LEFT, padx=5)

            elif current_parts > latest_parts:
                if not auto:
                    messagebox.showinfo("You're Ahead!", f"You're running a newer version (v{__version__}) than v{latest}.")
            else:
                if not auto:
                    messagebox.showinfo("Up to Date", f"You're on the latest version (v{__version__})")

        except Exception as e:
            logging.warning(f"Update check failed: {e}")
            if not auto:
                messagebox.showwarning("Update Check Failed", f"Could not check for updates:\n{e}")


    def open_code_entry(self):
        logging.info("Code Entry Window Opened. Did you expect a clue here?")
        code_win = Toplevel(self.root)
        code_win.title("    ")
        code_win.resizable(False, False)

        ttk.Label(code_win, text="     ").pack(padx=10, pady=(10, 0))
        entry = ttk.Entry(code_win, width=40)
        entry.insert(0, "Remember: ")
        entry.pack(padx=10, pady=10)

        def check_code():
            if entry.get().strip() == "Remember: Just Monika":
                logging.info("Debug Mode Enabled")
                self.config["debug_enabled"] = True
                self.save_config()
                code_win.destroy()
                messagebox.showinfo("Unlocked", "I unlocked some devtools for you, Player~")
                logging.info("Hehe~ You found it~ Good job~!")
                self.show_settings_window()  # Re-open with buttons revealed

        ttk.Button(code_win, text="Submit", command=check_code).pack(pady=(0, 10))

        code_win.update_idletasks()
        code_win.geometry(f"{entry.winfo_reqwidth() + 40}x{entry.winfo_reqheight() + 100}")




    def show_debug_window(self):
        self.debug_window = Toplevel(self.root)
        self.debug_window.title("Debug Log")
        self.debug_window.geometry("600x400")
        self.debug_text = Text(self.debug_window, wrap="word", bg="#1e1e1e", fg="#d4d4d4")
        self.debug_text.pack(fill=BOTH, expand=True)
        self.update_debug_log()

    def update_debug_log(self):
        try:
            with open(LOG_PATH, "r") as log_file:
                content = log_file.read()
            self.debug_text.delete("1.0", END)
            self.debug_text.insert(END, content)
            self.debug_text.see(END)
        except Exception as e:
            self.debug_text.insert(END, f"Error reading log: {e}")
        self.root.after(2000, self.update_debug_log)

    def create_widgets(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(0, 10))

        actions = [
            ("Import Vanilla", self.import_vanilla, "Import original DDLC files"),
            ("Import Mod", self.import_mod, "Add a new mod to the manager"),
            ("View Mods", self.view_mods, "View and rename imported mods"),
            ("Create Profile", self.create_profile, "Create new modded or vanilla profile"),
            ("Launch Profile", self.launch_profile, "Launch selected profile"),
            ("Choose Executable", self.choose_executable, "Select which .exe to run for the selected profile"),
            ("Refresh", self.refresh_profiles, "Refresh profile list"),
            ("Settings", self.show_settings_window, "View settings and options")
        ]



        for i, (text, command, tip) in enumerate(actions):
            btn = ttk.Button(btn_frame, text=text, command=command)
            btn.grid(row=0, column=i, padx=3)
            ToolTip(btn, tip)

        self.tree = ttk.Treeview(
            main_frame,
            columns=("mod", "playtime", "last_played"),
            show="tree headings",
            selectmode="browse"
        )

        self.tree.heading("#0", text="Profile Name", anchor=W)
        self.tree.heading("mod", text="Mod Used", anchor=W)
        self.tree.heading("playtime", text="Playtime", anchor=W)
        self.tree.heading("last_played", text="Last Played", anchor=W)

        self.tree.column("#0", width=200, stretch=False)
        self.tree.column("mod", width=150)
        self.tree.column("playtime", width=100)
        self.tree.column("last_played", width=150)

        scrollbar = ttk.Scrollbar(main_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.status = ttk.Label(self.root, text="Ready", relief=SUNKEN)
        self.status.pack(side=BOTTOM, fill=X)

    def delete_vanilla(self):
        if os.path.exists(PATHS["VANILLA"]):
            logging.info("Delete Vanilla prompt")
            if messagebox.askyesno("Confirm", "Delete imported Vanilla DDLC files?"):
                shutil.rmtree(PATHS["VANILLA"], ignore_errors=True)
                messagebox.showinfo("Success", "Vanilla files deleted.")
                logging.info("Vanila files deleted")

    def delete_mods(self):
        if os.path.exists(PATHS["MODS"]):
            logging.info("Delete Mods prompt")
            if messagebox.askyesno("Confirm", "Delete all imported mods?"):
                shutil.rmtree(PATHS["MODS"], ignore_errors=True)
                os.makedirs(PATHS["MODS"], exist_ok=True)
                messagebox.showinfo("Success", "All mods deleted.")
                logging.info("All Mods deleted")

    def delete_profiles(self):
        if os.path.exists(PATHS["PROFILES"]):
            logging.info("Delete Profiles prompt")
            if messagebox.askyesno("Confirm", "Delete all profiles?"):
                shutil.rmtree(PATHS["PROFILES"], ignore_errors=True)
                os.makedirs(PATHS["PROFILES"], exist_ok=True)
                messagebox.showinfo("Success", "All profiles deleted.")
                logging.info("All Profiles deleted")

    def clear_log(self):
        try:
            with open(LOG_PATH, "w") as log_file:
                log_file.write("")
                logging.info("Log file cleared")
            if self.debug_text.winfo_exists():
                self.debug_text.delete("1.0", END)
        except Exception as e:
            if self.debug_text.winfo_exists():
                self.debug_text.insert(END, f"Error clearing log: {e}")
                logging.error(f"Error clearing log {e}")

    def update_debug_log(self):
        try:
            with open(LOG_PATH, "r") as log_file:
                content = log_file.read()
            self.debug_text.delete("1.0", END)
            if self.debug_text.winfo_exists():
                self.debug_text.insert(END, content)
            if self.debug_text.winfo_exists():
                self.debug_text.see(END)
        except Exception as e:
            if self.debug_text.winfo_exists():
                self.debug_text.insert(END, f"Error reading log: {e}")

        self.root.after(2000, self.update_debug_log)

    def configure_styles(self):
        self.style.theme_use("clam")
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TButton", padding=6)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#0078d7")])

    def init_discord_rpc(self):
        try:
            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()

            self.rpc.update(
                state="Browsing Profiles",
                details="In Launcher",
                large_image="modding_club",
                large_text="Doki Doki Modding Club",
                small_image="in_launcher",
                small_text="idle"
            )
        except Exception as e:
            logging.warning(f"Discord RPC failed to connect: {e}")

    def on_exit(self):
        if self.watchdog:
            self.watchdog.stop()
            self.watchdog.join()
        self.root.destroy()

    def bind_all_widgets_to_stop_timer(self, widget):
        if isinstance(widget, (Button, ttk.Button, ttk.Entry, ttk.Label, ttk.Combobox, ttk.Treeview, ttk.Radiobutton)):
            widget.bind("<Button-1>", self.stop_timer_if_running, add="+")
        for child in widget.winfo_children():
           self.bind_all_widgets_to_stop_timer(child)

    def setup_bindings(self):
        self.tree.bind("<Double-1>", lambda e: self.launch_profile())
        self.tree.bind("<Delete>", lambda e: self.delete_selected_profile())
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Launch", command=self.launch_profile)
        self.context_menu.add_command(label="Rename", command=self.rename_selected_profile)
        self.context_menu.add_command(label="Delete", command=self.delete_selected_profile)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.root.bind("<Control-l>", lambda e: (logging.info("Ctrl+L pressed: Opening debug log"), self.show_debug_window()))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def update_status(self, message):
        logging.info(f"Status update: {message}")
        self.status.config(text=message)
        self.root.update_idletasks()

    def import_vanilla(self):
        logging.info("Begin Vanilla Import")
        path = filedialog.askdirectory(title="Select Vanilla DDLC Folder")
        if path and os.path.exists(os.path.join(path, "DDLC.exe")):
            shutil.rmtree(PATHS["VANILLA"], ignore_errors=True)
            shutil.copytree(path, PATHS["VANILLA"])
            messagebox.showinfo("Success", "Vanilla DDLC imported successfully!")
            logging.info("Vanilla files imported")

    def import_mod(self):
        logging.info("Begin Mod Import")
        path = filedialog.askdirectory(title="Select Mod Folder")
        if path and os.listdir(path):
            mod_name = os.path.basename(path)
            dest = os.path.join(PATHS["MODS"], mod_name)
            logging.info("Importing Mods")

            # Check if the mod folder contains .rpyc or .rpa files in its root
            has_game_files = any(
                file.lower().endswith((".rpyc", ".rpa"))
                for file in os.listdir(path)
            )

            if has_game_files:
                # Create destination /mod_name/game
                game_dest = os.path.join(dest, "game")
                logging.info("Game files in root detected, moving to /game")
                os.makedirs(game_dest, exist_ok=True)
                for item in os.listdir(path):
                    s = os.path.join(path, item)
                    d = os.path.join(game_dest, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
            else:
                shutil.copytree(path, dest, dirs_exist_ok=True)

            messagebox.showinfo("Success", f"Mod '{mod_name}' imported!")
            logging.info(f"Mod {mod_name} Imported successfully")

    def view_mods(self):
        self.mods_window = Toplevel(self.root)
        self.mods_window.title("Imported Mods")
        self.mods_window.geometry("400x300")
        mods = os.listdir(PATHS["MODS"])
        self.mods_tree = ttk.Treeview(self.mods_window, columns=(), show="tree", selectmode="browse")
        self.mods_tree.heading("#0", text="Mod Name", anchor=W)
        for m in mods:
            self.mods_tree.insert("", "end", text=m)
        self.mods_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        btn_frame = ttk.Frame(self.mods_window)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="Rename Mod", command=self.rename_selected_mod).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=self.mods_window.destroy).pack(side=LEFT, padx=5)

    def rename_selected_mod(self):
        selected = self.mods_tree.selection()
        if not selected:
            return
        old_name = self.mods_tree.item(selected[0], "text")
        rename_window = Toplevel(self.root)
        rename_window.title("Rename Mod")
        ttk.Label(rename_window, text="New Mod Name:").pack(padx=10, pady=5)
        new_name_entry = ttk.Entry(rename_window)
        new_name_entry.insert(0, old_name)
        new_name_entry.pack(padx=10, pady=5)
        def apply_rename():
            new_name = new_name_entry.get().strip()
            if not new_name or new_name == old_name:
                return
            old_path = os.path.join(PATHS["MODS"], old_name)
            new_path = os.path.join(PATHS["MODS"], new_name)
            if os.path.exists(new_path):
                messagebox.showerror("Error", "A mod with that name already exists!")
                return
            os.rename(old_path, new_path)
            self.mods_window.destroy()
            self.view_mods()
        ttk.Button(rename_window, text="Rename", command=apply_rename).pack(pady=10)

    def create_profile(self):
        if not os.listdir(PATHS["VANILLA"]):
            messagebox.showwarning("Warning", "Import vanilla DDLC first!")
            return
        logging.info("Beginning Profile Creation")
        mods = ["— Vanilla —"] + os.listdir(PATHS["MODS"])
        self.profile_window = Toplevel(self.root)
        self.profile_window.title("Create Profile")
        ttk.Label(self.profile_window, text="Profile Name:").grid(row=0, column=0, padx=5, pady=5)
        self.profile_entry = ttk.Entry(self.profile_window, width=30)
        self.profile_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.profile_window, text="Select Mod:").grid(row=1, column=0, padx=5, pady=5)
        self.mod_var = StringVar()
        self.mod_menu = ttk.Combobox(self.profile_window, textvariable=self.mod_var, values=mods, state="readonly")
        self.mod_menu.current(0)
        self.mod_menu.grid(row=1, column=1, padx=5, pady=5)
        btn_frame = ttk.Frame(self.profile_window)
        btn_frame.grid(row=2, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Create", command=self.build_profile).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.profile_window.destroy).pack(side=LEFT, padx=5)

    def build_profile(self):
        profile_name = self.profile_entry.get().strip()
        mod = self.mod_var.get()

        if not profile_name.isalnum():
            messagebox.showerror("Error", "Profile names must only contain letters and numbers!")
            logging.warning("Profile name contains invalid characters")
            return
        if not profile_name:
            messagebox.showwarning("Warning", "Enter a profile name!")
            logging.warning("Profile name cannot be empty")
            return
        profile_path = os.path.join(PATHS["PROFILES"], profile_name)
        if os.path.exists(profile_path):
            messagebox.showerror("Error", "Profile name already exists!")
            logging.error("Profile arleady exists")
            return
        shutil.copytree(PATHS["VANILLA"], profile_path)
        if mod != "— Vanilla —":
            shutil.copytree(os.path.join(PATHS["MODS"], mod), profile_path, dirs_exist_ok=True)
        original_exe = os.path.join(profile_path, "DDLC.exe")
        renamed_exe = os.path.join(profile_path, f"{profile_name}.exe")
        if os.path.exists(original_exe):
            os.rename(original_exe, renamed_exe)
        settings = {
            "preferred_exe": f"{profile_name}.exe",
            "mod_name": mod if mod != "— Vanilla —" else "Vanilla",
            "install_date": datetime.now().strftime("%Y-%m-%d"),
            "last_played": None,
            "playtime_seconds": 0
        }
        self.save_profile_settings(profile_path, settings)
        messagebox.showinfo("Success", f"Profile '{profile_name}' created!")
        logging.info(f"Profile {profile_name} created")
        self.profile_window.destroy()
        self.refresh_profiles()

    def choose_executable(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a profile first!")
            return
        profile_name = self.tree.item(selected[0], "text")
        profile_path = os.path.join(PATHS["PROFILES"], profile_name)
        exes = [f for f in os.listdir(profile_path) if f.lower().endswith(".exe")]
        if not exes:
            messagebox.showerror("Error", "No executable found in profile!")
            return
        settings = self.load_profile_settings(profile_path)
        current = settings.get("preferred_exe", exes[0])
        win = Toplevel(self.root)
        win.title(f"Select Executable for '{profile_name}'")
        win.geometry("300x200")
        ttk.Label(win, text="Choose which .exe to run:").pack(padx=10, pady=5)
        exe_var = StringVar(value=current)
        for exe in exes:
            ttk.Radiobutton(win, text=exe, variable=exe_var, value=exe).pack(anchor=W)
        def apply_choice():
            new_exe = exe_var.get()
            settings["preferred_exe"] = new_exe
            self.save_profile_settings(profile_path, settings)
            win.destroy()
            messagebox.showinfo("Info", f"Preferred executable set to '{new_exe}'")
        ttk.Button(win, text="OK", command=apply_choice).pack(pady=10)

    def launch_profile(self):
        selected = self.tree.selection()
        logging.info("Beginning Launch Profile")
        if not selected:
            messagebox.showwarning("Warning", "Select a profile first!")
            logging.info("No profile selected, stopping.")
            return

        profile_name = self.tree.item(selected[0], "text")
        profile_path = os.path.join(PATHS["PROFILES"], profile_name)
        settings = self.load_profile_settings(profile_path)
        exe_name = settings.get("preferred_exe", "DDLC.exe")
        exe_path = os.path.join(profile_path, exe_name)

        if not os.path.exists(exe_path):
            messagebox.showerror("Error", "Executable not found!")
            logging.info("Executable not found, stopping.")
            return

        renpy_save_path = get_ddlc_save_path()
        profile_save_dir = os.path.join(profile_path, "save")

        if renpy_save_path and os.path.exists(renpy_save_path):
            os.makedirs(profile_save_dir, exist_ok=True)
            shutil.rmtree(profile_save_dir, ignore_errors=True)
            shutil.copytree(renpy_save_path, profile_save_dir)

        if renpy_save_path and os.path.exists(renpy_save_path):
            shutil.rmtree(renpy_save_path, ignore_errors=True)
        if os.path.exists(profile_save_dir):
            shutil.copytree(profile_save_dir, renpy_save_path or PATHS["APPDATA"], dirs_exist_ok=True)

        mod_name = settings.get("mod_name", "DDLC")
        start_time = int(time.time())

        process = subprocess.Popen(
            f'start "" "{exe_path}"',
            cwd=profile_path,
            shell=True
        )
        logging.info("Game attempted launch.")


    # Track session time until the user clicks anything
        def end_session(elapsed):
            logging.info("End Session logic listening")
            settings["playtime_seconds"] += elapsed
            settings["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_profile_settings(profile_path, settings)
            self.refresh_profiles()
            self.update_status(f"Last session duration: {self.format_time(elapsed)}")
            logging.info(f"Game session ended. Elapsed: {elapsed} seconds")

            if renpy_save_path and os.path.exists(renpy_save_path):
                shutil.rmtree(profile_save_dir, ignore_errors=True)
                shutil.copytree(renpy_save_path, profile_save_dir)

        self.session_timer = SessionTimer(self.rpc, profile_name, mod_name, start_time, end_session)

        # Hook into any button click to stop the session
        def on_user_action(_):
            if hasattr(self, 'session_timer') and self.session_timer.running:
                self.session_timer.stop()
                logging.info("User interaction recorded")

        for widget in self.root.winfo_children():
            widget.bind("<Button-1>", on_user_action, add="+")

        process.wait()
        # Bind interaction handler to all widgets to end timer
        self.bind_all_widgets_to_stop_timer(self.root)



    @staticmethod
    def backup_appdata(profile):
        backup_path = os.path.join(PATHS["BACKUPS"], profile)
        renpy_path = get_ddlc_save_path()
        shutil.rmtree(backup_path, ignore_errors=True)
        if renpy_path:
            shutil.copytree(renpy_path, backup_path)


    def refresh_profiles(self):
        self.tree.delete(*self.tree.get_children())
        profiles = os.listdir(PATHS["PROFILES"])
        for profile in profiles:
            path = os.path.join(PATHS["PROFILES"], profile)
            settings = self.load_profile_settings(path)
            self.tree.insert("", "end", text=profile,
                             values=(settings.get("mod_name", "Unknown"),
                                     self.format_time(settings.get("playtime_seconds", 0)),
                                     settings.get("last_played", "Never")))

    def delete_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            return
        profile_name = self.tree.item(selected[0], "text")
        if messagebox.askyesno("Confirm", f"Delete profile '{profile_name}'?"):
            shutil.rmtree(os.path.join(PATHS["PROFILES"], profile_name), ignore_errors=True)
            shutil.rmtree(os.path.join(PATHS["BACKUPS"], profile_name), ignore_errors=True)
            self.refresh_profiles()

    def rename_selected_profile(self):
        selected = self.tree.selection()
        if not selected:
            return
        old_name = self.tree.item(selected[0], "text")
        rename_window = Toplevel(self.root)
        rename_window.title("Rename Profile")
        ttk.Label(rename_window, text="New Profile Name:").pack(padx=10, pady=5)
        new_name_entry = ttk.Entry(rename_window)
        new_name_entry.insert(0, old_name)
        new_name_entry.pack(padx=10, pady=5)
        def apply_rename():
            new_name = new_name_entry.get().strip()
            if not new_name or new_name == old_name:
                return
            if os.path.exists(os.path.join(PATHS["PROFILES"], new_name)):
                messagebox.showerror("Error", "Profile name already exists!")
                return
            os.rename(os.path.join(PATHS["PROFILES"], old_name),
                      os.path.join(PATHS["PROFILES"], new_name))
            self.refresh_profiles()
            rename_window.destroy()
        ttk.Button(rename_window, text="Rename", command=apply_rename).pack(pady=10)
    
    def stop_timer_if_running(self, event=None):
        if hasattr(self, 'session_timer') and self.session_timer.running:
            self.session_timer.stop()


    @staticmethod
    def format_time(seconds):
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hrs:02}:{mins:02}:{secs:02}"

    @staticmethod
    def backup_appdata(profile):
        backup_path = os.path.join(PATHS["BACKUPS"], profile)
        shutil.rmtree(backup_path, ignore_errors=True)
        if os.path.exists(PATHS["APPDATA"]):
            shutil.copytree(PATHS["APPDATA"], backup_path)

    def on_exit(self):
        logging.info("Application closed. Bye User~")
        self.root.destroy()

if __name__ == "__main__":
    root = Tk()
    app = DDLCManager(root)
    root.mainloop()
