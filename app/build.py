# build.py
import os
import shutil
import subprocess
import platform
from pathlib import Path

def clean_old_builds():
    """Removes old build/ and dist/ folders to ensure a clean compile."""
    print("[BUILD] Cleaning old build directories...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # Clean up old spec files if they exist
    for file in Path(".").glob("*.spec"):
        file.unlink()

def build_executable():
    """Runs PyInstaller with the optimal arguments for a PyQt6 app."""
    print("[BUILD] Starting PyInstaller...")
    
    # Define our PyInstaller arguments
    args = [
        "pyinstaller",
        "--name=DDLC_Mod_Manager",  # The name of the final executable
        "--windowed",               # Hides the terminal window (GUI only)
        "--noconfirm",              # Automatically overwrite output folder
        "--clean",                  # Clean PyInstaller cache
        
        # We use --onedir instead of --onefile. 
        # --onedir is MUCH faster to launch for PyQt6 apps and easier to debug.
        "--onedir",                 
        
        "main.py"                   # Our entry point
    ]
    
    # Run the command
    subprocess.run(args, check=True)
    
    print("\n[BUILD] Compilation complete!")
    
    os_name = platform.system()
    if os_name == "Linux":
        print("[BUILD] Your executable is located at: dist/DDLC_Mod_Manager/DDLC_Mod_Manager")
    elif os_name == "Windows":
        print("[BUILD] Your executable is located at: dist\\DDLC_Mod_Manager\\DDLC_Mod_Manager.exe")

if __name__ == "__main__":
    clean_old_builds()
    build_executable()