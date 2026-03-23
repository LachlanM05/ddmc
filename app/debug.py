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
        fake_base = project_root / "fakeroot" / "home" / "fakeuser"
        
    fake_base.mkdir(parents=True, exist_ok=True)
    
    # Inject the fake directory into the environment BEFORE importing core logic
    os.environ["DDLC_MANAGER_DEBUG_DIR"] = str(fake_base)
    print(f"[DEBUG] Sandboxed filesystem active at: {fake_base}")
    
    return fake_base

# CRITICAL: This must run before importing anything from 'core' 
# so the environment variable is set in time.
setup_fake_root()

from core.mod_logic import ProfileManager
from core.paths import ensure_directories

def main():
    # This line defines 'parser'.
    parser = argparse.ArgumentParser(description="Debug CLI for DDLC Mod Manager")
    
    # Define the possible arguments
    parser.add_argument("--vanilla", type=str, help="Path to a pristine vanilla DDLC folder to import")
    parser.add_argument("--mod", type=str, help="Path to a zipped mod file to install")
    parser.add_argument("--profile", type=str, default="testing123", help="Name of the test profile")
    parser.add_argument("--launch", action="store_true", help="Launch the specified profile after processing")
    
    args = parser.parse_args()
    
    # Initialize our fake directories inside fakeroot
    ensure_directories()
    
    if args.vanilla:
        print(f"[DEBUG] Importing vanilla DDLC from: {args.vanilla}")
        try:
            ProfileManager.import_vanilla(args.vanilla)
            print("[DEBUG] Vanilla import successful.")
        except Exception as e:
            print(f"[ERROR] {e}")
            
    if args.mod:
        print(f"[DEBUG] Using profile: '{args.profile}'")
        try:
            # Create the profile if it doesn't exist
            try:
                ProfileManager.create_profile(args.profile)
                print(f"[DEBUG] Profile '{args.profile}' created.")
            except FileExistsError:
                print(f"[DEBUG] Profile '{args.profile}' already exists, skipping creation.")

            print(f"[DEBUG] Extracting mod from '{args.mod}' into profile...")
            ProfileManager.install_zipped_mod(args.profile, args.mod)
            print("[DEBUG] Mod installation complete.")
        except Exception as e:
            print(f"[ERROR] {e}")

    if args.launch:
        print(f"[DEBUG] Attempting to launch profile: '{args.profile}'")
        try:
            ProfileManager.launch_profile(args.profile)
            print("[DEBUG] Launch command sent successfully.")
        except Exception as e:
            print(f"[ERROR] {e}")
            
    # If no arguments provided, show the help menu
    if not any([args.vanilla, args.mod, args.launch]):
        parser.print_help()

if __name__ == "__main__":
    main()