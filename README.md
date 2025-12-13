## 📄 MOSIP-Aligned Document Intelligence Project Guide

This guide provides an overview of the key features of the document intelligence system, followed by the installation and setup steps for both the frontend and the backend.

### ✨ Key Features of the Document Intelligence System

The project is a MOSIP-aligned backend system for OCR-based text extraction and document verification, developed as part of a hackathon challenge. It serves as a pre-registration/document intelligence layer, following MOSIP architectural principles.

| Feature Category | Feature Name | Description |
| :--- | :--- | :--- |
| **Data Extraction** | **OCR Extraction** | Extracts structured text from scanned images or PDFs. |
| | **Handwritten Text Recognition** | Supports extraction from handwritten documents. |
| **Data Integrity** | **Data Verification** | Compares OCR output with user-filled form data to verify details. |
| **Document Quality** | **Capture Quality Scoring** | Evaluates document quality based on blur, lighting, and clarity. |
| **Document Type** | **Aadhaar Detection** | Identifies whether an uploaded document is an Aadhaar. |
| **Authentication** | **OTP-Based Verification** | Uses email OTP for user validation. |
| **Architecture** | **Modular & Offline** | Features clean separation of extraction, verification, and scoring, utilizing offline ML models (no cloud-based OCR services). |

---

## 💻 Installation and Setup

### Prerequisites

Ensure you have Python (for backend) and Node.js/npm (for frontend) installed on your system.

### 1. General Installation Steps

1.  Clone the main repository:
    ```bash
    git clone [https://github.com/aditya25042005/ocr_extract.git](https://github.com/aditya25042005/ocr_extract.git)
    ```

### 2. Frontend Setup (using `frontend/reg2`)

The frontend is built using React/Vite.

| Step | Command | Description |
| :--- | :--- | :--- |
| **Navigate** | `cd ocr_extract/frontend/reg_form2` | Move into the frontend directory. |
| **Install** | `npm install` or `npm i` | Install all necessary Node modules. |
| **Run** | `npm run dev` or `yarn dev` | Start the development server (e.g., at `http://localhost:5173`). |

### 3. Backend Setup (using `backend`)

The backend is a Django project.

| Step | Command | Description |
| :--- | :--- | :--- |
| **Navigate** | `cd ocr_extract/backend` | Move into the backend directory. |
| **Virtual Env** | `python -m venv venv` | Create a Python virtual environment. |
| **Activate (Mac/Linux)** | `source venv/bin/activate` | Activate the environment on Mac/Linux. |
| **Activate (Windows)** | `venv\Scripts\activate` | Activate the environment on Windows. |
| **Install** | `pip install -r requirements.txt` | Install Python dependencies. |
| **Configuration** | Create a `.env` file with environment variables (e.g., `DJANGO_SECRET_KEY`, `SMTP_USER`, etc.). | Set up secure configuration and email service details. |
| **Migrate** | `python manage.py migrate` | Apply database migrations. |
| **Run** | `python manage.py runserver` | Start the Django server (runs at `http://127.0.0.1:8000`). |

### Integrated Backend Endpoints

The following APIs are integrated into the system for Document Intelligence:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/aadhar/ocr/` | `POST` | Aadhaar OCR extraction |
| `/api/handwritten/ocr/` | `POST` | Handwritten OCR |
| `/api/verify-documents/` | `POST` | OCR vs form data verification |
| `/api/aadhaar-detect/` | `POST` | Aadhaar document detection |
| `/api/quality-score/` | `POST` | Capture quality scoring 





## 🔎 `verify_documents` Function Documentation

This function processes two identity documents (e.g., a Birth Certificate for DOB and a Passport/Aadhaar for Names/Gender) and compares the OCR-extracted text against a set of target user details. It uses fuzzy matching (`thefuzz`) for flexible name comparison and specialized logic for gender (`M`/`F`) and date of birth to ensure robust verification.

---

### Input Parameters

The `verify_documents` method takes three arguments:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `birth_doc_path` | `str` | **File path** to the first document (used primarily to verify Date of Birth). Can be an image (`.jpg`, `.png`) or a PDF (`.pdf`). |
| `id_doc_path` | `str` | **File path** to the second document (used to verify Name and Gender). Typically a Passport or national ID. |
| `user_details` | `dict` | A **dictionary** containing the user's details to be verified against the documents. |

**Structure of `user_details` Dictionary:**

| Key | Type | Description |
| :--- | :--- | :--- |
| `"first_name"` | `str` | The target first name. |
| `"middle_name"` | `str` | The target middle name (can be `""` or `None`). |
| `"last_name"` | `str` | The target last name. |
| `"gender"` | `str` | The target gender (e.g., `"Male"` or `"Female"`). The function supports matching this against full words or single letters (`M`/`F`) on the document. |
| `"dob"` | `str` | The target date of birth (e.g., `"DD/MM/YYYY"`). |

---

### Output

The function returns a single **dictionary** (`output_report`) where each key corresponds to a checked field.

* If a detail is successfully matched (score $\ge 65$), the value is a dictionary containing the detected location and score.
* If the detail is not found or the score is too low, the value is `null`.

**Structure of `output_report` Dictionary:**

| Key | Type | Description |
| :--- | :--- | :--- |
| `"date_of_birth"` | `dict` or `null` | Result of DOB verification. |
| `"first_name"` | `dict` or `null` | Result of First Name verification. |
| `"middle_name"` | `dict` or `null` | Result of Middle Name verification. |
| `"last_name"` | `dict` or `null` | Result of Last Name verification. |
| `"gender"` | `dict` or `null` | Result of Gender verification. |

**Structure of Successful Match (`dict`):**

| Key | Type | Description |
| :--- | :--- | :--- |
| `"coordinates"` | `list` | The bounding box `[x1, y1, x2, y2]` of the detected text on the image. |
| `"match_score"` | `int` | The fuzzy match score (0-100). For Gender aliases, this is often 100. |
| `"detected_text"` | `str` | The exact text detected by the OCR in that area. |

---

### Example

#### ➡️ Input Parameters

```python
path_to_birth = r"D:\documents\birth_certificate.jpg"
path_to_id = r"D:\documents\passport.jpg"

target_details = {
    "first_name": "ELHAN",
    "middle_name": "BENNY", 
    "last_name": "THOMAS",
    "gender": "Male",
    "dob": "05/04/2005" 
}

{
    "date_of_birth": {
        "coordinates": [590, 439, 864, 481],
        "match_score": 100,
        "detected_text": "05/04/2005"
    },
    "first_name": {
        "coordinates": [600, 333, 738, 374],
        "match_score": 100,
        "detected_text": "ELHAN"
    },
    "middle_name": {
        "coordinates": [614, 223, 945, 268],
        "match_score": 100,
        "detected_text": "BENNY THOMAS"
    },
    "last_name": {
        "coordinates": [614, 223, 945, 268],
        "match_score": 100,
        "detected_text": "BENNY THOMAS"
    },
    "gender": {
        "coordinates": [880, 435, 990, 480],
        "match_score": 100,
        "detected_text": "M"
    }
}

```

## 📜 README: Smart Aadhar Data Extractor

This project uses a combination of **CRAFT** (text detection) and **TrOCR** (text recognition) to perform Optical Character Recognition (OCR) and extract structured data from Aadhar card images or PDFs.

---

### 📥 Input Parameter

The core extraction logic is contained within the `extract_aadhar_smart` function.

| Function | Parameter Name | Description | Example |
| :--- | :--- | :--- | :--- |
| `extract_aadhar_smart` | **`file_path`** | The full file path to the Aadhar document (image or PDF). | `'aad.pdf'` or `'document.jpg'` |

The function accepts a path to either a **PDF file** or a common image format (e.g., `.jpg`, `.jpeg`, `.png`).

---

### 🛠️ Prerequisite: Installing Poppler (For PDF Processing)

To process **PDF files**, the script relies on the `pdf2image` Python library, which requires the external utility **Poppler** to be installed on your system.

Follow these steps for installation on Windows:

1.  **Download Poppler:** Go to the official release page for the compatible version: [https://github.com/oschwartz10612/poppler-windows/releases/tag/v25.12.0-0](https://github.com/oschwartz10612/poppler-windows/releases/tag/v25.12.0-0).
2.  **Extract:** Download and unzip the file (e.g., `poppler-25.12.0.zip`) to a fixed location on your PC (e.g., `D:\poppler-25.12.0`).
3.  **Locate the Bin Path:** The required executable files are located in the `bin` directory within the extracted folder (e.g., `D:\poppler-25.12.0\Library\bin`).
4.  **Configure the Script:** You **must** update the **`POPPLER_PATH`** variable at the top of the Python script to point precisely to this `bin` directory:

    ```python
    POPPLER_PATH = r'D:\poppler-25.12.0\Library\bin' 
    # Update this path to match your installation location
    ```

---

### 📄 Output Format

The function returns a Python dictionary structured to provide both the **extracted value** and technical **metadata** for each field. This metadata is crucial for quality checks and post-processing.

The final output uses lower-cased keys for each field:

```json
{
    "name": {
        "value": "EXTRACTED NAME HERE",
        "coordinates": [x1, x2, y1, y2],
        "accuracy": 0.0
    },
    "DOB": {
        "value": "DD/MM/YYYY",
        "coordinates": [x1, x2, y1, y2],
        "accuracy": 0.0
    },
    "gender": {
        "value": "Male/Female",
        "coordinates": [x1, x2, y1, y2],
        "accuracy": 0.0
    },
    "aadhar_number": {
        "value": "XXXX XXXX XXXX",
        "coordinates": [x1, x2, y1, y2],
        "accuracy": 0.0
    }
}|
