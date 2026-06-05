import os
import json
import requests
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

def get_db():
    client = MongoClient(MONGO_URI)
    return client["esm_agent"]

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body, timeout=55)
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def get_study_context(db):
    responses = list(db.responses.find({}, {"_id": 0, "raw": 0}))
    participants = list(db.participants.find({}, {"_id": 0}))
    agent_actions = list(db.agent_actions.find({}, {"_id": 0}))
    latest_insight = db.insights.find_one({}, {"_id": 0}, sort=[("generated_at", -1)])

    valid = [r for r in responses if r.get("boredom_score") is not None and r.get("focus_score") is not None]

    by_activity = defaultdict(list)
    for r in valid:
        act = r.get("activity_before") or "Unknown"
        by_activity[str(act)].append(r)

    activity_stats = {}
    for act, items in by_activity.items():
        activity_stats[act] = {
            "count": len(items),
            "avg_boredom": round(sum(i["boredom_score"] for i in items) / len(items), 2),
            "avg_focus": round(sum(i["focus_score"] for i in items) / len(items), 2)
        }

    by_participant = defaultdict(list)
    for r in valid:
        pid = r.get("participant_name") or r.get("participant_id") or "unknown"
        by_participant[str(pid)].append(r)

    participant_stats = {}
    for pid, items in by_participant.items():
        participant_stats[pid] = {
            "count": len(items),
            "avg_boredom": round(sum(i["boredom_score"] for i in items) / len(items), 2),
            "avg_focus": round(sum(i["focus_score"] for i in items) / len(items), 2)
        }

    return {
        "total_responses": len(valid),
        "total_participants": len(participants),
        "overall_avg_boredom": round(sum(r["boredom_score"] for r in valid) / len(valid), 2) if valid else 0,
        "overall_avg_focus": round(sum(r["focus_score"] for r in valid) / len(valid), 2) if valid else 0,
        "by_activity": activity_stats,
        "by_participant": participant_stats,
        "agent_actions_count": len(agent_actions),
        "latest_insight": latest_insight.get("insight", "")[:500] if latest_insight else "",
        "sample_responses": [
            {
                "activity": r.get("activity_before"),
                "boredom": r.get("boredom_score"),
                "focus": r.get("focus_score"),
                "notes": r.get("notes"),
                "time": r.get("submitted_at")
            } for r in valid[-10:]
        ]
    }

@app.route("/", methods=["POST", "OPTIONS"])
def analyst(request):
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    data = request.get_json()
    if not data or not data.get("question"):
        return jsonify({"error": "No question provided"}), 400

    question = data.get("question")
    history = data.get("history", [])

    db = get_db()
    context = get_study_context(db)

    history_text = ""
    for turn in history[-4:]:
        role = "Researcher" if turn["role"] == "user" else "Assistant"
        content = turn["content"][:300] + "..." if len(turn["content"]) > 300 else turn["content"]
        history_text += f"{role}: {content}\n"

    prompt = f"""You are an AI research analyst for Momentra, an ESM research platform. You have direct access to the live study data.

LIVE STUDY DATA:
{json.dumps(context, indent=2)}

CONVERSATION HISTORY:
{history_text}

RESEARCHER QUESTION: {question}

Answer the researcher's question using the actual data provided. Be specific and quantitative — reference real numbers from the data. If the data doesn't contain enough information to answer fully, say so clearly and suggest what additional data would help.

Keep your answer concise (3-5 sentences max) unless a detailed breakdown is specifically requested. Write like a data-savvy research collaborator, not a formal report."""

    answer = call_gemini(prompt)

    res = jsonify({
        "answer": answer,
        "data_points_used": context["total_responses"]
    })
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
