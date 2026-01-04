import cv2
import numpy as np
import fitz  # PyMuPDF
from typing import Optional

# --------------------------------------------------
# PDF → IMAGE (first page) - Uses PyMuPDF
# --------------------------------------------------
def pdf_to_image(pdf_bytes: bytes) -> Optional[np.ndarray]:
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                return None

            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=220)

            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                return None

            return img
    except Exception:
        return None

# --------------------------------------------------
# TEXTURE / PAPER NOISE PENALTY
# --------------------------------------------------
def texture_penalty(gray: np.ndarray) -> float:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    high_freq = cv2.absdiff(gray, blur)
    level = np.mean(high_freq)
    # Yellow / dot-matrix scans spike here
    return np.clip((level - 6) * 4.0, 0, 35)

# --------------------------------------------------
# OCR DOCUMENT QUALITY SCORING (ADVANCED)
# --------------------------------------------------
def calc_document_quality(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img_area = gray.shape[0] * gray.shape[1]

    # 1. SHARPNESS 
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_score = np.clip(np.interp(lap_var, [20, 120], [50, 100]), 0, 100)
    noise_std = np.std(gray)
    noise_pen = np.clip((noise_std - 22) * 2.0, 0, 35)
    sharpness_score = min(np.clip(blur_score - noise_pen, 0, 100), 75)

    # 2. BINARIZATION (Used for background and text checks)
    _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. TEXT DENSITY
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    text_mask = cv2.morphologyEx(255 - bin_img, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    valid_area = 0
    text_blocks = 0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 10 < h < 80 and 30 < w < gray.shape[1] * 0.9:
            valid_area += w * h
            text_blocks += 1

    text_density = valid_area / img_area
    text_score = np.clip(text_density * 900, 0, 100)
    if text_density > 0.22: text_score *= 0.6
    elif text_density > 0.17: text_score *= 0.8

    # 4. BACKGROUND CLEANLINESS
    bg_pixels = gray[bin_img == 255]
    bg_noise = np.std(bg_pixels) if len(bg_pixels) > 1000 else 65
    background_score = np.clip(130 - bg_noise * 2.5, 0, 100)

    # 5. EXPOSURE
    mean_intensity = np.mean(gray)
    exposure_score = np.clip(np.interp(mean_intensity, [130, 240], [65, 100]), 0, 100)

    # 6. RESOLUTION
    h, w = gray.shape
    res_val = min(h, w)
    resolution_score = 100 if res_val >= 1000 else 80 if res_val >= 700 else 60

    # 7. FINAL CALCULATION
    texture = texture_penalty(gray)
    final_score = (
        0.15 * sharpness_score +
        0.25 * text_score +
        0.35 * background_score +
        0.15 * exposure_score +
        0.05 * resolution_score
    ) - texture

    final_score = round(np.clip(final_score, 0, 100), 2)
    status = "Excellent" if final_score >= 85 else "Good" if final_score >= 70 else "Fair" if final_score >= 50 else "Poor"

    return {
        "final_quality_score": final_score,
        "quality_status": status,
        "metrics": {
            "sharpness_score": round(sharpness_score, 2),
            "text_density_score": round(text_score, 2),
            "background_cleanliness_score": round(background_score, 2),
            "exposure_score": round(exposure_score, 2),
            "resolution_score": resolution_score,
            "texture_penalty": round(texture, 2),
            "text_blocks_detected": text_blocks
        }
    }