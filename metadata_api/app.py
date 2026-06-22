import datetime
import uuid

from flask import Flask, jsonify, request

app = Flask(__name__)

# Domain scenario: Business documents (section 10, option 17)
CATEGORIES = [
    "invoice",
    "contract",
    "purchase_order",
    "vendor_agreement",
    "quote",
    "receipt",
    "other",
]

DEPARTMENT_MAP = {
    "invoice": "Finance",
    "contract": "Legal",
    "purchase_order": "Procurement",
    "vendor_agreement": "Legal",
    "quote": "Procurement",
    "receipt": "Finance",
    "report": "Management",
    "ticket": "Operations",
    "article": "General",
    "other": "General",
}

CONFIDENTIAL_KEYWORDS = [
    "bank account",
    "routing number",
    "account number",
    "tax id",
    "ein",
    "ssn",
    "wire transfer",
    "payment terms",
    "proprietary",
    "confidential",
    "nda",
    "trade secret",
    "credit card",
]

INTERNAL_KEYWORDS = [
    "vendor",
    "purchase order",
    "procurement",
    "contract",
    "agreement",
    "invoice",
    "pricing",
    "internal",
    "net 30",
    "net 60",
]


def entity_text(entities) -> str:
    if not entities:
        return ""
    if isinstance(entities, dict):
        parts = []
        for value in entities.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            else:
                parts.append(str(value))
        return " ".join(parts).lower()
    return str(entities).lower()


def classify_sensitivity(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in CONFIDENTIAL_KEYWORDS):
        return "confidential"
    if any(keyword in lowered for keyword in INTERNAL_KEYWORDS):
        return "internal"
    return "public"


def count_entity_fields(entities) -> int:
    if not isinstance(entities, dict):
        return 0
    count = 0
    for value in entities.values():
        if isinstance(value, list) and value:
            count += 1
    return count


def adjust_confidence(base_score: float, entities) -> float:
    filled = count_entity_fields(entities)
    bonus = min(filled * 0.05, 0.15)
    adjusted = max(0.0, min(1.0, float(base_score) + bonus))
    return round(adjusted, 2)


def build_routing_tag(classification: str, sensitivity: str, confidence: float) -> str:
    if sensitivity == "confidential":
        return "escalate"
    if classification in {"contract", "vendor_agreement", "purchase_order"}:
        return "needs-review"
    if confidence < 0.7:
        return "needs-review"
    if classification in {"invoice", "receipt", "quote"}:
        return "auto-approved"
    return "needs-review"


def build_keyword_tags(classification: str, entities, sensitivity: str) -> list[str]:
    tags = [classification, sensitivity]
    if isinstance(entities, dict):
        for key, values in entities.items():
            if isinstance(values, list) and values:
                tags.append(key)
    return sorted(set(tags))


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/categories")
def categories():
    return jsonify({"categories": CATEGORIES, "scenario": "Business documents"})


@app.post("/sensitivity")
def sensitivity():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    entities = payload.get("entities", {})
    combined = f"{text} {entity_text(entities)}".strip()

    if not combined:
        return jsonify({"detail": "Provide text and/or entities"}), 400

    level = classify_sensitivity(combined)
    return jsonify({"sensitivity": level})


@app.post("/enrich")
def enrich():
    payload = request.get_json(silent=True) or {}

    classification = payload.get("classification", "other")
    sentiment = payload.get("sentiment", "neutral")
    confidence_score = payload.get("confidence_score", 0.0)
    entities = payload.get("entities", {})
    summary = payload.get("summary", "")
    filename = payload.get("filename")

    adjusted_confidence = adjust_confidence(confidence_score, entities)
    combined_text = f"{summary} {entity_text(entities)}"
    sensitivity = classify_sensitivity(combined_text)
    department = DEPARTMENT_MAP.get(classification, "General")
    routing_tag = build_routing_tag(classification, sensitivity, adjusted_confidence)
    keyword_tags = build_keyword_tags(classification, entities, sensitivity)

    result = {
        "document_id": str(uuid.uuid4()),
        "department": department,
        "sensitivity": sensitivity,
        "routing_tag": routing_tag,
        "keyword_tags": keyword_tags,
        "confidence_score": adjusted_confidence,
        "original_confidence_score": confidence_score,
        "classification": classification,
        "sentiment": sentiment,
        "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    if filename:
        result["filename"] = filename

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
