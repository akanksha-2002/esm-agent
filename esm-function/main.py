import os
import random
from datetime import date
from pymongo import MongoClient
from flask import jsonify

def schedule_prompts(request):
    client = MongoClient(os.environ.get("MONGO_URI"))
    db = client["esm_agent"]
    study = db.studies.find_one({"status": "active"})
    if not study:
        return jsonify({"error": "No active study"}), 404
    participants = list(db.participants.find({"status": "active"}))
    scheduled = []
    today = str(date.today())
    for participant in participants:
        for window in study["window_hours"]:
            start_min = window["start"] * 60
            end_min = window["end"] * 60
            random_min = random.randint(start_min, end_min - 30)
            send_time = f"{random_min // 60:02d}:{random_min % 60:02d}"
            existing = db.prompts.find_one({
                "participant_id": str(participant["_id"]),
                "scheduled_date": today,
                "window_start": window["start"]
            })
            if not existing:
                db.prompts.insert_one({
                    "participant_id": str(participant["_id"]),
                    "study_id": participant["study_id"],
                    "scheduled_date": today,
                    "window_start": window["start"],
                    "send_time": send_time,
                    "status": "scheduled",
                    "question_order": random.sample(range(1, 6), 5)
                })
                scheduled.append({"participant": participant["name"], "send_time": send_time})
    return jsonify({"date": today, "scheduled": len(scheduled), "schedule": scheduled})
