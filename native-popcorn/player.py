import subprocess
import os
import threading
import re

# Global reference to the active streaming process
active_process = None

def stop_player():
    """Kill the active peerflix server if it is running."""
    global active_process
    if active_process:
        print("Stopping background peerflix server...")
        try:
            active_process.terminate()
            active_process.wait(timeout=2)
        except Exception:
            try:
                active_process.kill()
            except Exception:
                pass
        active_process = None

def get_peerflix_bin(progress_callback=None):
    peerflix_dir = os.path.expanduser("~/.local/share/peerflix_app")
    peerflix_app_js = os.path.join(peerflix_dir, "node_modules", "peerflix", "app.js")
    
    if os.path.exists(peerflix_app_js):
        try:
            # Basic sanity check
            subprocess.run(["node", "--check", peerflix_app_js], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError:
            print("Corrupted peerflix installation detected. Reinstalling...")
            import shutil
            shutil.rmtree(peerflix_dir, ignore_errors=True)
            
    if not os.path.exists(peerflix_app_js):
        if progress_callback:
            import gi
            from gi.repository import GLib
            GLib.idle_add(lambda: progress_callback("Installing Stream Engine (one-time)..."))
        print("Peerflix not found. Installing locally for faster startups...")
        os.makedirs(peerflix_dir, exist_ok=True)
        try:
            subprocess.run(["npm", "install", "--prefix", peerflix_dir, "peerflix"], check=True)
        except Exception as e:
            print(f"Failed to install peerflix: {e}")
            raise e
        
    return peerflix_app_js

def play_magnet(magnet_link, player="mpv", progress_callback=None, file_index=None):
    """
    Launch peerflix with the given magnet link and external player.
    """
    global active_process
    stop_player() # Ensure any previous stream is stopped
    
    print(f"Launching peerflix on port 8888...")
    
    def launch():
        global active_process
        try:
            if progress_callback:
                progress_callback({"status": "Initializing stream engine..."})
                
            peerflix_js = get_peerflix_bin(progress_callback)
            
            # Start peerflix without a player flag so we can launch the player manually
            cmd = ["node", peerflix_js, magnet_link, "--port", "8888", "--path", "/var/tmp/native-popcorn"]
            if file_index is not None:
                cmd.extend(["--index", str(file_index)])
            
            # Don't pipe stdout, let it print to terminal so clivas works natively in the terminal
            process = subprocess.Popen(cmd)
            active_process = process
            
            if progress_callback:
                progress_callback({"status": "Buffering stream (check terminal for details)..."})
                
            # Give peerflix time to initialize the local server and start fetching metadata
            import time
            import socket
            import gi
            from gi.repository import GLib
            
            server_up = False
            for _ in range(60):
                if process.poll() is not None:
                    if progress_callback:
                        GLib.idle_add(lambda: progress_callback({"status": "Error: Stream engine exited."}))
                    return
                try:
                    with socket.create_connection(("127.0.0.1", 8888), timeout=1):
                        server_up = True
                        break
                except (ConnectionRefusedError, socket.timeout, OSError):
                    time.sleep(1)
                    
            if not server_up:
                if progress_callback:
                    GLib.idle_add(lambda: progress_callback({"status": "Error: Timeout waiting for stream."}))
                return
            
            if progress_callback:
                progress_callback({"status": "Launching MPV player..."})
                
            import shutil
            
            # Launch MPV manually. Handle both in-flatpak and out-of-flatpak scenarios
            if os.path.exists("/app/bin/mpv"):
                mpv_cmd = ["/app/bin/mpv"]
            elif shutil.which("mpv"):
                mpv_cmd = ["mpv"]
            else:
                mpv_cmd = ["flatpak", "run", "io.mpv.Mpv"]
                
            mpv_cmd.append("http://127.0.0.1:8888/")
            print(f"Executing: {' '.join(mpv_cmd)}")
            mpv_process = subprocess.Popen(mpv_cmd)
            
            if progress_callback:
                progress_callback({"status": "Playing!"})
                
            # Stats polling loop
            import urllib.request
            import json
            
            def poll_stats():
                while active_process == process and process.poll() is None and mpv_process.poll() is None:
                    try:
                        req = urllib.request.Request("http://127.0.0.1:8888/.json")
                        with urllib.request.urlopen(req, timeout=1) as response:
                            stats = json.loads(response.read().decode('utf-8'))
                            stats["status"] = "Downloading"
                            if progress_callback:
                                GLib.idle_add(lambda s=stats: progress_callback(s))
                    except Exception as ex:
                        pass
                    time.sleep(1)
                    
                # If MPV closed, stop peerflix automatically, but only if we are still the active process
                if mpv_process.poll() is not None and active_process == process:
                    GLib.idle_add(stop_player)
                    if progress_callback:
                        GLib.idle_add(lambda: progress_callback({"status": "Player closed.", "closed": True}))
                        
            threading.Thread(target=poll_stats, daemon=True).start()
                    
        except Exception as e:
            print(f"Error launching player: {e}")
            if progress_callback:
                progress_callback({"status": f"Error: {e}"})

    # Start the launch process in a background thread
    threading.Thread(target=launch, daemon=True).start()
    return None

def play_trailer(youtube_id):
    """Launch mpv to play the trailer."""
    global active_process
    stop_player()
    
    print(f"Playing trailer: {youtube_id}")
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    try:
        cmd = ["mpv", url]
        process = subprocess.Popen(cmd)
        active_process = process
        return process
    except Exception as e:
        print(f"Error launching trailer: {e}")
        return None
