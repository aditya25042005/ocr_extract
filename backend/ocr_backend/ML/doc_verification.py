import os
import re
import cv2
import torch
import numpy as np
from PIL import Image
from pdf2image import convert_from_path

# ---- LOAD MODELS (LOCAL, LIGHTWEIGHT) ----
from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction
)

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from thefuzz import fuzz


# -------------------------------
#      MODEL INITIALIZATION
# -------------------------------

USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"

# Load TrOCR (LOCAL ONLY, no download)
TROCR_PATH = "/Users/adityagupta/Desktop/Coding/MosipBackend/ocr_extract/backend/ocr_backend/ML/model_cache/models--microsoft--trocr-large-handwritten/snapshots/e68501f437cd2587ae5d68ee457964cac824ddee"   # ← update this
processor = TrOCRProcessor.from_pretrained(TROCR_PATH, local_files_only=True)
trocr_model = VisionEncoderDecoderModel.from_pretrained(TROCR_PATH, local_files_only=True).to(device)

# Load CRAFT text detector
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)


# -------------------------------
#      HELPER FUNCTIONS
# -------------------------------

def load_image(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=300)
        if len(pages) == 0:
            raise ValueError("PDF contains no pages")
        return np.array(pages[0].convert("RGB"))

    # handle cases where extension is wrong (e.g., a pdf saved as .jpg)
    try:
        return np.array(Image.open(file_path).convert("RGB"))
    except:
        # attempt PDF fallback
        try:
            pages = convert_from_path(file_path, dpi=300)
            return np.array(pages[0].convert("RGB"))
        except Exception:
            raise ValueError(f"Unsupported or corrupted image/PDF: {file_path}")



def detect_text_lines(image_rgb):
    """Detect text bounding boxes using CRAFT."""
    preds = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.5,
        link_threshold=0.1,
        low_text=0.3,
        cuda=USE_GPU
    )

    boxes = preds["boxes"]
    line_boxes = []

    for box in boxes:
        b = np.array(box).astype(int)
        x1 = b[:, 0].min()
        x2 = b[:, 0].max()
        y1 = b[:, 1].min()
        y2 = b[:, 1].max()
        line_boxes.append((x1, y1, x2, y2))

    return line_boxes


def recognize_text(image_rgb, box):
    """Recognize cropped text using TrOCR."""
    x1, y1, x2, y2 = box
    pil_img = Image.fromarray(image_rgb[y1:y2, x1:x2])

    pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad():
        outputs = trocr_model.generate(pixel_values)
        text = processor.batch_decode(outputs, skip_special_tokens=True)[0]

    return text.strip()


# -------------------------------
#    MAIN VERIFICATION CLASS
# -------------------------------

class DocumentVerifier:

    def extract_text_entries(self, file_path):
        """Extracts full OCR list: [{text, box}]"""
        img = load_image(file_path)
        boxes = detect_text_lines(img)

        results = []
        for box in boxes:
            text = recognize_text(img, box)
            if len(text.strip()) > 0:
                results.append({"text": text, "box": box})

        return results

    def find_match(self, entries, target):
        if not target:
            return None

        t = target.lower().strip()
        best = None
        high = 0

        for e in entries:
            score = fuzz.token_set_ratio(t, e["text"].lower())
            if score > high:
                high = score
                best = {
                    "detected_text": e["text"],
                    "coordinates": e["box"],
                    "match_score": score,
                }

        return best if high >= 60 else None

    def verify(self, birth_doc_path, id_doc_path, user):
        report = {}

        # Extract text from docs
        birth_entries = self.extract_text_entries(birth_doc_path)
        id_entries = self.extract_text_entries(id_doc_path)

        # DOB
        report["date_of_birth"] = self.find_match(birth_entries, user.get("dob"))

        # Name fields
        for field in ["first_name", "middle_name", "last_name"]:
            report[field] = self.find_match(id_entries, user.get(field))

        # Gender
        report["gender"] = self.find_match(id_entries, user.get("gender"))

        return report
