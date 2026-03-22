import argparse
import os
import platform
from pathlib import Path

def setup_fake_root():
    """Sets up a sandboxed directory structure based on the current OS."""
    project_root = Path(__file__).parent.resolve()
    os_name = platform.system()
    
    if os_name == "Windows":
        fake_base = project_root / "fakeroot" / "C" / "Users" / "fakeuser"
    else:
        # Handles Linux and macOS structures
        fake_base = project_root / "fakeroot" / "home" / "fakeuser"
        
    fake_base.mkdir(parents=True, exist_ok=True)
    
    # Inject the fake directory into the environment BEFORE importing core logic
    os.environ["DDLC_MANAGER_DEBUG_DIR"] = str(fake_base)
    print(f"[DEBUG] Sandboxed filesystem active at: {fake_base}")
    
    return fake_base

# CRITICAL: This must run before importing anything from 'core'
setup_fake_root()

from core.mod_logic import ProfileManager
from core.paths import ensure_directories

def main():
    parser = argparse.ArgumentParser(description="Debug CLI for DDLC Mod Manager")
    parser.add_argument("--vanilla", type=str, help="Path to a pristine vanilla DDLC folder to import")
    parser.add_argument("--mod", type=str, help="Path to a zipped mod file to install")
    parser.add_argument("--profile", type=str, default="test_profile", help="Name of the test profile (default: test_profile)")
    
    args = parser.parse_args()
    
    # Initialize our fake directories
    ensure_directories()
    
    if args.vanilla:
        print(f"[DEBUG] Importing vanilla DDLC from: {args.vanilla}")
        try:
            ProfileManager.import_vanilla(args.vanilla)
            print("[DEBUG] Vanilla import successful.")
        except Exception as e:
            print(f"[ERROR] {e}")
            
    if args.mod:
        print(f"[DEBUG] Creating profile: '{args.profile}'")
        try:
            ProfileManager.create_profile(args.profile)
            print(f"[DEBUG] Extracting mod from '{args.mod}' into profile...")
            ProfileManager.install_zipped_mod(args.profile, args.mod)
            print("[DEBUG] Mod installation complete.")
        except Exception as e:
            print(f"[ERROR] {e}")
            
    if not args.vanilla and not args.mod:
        parser.print_help()

if __name__ == "__main__":
    main()