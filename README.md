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
| `/api/quality-score/` | `POST` | Capture quality scoring |
