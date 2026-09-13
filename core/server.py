import os
import sys
import json
import time
import subprocess
import threading
import queue
import re
from collections import deque
from flask import Flask, jsonify, request, Response, send_from_directory

# Path Direktori Proyek
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))
WEB_DIR = os.path.join(CORE_DIR, 'web')
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    read_current_screen,
    get_cached_screen,
    get_connected_devices,
    register_auto_restore
)
from menu import (
    get_or_detect_wifi_ip,
    get_usb_device,
    is_port_reachable,
    launch_mirror_screen,
    parse_step_header,
    update_kordinat_txt_step,
    update_all_kordinat_txt_steps,
    sync_kordinat_and_config
)
from wd_xlm import update_sleep_in_kordinat

# Setup Flask Server
app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")

# State Bot Global & Threading Locks
bot_process = None
bot_state = "IDLE"  # "IDLE", "RUNNING", "WAITING_NEXT"
current_clone = None
next_clone = None
process_lock = threading.Lock()

# Logging & SSE Broadcast
log_history = deque(maxlen=2000)
log_lock = threading.Lock()
subscribers = []
subscribers_lock = threading.Lock()

def broadcast_log(line):
    """Menyimpan line log dan mengirim ke semua klien SSE yang terhubung."""
    clean_line = line.rstrip("\r\n")
    if not clean_line:
        return
    with log_lock:
        log_history.append(clean_line)
    with subscribers_lock:
        for q in list(subscribers):
            try:
                q.put_nowait(clean_line)
            except Exception:
                pass

def read_process_output(proc):
    """Thread pembaca output stdout dari subprocess bot."""
    global bot_state, bot_process, current_clone, next_clone
    
    broadcast_log("[SYSTEM] Subprocess bot telah dimulai.")
    
    for raw_line in iter(proc.stdout.readline, ''):
        line = raw_line.rstrip("\r\n")
        if not line and proc.poll() is not None:
            break
        
        broadcast_log(line)
        
        # Deteksi nomor akun yang sedang diproses
        m_start = re.search(r"MEMPROSES CLONE BITGET KE-(\d+)", line, re.IGNORECASE)
        if m_start:
            current_clone = int(m_start.group(1))
            next_clone = current_clone + 1
            bot_state = "RUNNING"
            
        # Deteksi status akun selesai dan menunggu konfirmasi akun berikutnya
        if "lanjut loop WD clone berikutnya" in line or "[STEP-BY-STEP] Menunggu konfirmasi..." in line:
            m_next = re.search(r"ke-(\d+)", line, re.IGNORECASE)
            if m_next:
                next_clone = int(m_next.group(1))
            bot_state = "WAITING_NEXT"
            broadcast_log(f"[PROMPT] Bot siap melanjutkan ke Clone ke-{next_clone}. Tekan tombol 'Lanjut (ENTER / CTRL+V)' atau gunakan shortcut keyboard.")
            
        elif "AKUN CLONE KE-" in line and "BERHASIL SELESAI DIPROSES" in line:
            bot_state = "WAITING_NEXT"

        elif "PROGRAM DIPAUSE" in line:
            bot_state = "WAITING_NEXT"
            broadcast_log("[PROMPT] Bot sedang DIPAUSE. Tekan ENTER atau CTRL+V untuk melanjutkan, atau 'Q' untuk berhenti.")

    proc.stdout.close()
    proc.wait()
    
    with process_lock:
        bot_process = None
        bot_state = "IDLE"
        
    broadcast_log(f"[SYSTEM] Subprocess bot telah selesai (Exit Code: {proc.returncode}).")

def load_config_data():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config_data(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        return False

# ==============================================================================
# ROUTE STATIC FILE (UI DASHBOARD)
# ==============================================================================

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(WEB_DIR, path)

# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/api/status', methods=['GET'])
def api_status():
    devices = get_connected_devices()
    screen_info = read_current_screen()
    cached_size, cached_density = get_cached_screen()
    config = load_config_data()
    
    # Deteksi IP WiFi
    usb_dev = get_usb_device()
    wifi_ip, is_live = get_or_detect_wifi_ip(usb_dev)
    
    return jsonify({
        "status": "success",
        "bot_state": bot_state,
        "current_clone": current_clone,
        "next_clone": next_clone,
        "devices": devices,
        "usb_device": usb_dev,
        "wifi_ip": wifi_ip,
        "is_wifi_live": is_live,
        "screen": {
            "active_size": screen_info.get("active_size"),
            "active_density": screen_info.get("active_density"),
            "physical_size": screen_info.get("physical_size"),
            "physical_density": screen_info.get("physical_density"),
            "cached_size": cached_size,
            "cached_density": cached_density,
            "is_bot_format": (screen_info.get("active_size") == "1080x2400" and screen_info.get("active_density") == "352")
        },
        "config": {
            "start_index": config.get("start_index", 1),
            "alamat_wd": config.get("alamat_wd", ""),
            "pin": config.get("pin", ""),
            "last_wifi_ip": config.get("last_wifi_ip", ""),
            "total_akun": config.get("total_akun", 1),
            "disabled_steps": config.get("disabled_steps", [])
        }
    })

@app.route('/api/bot/start', methods=['POST'])
def api_bot_start():
    global bot_process, bot_state, current_clone, next_clone
    
    with process_lock:
        if bot_process is not None and bot_process.poll() is None:
            return jsonify({"status": "error", "message": "Bot sedang berjalan!"}), 400
        
        data = request.get_json(silent=True) or {}
        start_index = data.get("start_index")
        manual_mode = data.get("manual", False)
        
        config = load_config_data()
        if start_index is not None:
            try:
                config["start_index"] = int(start_index)
                save_config_data(config)
            except ValueError:
                pass
                
        current_clone = config.get("start_index", 1)
        next_clone = current_clone + 1
        
        # Atur resolusi layar bot sebelum start
        record_and_apply_bot_screen(silent=True)
        
        cmd = [sys.executable, "-u", os.path.join(CORE_DIR, "wd_xlm.py")]
        if manual_mode:
            cmd.append("--manual")
            
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["BOT_MANAGED_SCREEN"] = "1"
        
        try:
            bot_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=PROJECT_ROOT,
                env=env
            )
            bot_state = "RUNNING"
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gagal menjalankan bot: {e}"}), 500
            
        t = threading.Thread(target=read_process_output, args=(bot_process,), daemon=True)
        t.start()
        
    return jsonify({
        "status": "success",
        "message": f"Bot dimulai untuk Clone ke-{current_clone}",
        "bot_state": bot_state,
        "current_clone": current_clone
    })

@app.route('/api/bot/next', methods=['POST'])
def api_bot_next():
    global bot_process, bot_state
    
    with process_lock:
        if bot_process is None or bot_process.poll() is not None:
            return jsonify({"status": "error", "message": "Bot sedang tidak berjalan!"}), 400
        
        data = request.get_json(silent=True) or {}
        custom_num = data.get("account_num")
        
        try:
            if custom_num:
                bot_process.stdin.write(f"{custom_num}\n")
            else:
                bot_process.stdin.write("\n")
            bot_process.stdin.flush()
            bot_state = "RUNNING"
            broadcast_log(f"[ACTION] Melanjutkan loop akun via Web UI (Input: '{custom_num or 'ENTER'}')")
            return jsonify({"status": "success", "message": "Perintah lanjut terkirim ke bot", "bot_state": bot_state})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gagal mengirim input ke bot: {e}"}), 500

@app.route('/api/bot/pause', methods=['POST'])
def api_bot_pause():
    global bot_process, bot_state
    
    with process_lock:
        if bot_process is None or bot_process.poll() is not None:
            return jsonify({"status": "error", "message": "Bot sedang tidak berjalan!"}), 400
            
        try:
            broadcast_log("[ACTION] Mengirim sinyal PAUSE ('p') ke bot via Web UI...")
            bot_process.stdin.write("p\n")
            bot_process.stdin.flush()
            bot_state = "WAITING_NEXT"
            return jsonify({"status": "success", "message": "Sinyal PAUSE berhasil dikirim ke bot", "bot_state": bot_state})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gagal mengirim sinyal pause: {e}"}), 500

@app.route('/api/bot/stop', methods=['POST'])
def api_bot_stop():
    global bot_process, bot_state
    
    with process_lock:
        if bot_process is None or bot_process.poll() is not None:
            bot_state = "IDLE"
            return jsonify({"status": "success", "message": "Bot sudah berhenti"})
        
        try:
            broadcast_log("[SYSTEM] Menghentikan bot...")
            bot_process.stdin.write("q\n")
            bot_process.stdin.flush()
        except Exception:
            pass
            
        time.sleep(0.5)
        if bot_process.poll() is None:
            try:
                bot_process.terminate()
                time.sleep(0.5)
                if bot_process.poll() is None:
                    bot_process.kill()
            except Exception:
                pass
                
        bot_process = None
        bot_state = "IDLE"
        
    return jsonify({"status": "success", "message": "Bot berhasil dihentikan", "bot_state": "IDLE"})

@app.route('/api/logs', methods=['GET'])
def api_logs():
    def event_stream():
        q = queue.Queue()
        with subscribers_lock:
            subscribers.append(q)
            with log_lock:
                for item in list(log_history):
                    yield f"data: {json.dumps({'line': item})}\n\n"
        try:
            while True:
                try:
                    line = q.get(timeout=20)
                    yield f"data: {json.dumps({'line': line})}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        except GeneratorExit:
            with subscribers_lock:
                if q in subscribers:
                    subscribers.remove(q)

    return Response(event_stream(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

@app.route('/api/logs/clear', methods=['POST'])
def api_logs_clear():
    with log_lock:
        log_history.clear()
    return jsonify({"status": "success", "message": "Log berhasil dibersihkan"})

@app.route('/api/steps', methods=['GET'])
def api_steps():
    sync_kordinat_and_config()
    config = load_config_data()
    disabled_list = [str(x) for x in config.get("disabled_steps", [])]
    
    steps = []
    if os.path.exists(KORDINAT_FILE):
        current_step = None
        with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                header = parse_step_header(stripped)
                if header:
                    step_id = header['id']
                    is_disabled = header['is_off'] or (str(step_id) in disabled_list)
                    current_step = {
                        "id": step_id,
                        "name": header['name'],
                        "full_title": header['full_title'],
                        "is_off": is_disabled,
                        "enabled": not is_disabled,
                        "commands": [],
                        "sleep": None
                    }
                    steps.append(current_step)
                    continue
                if stripped.startswith('#') or stripped.startswith('---'):
                    continue
                if current_step is not None:
                    current_step['commands'].append(stripped)
                    parts = stripped.split()
                    if parts and parts[0].lower() == 'sleep' and len(parts) > 1:
                        try:
                            current_step['sleep'] = float(parts[1])
                        except ValueError:
                            pass
                            
    return jsonify({"status": "success", "steps": steps, "count": len(steps)})

@app.route('/api/step/toggle', methods=['POST'])
def api_step_toggle():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    enabled = data.get("enabled", True)
    
    if step_id is None:
        return jsonify({"status": "error", "message": "step_id diperlukan"}), 400
        
    set_off = not enabled
    update_kordinat_txt_step(step_id, set_off)
    sync_kordinat_and_config()
    
    return jsonify({
        "status": "success",
        "message": f"Step {step_id} diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "step_id": step_id,
        "enabled": enabled
    })

@app.route('/api/step/toggle_all', methods=['POST'])
def api_step_toggle_all():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)
    
    set_off = not enabled
    update_all_kordinat_txt_steps(set_off)
    sync_kordinat_and_config()
    
    return jsonify({
        "status": "success",
        "message": f"Seluruh langkah diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "enabled": enabled
    })

@app.route('/api/step/delay', methods=['POST'])
def api_step_delay():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    delay = data.get("delay")
    
    if step_id is None or delay is None:
        return jsonify({"status": "error", "message": "step_id dan delay diperlukan"}), 400
        
    try:
        f_delay = float(delay)
        update_sleep_in_kordinat(step_id, f_delay)
        return jsonify({"status": "success", "message": f"Delay step {step_id} diubah menjadi {f_delay}s"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal update delay: {e}"}), 500

@app.route('/api/config', methods=['POST'])
def api_config_update():
    data = request.get_json(silent=True) or {}
    config = load_config_data()
    
    if "alamat_wd" in data:
        config["alamat_wd"] = str(data["alamat_wd"]).strip()
    if "pin" in data:
        config["pin"] = str(data["pin"]).strip()
    if "start_index" in data:
        try:
            config["start_index"] = int(data["start_index"])
        except ValueError:
            pass
    if "last_wifi_ip" in data:
        config["last_wifi_ip"] = str(data["last_wifi_ip"]).strip()
        
    save_config_data(config)
    return jsonify({"status": "success", "message": "Konfigurasi berhasil disimpan", "config": config})

@app.route('/api/screen/set', methods=['POST'])
def api_screen_set():
    success, msg = record_and_apply_bot_screen(silent=True)
    return jsonify({"status": "success" if success else "warning", "message": msg})

@app.route('/api/screen/restore', methods=['POST'])
def api_screen_restore():
    success = restore_recorded_screen(silent=True)
    return jsonify({"status": "success" if success else "warning", "message": "Layar dikembalikan ke ukuran asli" if success else "Tidak ada rekaman resolusi untuk di-restore"})

@app.route('/api/scrcpy', methods=['POST'])
def api_scrcpy_launch():
    try:
        threading.Thread(target=launch_mirror_screen, args=("-S -w --max-fps=120",), daemon=True).start()
        return jsonify({"status": "success", "message": "SCRCPY berhasil diluncurkan!"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal membuka SCRCPY: {e}"}), 500

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    register_auto_restore()
    print("=========================================================")
    print("      BITGET XLM WD BOT — WEB CONTROLLER SERVER          ")
    print("=========================================================")
    print(" Dashboard URL : http://127.0.0.1:5000                   ")
    print(" Local IP Access: http://0.0.0.0:5000                    ")
    print("=========================================================")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
