import time
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

class GameMonitorWorker(QThread):
    finished_playing = pyqtSignal(str, float)

    def __init__(self, profile_name, process):
        super().__init__()
        self.profile_name = profile_name
        self.process = process

    def run(self):
        print(f"\n[TRACKER] === Session Started for '{self.profile_name}' ===")
        start_time = time.time()
        initial_pid = self.process.pid
        print(f"[TRACKER] Initial subprocess PID from Popen: {initial_pid}")

        try:
            main_proc = psutil.Process(initial_pid)
            print(f"[TRACKER] Successfully hooked into PID {initial_pid} ({main_proc.name()})")

            # Give the game engine 1 second to spawn all its worker threads/children
            time.sleep(1)

            # Grab all child processes. If DDLC.sh forks the real game, it will be here.
            children = main_proc.children(recursive=True)
            print(f"[TRACKER] Found {len(children)} child processes on startup:")
            for child in children:
                print(f"  -> Child PID: {child.pid} ({child.name()})")

            # We pool the parent and all children. As long as ANY of these exist, the game is running.
            procs_to_track = [main_proc] + children

            is_playing = True
            while is_playing:
                time.sleep(2) # Heartbeat check every 2 seconds
                
                any_alive = False
                for p in procs_to_track:
                    try:
                        # Check if process is running and NOT a zombie
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            any_alive = True
                            break
                    except psutil.NoSuchProcess:
                        continue # Process died, move to the next one in the list

                if not any_alive:
                    print("[TRACKER] All tracked processes have terminated.")
                    is_playing = False

        except psutil.NoSuchProcess:
            print(f"[TRACKER] ERROR: Initial PID {initial_pid} died instantly before psutil could hook it.")
        except Exception as e:
            print(f"[TRACKER] FATAL ERROR during monitoring loop: {e}")

        end_time = time.time()
        session_time = end_time - start_time
        
        print(f"[TRACKER] Session ended. Raw calculated time: {session_time:.2f} seconds.")
        print(f"[TRACKER] =============================================\n")

        self.finished_playing.emit(self.profile_name, session_time)