VIDEO_SOURCE = 0

# Confidence threshold for live video (higher = fewer false positives)
CONFIDENCE_THRESHOLD = 0.35

# Confidence threshold for static image PPE model (helmet/vest - very low to catch them)
STATIC_CONFIDENCE_THRESHOLD = 0.03

# Confidence threshold for static image GG model (gloves/goggles)
STATIC_GG_CONFIDENCE_THRESHOLD = 0.20

PPE_CLASSES = ["helmet", "boots", "vest", "gloves", "goggles"]

AUTHORIZED_FACE_FOLDER = "authorized_faces"

INCIDENT_LOG = "incident_logs/logs.txt"

SNAPSHOT_FOLDER = "snapshots"

# ---- Login credentials (for manual admin login) ----
SECRET_KEY = "edgeshield-secret-2024-change-me"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ---- Email Alert Configuration ----
# Set EMAIL_ENABLED = True and fill in your Gmail details to receive email alerts.
# IMPORTANT: Use a Gmail App Password (not your real Gmail password).
# Generate one at: https://myaccount.google.com/apppasswords
EMAIL_ENABLED     = True
EMAIL_SENDER      = 'javvajibhuvi01@gmail.com'
EMAIL_PASSWORD    = 'lbgc lgoi okrr nnll'
EMAIL_RECIPIENTS  = ['javvajibuvi@gmail.com']
EMAIL_SMTP_HOST   = "smtp.gmail.com"
EMAIL_SMTP_PORT   = 587
