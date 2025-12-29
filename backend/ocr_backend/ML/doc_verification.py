import os
import re
import cv2
import numpy as np
import json
from pdf2image import convert_from_path
from thefuzz import fuzz
from paddleocr import PaddleOCR

# ----------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------
# Bypass Paddle's network check
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# Update this path to your local Poppler bin directory
POPPLER_PATH = r'C:\Users\adity\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin'

STOP_KEYWORDS = [
    "date of issue", "valid", "valid upto", "valid up to", "dob", "blood",
    "mobile", "phone", "email", "nationality", "document", "license"
]

INDIAN_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jammu and kashmir",
    "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra",
    "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal", "delhi", "puducherry"
]

# ----------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------
def normalize(text: str) -> str:
    if not text:
        return ""
    try:
        text = text.lower()
        text = re.sub(r"[^a-z0-9 ,\-\/]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""

def extract_pincode(text: str):
    try:
        match = re.search(r"\b\d{6}\b", text)
        return match.group(0) if match else None
    except Exception:
        return None

def load_image(file_path):
    """
    Safely loads an image or converts PDF to Image.
    Returns a BGR numpy array compatible with OpenCV/PaddleOCR.
    """
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
                if not pages:
                    print("PDF converted but no pages found.")
                    return None
                
                pil_img = pages[0]
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"PDF Conversion Failed for {file_path}: {e}")
                return None

        img = cv2.imread(file_path)
        if img is None:
            print(f"cv2 failed to read image: {file_path}")
        return img

    except Exception as e:
        print(f"Unexpected error in load_image: {e}")
        return None

# ----------------------------------------------------
# ADDRESS PARSER
# ----------------------------------------------------
class AddressParser:
    def __init__(self):
        self.cities = [
            "kochi", "kottayam", "kollam", "alappuzha", "ernakulam",
            "thrissur", "palakkad", "malappuram", "kannur", "kasaragod",
            "wayanad", "idukki", "calicut", "kozhikode", "mumbai", "delhi", 
            "bangalore", "chennai", "kolkata", "hyderabad", "pune"
        ]

    def find_address_block(self, lines):
        """
        Scans lines to identify the block of text corresponding to an address.
        lines input format: [[x1, x2, y1, y2], (text, score)]
        """
        try:
            block = []
            if not lines:
                return []

            # 1. Find "Address:" label
            for idx, ln in enumerate(lines):
                txt = ln[1][0].lower()
                
                if "address" in txt:
                    block.append(ln)
                    # include following lines until STOP KEYWORD or max 8 lines
                    for j in range(idx+1, min(idx+8, len(lines))):
                        nxt = lines[j][1][0].lower()
                        if any(stop in nxt for stop in STOP_KEYWORDS):
                            break
                        block.append(lines[j])
                    return block

            # If no label found, fallback: pick first 5 lines
            return lines[:5]
        except Exception:
            return []

    def parse(self, block, user_details):
        try:
            if not block:
                return None

            raw_text = ", ".join([ln[1][0] for ln in block])
            norm = normalize(raw_text)

            pin = extract_pincode(raw_text)

            state = None
            for st in INDIAN_STATES:
                if st.lower() in norm:
                    state = st.title()
                    break

            city = None
            for c in self.cities:
                if c in norm:
                    city = c.title()
                    break

            country = "India"

            address_line = raw_text
            if city: address_line = re.sub(city, "", address_line, flags=re.IGNORECASE)
            if state: address_line = re.sub(state, "", address_line, flags=re.IGNORECASE)
            if pin: address_line = re.sub(pin, "", address_line)
            address_line = re.sub(r"\s+", " ", address_line).strip(" ,.-")

            return {
                "raw_detected": raw_text,
                "address_line": address_line,
                "city": city,
                "state": state,
                "pincode": pin,
                "country": country
            }
        except Exception:
            return None

# ----------------------------------------------------
# MAIN DOCUMENT VERIFIER
# ----------------------------------------------------
class DocumentVerifier:
    def __init__(self):
        try:
            # Initialize PaddleOCR
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
            self.address_parser = AddressParser()
        except Exception as e:
            print(f"Failed to initialize PaddleOCR: {e}")
            self.ocr = None
    
    def parse_paddle_output(self, ocr_data):
        """
        Parses PaddleX OCRResult object into standard format.
        CONVERTS Polygon points to Diagonal Format: [x1, x2, y1, y2]
        (min_x, max_x, min_y, max_y)
        """
        parsed_lines = []
        if not ocr_data: return []

        result_obj = ocr_data[0]
        
        # Helper to convert 4 points to [x1, x2, y1, y2]
        def get_diag_coords(points):
            try:
                if isinstance(points, np.ndarray):
                    points = points.tolist()
                
                # Extract X and Y coordinates
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                
                x_min = int(min(xs))
                x_max = int(max(xs))
                y_min = int(min(ys))
                y_max = int(max(ys))
                
                # STRICT FORMAT: [x1, x2, y1, y2]
                return [x_min, x_max, y_min, y_max]
            except Exception:
                return points

        # A. PaddleX Dict Handling
        if hasattr(result_obj, 'keys') or isinstance(result_obj, dict):
            texts = result_obj.get('rec_texts', [])
            boxes = result_obj.get('rec_boxes', [])
            scores = result_obj.get('rec_scores', [])
            
            for text, box, score in zip(texts, boxes, scores):
                if isinstance(score, np.generic): score = float(score)
                coords = get_diag_coords(box)
                parsed_lines.append([coords, (text, score)])
                
        # B. Standard List Handling
        elif isinstance(result_obj, list):
            for line in result_obj:
                # line structure: [box, (text, score)]
                box = line[0]
                text_info = line[1]
                
                coords = get_diag_coords(box)
                parsed_lines.append([coords, text_info])
                
        return parsed_lines

    def extract_text_lines(self, file_path):
        try:
            if self.ocr is None:
                print("OCR model is not initialized.")
                return []

            img = load_image(file_path)
            if img is None: 
                print(f"Image load failed for {file_path}")
                return []

            ocr_data = self.ocr.ocr(img)
            if not ocr_data or ocr_data[0] is None:
                print(f"No text detected in {file_path}")
                return []
            
            return self.parse_paddle_output(ocr_data)
            
        except Exception as e:
            print(f"OCR Extraction failed for {file_path}: {e}")
            return []

    def find_match(self, lines, target, threshold=60):
        try:
            if not target or not lines:
                return None

            target = normalize(target)
            best = None
            best_score = 0

            for ln in lines:
                txt = normalize(ln[1][0])
                score = fuzz.token_set_ratio(txt, target)

                if score > best_score:
                    best_score = score
                    # ln[0] is already [x1, x2, y1, y2]
                    best = {
                        "detected_text": ln[1][0],
                        "coordinates": ln[0], 
                        "match_score": score/100
                    }

            return best if best_score >= threshold else None
        except Exception as e:
            print(f"Error during field matching: {e}")
            return None

    def detect_gender(self, lines, target_gender):
        try:
            if not target_gender or not lines:
                return None
            target_gender = target_gender.lower()

            for ln in lines:
                txt = ln[1][0].lower()
                # Check for label "Gender" or "Sex"
                if "gender" in txt or "sex" in txt:
                    if target_gender in txt:
                        return {
                            "coordinates": ln[0], # [x1, x2, y1, y2]
                            "detected_text": ln[1][0],
                            "match_score": 1
                        }
            return self.find_match(lines, target_gender)
        except Exception as e:
            print(f"Error detecting gender: {e}")
            return None

    def verify_documents(self, dob_path, id_path, address_path, user):
        result = {}
        try:
            # ---- DOB PROOF ----
            if dob_path:
                try:
                    dob_lines = self.extract_text_lines(dob_path)
                    result["date_of_birth"] = self.find_match(dob_lines, user.get("dob", ""))
                except Exception as e:
                    print(f"Error verifying DOB proof: {e}")
                    result["date_of_birth"] = {"error": "Processing Failed"}

            # ---- ID PROOF ----
            if id_path:
                try:
                    id_lines = self.extract_text_lines(id_path)
                    result["first_name"] = self.find_match(id_lines, user.get("first_name", ""))
                    result["middle_name"] = self.find_match(id_lines, user.get("middle_name", ""))
                    result["last_name"] = self.find_match(id_lines, user.get("last_name", ""))
                    result["gender"] = self.detect_gender(id_lines, user.get("gender", ""))
                except Exception as e:
                    print(f"Error verifying ID proof: {e}")
                    result["id_proof_error"] = "Processing Failed"

            # ---- ADDRESS PROOF ----
            if address_path:
                try:
                    addr_lines = self.extract_text_lines(address_path)
                    
                    # 1. Identify specific address block lines
                    addr_block = self.address_parser.find_address_block(addr_lines)
                    
                    # 2. Parse text content
                    parsed_addr = self.address_parser.parse(addr_block, user)
                    
                    # 3. Calculate bounding box for the WHOLE address block
                    # Format required: [x1, x2, y1, y2] (min_x, max_x, min_y, max_y)
                    if parsed_addr and addr_block:
                        min_xs = []
                        max_xs = []
                        min_ys = []
                        max_ys = []
                        
                        for line in addr_block:
                            # line[0] is [x1, x2, y1, y2]
                            coords = line[0]
                            min_xs.append(coords[0]) # x1
                            max_xs.append(coords[1]) # x2
                            min_ys.append(coords[2]) # y1
                            max_ys.append(coords[3]) # y2
                        
                        if min_xs:
                            final_x1 = min(min_xs)
                            final_x2 = max(max_xs)
                            final_y1 = min(min_ys)
                            final_y2 = max(max_ys)
                            
                            parsed_addr["block_coordinates"] = [final_x1, final_x2, final_y1, final_y2]
                        else:
                            parsed_addr["block_coordinates"] = None

                    result["address"] = parsed_addr
                except Exception as e:
                    print(f"Error verifying Address proof: {e}")
                    result["address"] = {"error": "Processing Failed"}

            return result

        except Exception as e:
            print(f"Critical failure in verify_documents: {e}")
            return {"status": "error", "message": str(e)}