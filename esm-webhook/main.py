import os
import requests
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

ACTIVITY_LABELS = {
    "8ae7fddf-04b4-4e9a-b219-774659acc00a": "Creative work (writing, art, design)",
    "d1f5e708-208f-4a2c-beb1-6456727e5b6e": "Passive activity (scrolling, watching)",
    "d6c943ff-a1f3-4340-872a-920f68204d47": "Social interaction",
    "55065165-984a-48c6-9e34-67da98570eaa": "Physical activity",
    "e1ed88e4-fd53-4111-bdc4-0b6b906592fb": "Work/studying",
    "2f8cdc08-275a-4132-bef7-d738f33a8704": "Other"
}

INSIGHTS_URL = "https://asia-south1-project-d7fef4ca-d9f0-4a6c-a39.cloudfunctions.net/esm-insights"

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["esm_agent"]

@app.route("/", methods=["POST"])
def receive_response(request):
    db = get_db()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    fields = {}
    for field in data.get("data", {}).get("fields", []):
        label = field.get("label", "")
        value = field.get("value")
        if isinstance(value, list) and len(value) > 0:
            value = value[0]
        fields[label] = value

    raw_activity = fields.get("What were you doing just before this prompt?")
    activity_label = ACTIVITY_LABELS.get(raw_activity, raw_activity)

    # Get participant name, fall back to participant_id, then unknown
    participant_name = fields.get("Your name") or fields.get("participant_id") or "unknown"

    response_doc = {
        "participant_id": participant_name.lower().strip().replace(" ", "_"),
        "participant_name": participant_name,
        "submitted_at": datetime.utcnow().isoformat(),
        "activity_before": activity_label,
        "boredom_score": fields.get("How bored do you feel right now? (1 = not at all, 10 = extremely)"),
        "focus_score": fields.get("How focused do you feel right now? (1 = not at all, 10 = extremely)"),
        "notes": fields.get("Anything else you want to note about this moment?"),
        "raw": fields
    }

    db.responses.insert_one(response_doc)

    # Upsert participant record
    db.participants.update_one(
        {"participant_id": response_doc["participant_id"]},
        {
            "$set": {"name": participant_name, "status": "active", "study_id": "boredom_creative_tasks"},
            "$inc": {"prompts_answered": 1}
        },
        upsert=True
    )

    # Trigger agent reasoning after every new response
    try:
        requests.post(INSIGHTS_URL, json={}, timeout=5)
    except Exception:
        pass

    return jsonify({"status": "saved"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
