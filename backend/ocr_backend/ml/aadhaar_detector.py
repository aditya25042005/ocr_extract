import os
import uuid
import fitz  # PyMuPDF
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

# Load model once
MODEL_PATH = hf_hub_download(
    repo_id="logasanjeev/indian-id-validator",
    filename="models/Id_Classifier.pt"
)
model = YOLO(MODEL_PATH)

CONF_THRESHOLD = 0.7


def _is_aadhaar_image(image_path: str) -> bool:
    results = model(image_path, verbose=False)
    probs = results[0].probs

    class_name = model.names[probs.top1]
    confidence = float(probs.top1conf)

    return (
        class_name in ["aadhar_front", "aadhar_back"]
        and confidence >= CONF_THRESHOLD
    )


def is_aadhaar(file_path: str) -> bool:
    file_path = str(file_path)

    # ---------- IMAGE ----------
    if file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        return _is_aadhaar_image(file_path)

    # ---------- PDF ----------
    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)

        for page in doc:
            pix = page.get_pixmap(dpi=300)
            temp_img = f"/tmp/aadhaar_{uuid.uuid4().hex}.jpg"
            pix.save(temp_img)

            try:
                if _is_aadhaar_image(temp_img):
                    return True
            finally:
                if os.path.exists(temp_img):
                    os.remove(temp_img)

        return False

    return False