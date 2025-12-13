import os
import cv2
import torch
import numpy as np
import re
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from craft_text_detector import Craft

# --- 1. CONFIGURATION ---
IMAGE_PATH = 'aad.jpg'
USE_GPU = torch.cuda.is_available()
device = "cuda" if USE_GPU else "cpu"
# Update your poppler path if needed
# POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin'
POPPLER_PATH = "/opt/homebrew/bin"


print(f"Loading TrOCR on {device.upper()}...")
processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed').to(device)

print("Loading CRAFT...")
craft = Craft(output_dir=None, crop_type="box", cuda=USE_GPU)

# --- 2. HELPER: PDF / IMAGE LOADER ---
# def load_file_as_numpy_image(file_path):
#     ext = os.path.splitext(file_path)[1].lower()
#     print("DEBUG FILE PATH:", file_path)
#     print("DEBUG EXT:", ext)

#     if ext == '.pdf':
#         print(f"Detected PDF: {file_path}. Converting to image...")
#         try:
#             pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
#             if not pages: return None
#             img = np.array(pages[0].convert("RGB"))
#             return np.ascontiguousarray(img)
#         except Exception as e:
#             print(f"PDF Conversion Error: {e}")
#             return None

#     elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
#         print(f"Detected Image: {file_path}")
#         img = Image.open(file_path).convert("RGB")
#         return np.ascontiguousarray(np.array(img))
    
#     else:
#         print(f"Unsupported file format: {ext}")
#         return None

def load_file_as_numpy_image(file_path):
    # 1. Try PDF
    if file_path.lower().endswith(".pdf"):
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            if pages:
                img = np.array(pages[0].convert("RGB"))
                return np.ascontiguousarray(img)
        except Exception as e:
            print("PDF Error:", e)

    # 2. Try image (supports files WITHOUT extension)
    try:
        print(f"Trying to load as image: {file_path}")
        img = Image.open(file_path).convert("RGB")
        return np.ascontiguousarray(np.array(img))
    except Exception as e:
        print("Image load error:", e)
        return None


# --- 3. HELPER: OCR READ WITH CONFIDENCE ---
def read_crop_with_confidence(pil_image, box):
    """
    Extracts text and calculates a confidence score (accuracy).
    Returns: (text, confidence_score)
    """
    box = np.array(box).astype(int)
    
    # Safety check: Ensure box has 4 points
    if len(box) != 4:
        return "", 0.0

    x_min, x_max = max(0, np.min(box[:, 0])), np.max(box[:, 0])
    y_min, y_max = max(0, np.min(box[:, 1])), np.max(box[:, 1])
    
    pad = 4
    x_min = max(0, x_min - pad)
    y_min = max(0, y_min - pad)
    x_max = min(pil_image.width, x_max + pad)
    y_max = min(pil_image.height, y_max + pad)
    
    cropped = pil_image.crop((x_min, y_min, x_max, y_max))
    
    # Preprocess
    pixel_values = processor(images=cropped, return_tensors="pt").pixel_values.to(device)
    
    with torch.no_grad():
        # Generate with scores to calculate confidence
        outputs = model.generate(
            pixel_values, 
            return_dict_in_generate=True, 
            output_scores=True
        )
        
        # Decode text
        generated_ids = outputs.sequences
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        # Calculate Confidence (Accuracy)
        # 1. Stack scores (tuple of tensors) into a single tensor
        # scores shape: (seq_len, batch_size, vocab_size)
        scores = torch.stack(outputs.scores, dim=1)
        
        # 2. Apply Softmax to get probabilities
        probs = torch.nn.functional.softmax(scores, dim=-1)
        
        # 3. Get the probability of the actual chosen token at each step
        # Note: generated_ids includes the start token, so we skip the first one for alignment
        token_ids = generated_ids[:, 1:] 
        
        # Gather probabilities of the selected tokens
        # We clamp token_ids length to match scores length in case of size mismatch
        len_to_check = min(token_ids.shape[1], probs.shape[1])
        selected_probs = torch.gather(probs[:, :len_to_check, :], 2, token_ids[:, :len_to_check].unsqueeze(-1)).squeeze(-1)
        
        # 4. Average probability across the sequence
        if selected_probs.numel() > 0:
            confidence = selected_probs.mean().item()
        else:
            confidence = 0.0

    return text, confidence

# --- 4. HELPER: FORMAT BOX ---
def format_box(box):
    """Converts polygon box to [x1, x2, y1, y2] (min_x, max_x, min_y, max_y)"""
    box = np.array(box).astype(int)
    x1 = int(np.min(box[:, 0]))
    x2 = int(np.max(box[:, 0]))
    y1 = int(np.min(box[:, 1]))
    y2 = int(np.max(box[:, 1]))
    return [x1, x2, y1, y2]

# --- 5. MAIN FUNCTION ---
def extract_aadhar_smart(file_path):
    # A. LOAD IMAGE
    image_np = load_file_as_numpy_image(file_path)
    if image_np is None: return {"Error": "Could not load file."}

    # B. DETECT TEXT
    print("Detecting text regions...")
    prediction = craft.detect_text(image_np)
    boxes = prediction["boxes"]
    
    pil_image = Image.fromarray(image_np)
    
    # Sort boxes top-to-bottom for logical parsing
    boxes = sorted(boxes, key=lambda b: b[0][1])
    
    # Initialize Output Structure
    final_output = {
        "name": {"value": "", "coordinates": [], "accuracy": 0.0},
        "DOB": {"value": "", "coordinates": [], "accuracy": 0.0},
        "gender": {"value": "", "coordinates": [], "accuracy": 0.0},
        "aadhar_number": {"value": "", "coordinates": [], "accuracy": 0.0},
    }

    text_map = [] 
    
    # C. READ ANCHORS & STORE METADATA
    print(f"Reading {len(boxes)} text regions...")
    for box in boxes:
        text, conf = read_crop_with_confidence(pil_image, box)
        if len(text) > 1:
            # We store the raw polygon box for logic, but will format it later
            text_map.append({'text': text, 'box': box, 'conf': conf})

    # D. PARSE DATA
    
    # 1. AADHAR NUMBER
    for item in text_map:
        clean = item['text'].replace(" ", "")
        # Look for exactly 12 digits
        if re.search(r'^\d{12}$', clean):
            final_output['aadhar_number'] = {
                "value": f"{clean[:4]} {clean[4:8]} {clean[8:]}",
                "coordinates": format_box(item['box']),
                "accuracy": round(item['conf'], 4)
            }
            break

    # 2. DATE OF BIRTH
    dob_found_index = -1
    for i, item in enumerate(text_map):
        match = re.search(r'\d{2}/\d{2}/\d{4}', item['text'])
        if match:
            final_output['DOB'] = {
                "value": match.group(0),
                "coordinates": format_box(item['box']),
                "accuracy": round(item['conf'], 4)
            }
            dob_found_index = i
            break
        
        # Check if "DOB" label exists but date is in next box
        lower_text = item['text'].lower()
        if ("dob" in lower_text or "birth" in lower_text) and (i + 1 < len(text_map)):
            next_item = text_map[i+1]
            match_next = re.search(r'\d{2}/\d{2}/\d{4}', next_item['text'])
            if match_next:
                final_output['DOB'] = {
                    "value": match_next.group(0),
                    "coordinates": format_box(next_item['box']),
                    "accuracy": round(next_item['conf'], 4)
                }
                dob_found_index = i + 1
                break

    # 3. GENDER
    for item in text_map:
        lower_text = item['text'].lower()
        if "male" in lower_text or "female" in lower_text:
            val = "Female" if "female" in lower_text else "Male"
            final_output['gender'] = {
                "value": val,
                "coordinates": format_box(item['box']),
                "accuracy": round(item['conf'], 4)
            }
            break

    # 4. NAME
    # Logic: Name usually appears 1-2 lines above DOB or near the top
    if dob_found_index > 0:
        # Search backwards from DOB
        for j in range(dob_found_index - 1, max(-1, dob_found_index - 4), -1):
            candidate = text_map[j]
            t_lower = candidate['text'].lower()
            
            # Filter out common noise/labels
            noise_words = ['india', 'government', 'father', 'address', 'dob', 'year', 'birth', 'uidai']
            if not any(x in t_lower for x in noise_words) and len(candidate['text']) > 3:
                # Basic check: Name usually doesn't contain numbers
                if not any(char.isdigit() for char in candidate['text']):
                    final_output['name'] = {
                        "value": candidate['text'],
                        "coordinates": format_box(candidate['box']),
                        "accuracy": round(candidate['conf'], 4)
                    }
                    break

    return final_output

if __name__ == "__main__":
    data = extract_aadhar_smart(IMAGE_PATH)
    
    # Print in the requested format
    import json
    print("\n" + "="*30)
    print("FINAL JSON OUTPUT:")
    print("="*30)
    print(json.dumps(data, indent=4))