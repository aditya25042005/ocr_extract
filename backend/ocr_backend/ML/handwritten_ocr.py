import os
import cv2
import torch
import numpy as np
import re
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from gliner import GLiNER

from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    empty_cuda_cache
)

FILE_PATH = 'doc7.jpg'
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
POPPLER_PATH = "/opt/homebrew/bin"

print(f"Running on: {device.upper()}")

# MODEL_CACHE = "/Users/adityagupta/Desktop/Coding/MosipBackend/ocr_extract/backend/ocr_backend/ML/model_cache/models--microsoft--trocr-large-handwritten/snapshots/e68501f437cd2587ae5d68ee457964cac824ddee"

#FOR KARN
# MODEL_CACHE = r"C:\Users\adity\Downloads\backend_ocr\ocr_extract\backend\ocr_backend\ML\model_cache\models--microsoft--trocr-large-handwritten\snapshots\e68501f437cd2587ae5d68ee457964cac824ddee"

# processor = TrOCRProcessor.from_pretrained(MODEL_CACHE, local_files_only=True)
# model = VisionEncoderDecoderModel.from_pretrained(MODEL_CACHE, local_files_only=True).to(device)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

snapshots_root = BASE_DIR / "ML" / "model_cache" / "models--microsoft--trocr-large-handwritten" / "snapshots"
MODEL_CACHE = next(snapshots_root.iterdir())  # autodetect snapshot folder

processor = TrOCRProcessor.from_pretrained(str(MODEL_CACHE), local_files_only=True)
model = VisionEncoderDecoderModel.from_pretrained(str(MODEL_CACHE), local_files_only=True).to(device)


print("Loading GLiNER model...")
ner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")

print("Loading CRAFT models...")
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)

def load_file_as_numpy_image(file_path):
    if not os.path.exists(file_path):
        return None
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        print(f"Detected PDF. Converting...")
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            return np.ascontiguousarray(np.array(pages[0].convert("RGB"))) if pages else None
        except Exception as e:
            print(f"PDF Error: {e}")
            return None
    try:
        return np.ascontiguousarray(np.array(Image.open(file_path).convert("RGB")))
    except:
        return None

def merge_boxes_into_lines(boxes, y_threshold=30):
    if not boxes:
        return []
    
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
        w = x_max - x_min
        h = y_max - y_min
        merged_results.append((x_min, y_min, w, h))
    
    return merged_results

def detect_text_craft(image_rgb):
    print("Running CRAFT prediction...")
    
    prediction_result = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.3,
        link_threshold=0.1,
        low_text=0.2,
        cuda=USE_GPU,
        long_size=1500
    )
    
    print("---- RAW CRAFT BOXES ----")
    print(prediction_result.get("boxes"))
    print("--------------------------")
    
    raw_boxes = prediction_result["boxes"]
    
    if raw_boxes is None or len(raw_boxes) == 0:
        print("CRAFT DETECTED ZERO BOXES ❌")
        return []
    
    formatted_boxes = []
    
    for box in raw_boxes:
        box_np = np.array(box).astype(int)
        x_min = np.min(box_np[:, 0])
        x_max = np.max(box_np[:, 0])
        y_min = np.min(box_np[:, 1])
        y_max = np.max(box_np[:, 1])
        w = x_max - x_min
        h = y_max - y_min
        if w > 5 and h > 5:
            formatted_boxes.append((x_min, y_min, w, h))
    
    print("RAW boxes:", len(raw_boxes), "Filtered:", len(formatted_boxes))
    
    final_lines = merge_boxes_into_lines(formatted_boxes, y_threshold=40)
    
    print("Merged lines:", len(final_lines))
    print("Final line boxes:", final_lines)
    
    return final_lines

def run_ocr_pipeline(file_path):
    print("HI")
    image_numpy_rgb = load_file_as_numpy_image(file_path)
    if image_numpy_rgb is None:
        return []
    
    boxes = detect_text_craft(image_numpy_rgb)
    
    print("========= DEBUG CRAFT =========")
    print("Detected raw boxes count:", len(boxes))
    print("Boxes:", boxes)
    print("================================")
    
    pil_image = Image.fromarray(image_numpy_rgb)
    lines_data = []
    
    for i, (x, y, w, h) in enumerate(boxes):
        pad = 8
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
        print(f" Line {i+1}: {text} (Conf: {conf:.2f})")
    
    print("Running CRAFT...")
    boxes = detect_text_craft(image_numpy_rgb)
    print("CRAFT returned boxes:", len(boxes), boxes)
    
    return lines_data

def extract_fields_with_coords(lines_data):
    full_text_block = "\n".join([line['text'] for line in lines_data])
    final_output = {}
    
    def map_to_line(value_text):
        if not value_text:
            return [], 0.0
        for line in lines_data:
            if value_text in line['text']:
                return line['coordinates'], line['ocr_confidence']
        for line in lines_data:
            if value_text in line['text'] or line['text'] in value_text:
                if len(line['text']) > 3:
                    return line['coordinates'], line['ocr_confidence']
        return [], 0.0
    
    pincode_found = False
    for line in lines_data:
        clean_text = line['text'].replace(" ", "").strip()
        if clean_text.isdigit() and len(clean_text) == 6:
            final_output["Pincode"] = {
                "value": clean_text,
                "coordinates": line['coordinates'],
                "confidence_score": line['ocr_confidence']
            }
            pincode_found = True
            break
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
    
    if not pincode_found:
        pin_match = re.search(r'\b\d{6}\b', full_text_block)
        if pin_match:
            val = pin_match.group(0)
            coords, conf = map_to_line(val)
            final_output["Pincode"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
    phone_val = None
    phone_coords = []
    phone_conf = 0.0
    
    labeled_match = re.search(r'(?:Ph|Phone|Mob|Mobile|Cell|Tel)\s*[:\.]?\s*([+\d\s\-]{10,15})', full_text_block, re.IGNORECASE)
    if labeled_match:
        raw_val = labeled_match.group(1)
        phone_val = re.sub(r'[^\d+]', '', raw_val)
        coords, conf = map_to_line(raw_val.strip())
        phone_coords, phone_conf = coords, conf
    
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
            coords, conf = map_to_line(raw_text)
            if not coords:
                coords, conf = map_to_line(clean_text)
            
            phone_coords, phone_conf = coords, conf
            break
    
    if phone_val:
        final_output["Phone"] = {"value": phone_val, "coordinates": phone_coords, "confidence_score": phone_conf if phone_conf else 0.8}
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text_block)
    if email_match:
        val = email_match.group(0)
        coords, conf = map_to_line(val)
        final_output["Email"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
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
    
    gender_match = re.search(r'\b(Male|Female|M|F)\b', full_text_block, re.IGNORECASE)
    if gender_match:
        val = gender_match.group(0)
        norm_val = "Male" if val.lower() in ['m','male'] else "Female"
        coords, conf = map_to_line(val)
        final_output["Gender"] = {"value": norm_val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
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
            if key not in final_output:
                final_output[key] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
        elif lbl == "full address":
            if "Address" in final_output:
                if txt not in final_output["Address"]["value"]:
                    final_output["Address"]["value"] += ", " + txt
            else:
                final_output["Address"] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
    
    if "Name" in final_output:
        full_name = final_output["Name"]["value"].strip()
        coords = final_output["Name"]["coordinates"]
        conf = final_output["Name"]["confidence_score"]
        parts = full_name.split()
        first_name = ""
        middle_name = ""
        last_name = ""
        if len(parts) == 1:
            first_name = parts[0]
            last_name = ""
        elif len(parts) == 2:
            first_name = parts[0]
            last_name = parts[1]
        elif len(parts) >= 3:
            first_name = parts[0]
            last_name = parts[-1]
            middle_name = " ".join(parts[1:-1])
        
        final_output["First Name"] = {"value": first_name, "coordinates": coords, "confidence_score": conf}
        final_output["Middle Name"] = {"value": middle_name, "coordinates": coords, "confidence_score": conf}
        final_output["Last Name"] = {"value": last_name, "coordinates": coords, "confidence_score": conf}
        del final_output["Name"]
    
    return final_output

def handwritten_extract(file_path):
    print("==== USING UPDATED HANDWRITTEN OCR FILE ====")
    print("file path is: ", file_path)
    
    print("File exists:", os.path.exists(file_path))
    print("File size:", os.path.getsize(file_path))
    
    try:
        img = Image.open(file_path)
        print("Image loaded successfully. Size:", img.size)
    except Exception as e:
        print("PIL ERROR:", e)
        return {"error": "File could not be opened by PIL"}
    
    ocr_lines = run_ocr_pipeline(file_path)
    if not ocr_lines:
        return {"error": "OCR failed or image unreadable 1"}
    
    structured_result = extract_fields_with_coords(ocr_lines)
    
    return {
        "lines": ocr_lines,
        "fields": structured_result
    }
import os
import cv2
import torch
import numpy as np
import re
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from gliner import GLiNER

from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    empty_cuda_cache
)

FILE_PATH = 'doc7.jpg'
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
POPPLER_PATH = "/opt/homebrew/bin"

print(f"Running on: {device.upper()}")

# MODEL_CACHE = "/Users/adityagupta/Desktop/Coding/MosipBackend/ocr_extract/backend/ocr_backend/ML/model_cache/models--microsoft--trocr-large-handwritten/snapshots/e68501f437cd2587ae5d68ee457964cac824ddee"

#FOR KARN
# MODEL_CACHE = r"C:\Users\adity\Downloads\backend_ocr\ocr_extract\backend\ocr_backend\ML\model_cache\models--microsoft--trocr-large-handwritten\snapshots\e68501f437cd2587ae5d68ee457964cac824ddee"

# processor = TrOCRProcessor.from_pretrained(MODEL_CACHE, local_files_only=True)
# model = VisionEncoderDecoderModel.from_pretrained(MODEL_CACHE, local_files_only=True).to(device)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

snapshots_root = BASE_DIR / "ML" / "model_cache" / "models--microsoft--trocr-large-handwritten" / "snapshots"
MODEL_CACHE = next(snapshots_root.iterdir())  # autodetect snapshot folder

processor = TrOCRProcessor.from_pretrained(str(MODEL_CACHE), local_files_only=True)
model = VisionEncoderDecoderModel.from_pretrained(str(MODEL_CACHE), local_files_only=True).to(device)


print("Loading GLiNER model...")
ner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")

print("Loading CRAFT models...")
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)

def load_file_as_numpy_image(file_path):
    if not os.path.exists(file_path):
        return None
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        print(f"Detected PDF. Converting...")
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            return np.ascontiguousarray(np.array(pages[0].convert("RGB"))) if pages else None
        except Exception as e:
            print(f"PDF Error: {e}")
            return None
    try:
        return np.ascontiguousarray(np.array(Image.open(file_path).convert("RGB")))
    except:
        return None

def merge_boxes_into_lines(boxes, y_threshold=30):
    if not boxes:
        return []
    
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
        w = x_max - x_min
        h = y_max - y_min
        merged_results.append((x_min, y_min, w, h))
    
    return merged_results

def detect_text_craft(image_rgb):
    print("Running CRAFT prediction...")
    
    prediction_result = get_prediction(
        image=image_rgb,
        craft_net=craft_net,
        refine_net=refine_net,
        text_threshold=0.3,
        link_threshold=0.1,
        low_text=0.2,
        cuda=USE_GPU,
        long_size=1500
    )
    
    print("---- RAW CRAFT BOXES ----")
    print(prediction_result.get("boxes"))
    print("--------------------------")
    
    raw_boxes = prediction_result["boxes"]
    
    if raw_boxes is None or len(raw_boxes) == 0:
        print("CRAFT DETECTED ZERO BOXES ❌")
        return []
    
    formatted_boxes = []
    
    for box in raw_boxes:
        box_np = np.array(box).astype(int)
        x_min = np.min(box_np[:, 0])
        x_max = np.max(box_np[:, 0])
        y_min = np.min(box_np[:, 1])
        y_max = np.max(box_np[:, 1])
        w = x_max - x_min
        h = y_max - y_min
        if w > 5 and h > 5:
            formatted_boxes.append((x_min, y_min, w, h))
    
    print("RAW boxes:", len(raw_boxes), "Filtered:", len(formatted_boxes))
    
    final_lines = merge_boxes_into_lines(formatted_boxes, y_threshold=40)
    
    print("Merged lines:", len(final_lines))
    print("Final line boxes:", final_lines)
    
    return final_lines

def run_ocr_pipeline(file_path):
    print("HI")
    image_numpy_rgb = load_file_as_numpy_image(file_path)
    if image_numpy_rgb is None:
        return []
    
    boxes = detect_text_craft(image_numpy_rgb)
    
    print("========= DEBUG CRAFT =========")
    print("Detected raw boxes count:", len(boxes))
    print("Boxes:", boxes)
    print("================================")
    
    pil_image = Image.fromarray(image_numpy_rgb)
    lines_data = []
    
    for i, (x, y, w, h) in enumerate(boxes):
        pad = 8
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
        print(f" Line {i+1}: {text} (Conf: {conf:.2f})")
    
    print("Running CRAFT...")
    boxes = detect_text_craft(image_numpy_rgb)
    print("CRAFT returned boxes:", len(boxes), boxes)
    
    return lines_data

def extract_fields_with_coords(lines_data):
    full_text_block = "\n".join([line['text'] for line in lines_data])
    final_output = {}
    
    def map_to_line(value_text):
        if not value_text:
            return [], 0.0
        for line in lines_data:
            if value_text in line['text']:
                return line['coordinates'], line['ocr_confidence']
        for line in lines_data:
            if value_text in line['text'] or line['text'] in value_text:
                if len(line['text']) > 3:
                    return line['coordinates'], line['ocr_confidence']
        return [], 0.0
    
    pincode_found = False
    for line in lines_data:
        clean_text = line['text'].replace(" ", "").strip()
        if clean_text.isdigit() and len(clean_text) == 6:
            final_output["Pincode"] = {
                "value": clean_text,
                "coordinates": line['coordinates'],
                "confidence_score": line['ocr_confidence']
            }
            pincode_found = True
            break
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
    
    if not pincode_found:
        pin_match = re.search(r'\b\d{6}\b', full_text_block)
        if pin_match:
            val = pin_match.group(0)
            coords, conf = map_to_line(val)
            final_output["Pincode"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
    phone_val = None
    phone_coords = []
    phone_conf = 0.0
    
    labeled_match = re.search(r'(?:Ph|Phone|Mob|Mobile|Cell|Tel)\s*[:\.]?\s*([+\d\s\-]{10,15})', full_text_block, re.IGNORECASE)
    if labeled_match:
        raw_val = labeled_match.group(1)
        phone_val = re.sub(r'[^\d+]', '', raw_val)
        coords, conf = map_to_line(raw_val.strip())
        phone_coords, phone_conf = coords, conf
    
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
            coords, conf = map_to_line(raw_text)
            if not coords:
                coords, conf = map_to_line(clean_text)
            
            phone_coords, phone_conf = coords, conf
            break
    
    if phone_val:
        final_output["Phone"] = {"value": phone_val, "coordinates": phone_coords, "confidence_score": phone_conf if phone_conf else 0.8}
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text_block)
    if email_match:
        val = email_match.group(0)
        coords, conf = map_to_line(val)
        final_output["Email"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
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
    
    gender_match = re.search(r'\b(Male|Female|M|F)\b', full_text_block, re.IGNORECASE)
    if gender_match:
        val = gender_match.group(0)
        norm_val = "Male" if val.lower() in ['m','male'] else "Female"
        coords, conf = map_to_line(val)
        final_output["Gender"] = {"value": norm_val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
    
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
            if key not in final_output:
                final_output[key] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
        elif lbl == "full address":
            if "Address" in final_output:
                if txt not in final_output["Address"]["value"]:
                    final_output["Address"]["value"] += ", " + txt
            else:
                final_output["Address"] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
    
    if "Name" in final_output:
        full_name = final_output["Name"]["value"].strip()
        coords = final_output["Name"]["coordinates"]
        conf = final_output["Name"]["confidence_score"]
        parts = full_name.split()
        first_name = ""
        middle_name = ""
        last_name = ""
        if len(parts) == 1:
            first_name = parts[0]
            last_name = ""
        elif len(parts) == 2:
            first_name = parts[0]
            last_name = parts[1]
        elif len(parts) >= 3:
            first_name = parts[0]
            last_name = parts[-1]
            middle_name = " ".join(parts[1:-1])
        
        final_output["First Name"] = {"value": first_name, "coordinates": coords, "confidence_score": conf}
        final_output["Middle Name"] = {"value": middle_name, "coordinates": coords, "confidence_score": conf}
        final_output["Last Name"] = {"value": last_name, "coordinates": coords, "confidence_score": conf}
        del final_output["Name"]
    
    return final_output

def handwritten_extract(file_path):
    print("==== USING UPDATED HANDWRITTEN OCR FILE ====")
    print("file path is: ", file_path)
    
    print("File exists:", os.path.exists(file_path))
    print("File size:", os.path.getsize(file_path))
    
    try:
        img = Image.open(file_path)
        print("Image loaded successfully. Size:", img.size)
    except Exception as e:
        print("PIL ERROR:", e)
        return {"error": "File could not be opened by PIL"}
    
    ocr_lines = run_ocr_pipeline(file_path)
    if not ocr_lines:
        return {"error": "OCR failed or image unreadable 1"}
    
    structured_result = extract_fields_with_coords(ocr_lines)
    
    return {
        "lines": ocr_lines,
        "fields": structured_result
    }


