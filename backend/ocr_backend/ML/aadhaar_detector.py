import os
from ultralytics import YOLO
from pdf2image import convert_from_path

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_cache/best.pt")
model = YOLO(MODEL_PATH)

REQUIRED_CLASSES = {0, 1, 2, 3}

def run_yolo(image_path, min_conf=0.5):
    results = model.predict(image_path)[0]
    detected = []

    for box in results.boxes:
        if box.conf[0] >= min_conf:
            detected.append(int(box.cls[0]))

    return REQUIRED_CLASSES.issubset(detected)


def is_aadhaar(path):
    path = str(path)

    # Case 1: Image file
    if path.lower().endswith((".jpg", ".jpeg", ".png")):
        return run_yolo(path)

    # Case 2: PDF file
    elif path.lower().endswith(".pdf"):
        pages = convert_from_path(path)
        for i, page in enumerate(pages):
            temp = f"/tmp/page_{i}.jpg"
            page.save(temp, "JPEG")

            if run_yolo(temp):
                return True

        return False

    return False
