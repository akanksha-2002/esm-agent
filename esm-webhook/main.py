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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["esm_agent"]

def generate_followup(participant_name, activity, boredom, focus, notes):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""You are an ESM research agent. A participant just reported high boredom.

Participant: {participant_name}
Activity before: {activity}
Boredom: {boredom}/10
Focus: {focus}/10
Notes: {notes or 'none'}

Generate ONE short, specific follow-up question (max 20 words) to better understand their boredom state. 
Make it feel natural and conversational, not clinical. Return only the question, nothing else."""

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body, timeout=10)
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

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
    participant_name = fields.get("Your name") or fields.get("participant_id") or "unknown"

    boredom = fields.get("How bored do you feel right now? (1 = not at all, 10 = extremely)")
    focus = fields.get("How focused do you feel right now? (1 = not at all, 10 = extremely)")
    notes = fields.get("Anything else you want to note about this moment?")

    response_doc = {
        "participant_id": participant_name.lower().strip().replace(" ", "_"),
        "participant_name": participant_name,
        "submitted_at": datetime.utcnow().isoformat(),
        "activity_before": activity_label,
        "boredom_score": boredom,
        "focus_score": focus,
        "notes": notes,
        "raw": fields
    }

    db.responses.insert_one(response_doc)

    db.participants.update_one(
        {"participant_id": response_doc["participant_id"]},
        {
            "$set": {"name": participant_name, "status": "active", "study_id": "boredom_creative_tasks"},
            "$inc": {"prompts_answered": 1}
        },
        upsert=True
    )

    # Agent reasoning — adaptive follow-up for high boredom
    agent_action = None
    try:
        if boredom is not None and int(boredom) >= 8:
            followup = generate_followup(participant_name, activity_label, boredom, focus, notes)
            agent_action = {
                "type": "adaptive_followup",
                "participant": participant_name,
                "trigger": f"High boredom ({boredom}/10) after {activity_label}",
                "followup_question": followup,
                "timestamp": datetime.utcnow().isoformat()
            }
            db.agent_actions.insert_one(agent_action)
    except Exception as e:
        pass

    # Trigger insights update
    try:
        requests.post(INSIGHTS_URL, json={}, timeout=5)
    except Exception:
        pass

    response_data = {"status": "saved"}
    if agent_action:
        response_data["agent_followup"] = agent_action["followup_question"]

    return jsonify(response_data), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
