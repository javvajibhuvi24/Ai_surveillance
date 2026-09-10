import os
import json
import time
import base64
import numpy as np
import cv2
import threading
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, Response, request, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.utils import secure_filename

from stream_handler import VideoProcessor, process_static_image, AUTHORIZED_FOLDER, flush_face_cache
from alerts import save_incident
import config
from network_utils import scan_wifi, connect_wifi, discover_cameras

app = Flask(__name__)
app.secret_key = getattr(config, 'SECRET_KEY', 'edgeshield-secret-key-change-me')

# ---- Auth credentials (for manual admin login) ----
ADMIN_USER = getattr(config, 'ADMIN_USER', 'admin')
ADMIN_PASS = getattr(config, 'ADMIN_PASS', 'admin123')

# ---- History log file ----
HISTORY_FILE = "incident_history.json"
CAMERAS_FILE = "cameras.json"

processors = {}  # cam_id -> VideoProcessor

def load_cameras():
    if os.path.exists(CAMERAS_FILE):
        try:
            with open(CAMERAS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return [{"id": "cam_default", "name": "Main Camera", "url": config.VIDEO_SOURCE}]

def save_cameras(cams):
    with open(CAMERAS_FILE, 'w') as f:
        json.dump(cams, f, indent=2)

def init_processors():
    cams = load_cameras()
    
    # Safety: always ensure the default webcam is present
    cam_ids = [c["id"] for c in cams]
    if "cam_default" not in cam_ids:
        default_cam = {"id": "cam_default", "name": "Main Camera", "url": 0}
        cams.insert(0, default_cam)
        save_cameras(cams)
        print("[STARTUP] Restored missing default webcam to cameras.json")
    
    # Clear stale DeepFace cache before starting processors to prevent concurrency issues
    flush_face_cache()
    
    for c in cams:
        cid = c["id"]
        # Skip cameras that were turned off before server restart
        if not c.get("enabled", True):
            print(f"[STARTUP] Skipping disabled camera: {c['name']}")
            continue
        url = c["url"]
        if isinstance(url, str) and url.isdigit():
            url = int(url)
        processors[cid] = VideoProcessor(url, cam_name=c["name"])

# We will delay initialization until admin login
processors_initialized = False

def ensure_processors_running():
    global processors_initialized
    if not processors_initialized:
        init_processors()
        processors_initialized = True


# ============================================================
# AUTH
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        if u == ADMIN_USER and p == ADMIN_PASS:
            session['logged_in'] = True
            session['user'] = u
            ensure_processors_running()
            return redirect(url_for('index'))
        else:
            error = True
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ============================================================
# HISTORY HELPERS
# ============================================================
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    # Fall back: parse incident_log.txt
    logs = []
    if os.path.exists('incident_log.txt'):
        try:
            with open('incident_log.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('[') and ']' in line:
                        idx = line.index(']')
                        ts = line[1:idx]
                        msg = line[idx+1:].strip()
                        logs.append({'timestamp': ts, 'message': msg, 'person': '', 'snapshot': ''})
        except Exception:
            pass
    return list(reversed(logs))


def append_history(entry):
    """Append a single incident entry to the history JSON file."""
    history = load_history()
    history.insert(0, entry)
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history[:2000], f, indent=2)  # keep max 2000 entries
    except Exception as e:
        print(f"[HISTORY] Write error: {e}")


# ============================================================
# PAGES
# ============================================================
@app.route('/')
@login_required
def index():
    ensure_processors_running()
    return render_template('index.html', session_user=session.get('user', 'admin'))


@app.route('/history')
@login_required
def history():
    return render_template('history.html', session_user=session.get('user', 'admin'))


# ============================================================
# TEST ALERT (startup)
# ============================================================
def test_alert():
    time.sleep(5)
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    save_incident(fake_frame, "TEST ALERT FROM AI SURVEILLANCE SYSTEM")

if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    threading.Thread(target=test_alert, daemon=True).start()


# ============================================================
# API: CAMERAS
# ============================================================
@app.route('/api/cameras', methods=['GET', 'POST'])
@login_required
def api_cameras():
    cams = load_cameras()
    if request.method == 'POST':
        data = request.json
        if not data or 'name' not in data or 'url' not in data:
            return jsonify({'success': False, 'error': 'Missing name or url'}), 400
        
        raw_url = str(data['url']).strip()
        
        # Auto-normalize: if it's a digit string, treat as webcam index
        if raw_url.isdigit():
            url = int(raw_url)
        # Auto-normalize: bare IP address like 192.168.1.50 — prepend rtsp://
        elif raw_url and not raw_url.startswith(('rtsp://', 'http://', 'https://', '/')):
            url = f"rtsp://{raw_url}/stream1"
        else:
            url = raw_url
        
        new_id = f"cam_{int(time.time())}"
        new_cam = {"id": new_id, "name": data['name'], "url": url if isinstance(url, str) else raw_url, "ssid": data.get('ssid', '')}
        cams.append(new_cam)
        save_cameras(cams)
        
        processors[new_id] = VideoProcessor(url, cam_name=new_cam['name'])
        return jsonify({'success': True, 'camera': new_cam})
        
    return jsonify(cams)

@app.route('/api/cameras/<cam_id>', methods=['DELETE'])
@login_required
def api_camera_delete(cam_id):
    cams = load_cameras()
    cams = [c for c in cams if c['id'] != cam_id]
    save_cameras(cams)
    
    if cam_id in processors:
        processors[cam_id].stop()
        del processors[cam_id]
        
    return jsonify({'success': True})

@app.route('/api/cameras/<cam_id>/restart', methods=['POST'])
@login_required
def api_camera_restart(cam_id):
    """Stop and restart a specific camera processor (reconnect)."""
    cams = load_cameras()
    cam = next((c for c in cams if c['id'] == cam_id), None)
    if not cam:
        return jsonify({'success': False, 'error': 'Camera not found'}), 404

    # Stop existing processor if running
    if cam_id in processors:
        try:
            processors[cam_id].stop()
        except Exception:
            pass
        del processors[cam_id]

    # Re-launch processor
    url = cam['url']
    if isinstance(url, str) and url.isdigit():
        url = int(url)

    processors[cam_id] = VideoProcessor(url, cam_name=cam['name'])
    return jsonify({'success': True, 'message': f"Reconnecting {cam['name']}..."})


@app.route('/api/cameras/<cam_id>/toggle', methods=['POST'])
@login_required
def api_camera_toggle(cam_id):
    """Enable or disable (pause/resume) a specific camera."""
    cams = load_cameras()
    cam = next((c for c in cams if c['id'] == cam_id), None)
    if not cam:
        return jsonify({'success': False, 'error': 'Camera not found'}), 404

    currently_enabled = cam.get('enabled', True)
    new_state = not currently_enabled

    # Update enabled state in cameras.json
    for c in cams:
        if c['id'] == cam_id:
            c['enabled'] = new_state
    save_cameras(cams)

    if new_state:
        # Turn ON — start processor if not running
        if cam_id not in processors:
            url = cam['url']
            if isinstance(url, str) and url.isdigit():
                url = int(url)
            processors[cam_id] = VideoProcessor(url, cam_name=cam['name'])
        return jsonify({'success': True, 'enabled': True, 'message': f"{cam['name']} turned ON"})
    else:
        # Turn OFF — stop processor
        if cam_id in processors:
            try:
                processors[cam_id].stop()
            except Exception:
                pass
            del processors[cam_id]
        return jsonify({'success': True, 'enabled': False, 'message': f"{cam['name']} turned OFF"})

@app.route('/api/cameras/<cam_id>/snapshot', methods=['POST'])
@login_required
def api_camera_snapshot(cam_id):
    """Trigger a manual screenshot for a specific camera."""
    if cam_id not in processors:
        return jsonify({'success': False, 'error': 'Camera is offline'}), 404
        
    processor = processors[cam_id]
    frame = None
    with processor.lock:
        if processor.latest_raw_frame is not None:
            frame = processor.latest_raw_frame.copy()
            
    if frame is not None:
        from alerts import save_incident
        # We spawn a thread to save it so it doesn't block
        import threading
        threading.Thread(
            target=save_incident,
            args=(frame, "Manual Screenshot"),
            kwargs={"person": processor.cached_name, "cam_name": processor.cam_name, "send_email": False},
            daemon=True
        ).start()
        return jsonify({'success': True, 'message': 'Screenshot saved to History'})
    else:
        return jsonify({'success': False, 'error': 'No video frame available'}), 400

# ============================================================
# API: NETWORK & DISCOVERY
# ============================================================
@app.route('/api/wifi/scan')
@login_required
def api_wifi_scan():
    networks = scan_wifi()
    return jsonify(networks)

@app.route('/api/wifi/connect', methods=['POST'])
@login_required
def api_wifi_connect():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    if not ssid or not password:
        return jsonify({'success': False, 'error': 'Missing credentials'}), 400
    
    success, msg = connect_wifi(ssid, password)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/cameras/discover')
@login_required
def api_cameras_discover():
    # This might take a few seconds, so the frontend should show a loader
    found_urls = discover_cameras()
    return jsonify(found_urls)

# ============================================================
# API: EMAIL SETTINGS
# ============================================================
@app.route('/api/email/settings', methods=['GET'])
@login_required
def api_email_get():
    return jsonify({
        'enabled':    getattr(config, 'EMAIL_ENABLED', False),
        'sender':     getattr(config, 'EMAIL_SENDER', ''),
        'recipients': getattr(config, 'EMAIL_RECIPIENTS', []),
    })

@app.route('/api/email/settings', methods=['POST'])
@login_required
def api_email_save():
    data = request.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.py')
    with open(config_path, 'r') as f:
        lines = f.readlines()

    def set_val(lines, key, value):
        new_lines = []
        found = False
        for line in lines:
            if line.strip().startswith(key + ' ') or line.strip().startswith(key + '='):
                new_lines.append(f"{key.ljust(18)}= {repr(value)}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key.ljust(18)}= {repr(value)}\n")
        return new_lines

    lines = set_val(lines, 'EMAIL_ENABLED',    bool(data.get('enabled', False)))
    lines = set_val(lines, 'EMAIL_SENDER',     data.get('sender', ''))
    lines = set_val(lines, 'EMAIL_PASSWORD',   data.get('password', ''))
    lines = set_val(lines, 'EMAIL_RECIPIENTS', data.get('recipients', []))

    with open(config_path, 'w') as f:
        f.writelines(lines)

    # Hot-reload config in memory
    import importlib
    importlib.reload(config)

    return jsonify({'success': True})

@app.route('/api/email/test', methods=['POST'])
@login_required
def api_email_test():
    import importlib
    importlib.reload(config)
    from alerts import send_email_alert
    import numpy as np, cv2 as _cv2
    blank = np.zeros((200, 400, 3), dtype=np.uint8)
    _cv2.putText(blank, "TEST ALERT", (80, 110), _cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 200), 2)
    test_img = "snapshots/test_email.jpg"
    _cv2.imwrite(test_img, blank)
    threading.Thread(
        target=send_email_alert,
        args=("✅ EdgeShield AI — Test Email", "<html><body style='font-family:Arial;background:#0f172a;color:#f1f5f9;padding:30px;'><h2 style='color:#00d4ff;'>✅ Email Alerts are Working!</h2><p>This is a test alert from <strong>EdgeShield AI</strong> Surveillance System.</p><p style='color:#94a3b8;font-size:13px;'>You will receive alerts like this automatically when a safety incident is detected.</p></body></html>", test_img),
        daemon=True
    ).start()
    return jsonify({'success': True})


# ============================================================
# VIDEO FEED
# ============================================================
@app.route('/video_feed/<cam_id>')
@login_required
def video_feed(cam_id):
    if cam_id not in processors:
        return "Camera not found", 404
    return Response(
        processors[cam_id].generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ============================================================
# API: STATS
# ============================================================
@app.route('/api/stats')
@login_required
def api_stats():
    stats = {}
    for cid, proc in processors.items():
        with proc.lock:
            stats[cid] = {
                'score': proc.latest_score,
                'labels': list(proc.latest_detected_labels),
                'name': proc.cached_name,
                'face_processing': proc.face_processing
            }
    return jsonify(stats)


# ============================================================
# API: ALERTS (recent — for live feed widget)
# ============================================================
@app.route('/api/alerts')
@login_required
def api_alerts():
    logs = []
    log_file = 'incident_log.txt'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines[-20:]):
                    line = line.strip()
                    if line.startswith('[') and ']' in line:
                        idx = line.index(']')
                        logs.append({'timestamp': line[1:idx], 'message': line[idx+1:].strip()})
        except Exception as e:
            print('Error reading log file:', e)
    return jsonify(logs)


# ============================================================
# API: HISTORY (full — for history page)
# ============================================================
@app.route('/api/history')
@login_required
def api_history():
    return jsonify(load_history())


@app.route('/api/clear_history', methods=['POST'])
@login_required
def api_clear_history():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        if os.path.exists('incident_log.txt'):
            open('incident_log.txt', 'w').close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API: FACES
# ============================================================
@app.route('/api/faces', methods=['GET'])
@login_required
def get_faces():
    faces = []
    if os.path.exists(AUTHORIZED_FOLDER):
        for f in os.listdir(AUTHORIZED_FOLDER):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                name = os.path.splitext(f)[0]
                if '.' in name:
                    name = name.split('.')[0]
                faces.append({'name': name, 'filename': f})
    return jsonify(faces)


@app.route('/authorized_faces/<path:filename>')
@login_required
def serve_authorized_face(filename):
    return send_from_directory(AUTHORIZED_FOLDER, filename)


def clear_deepface_cache():
    if os.path.exists(AUTHORIZED_FOLDER):
        for f in os.listdir(AUTHORIZED_FOLDER):
            if f.endswith('.pkl'):
                try:
                    os.remove(os.path.join(AUTHORIZED_FOLDER, f))
                    print(f'Cleared DeepFace cache: {f}')
                except Exception as e:
                    print('Error removing cache file:', e)


@app.route('/api/upload_face', methods=['POST'])
@login_required
def upload_face():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({'success': False, 'error': 'Missing image or name'}), 400
    name = request.form['name'].strip()
    file = request.files['image']
    if name == '' or file.filename == '':
        return jsonify({'success': False, 'error': 'Invalid name or file'}), 400
    secure_name = secure_filename(name)
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        return jsonify({'success': False, 'error': 'Unsupported file format'}), 400
    filename = f'{secure_name}{ext}'
    os.makedirs(AUTHORIZED_FOLDER, exist_ok=True)
    file_path = os.path.join(AUTHORIZED_FOLDER, filename)
    try:
        file.save(file_path)
        clear_deepface_cache()
        return jsonify({'success': True, 'message': f'Successfully registered {name}.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete_face', methods=['POST'])
@login_required
def delete_face():
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'success': False, 'error': 'Missing filename'}), 400
    filename = secure_filename(data['filename'])
    file_path = os.path.join(AUTHORIZED_FOLDER, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            clear_deepface_cache()
            return jsonify({'success': True, 'message': f'Deleted {filename}.'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404


# ============================================================
# API: STATIC TEST IMAGE
# ============================================================
@app.route('/api/test_image', methods=['POST'])
@login_required
def test_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image uploaded'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    try:
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'success': False, 'error': 'Invalid image file'}), 400
        MAX_DIM = 1920
        h, w = img.shape[:2]
        if max(h, w) > MAX_DIM:
            scale = MAX_DIM / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        annotated_img, score, name, labels = process_static_image(img)
        _, buffer = cv2.imencode('.jpg', annotated_img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # Save to history
        snapshot_name = f"snap_{int(time.time())}.jpg"
        snap_path = os.path.join('snapshots', snapshot_name)
        os.makedirs('snapshots', exist_ok=True)
        cv2.imwrite(snap_path, annotated_img)

        append_history({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'PPE violation detected' if score < 100 else 'Full PPE compliance',
            'person': name,
            'score': score,
            'snapshot': snapshot_name,
            'labels': labels
        })

        return jsonify({'success': True, 'score': score, 'name': name, 'labels': labels,
                        'image': f'data:image/jpeg;base64,{img_base64}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# SERVE SNAPSHOTS
# ============================================================
@app.route('/snapshots/<path:filename>')
@login_required
def serve_snapshot(filename):
    return send_from_directory('snapshots', filename)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)