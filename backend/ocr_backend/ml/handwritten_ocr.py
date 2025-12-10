import os
import cv2
import torch
import numpy as np
import re
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

# --- 1. CONFIGURATION ---
FILE_PATH = 'doc5.jpg'  # <--- Replace with your file
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin' # Update if needed

print(f"Running on: {device.upper()}")

# --- 2. LOAD MODELS ---

# A. TrOCR
print("Loading TrOCR model...")
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-handwritten')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-handwritten').to(device)

# B. GLiNER
print("Loading GLiNER model...")
ner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")

# C. CRAFT (Low-Level Loading)
print("Loading CRAFT models...")
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)

# --- 3. HELPER FUNCTIONS ---

def load_file_as_numpy_image(file_path):
    if not os.path.exists(file_path): return None
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        print(f"Detected PDF. Converting...")
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            return np.ascontiguousarray(np.array(pages[0].convert("RGB"))) if pages else None
        except Exception as e:
            print(f"PDF Error: {e}"); return None
    elif ext in ['.jpg', '.png', '.jpeg']:
        print(f"Detected Image.")
        return np.ascontiguousarray(np.array(Image.open(file_path).convert("RGB")))
    return None

def merge_boxes_into_lines(boxes, y_threshold=30):
    """
    Merges adjacent word-level boxes into a single line-level box.
    Crucial for fixing fragmentation (e.g., keeping 'Blood group' together).
    """
    if not boxes:
        return []

    # 1. Sort primarily by Y (top to bottom)
    boxes = sorted(boxes, key=lambda b: b[1])
    
    lines = []
    current_line = [boxes[0]]

    # 2. Group boxes into lines based on Y-proximity
    for i in range(1, len(boxes)):
        box = boxes[i]
        last_box = current_line[-1]

        # Calculate vertical center of boxes
        cy_box = box[1] + (box[3] / 2)
        cy_last = last_box[1] + (last_box[3] / 2)

        # If vertical centers are close, they are on the same line
        if abs(cy_box - cy_last) < y_threshold:
            current_line.append(box)
        else:
            lines.append(current_line)
            current_line = [box]
    lines.append(current_line)

    # 3. Merge the groups into single bounding boxes
    merged_results = []
    for line_boxes in lines:
        # Sort words inside the line Left-to-Right (X-coordinate)
        # This fixes the "A- blood group" vs "Blood group A-" ordering issue
        line_boxes = sorted(line_boxes, key=lambda b: b[0])
        
        x_min = min(b[0] for b in line_boxes)
        y_min = min(b[1] for b in line_boxes)
        x_max = max(b[0] + b[2] for b in line_boxes)
        y_max = max(b[1] + b[3] for b in line_boxes)
        
        w = x_max - x_min
        h = y_max - y_min
        
        merged_results.append((x_min, y_min, w, h))

    return merged_results

# --- 4. CRAFT DETECTION ---
def detect_text_craft(image_rgb):
    print("Running CRAFT prediction...")
    prediction_result = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.7,
        link_threshold=0.4,
        low_text=0.4,
        cuda=USE_GPU,
        long_size=1280
    )
    
    # Extract raw word boxes
    raw_boxes = prediction_result["boxes"]
    formatted_boxes = []
    
    for box in raw_boxes:
        box_np = np.array(box).astype(int)
        x_min = np.min(box_np[:, 0])
        x_max = np.max(box_np[:, 0])
        y_min = np.min(box_np[:, 1])
        y_max = np.max(box_np[:, 1])
        
        w = x_max - x_min
        h = y_max - y_min
        
        # Filter noise
        if w > 10 and h > 10:
            formatted_boxes.append((x_min, y_min, w, h))
            
    print(f"Raw word boxes found: {len(formatted_boxes)}")
    
    # MERGE STEP: Group words into full lines
    final_lines = merge_boxes_into_lines(formatted_boxes, y_threshold=30)
    print(f"Merged into text lines: {len(final_lines)}")
    
    return final_lines

# --- 5. OCR PIPELINE ---
def run_ocr_pipeline(file_path):
    image_numpy_rgb = load_file_as_numpy_image(file_path)
    if image_numpy_rgb is None: return []

    # Detect & Merge
    boxes = detect_text_craft(image_numpy_rgb)

    # Read Text
    pil_image = Image.fromarray(image_numpy_rgb)
    lines_data = [] 

    for i, (x, y, w, h) in enumerate(boxes):
        pad = 8 # Slightly increased padding for context
        img_h, img_w, _ = image_numpy_rgb.shape
        
        x_new = max(0, int(x) - pad)
        y_new = max(0, int(y) - pad)
        w_new = min(img_w - x_new, int(w) + 2*pad)
        h_new = min(img_h - y_new, int(h) + 2*pad)

        cropped = pil_image.crop((x_new, y_new, x_new+w_new, y_new+h_new))
        pixel_values = processor(images=cropped, return_tensors="pt").pixel_values.to(device)

        with torch.no_grad():
            outputs = model.generate(
                pixel_values, 
                return_dict_in_generate=True, 
                output_scores=True
            )
            generated_ids = outputs.sequences
            text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            try:
                transition_scores = model.compute_transition_scores(
                    sequences=generated_ids, scores=outputs.scores, normalize_logits=True
                )
                conf = torch.exp(transition_scores.mean()).item()
            except:
                conf = 0.0

        lines_data.append({
            "text": text,
            "coordinates": [int(x), int(x+w), int(y), int(y+h)],
            "ocr_confidence": round(conf, 4)
        })
        print(f"  Line {i+1}: {text} (Conf: {conf:.2f})")

    return lines_data

# --- 6. FIELD EXTRACTION ---
def extract_fields_with_coords(lines_data):
    full_text_block = "\n".join([line['text'] for line in lines_data])
    final_output = {}

    def map_to_line(value_text):
        if not value_text: return [], 0.0
        # Exact match
        for line in lines_data:
            if value_text in line['text']:
                return line['coordinates'], line['ocr_confidence']
        # Partial match
        for line in lines_data:
            if value_text in line['text'] or line['text'] in value_text:
                if len(line['text']) > 3: 
                    return line['coordinates'], line['ocr_confidence']
        return [], 0.0

    # --- A. REGEX ---
    
    # 1. Pincode (UPDATED)
    # Strategy: Check strictly line-by-line first to handle "691 00 4"
    pincode_found = False
    for line in lines_data:
        # Remove spaces to check for hidden pincodes
        clean_text = line['text'].replace(" ", "").strip()
        
        # Check if line is exactly 6 digits (e.g., "691 00 4" -> "691004")
        if clean_text.isdigit() and len(clean_text) == 6:
            # We found a standalone pincode line
            final_output["Pincode"] = {
                "value": clean_text, 
                "coordinates": line['coordinates'], 
                "confidence_score": line['ocr_confidence']
            }
            pincode_found = True
            break
            
        # Check if line contains label + 6 digits (e.g. "Pin: 560 068")
        if "pin" in line['text'].lower():
            digits = "".join(filter(str.isdigit, line['text']))
            if len(digits) == 6:
                final_output["Pincode"] = {
                    "value": digits, 
                    "coordinates": line['coordinates'], 
                    "confidence_score": line['ocr_confidence']
                }
                pincode_found = True
                break
    
    # Fallback: strict regex on full block if line-by-line failed
    if not pincode_found:
        pin_match = re.search(r'\b\d{6}\b', full_text_block)
        if pin_match:
            val = pin_match.group(0)
            coords, conf = map_to_line(val)
            final_output["Pincode"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}

    # 2. Phone Number (NEW ADDITION)
    # We add this BEFORE GLiNER because Regex is better at catching "98959 - 75260"
    # This pattern catches 10-15 digits with optional spaces or hyphens
    phone_match = re.search(r'(?:Ph|Phone|Mob|Mobile|Cell)?\s*[:\.]?\s*(\+?\d[\d\s\-]{8,15}\d)', full_text_block, re.IGNORECASE)
    if phone_match:
        raw_val = phone_match.group(1)
        # Clean the value (remove spaces/hyphens) for final output
        clean_phone = re.sub(r'[\s\-]', '', raw_val)
        
        if len(clean_phone) >= 10:
            # We map using the RAW value (with spaces) to find coordinates correctly
            coords, conf = map_to_line(raw_val.strip())
            
            # If map_to_line fails (because raw_val spans lines or is partial), try finding the line containing the first chunk
            if not coords:
                first_chunk = raw_val.split('-')[0].strip()
                coords, conf = map_to_line(first_chunk)

            final_output["Phone"] = {"value": clean_phone, "coordinates": coords, "confidence_score": conf if conf else 0.8}

    # 3. Email (No change)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text_block)
    if email_match:
        val = email_match.group(0)
        coords, conf = map_to_line(val)
        final_output["Email"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}

    # 4. Blood Group (No change)
    bg_found = False
    for line in lines_data:
        t = line['text']
        bg_match = re.search(r'\b(A|B|AB|O)[-\s]?(?:positive|negative|\+ve|\-ve|[\+\-])', t, re.IGNORECASE)
        if bg_match:
            raw_val = bg_match.group(0)
            norm_val = raw_val.upper().replace('POSITIVE','+').replace('NEGATIVE','-').replace('VE','').replace(' ','').strip()
            final_output["Blood Group"] = {"value": norm_val, "coordinates": line['coordinates'], "confidence_score": line['ocr_confidence']}
            bg_found = True
            break
    if not bg_found:
        bg_match = re.search(r'\b(A|B|AB|O)[\+\-]', full_text_block, re.IGNORECASE)
        if bg_match:
            val = bg_match.group(0).upper()
            coords, conf = map_to_line(val)
            final_output["Blood Group"] = {"value": val, "coordinates": coords, "confidence_score": conf}

    # 5. Gender (No change)
    gender_match = re.search(r'\b(Male|Female|M|F)\b', full_text_block, re.IGNORECASE)
    if gender_match:
        val = gender_match.group(0)
        norm_val = "Male" if val.lower() in ['m','male'] else "Female"
        coords, conf = map_to_line(val)
        final_output["Gender"] = {"value": norm_val, "coordinates": coords, "confidence_score": conf if conf else 1.0}

    # --- B. AI EXTRACTION (GLiNER) ---
    labels = ["person name", "phone number", "date of birth", "full address", "city", "state", "country"]
    entities = ner_model.predict_entities(full_text_block, labels, threshold=0.3)

    for ent in entities:
        lbl = ent["label"]
        txt = ent["text"].strip()
        score = round(ent["score"], 2)
        coords, conf = map_to_line(txt)
        
        final_conf = conf if conf > 0 else score

        key_map = {
            "person name": "Name",
            "phone number": "Phone",
            "date of birth": "DOB",
            "city": "City",
            "state": "State",
            "country": "Country"
        }

        if lbl in key_map:
            key = key_map[lbl]
            # Priority Check:
            # If we already found "Phone" or "Pincode" via Regex, usually Regex is more accurate for digits.
            # Only overwrite if GLiNER confidence is significantly higher or if Regex missed it.
            if key not in final_output:
                final_output[key] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
        
        elif lbl == "full address":
            if "Address" in final_output:
                if txt not in final_output["Address"]["value"]:
                    final_output["Address"]["value"] += ", " + txt
            else:
                final_output["Address"] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}

    return final_output

# --- EXECUTE ---
if __name__ == "__main__":
    ocr_lines = run_ocr_pipeline(FILE_PATH)
    
    if ocr_lines:
        structured_result = extract_fields_with_coords(ocr_lines)
        
        print("\n" + "="*90)
        print(f"{'FIELD':<15} | {'VALUE':<35} | {'CONF':<5} | {'COORDS [x1, x2, y1, y2]'}")
        print("="*90)
        
        for field, data in structured_result.items():
            print(f"{field:<15} | {data['value']:<35} | {data['confidence_score']:<5} | {data['coordinates']}")
