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
}