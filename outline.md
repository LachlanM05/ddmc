

This outline is completely written with AI. As me personally, I have no idea what the hell is going on in this one insurmountable python file.






The code is self-contained in a single Python file (ddlc_manager.py), making it relatively straightforward to understand and rebuild. It's built for Windows (evident from paths like `%APPDATA%` and `.exe` handling), but the logic could be adapted for cross-platform use. The project appears to be a personal tool by LachlanM05, with version checking and update downloads from a custom server.

Since you're planning to rebuild it (possibly with PyQt6, assuming that's what "Pqty6" refers to—a popular Python GUI framework for more modern, customizable interfaces), I'll provide a comprehensive breakdown below. This includes the core functionality, architecture, dependencies, and any quirks or edge cases. The rebuild could focus on porting the GUI from Tkinter to PyQt6 for better styling and performance, while keeping the backend logic intact.

#### 1. **Overview and Purpose**
   - **What it does**: DDLC Mod Manager helps users avoid the hassle of manually copying files, managing save data, and dealing with mod conflicts. DDLC mods often modify game files (e.g., `.rpyc` scripts or `.rpa` archives), and running multiple mods can corrupt saves or the game. This tool creates "profiles" as isolated copies of the game, applies mods on top, and handles Ren'Py save folder backups/restores automatically.
   - **Target Audience**: DDLC modding enthusiasts who want a user-friendly way to switch between mods without technical setup. It includes a "secret" debug mode (unlocked with a specific code) for developers or power users.
   - **Key Philosophy**: The app emphasizes safety (e.g., backups, validation) and simplicity. It logs everything for debugging and checks for updates on launch.
   - **Version and Updates**: Current version is 1.1.3. It fetches the latest version and changelog from `https://lachlanm05.com/ddmc_r/latest_version.txt` and downloads updates from `https://lachlanm05.com/ddmc_r/ddlc_manager.exe`. Updates are applied by downloading a new `.exe`, renaming the old one, and launching the new version with a cleanup script.

#### 2. **Main Features**
   - **Import Vanilla DDLC**: Users select the original DDLC folder (must contain `DDLC.exe`) and copy it to an internal "vanilla" directory.
   - **Import Mods**: Users select mod folders. The app detects if mod files (`.rpyc`, `.rpa`) are in the root and moves them to a `game/` subfolder for proper Ren'Py structure. Mods are stored in a "mods" directory.
   - **Create Profiles**: Combines vanilla files with a selected mod (or none for vanilla-only). Each profile is a full copy of the game, with settings like preferred executable and Ren'Py save folder.
   - **Launch Profiles**: Launches the profile's executable, tracks playtime, updates Discord RPC, and manages save data. On launch, it backs up the current Ren'Py saves, restores profile-specific saves, and re-backs up after closing.
   - **Profile Management**: View profiles in a tree view (name, mod used, playtime, last played). Edit settings (e.g., change executable or save folder), rename, or delete profiles.
   - **Mod Management**: View imported mods, rename them.
   - **Save Data Handling**: Uses Ren'Py's save folder (typically `%APPDATA%\RenPy\<game_folder>`). Profiles have custom save folders to isolate saves. Backups are stored in an "appdata_backups" directory.
   - **Playtime Tracking**: Tracks total playtime per profile and globally. Uses a background timer that stops on user interaction with the app.
   - **Discord Rich Presence**: Integrates with Discord to show status (e.g., "Playing <mod>", "In Launcher"). Requires a Discord app with client ID `1371433500745531472`.
   - **Settings and Options**:
     - Dark/light mode toggle.
     - Auto-update toggle.
     - Delete options for vanilla, mods, or profiles.
     - Debug mode (unlocked with code "Remember: Just Monika") adds advanced tools like opening folders, viewing logs, wiping config, or force-quitting.
   - **Logging and Debugging**: Logs to `ddlc_manager.log` in `%APPDATA%\DDLCModManager`. Includes a live debug window and session info panel.
   - **Update Checking**: Automatic on launch (unless disabled). Manual check available. Downloads and applies updates seamlessly.
   - **Tooltips and UI Polish**: Buttons have hover tooltips. The UI is responsive, with a status bar and context menus (right-click on profiles).

#### 3. **Architecture and Code Structure**
   - **Entry Point**: The script runs `if __name__ == "__main__"`, creating a Tkinter root window and instantiating `DDLCManager`.
   - **Main Class: `DDLCManager`**:
     - **Initialization (`__init__`)**: Sets up the window, loads config, enables dark mode, initializes Discord RPC, creates widgets, and starts update checks. It also attempts to delete old `.exe` files post-update.
     - **Config Management**: Stores settings in `%APPDATA%\DDLCModManager\config.txt` (plain text, key=value format). Includes debug mode, dark mode, ignored updates, old exe path, etc.
     - **Profile Settings**: Each profile has a `settings.json` with mod name, executable, install date, playtime, last played, and Ren'Py folder.
     - **Key Methods**:
       - `create_widgets()`: Builds the main UI (buttons, tree view for profiles).
       - `import_vanilla()`, `import_mod()`: Handle file copying with validation.
       - `create_profile()`, `build_profile()`: Create new profiles with mod selection.
       - `launch_profile()`: Core launch logic, including save management and timer start.
       - `refresh_profiles()`: Updates the profile tree view.
       - `check_for_updates()`: Fetches version info, shows changelog, downloads updates.
       - `show_settings_window()`: Settings UI, including debug tools if unlocked.
       - `init_discord_rpc()`: Sets up pypresence for Discord integration.
       - `SessionTimer`: A separate class for playtime tracking and RPC updates. Runs in a thread, stops on user interaction.
     - **UI Components**: Uses ttk for themed widgets. Treeview for profiles, buttons for actions, toplevel windows for dialogs.
     - **Event Handling**: Bindings for double-click launch, right-click menu, keyboard shortcuts (Ctrl+L for debug log).
   - **Utility Classes/Functions**:
     - `ToolTip`: Custom tooltip class for hover help.
     - `get_ddlc_save_path()`: Finds the DDLC save folder in Ren'Py.
     - Static methods like `format_time()` for playtime display.
   - **Paths and Constants**:
     - All data stored in `%APPDATA%\DDLCModManager` (vanilla, mods, profiles, backups, config, log).
     - Constants for URLs, Discord ID, etc.
   - **Threading**: Uses threads for background tasks like deleting old exes, update downloads, and the session timer.
   - **Error Handling**: Basic try-except blocks, logging warnings/errors. Uses messagebox for user alerts.
   - **Security/Validation**: Checks for valid profile names (alphanumeric + spaces/underscores/dashes), ensures executables exist, validates mod imports.

#### 4. **Dependencies and Environment**
   - **Python Libraries**:
     - `tkinter` and `tkinter.ttk`: For GUI (built-in, no install needed).
     - `pypresence`: For Discord RPC (install via pip: `pip install pypresence`).
     - `psutil`: For process monitoring (used in session tracking; `pip install psutil`).
     - `ctypes`, `sys`, `webbrowser`, `urllib.request`: Built-in for system interactions.
     - `os`, `shutil`, `json`, `logging`, `time`, `datetime`, `threading`: All built-in.
   - **External Requirements**:
     - Windows-specific (uses `os.startfile`, shell commands like `start ""`).
     - Ren'Py game engine (DDLC runs on it; the app assumes Ren'Py save structure).
     - Internet for updates (optional, can be disabled).
   - **Build/Packaging**: There's a ddlc_manager.spec file, suggesting it's packaged with PyInstaller for distribution as an `.exe`.

#### 5. **File Structure (Based on Workspace)**
   - ddmc (project root):
     - ddlc_manager.py: Main script (~1000+ lines).
     - ddlc_manager.spec: PyInstaller spec for building the executable.
     - LICENSE: Presumably open-source license.
     - README.md: Likely documentation (not provided, but typical for such projects).
   - **Runtime Directories** (created in `%APPDATA%\DDLCModManager`):
     - `vanilla/`: Copied vanilla DDLC files.
     - `mods/`: Imported mod folders.
     - `profiles/`: Profile directories (each a full game copy).
     - `appdata_backups/`: Save data backups per profile.
     - `config.txt`: Settings.
     - `ddlc_manager.log`: Logs.

#### 6. **Potential Issues, Quirks, and Rebuild Considerations**
   - **Windows-Only**: Heavy reliance on Windows paths and commands. For cross-platform, abstract paths and use subprocess more carefully.
   - **Save Management Complexity**: The backup/restore logic is intricate to prevent save corruption. Test thoroughly—DDLC saves are JSON-based in Ren'Py folders.
   - **Update Mechanism**: Involves downloading executables and using batch scripts for cleanup. Secure (uses HTTPS), but could be improved with checksums.
   - **Debug Mode**: Easter egg-style; the code is hardcoded. In a rebuild, make it a proper dev flag.
   - **Performance**: Tkinter is lightweight but dated. PyQt6 would allow modern styling, better theming, and more widgets (e.g., QTreeView instead of Treeview).
   - **Threading and Timers**: The session timer stops on any UI interaction, which might feel intrusive. Could refine with better event filtering.
   - **Logging**: Prunes logs over 200MB, but no rotation. Uses basic logging; could upgrade to a library like loguru.
   - **Edge Cases**: Handles mod files in root by moving to `game/`. Validates executables and profile names. Assumes Ren'Py structure.
   - **Rebuild Tips**: 
     - Port GUI to PyQt6: Replace Tkinter widgets with Qt equivalents (e.g., QMainWindow, QTreeWidget, QDialogs).
     - Keep core logic: Import, profile creation, launch, and save handling are portable.
     - Add tests: The code lacks unit tests; add them for reliability.
     - Modernize: Use pathlib for paths, dataclasses for settings, and async for updates if needed.
     - Security: Avoid shell=True in subprocess; use lists for commands.