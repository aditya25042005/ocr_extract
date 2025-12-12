import os
import re
import cv2
import numpy as np
from pdf2image import convert_from_path
from thefuzz import fuzz
from paddleocr import PaddleOCR


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
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ,\-\/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pincode(text: str):
    match = re.search(r"\b\d{6}\b", text)
    return match.group(0) if match else None


def load_image(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=300)
        pil_img = pages[0]  # FIRST PAGE ONLY
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    img = cv2.imread(file_path)
    return img


# ----------------------------------------------------
# ADDRESS PARSER (PRODUCTION-GRADE)
# ----------------------------------------------------
class AddressParser:
    def __init__(self, city_list=None):
        # You can load a 5000-city CSV here. For now, minimal list:
        self.cities = [
            "kochi", "kottayam", "kollam", "alappuzha", "ernakulam",
            "thrissur", "palakkad", "malappuram", "kannur", "kasaragod",
            "wayanad", "idukki", "calicut", "kozhikode"
        ]

    def find_address_block(self, lines):
        """
        lines = [ (box, (text, score)) ... ]
        """
        block = []

        # 1. Find "Address:" label
        for idx, ln in enumerate(lines):
            txt = ln[1][0].lower()
            if "address" in txt:
                # include this line
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

    def parse(self, block, user_details):
        """
        block = OCR lines selected as address region
        """
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

        # ADDRESS LINE = remove city/state/pincode
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


# ----------------------------------------------------
# MAIN DOCUMENT VERIFIER (PaddleOCR-based)
# ----------------------------------------------------
class DocumentVerifier:
    def __init__(self, poppler_path=None):
        self.ocr = PaddleOCR(
        use_angle_cls=True,
        lang='en'
    )

        self.address_parser = AddressParser()

    def parse_paddle_output(self, ocr_result):
        """
        Standardize PaddleOCR output:
        Returns: [ [box, (text, score)], ... ]
        """
        parsed = []
        if not ocr_result:
            return parsed

        # ocr_result = [ [ [box], (text, score) ], ... ]
        for line in ocr_result:
            box = line[0]
            text, conf = line[1]
            parsed.append([box, (text, conf)])

        return parsed

    def extract_text_lines(self, file_path):
        img = load_image(file_path)
        if img is None: 
            return []

        ocr_data = self.ocr.ocr(img)
        return self.parse_paddle_output(ocr_data)

    # --------------------------------------------------------
    # FIELD MATCHERS
    # --------------------------------------------------------
    def find_match(self, lines, target, threshold=60):
        if not target:
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

    # --------------------------------------------------------
    # GENDER SPECIAL HANDLING
    # --------------------------------------------------------
    def detect_gender(self, lines, target_gender):
        if not target_gender:
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

    # --------------------------------------------------------
    # MAIN VERIFY FUNCTION
    # --------------------------------------------------------
    def verify_documents(self, dob_path, id_path, address_path, user):
        result = {}

        # ---- DOB PROOF ----
        dob_lines = self.extract_text_lines(dob_path)
        result["date_of_birth"] = self.find_match(dob_lines, user["dob"])

        # ---- ID PROOF ----
        id_lines = self.extract_text_lines(id_path)
        result["first_name"] = self.find_match(id_lines, user["first_name"])
        result["middle_name"] = self.find_match(id_lines, user.get("middle_name", ""))
        result["last_name"] = self.find_match(id_lines, user["last_name"])
        result["gender"] = self.detect_gender(id_lines, user["gender"])

        # ---- ADDRESS PROOF ----
        addr_lines = self.extract_text_lines(address_path)
        addr_block = self.address_parser.find_address_block(addr_lines)
        parsed_addr = self.address_parser.parse(addr_block, user)

        result["address"] = parsed_addr

        return result
