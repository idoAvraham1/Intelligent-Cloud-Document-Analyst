import base64
import io
from pathlib import Path

import fitz
from docx import Document
from flask import Flask, jsonify, request

app = Flask(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_pdf_text(file_bytes: bytes, filename: str) -> dict:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = [page.get_text() for page in doc]
    page_count = len(text_parts)
    doc.close()

    extracted_text = "\n".join(text_parts).strip()
    if not extracted_text:
        extracted_text = (
            "[No selectable text found - this may be a scanned PDF. "
            "Consider Gemini Vision for image-based pages.]"
        )

    return {
        "filename": filename,
        "file_type": "pdf",
        "extracted_text": extracted_text,
        "page_count": page_count,
    }


def extract_docx_text(file_bytes: bytes, filename: str) -> dict:
    doc = Document(io.BytesIO(file_bytes))
    text_parts = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]

    extracted_text = "\n".join(text_parts).strip()
    if not extracted_text:
        extracted_text = "[No text found in DOCX paragraphs.]"

    return {
        "filename": filename,
        "file_type": "docx",
        "extracted_text": extracted_text,
        "paragraph_count": len(text_parts),
    }


def parse_upload() -> tuple[bytes, str]:
    """Accept file bytes from multipart form or JSON base64 payload."""
    if "file" in request.files:
        uploaded = request.files["file"]
        filename = uploaded.filename or ""
        file_bytes = uploaded.read()
        if not file_bytes:
            raise ValueError("Uploaded file is empty")
        return file_bytes, filename

    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename") or ""
    content_base64 = payload.get("content_base64")

    if not filename:
        raise ValueError("Missing required field: filename")
    if not content_base64:
        raise ValueError("Missing required field: content_base64 (or multipart file field: file)")

    try:
        file_bytes = base64.b64decode(content_base64)
    except Exception as exc:
        raise ValueError("Invalid base64 in content_base64") from exc

    if not file_bytes:
        raise ValueError("Uploaded file is empty")

    return file_bytes, filename


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/extract")
def extract_document():
    try:
        file_bytes, filename = parse_upload()
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return jsonify({"detail": "Only PDF and DOCX files are supported"}), 400

    try:
        if suffix == ".pdf":
            result = extract_pdf_text(file_bytes, filename)
        else:
            result = extract_docx_text(file_bytes, filename)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"detail": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
