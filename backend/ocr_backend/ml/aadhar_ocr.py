import os
import cv2
import torch
import numpy as np
import re
import json
from datetime import datetime
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from gliner import GLiNER

# --- IMPORT LOW-LEVEL CRAFT FUNCTIONS ---
from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    empty_cuda_cache
)

# ============================================================================
# 0. CRITICAL HOTFIX FOR CRAFT
# ============================================================================
import craft_text_detector.craft_utils as craft_utils

def clean_english_text(text):
    if not text: return None
    # 1. Clean basic noise
    text = re.sub(r'[^a-zA-Z0-9\s\.\,\:\/\-\(\)\&]', '', text).strip()
    
    # 2. Poison List (Common Hindi->English Hallucinations)
    poison_words = {'fett', 'fram', 'ana', 'faxn', 'usar', 'highan', 'pthz'}
    
    words = text.split()
    valid_words = []
    allow_list = {'mr', 'mrs', 'dr', 'st', 'rd', 'ln', 'no', 'id', 'male', 'female'} 

    for word in words:
        clean_word = word.lower().strip(".,:/-")
        if clean_word in poison_words: continue
        if re.search(r'\d', word): # Keep numbers
            valid_words.append(word); continue
        if len(word) == 1 and word in ".,:/-&": # Keep punctuation
            valid_words.append(word); continue

        has_vowel = bool(re.search(r'[aeiouy]', clean_word))
        if has_vowel or clean_word in allow_list:
            valid_words.append(word)

    final_text = " ".join(valid_words).strip()
    if len(final_text) < 3 or not re.search(r'[a-zA-Z0-9]', final_text): return None
    return final_text

def safe_adjustResultCoordinates(polys, ratio_w, ratio_h, ratio_net=2):
    fixed_polys = []
    if len(polys) > 0:
        for k in range(len(polys)):
            if polys[k] is not None:
                poly = np.array(polys[k])
                poly *= (ratio_w * ratio_net, ratio_h * ratio_net)
                x_min, y_min = np.min(poly, axis=0)
                x_max, y_max = np.max(poly, axis=0)
                standard_box = np.array([[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]], dtype=np.float32)
                fixed_polys.append(standard_box)
    return np.array(fixed_polys)

craft_utils.adjustResultCoordinates = safe_adjustResultCoordinates
# ============================================================================

# --- 1. CONFIGURATION ---
FILE_PATH = 'aad.pdf'   # <--- Supports multi-page PDF now
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin' 

print(f"Running on: {device.upper()}")

# --- 2. LOAD MODELS ---
print("Loading TrOCR (Printed)...")
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed').to(device)

print("Loading GLiNER...")
ner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1").to(device)

print("Loading CRAFT...")
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)

# --- 3. HELPER FUNCTIONS ---

def load_file_as_images(file_path):
    """
    Returns a LIST of images. 
    If PDF: returns [page1, page2, ...]
    If Image: returns [image]
    """
    if not os.path.exists(file_path): return []
    ext = os.path.splitext(file_path)[1].lower()
    
    images = []
    if ext == '.pdf':
        try:
            # Removed 'last_page=1' so it processes ALL pages
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
            for page in pages:
                images.append(np.ascontiguousarray(np.array(page.convert("RGB"))))
        except Exception as e: print(f"PDF Error: {e}")
    elif ext in ['.jpg', '.png', '.jpeg']:
        images.append(np.ascontiguousarray(np.array(Image.open(file_path).convert("RGB"))))
    
    return images

def merge_boxes_into_lines(boxes, y_threshold=12):
    if not boxes: return []
    boxes = sorted(boxes, key=lambda b: b[1])
    lines = []
    current_line = [boxes[0]]

    for i in range(1, len(boxes)):
        box = boxes[i]
        last_box = current_line[-1]
        cy_box = box[1] + (box[3] / 2)
        cy_last = last_box[1] + (last_box[3] / 2)

        if abs(cy_box - cy_last) < y_threshold:
            current_line.append(box)
        else:
            lines.append(current_line)
            current_line = [box]
    lines.append(current_line)

    merged_results = []
    for line_boxes in lines:
        line_boxes = sorted(line_boxes, key=lambda b: b[0])
        x_min = min(b[0] for b in line_boxes)
        y_min = min(b[1] for b in line_boxes)
        x_max = max(b[0] + b[2] for b in line_boxes)
        y_max = max(b[1] + b[3] for b in line_boxes)
        merged_results.append((int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)))

    return merged_results

# --- 4. CRAFT DETECTION ---
def detect_text_craft(image_rgb):
    prediction_result = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.6,
        link_threshold=0.3,
        low_text=0.3,
        cuda=USE_GPU,
        long_size=1280
    )
    raw_boxes = prediction_result["boxes"]
    formatted_boxes = []
    for box in raw_boxes:
        box_np = np.array(box).astype(int)
        x_min, x_max = np.min(box_np[:, 0]), np.max(box_np[:, 0])
        y_min, y_max = np.min(box_np[:, 1]), np.max(box_np[:, 1])
        w, h = x_max - x_min, y_max - y_min
        if w > 8 and h > 8: formatted_boxes.append((x_min, y_min, w, h))
            
    return merge_boxes_into_lines(formatted_boxes, y_threshold=12)

# --- 5. MULTI-PAGE OCR PIPELINE ---
def run_ocr_pipeline(file_path):
    images = load_file_as_images(file_path) # Now returns list of images
    if not images: return []

    all_pages_data = []

    print(f"DEBUG: Processing {len(images)} page(s)...")

    # Loop through every page found in the PDF
    for page_idx, image_numpy_rgb in enumerate(images):
        current_page_num = page_idx + 1
        print(f"\n--- Processing Page {current_page_num} ---")
        
        boxes = detect_text_craft(image_numpy_rgb)
        pil_image = Image.fromarray(image_numpy_rgb)
        
        for i, (x, y, w, h) in enumerate(boxes):
            pad = 4
            img_h, img_w, _ = image_numpy_rgb.shape
            x_new, y_new = max(0, int(x) - pad), max(0, int(y) - pad)
            w_new, h_new = min(img_w - x_new, int(w) + 2*pad), min(img_h - y_new, int(h) + 2*pad)
            cropped = pil_image.crop((x_new, y_new, x_new+w_new, y_new+h_new))

            pixel_values = processor(images=cropped, return_tensors="pt").pixel_values.to(device)
            
            with torch.no_grad():
                outputs = model.generate(pixel_values, return_dict_in_generate=True, output_scores=True)
                raw_text = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
                try:
                    conf = torch.exp(model.compute_transition_scores(
                        sequences=outputs.sequences, scores=outputs.scores, normalize_logits=True
                    ).mean()).item()
                except: conf = 0.5

            is_likely_id = bool(re.search(r'[A-Z]{3}[0-9]{7}', raw_text))
            
            if conf < 0.55 and not is_likely_id:
                continue
                
            cleaned_text = clean_english_text(raw_text)

            if cleaned_text:
                all_pages_data.append({
                    "text": cleaned_text,
                    "coordinates": [int(x), int(x+w), int(y), int(y+h)],
                    "ocr_confidence": round(conf, 4),
                    "page": current_page_num  # <--- STORE PAGE NUMBER HERE
                })
                print(f"P{current_page_num} | Line {i+1:02d} | {cleaned_text}")

    print("="*50 + "\n")
    return all_pages_data

# --- 6. EXTRACTION LOGIC (WITH PAGE SUPPORT) ---
def extract_fields_with_coords(lines_data):
    full_text_block = "\n".join([line['text'] for line in lines_data])
    final_output = {}

    # --- UPDATED MAPPER: Returns (Coords, Conf, Page) ---
    def map_to_line(value_text):
        if not value_text: return [], 0.0, None
        value_lower = value_text.lower()
        
        # 1. Exact Match
        for line in lines_data:
            if value_lower in line['text'].lower(): 
                return line['coordinates'], line['ocr_confidence'], line['page']
        
        # 2. Fuzzy Match
        for line in lines_data:
            line_lower = line['text'].lower()
            if value_lower in line_lower or line_lower in value_lower:
                if len(line['text']) > 4: 
                    return line['coordinates'], line['ocr_confidence'], line['page']
        return [], 0.0, None

    # --- 1. DOB (Chronological Sort) ---
    date_pattern = r'\b\d{2}[/-]\d{2}[/-]\d{4}\b'
    all_date_matches = re.findall(date_pattern, full_text_block)
    parsed_dates = []

    for raw_date_str in all_date_matches:
        clean_date_str = raw_date_str.replace('/', '-')
        try:
            dt_object = datetime.strptime(clean_date_str, "%d-%m-%Y")
            parsed_dates.append((dt_object, raw_date_str))
        except ValueError: continue

    if parsed_dates:
        parsed_dates.sort(key=lambda x: x[0]) # Sort oldest first
        earliest_raw_val = parsed_dates[0][1]
        
        coords, conf, page = map_to_line(earliest_raw_val)
        final_output["DOB"] = {
            "value": earliest_raw_val.replace('/', '-'), 
            "coordinates": coords, 
            "confidence_score": conf,
            "page": page
        }

    # --- 2. GENDER ---
    gender_match = re.search(r'\b(Male|Female|Transgender)\b', full_text_block, re.IGNORECASE)
    if gender_match:
        raw_val = gender_match.group(0)
        coords, conf, page = map_to_line(raw_val)
        final_output["Gender"] = {
            "value": raw_val.title(), "coordinates": coords, "confidence_score": conf, "page": page
        }

    # --- 3. GLiNER ---
    labels = ["person name", "address", "city", "state"]
    entities = ner_model.predict_entities(full_text_block, labels, threshold=0.3)
    key_mapping = {"person name": "Name", "address": "Address", "city": "City", "state": "State"}

    for ent in entities:
        lbl, txt, score = ent['label'], ent['text'].strip(), round(float(ent['score']), 4)
        if lbl in key_mapping:
            target_key = key_mapping[lbl]
            coords, conf, page = map_to_line(txt)
            final_conf = conf if conf > 0 else score 

            if target_key == "Address":
                if "Address" in final_output:
                      # Avoid duplicates if GLiNER detects parts of the same address
                      if txt not in final_output["Address"]["value"]: 
                          final_output["Address"]["value"] += ", " + txt
                else: 
                    final_output["Address"] = {
                        "value": txt, "coordinates": coords, "confidence_score": final_conf, "page": page
                    }
            elif target_key not in final_output:
                final_output[target_key] = {
                    "value": txt, "coordinates": coords, "confidence_score": final_conf, "page": page
                }

    # --- 4. NAME SPLITTING ---
    if "Name" in final_output:
        full_name = final_output["Name"]["value"]
        coords = final_output["Name"]["coordinates"]
        conf = final_output["Name"]["confidence_score"]
        page = final_output["Name"]["page"]
        
        parts = full_name.split()
        first, middle, last = "", "", ""
        if len(parts) == 1: first = parts[0]
        elif len(parts) == 2: first, last = parts[0], parts[1]
        elif len(parts) >= 3: first, last, middle = parts[0], parts[-1], " ".join(parts[1:-1])
        
        final_output["First Name"] = {"value": first, "coordinates": coords, "confidence_score": conf, "page": page}
        final_output["Middle Name"] = {"value": middle, "coordinates": coords, "confidence_score": conf, "page": page}
        final_output["Last Name"] = {"value": last, "coordinates": coords, "confidence_score": conf, "page": page}
        del final_output["Name"]

    # --- 5. CLEAN OUTPUT (Remove Nulls) ---
    required = ["First Name", "Middle Name", "Last Name", "DOB", "Gender", "Address", "City", "State"]
    
    # Only include keys that exist in final_output and are not None
    clean_results = {k: final_output.get(k) for k in required if final_output.get(k) is not None}
    
    return {"fields": clean_results}
# --- EXECUTE ---
if __name__ == "__main__":
    ocr_lines = run_ocr_pipeline(FILE_PATH)
    if ocr_lines:
        result = extract_fields_with_coords(ocr_lines)
        print(json.dumps(result, indent=4))