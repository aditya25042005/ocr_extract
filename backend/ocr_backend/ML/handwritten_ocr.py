import os
import re
import cv2
import torch
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from gliner import GLiNER

from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    empty_cuda_cache,
)

from thefuzz import fuzz

# ---- CONFIG ----
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
POPPLER_PATH = "/opt/homebrew/bin"  # update if needed

# Local cache path for TrOCR (update to your actual snapshot path)
MODEL_CACHE = (
    "/Users/adityagupta/Desktop/Coding/MosipBackend/ocr_extract/backend/ocr_backend/ML/"
    "model_cache/models--microsoft--trocr-large-handwritten/snapshots/"
    "e68501f437cd2587ae5d68ee457964cac824ddee"
)

# ---- LOAD MODELS (local_files_only to prevent re-download) ----
# Load TrOCR
try:
    processor = TrOCRProcessor.from_pretrained(MODEL_CACHE, local_files_only=True)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_CACHE, local_files_only=True).to(device)
except Exception as e:
    # fail loudly for debugging when model path is incorrect
    raise RuntimeError(f"Failed to load TrOCR from {MODEL_CACHE}: {e}")

# Load GLiNER (NER model)
try:
    ner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
except Exception:
    ner_model = None  # GLiNER optional — we'll guard its use later

# Load CRAFT models
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)


# -------------------
# Helper utilities
# -------------------

def load_file_as_numpy_image(file_path):
    """Load PDF or image into a HWC RGB numpy array."""
    if not os.path.exists(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()
    # PDF support
    if ext == ".pdf" or file_path.lower().endswith(".pdf"):
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            if not pages:
                return None
            return np.ascontiguousarray(np.array(pages[0].convert("RGB")))
        except Exception:
            # fall-through to image loader
            pass

    try:
        pil = Image.open(file_path).convert("RGB")
        return np.ascontiguousarray(np.array(pil))
    except Exception:
        # as a last resort, try converting as PDF again (handles wrong extension)
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            if not pages:
                return None
            return np.ascontiguousarray(np.array(pages[0].convert("RGB")))
        except Exception:
            return None


def merge_boxes_into_lines(boxes, y_threshold=30):
    """Given word-level boxes (x,y,w,h) group them into line boxes."""
    if not boxes:
        return []

    boxes = sorted(boxes, key=lambda b: b[1])
    lines = []
    current = [boxes[0]]
    for box in boxes[1:]:
        last = current[-1]
        cy_box = box[1] + box[3] / 2
        cy_last = last[1] + last[3] / 2
        if abs(cy_box - cy_last) < y_threshold:
            current.append(box)
        else:
            lines.append(current)
            current = [box]
    lines.append(current)

    merged = []
    for group in lines:
        group = sorted(group, key=lambda b: b[0])
        x_min = min(b[0] for b in group)
        y_min = min(b[1] for b in group)
        x_max = max(b[0] + b[2] for b in group)
        y_max = max(b[1] + b[3] for b in group)
        merged.append((x_min, y_min, x_max - x_min, y_max - y_min))
    return merged


def detect_text_craft(image_rgb):
    """Run CRAFT text detector and return merged line boxes (x,y,w,h)."""
    print("Running CRAFT prediction...")

    prediction_result = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.3,
        link_threshold=0.1,
        low_text=0.2,
        cuda=USE_GPU,
        long_size=1500,
    )

    # Normalise 'boxes' safely (handle None, list, numpy array)
    raw_boxes = prediction_result.get("boxes", None)
    if raw_boxes is None:
        raw_boxes = []
    elif isinstance(raw_boxes, np.ndarray):
        # Convert ndarray of polygons into Python list
        try:
            raw_boxes = raw_boxes.tolist()
        except Exception:
            # Fallback: iterate rows
            raw_boxes = [np.array(b).tolist() for b in raw_boxes]
    elif not isinstance(raw_boxes, (list, tuple)):
        # unexpected type — coerce to empty
        raw_boxes = []

    # If empty, return early
    if not raw_boxes:
        print("CRAFT DETECTED ZERO BOXES ❌")
        return []

    # Convert poly boxes -> word boxes (x,y,w,h)
    formatted_boxes = []
    for box in raw_boxes:
        try:
            box_np = np.array(box).astype(int)
            x_min = np.min(box_np[:, 0])
            x_max = np.max(box_np[:, 0])
            y_min = np.min(box_np[:, 1])
            y_max = np.max(box_np[:, 1])

            w = x_max - x_min
            h = y_max - y_min

            if w > 5 and h > 5:
                formatted_boxes.append((x_min, y_min, w, h))
        except Exception as ex:
            # ignore malformed boxes but log minimal info
            print("Skipping malformed box:", ex)
            continue

    if not formatted_boxes:
        print("No valid formatted boxes after filtering.")
        return []

    # Merge into line-level boxes
    final_lines = merge_boxes_into_lines(formatted_boxes, y_threshold=40)

    print("Merged lines:", len(final_lines))
    return final_lines



def recognize_crop_with_trocr(pil_image):
    """Return text and (optionally) a confidence inference using TrOCR."""
    pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values.to(device)
    with torch.no_grad():
        outputs = model.generate(pixel_values, return_dict_in_generate=True, output_scores=True)
        generated_ids = outputs.sequences
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # attempt to compute a stable confidence if possible
        try:
            scores = outputs.scores  # list of tensors
            # compute average of max probabilities per step (approximate)
            stacked = torch.stack(scores, dim=1)  # (batch, seq, vocab)
            probs = torch.nn.functional.softmax(stacked, dim=-1)
            token_ids = generated_ids[:, 1 : 1 + probs.shape[1]]
            sel = torch.gather(probs, 2, token_ids.unsqueeze(-1)).squeeze(-1)
            conf = float(sel.mean().clamp(0.0, 1.0).item())
        except Exception:
            conf = 0.0

    return text.strip(), round(conf, 4)


def format_box_xywh_to_xyxy(box):
    x, y, w, h = box
    return [int(x), int(x + w), int(y), int(y + h)]


# ----------------------
# OCR pipeline
# ----------------------

def run_ocr_pipeline(file_path):
    """Detect text lines and recognize each line. Returns list of dicts: {text, coordinates, ocr_confidence}"""
    image_rgb = load_file_as_numpy_image(file_path)
    if image_rgb is None:
        return []

    boxes = detect_text_craft(image_rgb)

    pil_image = Image.fromarray(image_rgb)
    lines_data = []
    for i, (x, y, w, h) in enumerate(boxes):
        pad = 8
        img_h, img_w = image_rgb.shape[0], image_rgb.shape[1]
        x0 = max(0, int(x) - pad)
        y0 = max(0, int(y) - pad)
        x1 = min(img_w, int(x + w) + pad)
        y1 = min(img_h, int(y + h) + pad)
        cropped = pil_image.crop((x0, y0, x1, y1))
        text, conf = recognize_crop_with_trocr(cropped)
        if text is None:
            continue
        lines_data.append({
            "text": text,
            "coordinates": format_box_xywh_to_xyxy((x, y, w, h)),
            "ocr_confidence": conf
        })

    return lines_data


# ----------------------
# Field extraction
# ----------------------

def find_raw_line(keywords, lines_data):
    """Return the first line text and confidence containing any keyword (case-insensitive)."""
    if not keywords:
        return None, 0.0
    for line in lines_data:
        lt = line["text"].lower()
        if any(kw.lower() in lt for kw in keywords):
            return line["text"], line["ocr_confidence"]
    return None, 0.0


def map_to_line(value_text, lines_data):
    """Return coords and confidence of the line containing value_text (exact substring); else ([],0.0)."""
    if not value_text:
        return [], 0.0
    for line in lines_data:
        if value_text in line["text"]:
            return line["coordinates"], line["ocr_confidence"]
    # try case-insensitive
    for line in lines_data:
        if value_text.lower() in line["text"].lower():
            return line["coordinates"], line["ocr_confidence"]
    return [], 0.0


def extract_fields_with_coords(lines_data):
    """Main extractor that returns structured fields + raw lines + confidences."""
    full_text_block = "\n".join([ld["text"] for ld in lines_data])
    final_output = {}

    # helper to standardize date-like strings (very basic)
    def normalize_date_str(s):
        s = s.strip()
        m = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', s)
        if m:
            return m.group(1)
        m = re.search(r'(\d{2}[-/]\d{2}[-/]\d{2})', s)
        if m:
            return m.group(1)
        return s

    # ---------- PINCODE ----------
    pincode_found = False
    for line in lines_data:
        clean = re.sub(r'\s+', '', line["text"])
        if clean.isdigit() and len(clean) == 6:
            final_output["Pincode"] = {
                "value": clean,
                "raw_line": line["text"],
                "coordinates": line["coordinates"],
                "confidence_score": line["ocr_confidence"],
            }
            pincode_found = True
            break
        if "pin" in line["text"].lower():
            digits = "".join(filter(str.isdigit, line["text"]))
            if len(digits) == 6:
                final_output["Pincode"] = {
                    "value": digits,
                    "raw_line": line["text"],
                    "coordinates": line["coordinates"],
                    "confidence_score": line["ocr_confidence"],
                }
                pincode_found = True
                break
    if not pincode_found:
        pin_match = re.search(r'\b\d{6}\b', full_text_block)
        if pin_match:
            val = pin_match.group(0)
            coords, conf = map_to_line(val, lines_data)
            final_output["Pincode"] = {"value": val, "raw_line": val, "coordinates": coords, "confidence_score": conf}

    # ---------- PHONE ----------
    phone_val = None
    phone_coords = []
    phone_conf = 0.0
    labeled_match = re.search(r'(?:Ph|Phone|Mob|Mobile|Cell|Tel)\s*[:\.]?\s*([+\d\s\-]{7,20})', full_text_block, re.IGNORECASE)
    if labeled_match:
        raw_val = labeled_match.group(1)
        phone_val = re.sub(r'[^\d]', '', raw_val)
        phone_coords, phone_conf = map_to_line(raw_val.strip(), lines_data)
    if not phone_val:
        candidates = re.finditer(r'\b(?:\+?[\d\s\-]{10,15})\b', full_text_block)
        for cand in candidates:
            raw_text = cand.group(0).strip()
            clean_text = re.sub(r'[^\d]', '', raw_text)
            if len(clean_text) < 10 or len(clean_text) > 13:
                continue
            if raw_text.count('-') >= 2 or raw_text.count('/') >= 2:
                continue
            if "Pincode" in final_output and clean_text == final_output["Pincode"]["value"]:
                continue
            phone_val = clean_text
            phone_coords, phone_conf = map_to_line(raw_text, lines_data)
            if not phone_coords:
                phone_coords, phone_conf = map_to_line(clean_text, lines_data)
            break
    if phone_val:
        final_output["Phone"] = {
            "value": phone_val,
            "raw_line": phone_coords and next((l["text"] for l in lines_data if l["coordinates"] == phone_coords), phone_val),
            "coordinates": phone_coords,
            "confidence_score": phone_conf or 0.0,
        }

    # ---------- EMAIL ----------
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', full_text_block)
    if email_match:
        val = email_match.group(0)
        coords, conf = map_to_line(val, lines_data)
        final_output["Email"] = {"value": val, "raw_line": val, "coordinates": coords, "confidence_score": conf or 0.0}

    # ---------- BLOOD GROUP ----------
    raw_bg_line, raw_bg_conf = find_raw_line(["blood", "blood group", "bloodgroup"], lines_data)
    bg_found = False
    for line in lines_data:
        t = line["text"]
        m = re.search(r'\b(A|B|AB|O)[\s\-]?(?:positive|negative|\+ve|\-ve|[\+\-])', t, re.IGNORECASE)
        if m:
            raw_val = m.group(0)
            norm_val = raw_val.upper().replace("POSITIVE", "+").replace("NEGATIVE", "-").replace("VE", "").replace(" ", "")
            final_output["Blood Group"] = {
                "raw_line": raw_bg_line or t,
                "value": norm_val,
                "coordinates": line["coordinates"],
                "confidence_score": max(line["ocr_confidence"], raw_bg_conf),
            }
            bg_found = True
            break
    if not bg_found:
        m = re.search(r'\b(A|B|AB|O)[\+\-]\b', full_text_block, re.IGNORECASE)
        if m:
            val = m.group(0).upper()
            coords, conf = map_to_line(val, lines_data)
            final_output["Blood Group"] = {"raw_line": val, "value": val, "coordinates": coords, "confidence_score": conf}

    # ---------- GENDER ----------
    raw_gender_line, raw_gender_conf = find_raw_line(["gender", "sex"], lines_data)
    gender_match = re.search(r'\b(Male|Female|M|F|Other|O)\b', full_text_block, re.IGNORECASE)
    if gender_match:
        val = gender_match.group(0)
        norm_val = "Other" if val.lower() in ["o", "other"] else ("Male" if val.lower() in ["m", "male"] else "Female")
        coords, conf = map_to_line(val, lines_data)
        final_output["Gender"] = {
            "raw_line": raw_gender_line or val,
            "value": norm_val,
            "coordinates": coords,
            "confidence_score": raw_gender_conf or conf or 0.0,
        }

    # ---------- DOB ----------
    raw_dob_line, raw_dob_conf = find_raw_line(["dob", "date of birth", "birth"], lines_data)
    dob_found = False
    for line in lines_data:
        m = re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', line["text"])
        if m:
            dt = normalize_date_str(m.group(0))
            final_output["DOB"] = {
                "raw_line": raw_dob_line or line["text"],
                "value": dt,
                "coordinates": line["coordinates"],
                "confidence_score": raw_dob_conf or line["ocr_confidence"],
            }
            dob_found = True
            break
    if not dob_found:
        m = re.search(r'\d{2}[-/]\d{2}[-/]\d{4}', full_text_block)
        if m:
            dt = normalize_date_str(m.group(0))
            coords, conf = map_to_line(m.group(0), lines_data)
            final_output["DOB"] = {"raw_line": m.group(0), "value": dt, "coordinates": coords, "confidence_score": conf}

    # ---------- ADDRESS (simple parsing) ----------
    # prefer lines that contain 'India' or a 6-digit pincode or comma-separated long address
    raw_address_line, raw_addr_conf = find_raw_line(["india", "pincode", "pin", ","], lines_data)
    if raw_address_line:
        # try to extract pincode/city/state from that line
        pin_in_line = re.search(r'\b\d{6}\b', raw_address_line)
        city_state = [s.strip() for s in raw_address_line.split(",") if s.strip()]
        city = city_state[0] if len(city_state) >= 1 else ""
        state = city_state[1] if len(city_state) >= 2 else ""
        country = city_state[-1] if len(city_state) >= 1 else ""
        final_output["Address"] = {
            "raw_line": raw_address_line,
            "city": city,
            "state": state,
            "country": country,
            "pincode": pin_in_line.group(0) if pin_in_line else (final_output.get("Pincode", {}).get("value")),
            "confidence_score": raw_addr_conf or 0.0,
        }

    # ---------- GLiNER (optional) ----------
    if ner_model is not None:
        try:
            labels = ["person name", "phone number", "date of birth", "full address", "city", "state", "country"]
            ents = ner_model.predict_entities(full_text_block, labels, threshold=0.3)
            for ent in ents:
                lbl = ent["label"]
                txt = ent["text"].strip()
                score = round(ent.get("score", 0.0), 2)
                coords, conf = map_to_line(txt, lines_data)
                final_conf = conf if conf and conf > 0 else score
                key_map = {
                    "person name": "Name",
                    "phone number": "Phone",
                    "date of birth": "DOB",
                    "city": "City",
                    "state": "State",
                    "country": "Country",
                }
                if lbl in key_map and key_map[lbl] not in final_output:
                    final_output[key_map[lbl]] = {"value": txt, "raw_line": txt, "coordinates": coords, "confidence_score": final_conf}
                elif ent["label"] == "full address" and "Address" not in final_output:
                    final_output["Address"] = {"raw_line": txt, "value": txt, "confidence_score": final_conf}
        except Exception:
            pass

    # ---------- NAME SPLIT ----------
    # If GLiNER found Name, use it; otherwise pick first long non-numeric line near top
    name_line = None
    if "Name" in final_output:
        name_line = final_output["Name"]["value"]
        name_conf = final_output["Name"].get("confidence_score", 0.0)
    else:
        # find top-most line that looks like a name (letters & short)
        for line in lines_data:
            t = line["text"]
            if len(t) > 2 and not any(ch.isdigit() for ch in t) and len(t.split()) <= 5:
                name_line = t
                name_conf = line["ocr_confidence"]
                break

    if name_line:
        parts = name_line.strip().split()
        first = parts[0] if len(parts) >= 1 else ""
        last = parts[-1] if len(parts) >= 2 else ""
        middle = " ".join(parts[1:-1]) if len(parts) > 2 else ""
        final_output["Name Raw"] = {
            "raw_line": name_line,
            "first_name": first,
            "middle_name": middle,
            "last_name": last,
            "confidence_score": name_conf or 0.0,
        }

    return final_output


# ----------------------
# Public function used by Django view
# ----------------------

def handwritten_extract(file_path):
    """
    Main function called by Django endpoint.
    Returns {'lines': [...], 'fields': {...}} or {'error': '...'}
    """
    if not os.path.exists(file_path):
        return {"error": "file not found"}

    image_size = os.path.getsize(file_path)
    if image_size == 0:
        return {"error": "empty file"}

    lines = run_ocr_pipeline(file_path)
    if not lines:
        return {"error": "OCR failed or image unreadable"}

    fields = extract_fields_with_coords(lines)

    return {"lines": lines, "fields": fields}
