import os
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["esm_agent"]

@app.route("/", methods=["POST"])
def receive_response(request):
    db = get_db()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    
    # Tally sends fields as a list of {label, value} objects
    fields = {}
    for field in data.get("data", {}).get("fields", []):
        label = field.get("label", "")
        value = field.get("value")
        if isinstance(value, list) and len(value) > 0:
            value = value[0]
        fields[label] = value

    response_doc = {
        "participant_id": fields.get("participant_id", "unknown"),
        "submitted_at": datetime.utcnow().isoformat(),
        "activity_before": fields.get("What were you doing just before this prompt?"),
        "boredom_score": fields.get("How bored do you feel right now? (1 = not at all, 10 = extremely)"),
        "focus_score": fields.get("How focused do you feel right now? (1 = not at all, 10 = extremely)"),
        "notes": fields.get("Anything else you want to note about this moment?"),
        "raw": fields
    }
    
    db.responses.insert_one(response_doc)
    db.participants.update_one(
        {"study_id": "boredom_creative_tasks"},
        {"$inc": {"prompts_answered": 1}}
    )
    return jsonify({"status": "saved"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
