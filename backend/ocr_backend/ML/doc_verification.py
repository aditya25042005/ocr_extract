import os
import re
import cv2
import numpy as np
import logging  # <--- Added logging
from pdf2image import convert_from_path
from thefuzz import fuzz
from paddleocr import PaddleOCR

# Configure Logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
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
    except Exception as e:
        logging.error(f"Error normalizing text: {e}")
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
    """
    try:
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                # Update this path if needed
                POPPLER_PATH = r'C:\Users\adity\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin'
                
                pages = convert_from_path(file_path, dpi=300, poppler_path=POPPLER_PATH)
                if not pages:
                    logging.error("PDF converted but no pages found.")
                    return None
                
                pil_img = pages[0]  # FIRST PAGE ONLY
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception as e:
                logging.error(f"PDF Conversion Failed for {file_path}: {e}")
                return None

        # Standard Image Load
        img = cv2.imread(file_path)
        if img is None:
            logging.error(f"cv2 failed to read image: {file_path}")
        return img

    except Exception as e:
        logging.error(f"Unexpected error in load_image: {e}")
        return None


# ----------------------------------------------------
# ADDRESS PARSER (PRODUCTION-GRADE)
# ----------------------------------------------------
class AddressParser:
    def __init__(self, city_list=None):
        self.cities = [
            "kochi", "kottayam", "kollam", "alappuzha", "ernakulam",
            "thrissur", "palakkad", "malappuram", "kannur", "kasaragod",
            "wayanad", "idukki", "calicut", "kozhikode"
        ]

    def find_address_block(self, lines):
        try:
            block = []
            if not lines:
                return []

            # 1. Find "Address:" label
            for idx, ln in enumerate(lines):
                txt = ln[1][0].lower()
                if "address" in txt:
                    block.append(ln)
                    # include following lines until STOP KEYWORD
                    for j in range(idx+1, min(idx+8, len(lines))):
                        nxt = lines[j][1][0].lower()
                        if any(stop in nxt for stop in STOP_KEYWORDS):
                            break
                        block.append(lines[j])
                    return block

            # If no label found, fallback: pick first 5 lines
            return lines[:5]
        except Exception as e:
            logging.error(f"Error finding address block: {e}")
            return []

    def parse(self, block, user_details):
        try:
            if not block:
                return None

            raw_text = ", ".join([ln[1][0] for ln in block])
            norm = normalize(raw_text)

            # PINCODE
            pin = extract_pincode(raw_text)

            # STATE
            state = None
            for st in INDIAN_STATES:
                if st.lower() in norm:
                    state = st.title()
                    break

            # CITY
            city = None
            for c in self.cities:
                if c in norm:
                    city = c.title()
                    break

            # COUNTRY
            country = "India"

            # ADDRESS LINE cleaning
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
        except Exception as e:
            logging.error(f"Error parsing address text: {e}")
            return None


# ----------------------------------------------------
# MAIN DOCUMENT VERIFIER (PaddleOCR-based)
# ----------------------------------------------------
class DocumentVerifier:
    def __init__(self, poppler_path=r'C:\Users\adity\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin'):
        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
            self.address_parser = AddressParser()
        except Exception as e:
            logging.error(f"Failed to initialize PaddleOCR: {e}")
            self.ocr = None
   
    def parse_paddle_output(self, ocr_data):
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
        

   
    def extract_text_lines(self, file_path):
        try:
            if self.ocr is None:
                logging.error("OCR model is not initialized.")
                return []

            img = load_image(file_path)
            if img is None: 
                logging.error(f"Image load failed for {file_path}")
                return []

            ocr_data = self.ocr.ocr(img)
            if not ocr_data:
                logging.warning(f"No text detected in {file_path}")
                return []
            print(ocr_data)
            return self.parse_paddle_output(ocr_data)
            
        except Exception as e:
            logging.error(f"OCR Extraction failed for {file_path}: {e}")
            return []

    # --------------------------------------------------------
    # FIELD MATCHERS
    # --------------------------------------------------------
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
                    best = {
                        "detected_text": ln[1][0],
                        "coordinates": ln[0],
                        "match_score": score
                    }

            return best if best_score >= threshold else None
        except Exception as e:
            logging.error(f"Error during field matching: {e}")
            return None

    # --------------------------------------------------------
    # GENDER SPECIAL HANDLING
    # --------------------------------------------------------
    def detect_gender(self, lines, target_gender):
        try:
            if not target_gender or not lines:
                return None
            target_gender = target_gender.lower()

            for ln in lines:
                txt = ln[1][0].lower()
                if "gender" in txt or "sex" in txt:
                    if target_gender in txt:
                        return {
                            "coordinates": ln[0],
                            "detected_text": ln[1][0],
                            "match_score": 100
                        }
            # fallback
            return self.find_match(lines, target_gender)
        except Exception as e:
            logging.error(f"Error detecting gender: {e}")
            return None

    # --------------------------------------------------------
    # MAIN VERIFY FUNCTION
    # --------------------------------------------------------
    def verify_documents(self, dob_path, id_path, address_path, user):
        result = {}
        try:
            print(user)
            # ---- DOB PROOF ----
            if dob_path:
                try:
                    dob_lines = self.extract_text_lines(dob_path)
                    print(dob_lines)
                    result["date_of_birth"] = self.find_match(dob_lines, user.get("dob", ""))
                    print(result)
                except Exception as e:
                    logging.error(f"Error verifying DOB proof: {e}")
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
                    logging.error(f"Error verifying ID proof: {e}")
                    result["id_proof_error"] = "Processing Failed"

            # ---- ADDRESS PROOF ----
            if address_path:
                try:
                    addr_lines = self.extract_text_lines(address_path)
                    addr_block = self.address_parser.find_address_block(addr_lines)
                    parsed_addr = self.address_parser.parse(addr_block, user)
                    result["address"] = parsed_addr
                except Exception as e:
                    logging.error(f"Error verifying Address proof: {e}")
                    result["address"] = {"error": "Processing Failed"}

            return result

        except Exception as e:
            logging.critical(f"Critical failure in verify_documents: {e}")
            return {"status": "error", "message": str(e)}