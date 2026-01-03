import cv2
import numpy as np
from pdf2image import convert_from_path
import tempfile


# -----------------------
# PDF → IMAGE using poppler (via pdf2image)
# -----------------------
def pdf_to_image(django_file):
    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(django_file.read())
        tmp_path = tmp.name

    # Convert first page to image
    pages = convert_from_path(tmp_path, dpi=200)
    page = pages[0]  # first page only

    # Convert PIL image → OpenCV BGR
    image = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
    return image


# -----------------------
# IMAGE QUALITY SCORING FUNCTION
# -----------------------
def calc_scores(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    brightness = np.mean(gray)
    brightness_score = round((brightness / 255) * 100, 2)

    contrast = np.std(gray)
    contrast_score = round((contrast / 128) * 100, 2)

    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_score = round(min(sharpness / 1000, 1) * 100, 2)

    dark_ratio = np.mean(gray < 30)
    bright_ratio = np.mean(gray > 225)

    if dark_ratio > 0.35:
        exposure_status = "Underexposed"
        exposure_score = 20
    elif bright_ratio > 0.35:
        exposure_status = "Overexposed"
        exposure_score = 20
    else:
        exposure_status = "Good"
        exposure_score = 100

    final_score = round(
        0.30 * brightness_score +
        0.25 * contrast_score +
        0.30 * sharpness_score +
        0.15 * exposure_score,
        2
    )

    return {
        "brightness_score": brightness_score,
        "contrast_score": contrast_score,
        "sharpness_score": sharpness_score,
        "exposure_status": exposure_status,
        "final_quality_score": final_score
    }


# -----------------------
# PROCESS UPLOADED FILE (PDF or Image)
# -----------------------
def process_uploaded_file(django_file):
    ext = django_file.name.split(".")[-1].lower()

    if ext == "pdf":
        return pdf_to_image(django_file)

    # Image case
    data = django_file.read()
    np_img = np.frombuffer(data, np.uint8)
    return cv2.imdecode(np_img, cv2.IMREAD_COLOR)
