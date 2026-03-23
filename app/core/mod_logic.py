# core/mod_logic.py
import os
import stat
import shutil
import zipfile
import subprocess
import platform
import json
import time
from datetime import datetime
from pathlib import Path
from .paths import MODS_DIR, VANILLA_DIR, PROFILES_DIR


class ProfileManager:
    @staticmethod
    def import_vanilla(source_path: str | Path) -> bool:
        """Copies a clean DDLC installation into our secure vanilla storage."""
        source = Path(source_path)
        
        has_exe = (source / "DDLC.exe").exists()
        has_sh = (source / "DDLC.sh").exists()
        
        if not has_exe and not has_sh:
            raise ValueError("This does not look like a valid DDLC directory. Missing DDLC.exe or DDLC.sh.")
        
        # Clear existing vanilla if re-importing, then copy
        if VANILLA_DIR.exists():
            shutil.rmtree(VANILLA_DIR)
        shutil.copytree(source, VANILLA_DIR)
        return True

    @staticmethod
    def create_profile(profile_name: str, mod_name: str = "Vanilla Base") -> Path:
        """Clones the vanilla game into a new profile directory."""
        profile_path = PROFILES_DIR / profile_name
        if profile_path.exists():
            raise FileExistsError(f"A profile named '{profile_name}' already exists.")
        
        if not VANILLA_DIR.exists():
            raise FileNotFoundError("Vanilla DDLC has not been imported yet.")

        # Clone the vanilla game
        shutil.copytree(VANILLA_DIR, profile_path)
        
        # Inject Save Data Isolation Script
        isolation_script = profile_path / "game" / "zz_save_isolation.rpy"
        script_content = (
            "python early:\n"
            "    import os\n"
            "    config.savedir = os.path.join(config.basedir, 'save_data')\n"
        )
        isolation_script.write_text(script_content)
        
        # --- FIXED: Use the passed mod_name ---
        ProfileManager.init_profile_settings(profile_name, mod_name)
        
        return profile_path

    @staticmethod
    def install_zipped_mod(profile_name: str, zip_path: str | Path):
        """Extracts a zipped mod directly into the target profile."""
        profile_path = PROFILES_DIR / profile_name
        game_folder = profile_path / "game"
        
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Extract to a temporary folder inside the profile first
            temp_extract = profile_path / "_temp_mod_extract"
            zip_ref.extractall(temp_extract)

            # DDLC Mod Quirk: Move .rpa, .rpy, .rpyc files to the game/ folder
            for item in temp_extract.rglob("*"):
                if item.is_file():
                    if item.suffix in [".rpa", ".rpy", ".rpyc"]:
                        rel_path = item.relative_to(temp_extract)
                        target = game_folder / rel_path.name
                        
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(target))

            # Cleanup the temp extraction folder
            shutil.rmtree(temp_extract)

    @staticmethod
    def launch_profile(profile_name: str):
        """Launches the specified profile and sandboxes its save data."""
        profile_path = PROFILES_DIR / profile_name
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")

        # 1. Define where this specific profile should keep its saves
        save_dir = profile_path / "save_data"
        save_dir.mkdir(parents=True, exist_ok=True)

        # 2. OS routing for the correct executable
        os_name = platform.system()
        if os_name == "Windows":
            target_executable = profile_path / "DDLC.exe"
        else:
            target_executable = profile_path / "DDLC.sh"
            
            # Ensure Linux execution privileges
            if target_executable.exists():
                st = os.stat(target_executable)
                os.chmod(target_executable, st.st_mode | stat.S_IEXEC)

        if not target_executable.exists():
            raise FileNotFoundError(f"Executable not found at '{target_executable}'")

        # 3. Create a custom environment dictionary for the game
        # We copy the current system environment so we don't break anything else
        custom_env = os.environ.copy()
        
        # Inject the Ren'Py specific variable. 
        # The game will now completely ignore ~/.renpy or %APPDATA%\RenPy
        custom_env["RENPY_PATH_TO_SAVES"] = str(save_dir)

        print(f"[INFO] Launching {target_executable} with isolated saves at {save_dir}...")
        
        # 4. Launch the process with the injected environment
        process = subprocess.Popen(
            [str(target_executable)],
            cwd=str(profile_path),
            env=custom_env,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return process

    @staticmethod
    def import_mod_globally(zip_path: str | Path) -> Path:
        """Copies a mod zip into the global manager storage."""
        source = Path(zip_path)
        if not source.exists() or source.suffix.lower() != '.zip':
            raise ValueError("Invalid file. Must be a .zip archive.")
            
        target = MODS_DIR / source.name
        if target.exists():
            raise FileExistsError(f"Mod '{source.name}' is already imported.")
            
        shutil.copy2(source, target)
        return target

    @staticmethod
    def delete_mod(mod_filename: str):
        """Removes a mod from the global storage."""
        target = MODS_DIR / mod_filename
        if target.exists():
            target.unlink() # Deletes the file

    @staticmethod
    def rename_mod(old_name: str, new_name: str):
        """Renames a globally stored mod zip."""
        if not new_name.lower().endswith('.zip'):
            new_name += '.zip'
            
        old_path = MODS_DIR / old_name
        new_path = MODS_DIR / new_name
        
        if new_path.exists():
            raise FileExistsError(f"A mod named '{new_name}' already exists.")
        if old_path.exists():
            old_path.rename(new_path)

    @staticmethod
    def delete_profile(profile_name: str):
        """Completely removes a profile and its isolated saves."""
        profile_path = PROFILES_DIR / profile_name
        if profile_path.exists():
            shutil.rmtree(profile_path)

    @staticmethod
    def rename_profile(old_name: str, new_name: str):
        """Renames a profile directory."""
        old_path = PROFILES_DIR / old_name
        new_path = PROFILES_DIR / new_name
        
        if new_path.exists():
            raise FileExistsError(f"Profile '{new_name}' already exists.")
        if old_path.exists():
            old_path.rename(new_path)

    @staticmethod
    def export_profile(profile_name: str, export_destination: str | Path):
        """Zips up an entire profile (game + saves) for backup."""
        profile_path = PROFILES_DIR / profile_name
        dest_path = Path(export_destination)
        
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_name}' does not exist.")
            
        # Ensure the destination ends in .zip
        if dest_path.suffix.lower() != '.zip':
            dest_path = dest_path.with_suffix('.zip')
            
        # shutil.make_archive expects the destination without the extension
        archive_base = str(dest_path.with_suffix(''))
        shutil.make_archive(archive_base, 'zip', root_dir=profile_path)

    @staticmethod
    def get_available_mods() -> list[str]:
        """Returns a list of all globally imported mods."""
        if not MODS_DIR.exists():
            return []
        return [f.name for f in MODS_DIR.glob('*.zip')]
    
    # read settings for a profile, which includes mod name, playtime, and last played timestamp
    @staticmethod
    def _get_settings_path(profile_name: str) -> Path:
        """Helper method to locate the settings file for a profile."""
        return PROFILES_DIR / profile_name / "settings.json"
    
    @staticmethod
    def get_profile_settings(profile_name: str) -> dict:
        """Reads the settings file for a profile."""
        settings_path = ProfileManager._get_settings_path(profile_name)
        if settings_path.exists():
            with open(settings_path, "r") as f:
                return json.load(f)
        return {"mod_name": "Unknown", "playtime_seconds": 0.0, "last_played": "Never"}

    @staticmethod
    def init_profile_settings(profile_name: str, mod_name: str):
        """Creates the initial tracking file for a new profile."""
        settings = {
            "mod_name": mod_name,
            "playtime_seconds": 0.0,
            "last_played": None
        }
        with open(ProfileManager._get_settings_path(profile_name), "w") as f:
            json.dump(settings, f, indent=4)

    @staticmethod
    def add_playtime(profile_name: str, session_seconds: float):
        """Adds a session's time to the profile's total with deep logging."""
        settings_path = ProfileManager._get_settings_path(profile_name)
        
        print(f"[DB] Attempting to save {session_seconds:.2f}s to profile '{profile_name}'")
        
        if settings_path.exists():
            with open(settings_path, "r") as f:
                settings = json.load(f)
                
            old_time = settings.get("playtime_seconds", 0.0)
            print(f"[DB] Current stored time: {old_time:.2f}s")
            
            settings["playtime_seconds"] = old_time + session_seconds
            settings["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
                
            print(f"[DB] SUCCESS: Time updated to {settings['playtime_seconds']:.2f}s")
        else:
            print(f"[DB] ERROR: Could not find settings file at {settings_path}")