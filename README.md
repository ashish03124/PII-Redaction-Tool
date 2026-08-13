# PII Redaction Tool

A robust, localized, and formatting-preserving PII (Personally Identifiable Information) Redaction Tool. It processes complex `.docx` files (such as high-stakes corporate filings like a Red Herring Prospectus) to redact and anonymize sensitive information, replacing it with realistic, contextually matching fake data while retaining the document's original structure, styles, tables, and headers/footers.

## Features

1. **Hybrid PII Detection Engine**: Combines **Microsoft Presidio** with **spaCy** NLP models and custom regular-expression-based **Entity Recognizers**.
2. **Indian-Context Support**: Specially tuned custom recognizers to detect Indian company structures (e.g., *LLP, Pvt Ltd, Associates*), Indian address formats, local phone numbers, and common Indian name salutations/roles.
3. **Faker-Based Consistent Registry**: Tracks every real entity name, email, phone, etc., and maps it consistently to a realistic fake alternative (using the `en_IN` locale) across the entire document.
4. **Format-Preserving DOCX Traversal**: Uses an index-mapping algorithm operating from back-to-front by paragraph/table/run to perform edits without breaking font styles, bold/italic, alignment, or cell borders. It recursively handles nested tables, headers, and footers.
5. **Rigorous Evaluation Framework**: Includes an evaluation suite to compute and report Entity-level Precision, Recall, F1-Score, and Accuracy (IoU) across 9 PII categories.

---

## Detection & Redaction Capabilities

The tool identifies, anonymizes, and consistent-maps the following 9 PII types:
*   **Full Names** (`PERSON`): Supported by spaCy, corporate role context (e.g. `Sandesh Bhagwat, CEO`), and salutations (e.g. `Mr.`, `Shri`).
*   **Email Addresses** (`EMAIL_ADDRESS`): Standard email formats.
*   **Phone Numbers** (`PHONE_NUMBER`): Indian mobile formats and standard landlines.
*   **Company Names** (`COMPANY`): Corporate entity names matched via custom suffix regex patterns (e.g. `LLP`, `Private Limited`, `Associates`) and spaCy ORG labels.
*   **Physical/Mailing Addresses** (`ADDRESS`): Structured local addresses, village blocks, peth areas, and pincodes.
*   **US Social Security Numbers (SSNs)** (`US_SSN`): Standard SSN formats.
*   **Credit Card Numbers** (`CREDIT_CARD`): Standard 16-digit cards, bypassing Luhn check validation for test dummy card data.
*   **Dates of Birth** (`DATE_OF_BIRTH`): Date formats like `October 12, 1974` or `12/10/1974`.
*   **IP Addresses** (`IP_ADDRESS`): IPv4 formats.

---

## Installation & Setup

### Prerequisites
Make sure you have Python 3.8+ installed on your system.

### Install Dependencies
Clone the repository and run the following commands to install the required libraries and download the English spaCy language model:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## Usage

### 1. Run Document Redaction
To redact the default prospectus (`Red Herring Prospectus.docx`) and output a redacted copy (`Red Herring Prospectus_Redacted.docx`), run:

```bash
python run.py
```

To specify custom input/output documents, pass them as arguments:
```bash
python run.py path/to/input.docx path/to/output.docx
```

### 2. Run Evaluation
To run the evaluation framework against the ground-truth test suite and report metrics, run:

```bash
python evaluate.py
```

---

## Evaluation Results

Running the evaluation framework reports the following entity-level performance:

```
==================================================
EVALUATION REPORT
==================================================
| PII Type        | TP   | FP   | FN   | Precision | Recall    | F1-Score  |
|-----------------|------|------|------|-----------|-----------|-----------|
| PERSON          | 7    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| EMAIL_ADDRESS   | 4    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| PHONE_NUMBER    | 3    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| COMPANY         | 4    | 0    | 1    | 1.0000    | 0.8000    | 0.8889    |
| ADDRESS         | 6    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| DATE_OF_BIRTH   | 1    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| IP_ADDRESS      | 2    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| US_SSN          | 1    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
| CREDIT_CARD     | 1    | 0    | 0    | 1.0000    | 1.0000    | 1.0000    |
|-----------------|------|------|------|-----------|-----------|-----------|
| OVERALL         | 29   | 0    | 1    | 1.0000    | 0.9667    | 0.9831    |
==================================================
Entity-level Accuracy (IoU): 0.9667
```

### Analysis & Trade-offs
*   **Precision (100%)**: The tool achieved perfect precision. There are **zero false positives**, meaning non-sensitive words or normal sentences are not incorrectly flagged and redacted.
*   **Recall (96.67%)**: The tool detected 29 out of 30 PII entities in the test set.
*   **The Single Missed Entity**: The only false negative (`FN`) was the company `HDFC Limited` in Sentence 6. This is a structural overlap because the parent address string (`5th Floor, Gopal House Opposite Harshal Hall, above HDFC Limited Karve Road, Pune – 411 038 Maharashtra, India`) was matched and redacted as an `ADDRESS` entity. Since the entire address block was replaced with a fake address (e.g. `29, Raj Path, Chennai`), `HDFC Limited` was effectively anonymized and no security leak occurred.
