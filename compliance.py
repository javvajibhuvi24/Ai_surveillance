REQUIRED_ITEMS = ["glasses", "gloves", "coat"]


def calculate_compliance(detections):
    detected_labels = [d["label"] for d in detections]

    score = 0

    for item in REQUIRED_ITEMS:
        if item in detected_labels:
            score += 33.33

    return round(score, 2)