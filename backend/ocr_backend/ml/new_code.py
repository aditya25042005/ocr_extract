# from fastapi import FastAPI, File, UploadFile
# from fastapi.responses import JSONResponse
import cv2
import numpy as np
import fitz  # PyMuPDF

# app = FastAPI(title="OCR Document Quality API")

MAX_PIXELS = 20_000_000  # ~20MP safety


# -----------------------
# PDF → IMAGE (first page)
# -----------------------
def pdf_to_image(pdf_bytes: bytes) -> np.ndarray | None:
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.page_count == 0:
                return None

            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200)

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


# -----------------------
# OCR-FRIENDLY QUALITY SCORING
# -----------------------
def calc_document_quality(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # --- Adaptive threshold to isolate text ---
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        31, 15
    )

    text_pixels_ratio = np.mean(thresh > 0)

    # --- Edge sharpness (text edges only) ---
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    # --- Laplacian variance (text zones weighted) ---
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = lap.var()

    # Normalize scores
    edge_score = min(edge_density * 800, 100)
    sharpness_score = min(sharpness / 12, 100)
    text_presence_score = min(text_pixels_ratio * 400, 100)

    # --- Exposure (ignore background whites) ---
    midtones = gray[(gray > 40) & (gray < 215)]
    if len(midtones) == 0:
        exposure_score = 40
    else:
        exposure_std = np.std(midtones)
        exposure_score = min(exposure_std * 2, 100)

    # --- Resolution score ---
    h, w = gray.shape
    resolution_score = 100 if (h >= 900 and w >= 900) else 70

    # --- Final OCR Readiness Score ---
    final_score = round(
        0.30 * sharpness_score +
        0.25 * edge_score +
        0.20 * text_presence_score +
        0.15 * exposure_score +
        0.10 * resolution_score,
        2
    )

    if final_score >= 75:
        status = "Excellent"
    elif final_score >= 60:
        status = "Good"
    elif final_score >= 45:
        status = "Fair"
    else:
        status = "Poor"

    return {
        "final_score": final_score,
        "quality_status": status,
        "sharpness_score": round(sharpness_score, 2),
        "edge_density_score": round(edge_score, 2),
        "text_presence_score": round(text_presence_score, 2),
        "exposure_score": round(exposure_score, 2),
        "resolution_score": resolution_score
        
    }


# -----------------------
# FASTAPI ENDPOINT
# -----------------------
# @app.post("/document-quality")
# async def document_quality(file: UploadFile = File(...)):
#     if not file.content_type or not file.content_type.startswith(
#         ("image/", "application/pdf")
#     ):
#         return JSONResponse(
#             status_code=400,
#             content={"error": "Unsupported file type"}
#         )

#     data = await file.read()

#     if file.content_type == "application/pdf":
#         image = pdf_to_image(data)
#     else:
#         np_img = np.frombuffer(data, np.uint8)
#         image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

#     if image is None:
#         return JSONResponse(
#             status_code=400,
#             content={"error": "Invalid or corrupted file"}
#         )

#     h, w = image.shape[:2]
#     if h * w > MAX_PIXELS:
#         return JSONResponse(
#             status_code=400,
#             content={"error": "Image too large"}
#         )

#     result = calc_document_quality(image)
#     return JSONResponse(result)
