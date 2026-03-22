import os
from pathlib import Path

# Check if we are running in a sandboxed debug environment
DEBUG_BASE = os.environ.get("DDLC_MANAGER_DEBUG_DIR")

if DEBUG_BASE:
    BASE_DATA_DIR = Path(DEBUG_BASE) / ".ddlc_mod_manager"
else:
    BASE_DATA_DIR = Path.home() / ".ddlc_mod_manager"

VANILLA_DIR = BASE_DATA_DIR / "vanilla"
PROFILES_DIR = BASE_DATA_DIR / "profiles"
MODS_DIR = BASE_DATA_DIR / "imported_mods"

def ensure_directories():
    """Creates the necessary folder structure if it doesn't exist."""
    VANILLA_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    MODS_DIR.mkdir(parents=True, exist_ok=True)