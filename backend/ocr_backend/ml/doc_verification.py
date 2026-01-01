import cv2
import numpy as np
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from thefuzz import fuzz
import os
import json

# Bypass Paddle's network check
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True' 

POPPLER_PATH = r'D:\ELHAN\MOSIP\poppler-25.12.0\Library\bin'

class DocumentVerifier:
    def __init__(self):
        # Initialize PaddleOCR
        # use_angle_cls=True ensures rotated text is handled
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
    
    def _load_image(self, file_path):
        """
        Loads image, converts PDF if needed, and applies CRITICAL image processing.
        Returns a 3-channel BGR image suitable for PaddleOCR.
        """
        if not file_path or not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return None

        file_ext = os.path.splitext(file_path)[1].lower()
        img_bgr = None

        # 1. Load File
        if file_ext == '.pdf':
            try:
                images = convert_from_path(file_path, poppler_path=POPPLER_PATH)
                img_bgr = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error converting PDF: {e}")
                return None
        else:
            img_bgr = cv2.imread(file_path)
            
        if img_bgr is None:
             return None

        # 2. Image Processing (Grayscale + Otsu Thresholding)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Otsu's thresholding automatically finds the best contrast for text
        _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 3. CRITICAL: Convert back to 3-Channel BGR
        # PaddleOCR requires (H, W, 3). Even though it looks B&W, we restore the channels.
        thresholded_3channel = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)
        
        return thresholded_3channel

    def _find_word_in_lines(self, ocr_lines, target_value, threshold=65):
        """
        Scans through OCR lines using fuzz.token_set_ratio.
        """
        if not target_value:
            return None

        target_str = str(target_value).strip().lower()
        best_match = None
        highest_score = 0

        # ocr_lines format: [ [box, (text, score)], ... ]
        for line in ocr_lines:
            if not line or len(line) < 2: continue

            box = line[0]
            detected_text_full = line[1][0]
            
            # Use token_set_ratio: robust against partial noise and re-ordering
            # e.g., Matches "JOLLY" inside "Name: JOLLY JOHN" with high score
            score = fuzz.token_set_ratio(target_str, detected_text_full.lower())
            
            if score > highest_score:
                highest_score = score
                best_match = {
                    "coordinates": box, 
                    "match_score": score,
                    "detected_text": detected_text_full
                }

        if highest_score >= threshold:
            return best_match
        return None

    def parse_paddlex_result(self, ocr_data):
        """
        Parses PaddleX OCRResult object into standard format: [[box, (text, score)], ...]
        Handles both Dictionary (PaddleX) and List (Standard) outputs.
        """
        parsed_lines = []
        if not ocr_data: return []

        result_obj = ocr_data[0]
        
        # A. PaddleX Dict Handling
        if hasattr(result_obj, 'keys') or isinstance(result_obj, dict):
            texts = result_obj.get('rec_texts', [])
            boxes = result_obj.get('rec_boxes', [])
            scores = result_obj.get('rec_scores', [])
            
            for text, box, score in zip(texts, boxes, scores):
                if isinstance(box, np.ndarray): box = box.tolist()
                if isinstance(score, np.generic): score = float(score)
                parsed_lines.append([box, (text, score)])
                
        # B. Standard List Handling
        elif isinstance(result_obj, list):
            for line in result_obj:
                # line structure: [box, (text, score)]
                box = line[0]
                text_info = line[1]
                
                if isinstance(box, np.ndarray): box = box.tolist()
                
                parsed_lines.append([box, text_info])
                
        return parsed_lines

    def verify_documents(self, birth_doc_path, id_doc_path, address_doc_path, user_details):
        output_report = {}

        # --- Helper: Smart Gender Context Search ---
        def _smart_gender_check(ocr_lines, target_gender):
            if not target_gender: return None
            
            # 1. Setup Aliases (Input "Male" -> Search for "M")
            gender_map = {"male": "m", "female": "f", "transgender": "t"}
            target_lower = str(target_gender).lower().strip()
            target_alias = gender_map.get(target_lower, target_lower) 
            
            print(f"   > Gender Check: Looking for '{target_gender}' or alias '{target_alias}'")

            # --- STRATEGY A: Label + Proximity Search ---
            for i, line in enumerate(ocr_lines):
                if not line: continue
                text_obj = line[1]
                current_text = (text_obj[0] if isinstance(text_obj, tuple) else str(text_obj)).lower()

                # Did we find a Gender Label?
                if any(label in current_text for label in ["sex", "gender", "लिंग", "sex/ling"]):
                    # 1. Check same line
                    words_in_line = current_text.replace(":", " ").split()
                    if target_alias in words_in_line:
                        return {"coordinates": line[0], "match_score": 100, "detected_text": line[1][0]}

                    # 2. Look Ahead (next 6 lines)
                    lookahead_range = min(len(ocr_lines), i + 7)
                    for j in range(i + 1, lookahead_range):
                        next_line = ocr_lines[j]
                        if not next_line: continue
                        
                        next_text_obj = next_line[1]
                        next_text = (next_text_obj[0] if isinstance(next_text_obj, tuple) else str(next_text_obj)).strip().lower()
                        
                        if next_text == target_alias:
                            return {"coordinates": next_line[0], "match_score": 100, "detected_text": next_line[1][0]}
                        if target_lower in next_text:
                            return {"coordinates": next_line[0], "match_score": 100, "detected_text": next_line[1][0]}

            # --- STRATEGY B: Global Exact Match (Fallback) ---
            for line in ocr_lines:
                if not line: continue
                text_obj = line[1]
                detected_text = (text_obj[0] if isinstance(text_obj, tuple) else str(text_obj)).strip()
                
                if detected_text.lower() == target_alias or target_lower == detected_text.lower():
                      return {"coordinates": line[0], "match_score": 100, "detected_text": detected_text}

            return None

        # --- PROCESS FILE 1: Birth Document (DOB Check) ---
        print(f"Processing Birth Document: {birth_doc_path}...")
        img_birth = self._load_image(birth_doc_path)
        if img_birth is not None:
            raw_birth = self.ocr.ocr(img_birth)
            normalized_birth = self.parse_paddlex_result(raw_birth)
            output_report['date_of_birth'] = self._find_word_in_lines(
                normalized_birth, user_details.get('dob')
            )
        else:
             output_report['date_of_birth'] = None

        # --- PROCESS FILE 2: ID Document (Details Check) ---
        print(f"Processing ID Document: {id_doc_path}...")
        img_id = self._load_image(id_doc_path)
        if img_id is not None:
            raw_id = self.ocr.ocr(img_id)
            normalized_id = self.parse_paddlex_result(raw_id)

            # 1. Check Names
            fields_to_check = ['first_name', 'middle_name', 'last_name']
            for field in fields_to_check:
                val = user_details.get(field)
                if val:
                    print(f"   > Searching for {field}: '{val}'")
                    output_report[field] = self._find_word_in_lines(normalized_id, val)
                else:
                    output_report[field] = None

            # 2. Check Gender (Smart Context)
            gender_val = user_details.get('gender')
            output_report['gender'] = _smart_gender_check(normalized_id, gender_val)

        else:
            for field in ['first_name', 'middle_name', 'last_name', 'gender']:
                output_report[field] = None

        # --- PROCESS FILE 3: Address Proof (Address Check) ---
        # Checks address line, city, state, country, pincode
        print(f"Processing Address Proof: {address_doc_path}...")
        img_address = self._load_image(address_doc_path)
        
        address_fields = ['address_line1', 'city', 'state', 'country', 'pincode']
        
        if img_address is not None:
            raw_addr = self.ocr.ocr(img_address)
            normalized_addr = self.parse_paddlex_result(raw_addr)
            
            for field in address_fields:
                val = user_details.get(field)
                if val:
                    print(f"   > Searching for {field}: '{val}'")
                    # Using existing fuzzy logic - works well for addresses because 
                    # token_set_ratio handles partial string matches effectively.
                    output_report[field] = self._find_word_in_lines(normalized_addr, val)
                else:
                    output_report[field] = None # Field not provided in target
        else:
            # If image load fails, mark all address fields as None
            for field in address_fields:
                output_report[field] = None

        return output_report
    
# --- Execution ---
if __name__ == "__main__":
    verifier = DocumentVerifier()

    # Define User Details EXACTLY as they should appear
    target_details = {
        # Personal
        "first_name": "Aditya",
        "middle_name": "",
        "last_name": "Karn",
        "gender": "Male",
        "dob": "25-04-2005",
        
        # Address
        "address_line1": "Kochuparambil House, 2nd Milestone",
        "city": "Kollam",
        "state": "Kerala",
        "country": "India",
        "pincode": "691004"
    }

    # UPDATE THESE PATHS to your actual files
    path_to_birth = r"D:\ELHAN\MOSIP\OCR\voter.jpg"
    path_to_id = r"D:\ELHAN\MOSIP\OCR\pan.jpg"
    path_to_address = r"D:\ELHAN\MOSIP\OCR\doc7.jpg" # Using Aadhaar or Driver's license here

    # Verify existing files
    results = verifier.verify_documents(path_to_birth, path_to_id, path_to_address, target_details)
        
    # --- TABULAR OUTPUT CONFIGURATION ---
    w_field = 20
    w_status = 10
    w_score = 8
    w_text = 30
    w_coords = 25

    h_line = f"+{'-'*(w_field+2)}+{'-'*(w_status+2)}+{'-'*(w_score+2)}+{'-'*(w_text+2)}+{'-'*(w_coords+2)}+"

    print("\n")
    print(f"{' DOCUMENT VERIFICATION REPORT ':^{len(h_line)}}")
    print(h_line)
    print(f"| {'FIELD':<{w_field}} | {'STATUS':<{w_status}} | {'SCORE':<{w_score}} | {'DETECTED TEXT':<{w_text}} | {'COORDINATES':<{w_coords}} |")
    print(h_line)

    # Order of fields for cleaner display
    display_order = [
        'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 
        'address_line1', 'city', 'state', 'country', 'pincode'
    ]

    for field in display_order:
        data = results.get(field)
        field_display = field.replace('_', ' ').title()
        
        # Skip fields not in target_details if needed, but here we show all
        
        if data:
            status = "FOUND"
            score = f"{data.get('match_score', 0)}%"
            
            raw_text = str(data.get('detected_text', 'N/A'))
            text_display = (raw_text[:w_text-3] + '...') if len(raw_text) > w_text else raw_text
            
            raw_coords = str(data.get('coordinates', []))
            coords_display = (raw_coords[:w_coords-3] + '...') if len(raw_coords) > w_coords else raw_coords
        else:
            status = "MISSING" if target_details.get(field) else "N/A"
            score = "0%"
            text_display = "-"
            coords_display = "-"

        print(f"| {field_display:<{w_field}} | {status:<{w_status}} | {score:<{w_score}} | {text_display:<{w_text}} | {coords_display:<{w_coords}} |")
        print(h_line)
    print("\n")