import os
import uuid
from ultralytics import YOLO
from pdf2image import convert_from_path
from PIL import Image

# ---------------------------------------------------------
# Load YOLO model ONCE (important for performance)
# ---------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_cache/best.pt")
model = YOLO(MODEL_PATH)

# Confidence threshold (balanced for recall)
YOLO_CONF = 0.45
YOLO_IMGSZ = 640


# ---------------------------------------------------------
# YOLO inference on a single image
# ---------------------------------------------------------
def _detect_aadhaar_in_image(image_path: str) -> bool:
    """
    Returns True if YOLO detects *any* Aadhaar-related object.
    """
    results = model.predict(
        source=image_path,
        conf=YOLO_CONF,
        imgsz=YOLO_IMGSZ,
        verbose=False
    )[0]

    # If model predicts at least one box → Aadhaar detected
    return results.boxes is not None and len(results.boxes) > 0


# ---------------------------------------------------------
# Public function used by Django view
# ---------------------------------------------------------
def is_aadhaar(file_path: str) -> bool:
    """
    Detect Aadhaar card from image or PDF.
    """

    file_path = str(file_path).lower()

    # ---------------- IMAGE ----------------
    if file_path.endswith((".jpg", ".jpeg", ".png")):
        return _detect_aadhaar_in_image(file_path)

    # ---------------- PDF ------------------
    if file_path.endswith(".pdf"):
        try:
            pages = convert_from_path(file_path, dpi=300)
        except Exception:
            # PDF unreadable
            return False

        for page in pages:
            temp_img = f"/tmp/aadhaar_{uuid.uuid4().hex}.jpg"
            page.save(temp_img, "JPEG")

            try:
                if _detect_aadhaar_in_image(temp_img):
                    return True
            finally:
                # Cleanup temp file
                if os.path.exists(temp_img):
                    os.remove(temp_img)

        return False

    # Unsupported file type
    return False
