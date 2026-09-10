import cv2
import os
import requests
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
import config

SNAPSHOT_FOLDER = "snapshots"
LOG_FILE        = "incident_log.txt"

os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# ---- Telegram Configuration ----
BOT_TOKEN = "8949496933:AAGu_RIKFv4fnrkRPIxGbhLC9P5FzM51AM0"
CHAT_ID   = "1205600909"


def send_telegram_alert(message, image_path):
    """Sends a text message + snapshot photo to the configured Telegram bot."""
    try:
        msg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp1 = requests.post(
            msg_url,
            data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        print(f"[TELEGRAM] Message sent -> {resp1.status_code}: {resp1.text[:120]}")

        if os.path.exists(image_path):
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as photo:
                resp2 = requests.post(
                    photo_url,
                    data={"chat_id": CHAT_ID},
                    files={"photo": photo},
                    timeout=15
                )
            print(f"[TELEGRAM] Photo sent   -> {resp2.status_code}: {resp2.text[:120]}")

    except requests.exceptions.Timeout:
        print("[TELEGRAM] Request timed out.")
    except Exception as e:
        print(f"[TELEGRAM] Error: {e}")


def send_email_alert(subject, html_body, image_path):
    """Sends an HTML email with the snapshot attached. Uses config.py credentials."""
    try:
        if not getattr(config, 'EMAIL_ENABLED', False):
            return
        sender    = config.EMAIL_SENDER
        password  = config.EMAIL_PASSWORD
        recipients = config.EMAIL_RECIPIENTS
        if not sender or not password or not recipients:
            print("[EMAIL] Missing sender/password/recipients in config.py — skipping.")
            return

        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"]    = f"EdgeShield AI <{sender}>"
        msg["To"]      = ", ".join(recipients)

        # HTML body with embedded snapshot
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Attach snapshot image
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
            image = MIMEImage(img_data, name=os.path.basename(image_path))
            image.add_header("Content-ID", "<snapshot>")
            image.add_header("Content-Disposition", "inline", filename=os.path.basename(image_path))
            msg.attach(image)

        with smtplib.SMTP(config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())

        print(f"[EMAIL] Alert sent to: {', '.join(recipients)}")

    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] Authentication failed — check EMAIL_SENDER and EMAIL_PASSWORD in config.py")
    except Exception as e:
        print(f"[EMAIL] Error: {e}")


def save_incident(frame, message, person="UNKNOWN", score=None, missing=None, cam_name="Main Camera", send_email=True):
    """
    Saves a snapshot and log entry, then fires Telegram + Email alerts asynchronously.
    
    Args:
        send_email: If False, skip email this time (Telegram still fires). 
                    Used to apply a longer email cooldown than Telegram.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename  = f"{SNAPSHOT_FOLDER}/{timestamp}.jpg"
    cv2.imwrite(filename, frame)

    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

    # ---- Save to JSON History ----
    import json
    history_file = "incident_history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception:
            pass
    
    entry = {
        "timestamp": timestamp.replace('_', ' '),
        "message": message,
        "person": person,
        "camera": cam_name,
        "snapshot": filename,
        "score": score if score is not None else "",
        "missing": missing if missing else []
    }
    history.insert(0, entry)
    try:
        with open(history_file, "w") as f:
            json.dump(history[:2000], f, indent=2)
    except Exception as e:
        print(f"[HISTORY] Write error: {e}")

    print(f"[ALERT] {message}")

    # ---- Build Telegram message ----
    emoji = "🚨"
    lines = [
        f"{emoji} <b>SAFETY ALERT</b> {emoji}",
        f"📷 <b>Camera:</b> {cam_name}",
        f"📅 <b>Time:</b> {timestamp.replace('_', ' ')}",
        f"👤 <b>Person:</b> {person}",
        f"⚠️ <b>Incident:</b> {message}",
    ]
    if score is not None:
        lines.append(f"📊 <b>PPE Compliance:</b> {score}%")
    if missing:
        lines.append(f"❌ <b>Missing PPE:</b> {', '.join(m.upper() for m in missing)}")
    lines.append("\n<i>AI Surveillance System — Auto Alert</i>")
    telegram_message = "\n".join(lines)

    # ---- Build HTML email body ----
    missing_html = ""
    if missing:
        items = "".join(f"<li style='color:#ef4444;'>{m.upper()}</li>" for m in missing)
        missing_html = f"<p><strong>❌ Missing PPE:</strong></p><ul>{items}</ul>"

    score_html = f"<p><strong>📊 PPE Compliance:</strong> <span style='color:{'#10b981' if score and score >= 100 else '#ef4444'};font-size:18px;font-weight:bold;'>{score}%</span></p>" if score is not None else ""

    email_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#f1f5f9;padding:0;margin:0;">
      <div style="max-width:600px;margin:30px auto;background:#1e293b;border-radius:12px;overflow:hidden;border:1px solid #334155;">
        <div style="background:linear-gradient(135deg,#ef4444,#b91c1c);padding:24px 28px;">
          <h1 style="margin:0;font-size:22px;color:#fff;">🚨 EdgeShield AI — Safety Alert</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">Automated Incident Notification</p>
        </div>
        <div style="padding:24px 28px;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:8px 0;color:#94a3b8;width:140px;">📷 Camera</td><td style="padding:8px 0;font-weight:bold;">{cam_name}</td></tr>
            <tr><td style="padding:8px 0;color:#94a3b8;">📅 Time</td><td style="padding:8px 0;">{timestamp.replace('_', ' ')}</td></tr>
            <tr><td style="padding:8px 0;color:#94a3b8;">👤 Person</td><td style="padding:8px 0;">{person}</td></tr>
            <tr><td style="padding:8px 0;color:#94a3b8;">⚠️ Incident</td><td style="padding:8px 0;color:#f87171;font-weight:bold;">{message}</td></tr>
          </table>
          {score_html}
          {missing_html}
          <div style="margin-top:20px;border-radius:8px;overflow:hidden;">
            <p style="color:#94a3b8;font-size:13px;margin-bottom:8px;">📸 Incident Snapshot:</p>
            <img src="cid:snapshot" style="width:100%;border-radius:8px;border:1px solid #334155;" alt="Snapshot">
          </div>
        </div>
        <div style="padding:16px 28px;background:#0f172a;text-align:center;color:#475569;font-size:12px;">
          EdgeShield AI Surveillance System &nbsp;|&nbsp; Auto-generated alert
        </div>
      </div>
    </body></html>
    """

    subject = f"🚨 Safety Alert — {message} [{cam_name}]"

    # Always fire Telegram (15s cooldown handled by caller)
    threading.Thread(target=send_telegram_alert, args=(telegram_message, filename), daemon=True).start()

    # Only fire email when the 5-minute email cooldown has passed
    if send_email:
        threading.Thread(target=send_email_alert, args=(subject, email_html, filename), daemon=True).start()
    else:
        print("[EMAIL] Skipped — within 5-minute email cooldown")
