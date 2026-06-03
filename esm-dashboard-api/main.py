import os
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["esm_agent"]

@app.route("/", methods=["GET"])
def dashboard(request):
    db = get_db()

    responses = list(db.responses.find({}, {"_id": 0, "raw": 0}))
    participants = list(db.participants.find({}, {"_id": 0}))
    prompts_total = db.prompts.count_documents({})
    latest_insight = db.insights.find_one(
        {}, {"_id": 0}, sort=[("generated_at", -1)]
    )

    # Agent actions (latest 10)
    agent_actions = list(db.agent_actions.find(
        {}, {"_id": 0}, sort=[("timestamp", -1)], limit=10
    ))

    # Calculate compliance per participant
    for p in participants:
        answered = p.get("prompts_answered", 0)
        sent = p.get("prompts_sent", prompts_total) or 1
        p["compliance_rate"] = min(100, round((answered / sent) * 100))

    return jsonify({
        "responses": responses,
        "participants": participants,
        "prompts_total": prompts_total,
        "latest_insight": latest_insight,
        "agent_actions": agent_actions
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
