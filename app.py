from flask import Flask, render_template, request, jsonify, Response
import subprocess
import os
import signal
import queue
import threading

app = Flask(__name__)

# Global variables for process management
bot_process = None
log_queue = queue.Queue()

def read_output(process):
    """Membaca output dari subprocess dan memasukkannya ke queue"""
    for line in iter(process.stdout.readline, ''):
        if line:
            log_queue.put(line)
    process.stdout.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_process
    if bot_process is None or bot_process.poll() is not None:
        # Kosongkan queue log lama
        while not log_queue.empty():
            log_queue.get()
            
        # Set environment variable untuk remote ADB (jika perlu)
        env = os.environ.copy()
        # env['ADB_SERVER_SOCKET'] = 'tcp:127.0.0.1:5037' # Uncomment di VPS nanti
        
        # Jalankan script menggunakan python
        bot_process = subprocess.Popen(
            ['python', 'wd_xlm.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Mulai thread untuk membaca output secara asinkron
        t = threading.Thread(target=read_output, args=(bot_process,), daemon=True)
        t.start()
        
        return jsonify({"status": "success", "message": "Bot mulai berjalan!"})
    else:
        return jsonify({"status": "error", "message": "Bot sudah berjalan!"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_process
    if bot_process and bot_process.poll() is None:
        if os.name == 'nt': # Windows
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)])
        else: # Linux/VPS
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
        bot_process = None
        return jsonify({"status": "success", "message": "Bot berhasil dihentikan."})
    else:
        return jsonify({"status": "error", "message": "Tidak ada bot yang sedang berjalan."})

@app.route('/status', methods=['GET'])
def get_status():
    if bot_process and bot_process.poll() is None:
        return jsonify({"running": True})
    return jsonify({"running": False})

@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                # Mengambil log dari queue (timeout 1 detik agar tidak block selamanya)
                line = log_queue.get(timeout=1.0)
                yield f"data: {line}\n\n"
            except queue.Empty:
                # Cek apakah bot masih jalan
                if bot_process and bot_process.poll() is not None:
                    # Bot sudah selesai
                    yield "data: [SYSTEM] Bot telah selesai berjalan.\n\n"
                    break
                # Kirim sinyal ping (keep-alive)
                yield ":\n\n"
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Jalankan server di semua interface (0.0.0.0) port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
