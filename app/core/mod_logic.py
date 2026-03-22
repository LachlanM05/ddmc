# core/mod_logic.py
import shutil
import zipfile
from pathlib import Path
from .paths import VANILLA_DIR, PROFILES_DIR

class ProfileManager:
    @staticmethod
    def import_vanilla(source_path: str | Path) -> bool:
        """Copies a clean DDLC installation into our secure vanilla storage."""
        source = Path(source_path)
        if not (source / "DDLC.exe").exists() and not (source / "DDLC.sh").exists():
            raise ValueError("This does not look like a valid DDLC directory.")
        
        # Clear existing vanilla if re-importing, then copy
        if VANILLA_DIR.exists():
            shutil.rmtree(VANILLA_DIR)
        shutil.copytree(source, VANILLA_DIR)
        return True

    @staticmethod
    def create_profile(profile_name: str) -> Path:
        """Clones the vanilla game into a new profile directory."""
        profile_path = PROFILES_DIR / profile_name
        if profile_path.exists():
            raise FileExistsError(f"A profile named {profile_name} already exists.")
        
        if not VANILLA_DIR.exists():
            raise FileNotFoundError("Vanilla DDLC has not been imported yet.")

        shutil.copytree(VANILLA_DIR, profile_path)
        return profile_path

    @staticmethod
    def install_zipped_mod(profile_name: str, zip_path: str | Path):
        """Extracts a zipped mod directly into the target profile."""
        profile_path = PROFILES_DIR / profile_name
        game_folder = profile_path / "game"
        
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile {profile_name} does not exist.")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to a temporary folder inside the profile first
            temp_extract = profile_path / "_temp_mod_extract"
            zip_ref.extractall(temp_extract)

            # DDLC Mod Quirk: If files are dumped in the root, move them to 'game/'
            for item in temp_extract.rglob('*'):
                if item.is_file():
                    # If it's an engine file or script, it usually belongs in the game folder
                    if item.suffix in ['.rpa', '.rpy', '.rpyc']:
                        # Calculate relative path to maintain folder structures from the zip
                        rel_path = item.relative_to(temp_extract)
                        target = game_folder / rel_path.name
                        
                        # Ensure target subdirectory exists, then move
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(target))

            # Cleanup the temp extraction folder
            shutil.rmtree(temp_extract)