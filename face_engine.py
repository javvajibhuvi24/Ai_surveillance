from deepface import DeepFace
import os
import cv2

AUTHORIZED_FOLDER = "authorized_faces"


def recognize_faces(frame):

    detected_people = []

    try:
        results = DeepFace.find(
            img_path=frame,
            db_path=AUTHORIZED_FOLDER,
            enforce_detection=False,
            silent=True
        )

        if len(results) > 0 and not results[0].empty:

            identity_path = results[0].iloc[0]["identity"]

            name = os.path.basename(identity_path).split(".")[0]

            detected_people.append(name)

        else:
            detected_people.append("UNKNOWN")

    except:
        detected_people.append("UNKNOWN")

    return detected_people