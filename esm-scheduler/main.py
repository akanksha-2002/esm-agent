import os
import random
from datetime import datetime, date
from pymongo import MongoClient
from flask import Flask, jsonify

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI")

def get_db():
    client = MongoClient(MONGO_URI)
    return client["esm_agent"]

@app.route("/schedule", methods=["GET"])
def schedule_prompts():
    db = get_db()
    
    # Get active study
    study = db.studies.find_one({"status": "active"})
    if not study:
        return jsonify({"error": "No active study found"}), 404
    
    # Get active participants
    participants = list(db.participants.find({"status": "active"}))
    if not participants:
        return jsonify({"error": "No active participants"}), 404
    
    scheduled = []
    today = str(date.today())
    
    for participant in participants:
        for window in study["window_hours"]:
            # Random time within each window
            start_min = window["start"] * 60
            end_min = window["end"] * 60
            random_min = random.randint(start_min, end_min - 30)
            send_hour = random_min // 60
            send_minute = random_min % 60
            send_time = f"{send_hour:02d}:{send_minute:02d}"
            
            # Check if already scheduled today
            existing = db.prompts.find_one({
                "participant_id": str(participant["_id"]),
                "scheduled_date": today,
                "window_start": window["start"]
            })
            
            if not existing:
                prompt_doc = {
                    "participant_id": str(participant["_id"]),
                    "study_id": participant["study_id"],
                    "scheduled_date": today,
                    "window_start": window["start"],
                    "send_time": send_time,
                    "status": "scheduled",
                    "question_order": random.sample(range(1, 6), 5),
                    "created_at": datetime.utcnow().isoformat()
                }
                db.prompts.insert_one(prompt_doc)
                scheduled.append({
                    "participant": participant["name"],
                    "send_time": send_time,
                    "window": f"{window['start']}:00-{window['end']}:00"
                })
    
    return jsonify({
        "date": today,
        "prompts_scheduled": len(scheduled),
        "schedule": scheduled
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
