import os
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["esm_agent"]

@app.route("/", methods=["GET", "OPTIONS"])
def dashboard(request):
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    db = get_db()
    responses = list(db.responses.find({}, {"_id": 0, "raw": 0}))
    participants = list(db.participants.find({}, {"_id": 0}))
    prompts_total = db.prompts.count_documents({})
    latest_insight = db.insights.find_one({}, {"_id": 0}, sort=[("generated_at", -1)])
    agent_actions = list(db.agent_actions.find({}, {"_id": 0}, sort=[("timestamp", -1)], limit=10))

    for p in participants:
        answered = p.get("prompts_answered", 0)
        sent = p.get("prompts_sent", prompts_total) or 1
        p["compliance_rate"] = min(100, round((answered / sent) * 100))

    res = jsonify({
        "responses": responses,
        "participants": participants,
        "prompts_total": prompts_total,
        "latest_insight": latest_insight,
        "agent_actions": agent_actions
    })
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
