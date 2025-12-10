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
POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin'

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
# We load the networks directly. This prevents the wrapper class issues.
craft_net = load_craftnet_model(cuda=USE_GPU)
refine_net = load_refinenet_model(cuda=USE_GPU)

# --- 3. HELPER: FILE LOADER ---
def load_file_as_numpy_image(file_path):
    if not os.path.exists(file_path): return None
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        print(f"Detected PDF. Converting...")
        try:
            pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH, last_page=1)
            # Ensure RGB and contiguous memory
            return np.ascontiguousarray(np.array(pages[0].convert("RGB"))) if pages else None
        except Exception as e:
            print(f"PDF Error: {e}"); return None
    elif ext in ['.jpg', '.png', '.jpeg']:
        print(f"Detected Image.")
        # Load directly as RGB
        return np.ascontiguousarray(np.array(Image.open(file_path).convert("RGB")))
    return None

# --- 4. CRAFT DETECTION (Using Low-Level get_prediction) ---
def detect_text_craft(image_rgb):
    """
    Runs CRAFT using get_prediction to find text regions.
    """
    # get_prediction expects an RGB image (which our loader provides).
    
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
    
    # Extract boxes (Format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]])
    raw_boxes = prediction_result["boxes"]
    
    formatted_boxes = []
    
    for box in raw_boxes:
        # Convert to numpy for easy math
        box_np = np.array(box).astype(int)
        
        x_min = np.min(box_np[:, 0])
        x_max = np.max(box_np[:, 0])
        y_min = np.min(box_np[:, 1])
        y_max = np.max(box_np[:, 1])
        
        w = x_max - x_min
        h = y_max - y_min
        
        # Filter tiny noise
        if w > 10 and h > 10:
            formatted_boxes.append((x_min, y_min, w, h))
            
    # Sort boxes Top-to-Bottom based on Y coordinate
    return sorted(formatted_boxes, key=lambda b: b[1])

# --- 5. OCR PIPELINE ---
def run_ocr_pipeline(file_path):
    # 1. Load Image (RGB Numpy Array)
    image_numpy_rgb = load_file_as_numpy_image(file_path)
    if image_numpy_rgb is None: return []

    # 2. Detect Text
    boxes = detect_text_craft(image_numpy_rgb)
    print(f"Found {len(boxes)} text lines.")

    # 3. Read Text with TrOCR
    pil_image = Image.fromarray(image_numpy_rgb)
    lines_data = [] 

    for i, (x, y, w, h) in enumerate(boxes):
        pad = 5
        img_h, img_w, _ = image_numpy_rgb.shape
        
        # Ensure coordinates are within image bounds
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
            
            # Calculate Confidence
            try:
                transition_scores = model.compute_transition_scores(
                    sequences=generated_ids, scores=outputs.scores, normalize_logits=True
                )
                conf = torch.exp(transition_scores.mean()).item()
            except:
                conf = 0.0

        # Store data: coordinates format [x1, x2, y1, y2]
        lines_data.append({
            "text": text,
            "coordinates": [int(x), int(x+w), int(y), int(y+h)],
            "ocr_confidence": round(conf, 4)
        })
        print(f"  Line {i+1}: {text} (Conf: {conf:.2f})")

    return lines_data

# --- 6. FIELD EXTRACTION (Hybrid AI/Regex) ---
def extract_fields_with_coords(lines_data):
    full_text_block = "\n".join([line['text'] for line in lines_data])
    final_output = {}

    # Helper: Find original coordinates for a substring
    def map_to_line(value_text):
        if not value_text: return [], 0.0
        # Exact match attempt
        for line in lines_data:
            if value_text in line['text']:
                return line['coordinates'], line['ocr_confidence']
        # Fuzzy/Substring attempt
        for line in lines_data:
            if value_text in line['text'] or line['text'] in value_text:
                if len(line['text']) > 3: 
                    return line['coordinates'], line['ocr_confidence']
        return [], 0.0

    # --- A. REGEX EXTRACTION ---
    
    # 1. Pincode
    pin_match = re.search(r'\b\d{6}\b', full_text_block)
    if pin_match:
        val = pin_match.group(0)
        coords, conf = map_to_line(val)
        final_output["Pincode"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}

    # 2. Email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text_block)
    if email_match:
        val = email_match.group(0)
        coords, conf = map_to_line(val)
        final_output["Email"] = {"value": val, "coordinates": coords, "confidence_score": conf if conf else 1.0}

    # 3. Blood Group
    bg_pattern = r'\b(A|B|AB|O)[-\s]?(?:positive|negative|\+ve|\-ve|[\+\-])?(?!\w)'
    for match in re.finditer(bg_pattern, full_text_block, re.IGNORECASE):
        raw_val = match.group(0)
        norm_val = raw_val.upper().replace('POSITIVE','+').replace('NEGATIVE','-').replace('VE','').replace(' ','').replace('++','+')
        if len(norm_val) >= 2 and any(x in norm_val for x in ['+','-']):
            coords, conf = map_to_line(raw_val)
            final_output["Blood Group"] = {"value": norm_val, "coordinates": coords, "confidence_score": conf if conf else 1.0}
            break

    # 4. Gender
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
            if key not in final_output:
                final_output[key] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}
        
        elif lbl == "full address":
            if "Address" in final_output:
                current_val = final_output["Address"]["value"]
                final_output["Address"]["value"] = current_val + ", " + txt
                final_output["Address"]["coordinates"] = coords
            else:
                final_output["Address"] = {"value": txt, "coordinates": coords, "confidence_score": final_conf}

    return final_output

# --- EXECUTE ---
if __name__ == "__main__":
    ocr_lines = run_ocr_pipeline(FILE_PATH)
    
    if ocr_lines:
        structured_result = extract_fields_with_coords(ocr_lines)
        
        print("\n" + "="*80)
        print(f"{'FIELD':<15} | {'VALUE':<30} | {'CONF':<5} | {'COORDS [x1, x2, y1, y2]'}")
        print("="*80)
        
        for field, data in structured_result.items():
            print(f"{field:<15} | {data['value']:<30} | {data['confidence_score']:<5} | {data['coordinates']}")
# import os
# import cv2
# import torch
# import numpy as np
# from PIL import Image
# from pdf2image import convert_from_path
# from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# # --- 1. CONFIGURATION ---
# FILE_PATH = 'img3.jpg'  # <--- Can be .pdf, .jpg, .png
# USE_GPU = torch.cuda.is_available()
# device = "cuda" if USE_GPU else "cpu"

# # On Windows, if Poppler is not in PATH, set this: e.g., r"C:\poppler\bin"
# POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin'

# print(f"Running on: {device.upper()}")

# # --- 2. LOAD TrOCR MODEL ---
# print("Loading TrOCR model...")
# processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-handwritten')
# model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-handwritten').to(device)

# # --- 3. HELPER: FILE LOADER (PDF/Image to NumPy) ---
# def load_file_as_numpy_image(file_path):
#     """
#     Checks if input is PDF or Image. 
#     Returns: RGB NumPy array of the first page/frame.
#     """
#     if not os.path.exists(file_path):
#         print(f"Error: File not found at {file_path}")
#         return None

#     ext = os.path.splitext(file_path)[1].lower()
    
#     # CASE A: PDF Input
#     if ext == '.pdf':
#         print(f"Detected PDF: {file_path}. Converting to image...")
#         try:
#             # Convert first page (last_page=1)
#             # dpi=300 is standard for good OCR results
#             pages = convert_from_path(
#                 file_path, 
#                 dpi=300, 
#                 poppler_path=POPPLER_PATH, 
#                 last_page=1
#             )
            
#             if not pages:
#                 print("Error: PDF is empty.")
#                 return None
            
#             # Convert PIL image to RGB NumPy Array
#             return np.array(pages[0].convert("RGB"))
            
#         except Exception as e:
#             print(f"PDF Conversion Error: {e}")
#             print("Ensure Poppler is installed and POPPLER_PATH is correct.")
#             return None

#     # CASE B: Image Input
#     elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
#         print(f"Detected Image: {file_path}")
#         try:
#             # Open with PIL to ensure RGB consistency
#             img = Image.open(file_path).convert("RGB")
#             return np.array(img)
#         except Exception as e:
#             print(f"Error opening image: {e}")
#             return None
    
#     else:
#         print(f"Error: Unsupported file format: {ext}")
#         return None

# # --- 4. OPENCV DETECTION ---
# def detect_lines_opencv(image_rgb):
#     """
#     Detects text lines using morphological dilation on an RGB NumPy array.
#     """
#     # Convert RGB to Grayscale
#     gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

#     # Thresholding (Binary Inv + Otsu)
#     _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    

#     # Dilation (Smearing to connect characters)
#     # (25, 2) kernel smears horizontally
#     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 2))
#     dilated = cv2.dilate(thresh, kernel, iterations=1)

#     # Find Contours
#     contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

#     boxes = []
#     for cnt in contours:
#         x, y, w, h = cv2.boundingRect(cnt)
#         if w > 20 and h > 10:
#             boxes.append((x, y, w, h))

#     # Sort Top-to-Bottom
#     boxes = sorted(boxes, key=lambda b: b[1])

#     return boxes

# # --- 5. MAIN PIPELINE ---
# def run_ocr_pipeline(file_path):
#     # A. Load File (Handles PDF conversion internally)
#     image_numpy_rgb = load_file_as_numpy_image(file_path)
    
#     if image_numpy_rgb is None:
#         return "Error: Could not process file."

#     # B. Detect Lines
#     print("Detecting text lines...")
#     boxes = detect_lines_opencv(image_numpy_rgb)
    
#     if len(boxes) == 0:
#         print("No text lines detected.")
#         return ""

#     print(f"Found {len(boxes)} lines.")

#     # Create PIL Image for Cropping (TrOCR expects PIL)
#     pil_image = Image.fromarray(image_numpy_rgb)
#     full_text = []

#     # C. Crop and Recognize
#     for i, (x, y, w, h) in enumerate(boxes):
#         # Padding logic
#         pad = 5
#         x_new = max(0, x - pad)
#         y_new = max(0, y - pad)
        
#         # Ensure we don't crop outside image bounds
#         img_h, img_w, _ = image_numpy_rgb.shape
#         w_new = min(img_w - x_new, w + 2*pad)
#         h_new = min(img_h - y_new, h + 2*pad)

#         # Crop
#         cropped_image = pil_image.crop((x_new, y_new, x_new + w_new, y_new + h_new))

#         # TrOCR Inference
#         pixel_values = processor(images=cropped_image, return_tensors="pt").pixel_values.to(device)
        
#         with torch.no_grad():
#             generated_ids = model.generate(pixel_values)
#             text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
#         print(f"  Line {i+1}: {text}")
#         full_text.append(text)

#     return "\n".join(full_text)

# # --- EXECUTE ---
# if __name__ == "__main__":
#     final_result = run_ocr_pipeline(FILE_PATH)
#     print("\n" + "="*30)
#     print("FINAL OUTPUT:")
#     print("="*30)
#     print(final_result)

