# Intelligent Cloud Document Analyst

**Scenario:** Business documents (contracts, invoices, purchase orders, vendor agreements)  
**Stack:** n8n · Google Gemini 3 Flash · Flask APIs · Google Sheets · Gmail

Automated pipeline: a new file in Google Drive is extracted, analyzed by Gemini, enriched by a custom metadata API, logged to Google Sheets, and reported by email.

---

## Project structure

| Path | Role |
|------|------|
| `extract_api/` | PDF & DOCX text extraction (Flask, port 8001) |
| `metadata_api/` | Department, sensitivity, routing enrichment (Flask, port 8000) |
| `workflows/` | Exported n8n workflows (see below) |
| `incoming_docs/` | Sample test documents |
| `images/` | Screenshots referenced in this README |

### extract_api

Used by the main workflow for **PDF** (PyMuPDF) and **DOCX** (python-docx) files. n8n sends the downloaded file to `POST /extract` (multipart field `file`). Returns `filename`, `file_type`, `extracted_text`.

Also exposes `GET /health`.

### metadata_api

Called after Gemini parsing. `POST /enrich` adds `document_id`, `department`, `sensitivity`, `routing_tag`, `keyword_tags`, adjusted `confidence_score`, and `processed_at`.

Also exposes `GET /health`, `GET /categories`, `POST /sensitivity`.

**Both APIs must be running** before the n8n workflows execute — `extract_api` on port **8001** (PDF/DOCX parsing) and `metadata_api` on port **8000** (enrichment after Gemini).

### Workflow exports (`workflows/`)

| File | Description |
|------|-------------|
| `Document Analyst.json` | Main document processing pipeline |
| `send_daily_mail.json` | Scheduled daily digest (bonus) |

Import in n8n via **Workflows → Import from File**. Credentials (Google Drive, Sheets, Gmail, Gemini API key) must be reconnected after import.

---

## Main workflow

[Open full-size main flow screenshot](./images/main_flow.png)

![Main n8n workflow](./images/main_flow.png)

| Stage | What happens |
|-------|----------------|
| **Trigger** | Google Drive — new file in watched folder → download |
| **Parsing** | Switch on extension: **txt** (Code) · **pdf/docx** (`extract_api`) → Merge → Clean text |
| **Gemini** | Build prompt → Gemini 3 Flash (structured JSON) → Parse response |
| **Enrich** | `metadata_api` — department, sensitivity, routing tag |
| **Outputs** | Append row to Google Sheets · upload report to Drive · send completion email |

### Fallback logic

| Branch | Trigger | Result |
|--------|---------|--------|
| Unsupported file type | Switch fallback (not txt / pdf / docx) | Rejection email |
| Gemini API failure | HTTP Request error output (after retries) | Failure alert email |
| Confidential document | IF `sensitivity = confidential` after Enrich | Immediate review email; pipeline continues |

### Working outputs

**Google Sheets — one row per processed document**

![Google Sheets results](./images/sheet.png)

**Email — document processed successfully**

![Document processed email](./images/new_doc_mail.png)

**Email — confidential document alert**

![Confidential alert email](./images/Immediate_review_mail.png)

**Email — unsupported file type rejected**

![Unsupported file email](./images/unsupported_file_mail.png)

---

## Daily digest workflow (bonus)

[Open full-size daily mail flow screenshot](./images/daily_mail_flow.png)

![Daily mail n8n workflow](./images/daily_mail_flow.png)

Schedule Trigger → read Google Sheets → Code (filter last 24h, build summary) → IF rows exist → Gmail digest.

![Daily digest email](./images/daily_mail.png)
