import os
import requests
from datetime import datetime
from pymongo import MongoClient
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

def get_db():
    client = MongoClient(MONGO_URI)
    return client["esm_agent"]

MONGO_MCP_URL = "https://mcp.mongodb.com/mongodb-atlas"
MONGO_API_KEY = os.environ.get("MONGODB_API_KEY")

def log_to_mcp(collection, document_id):
    """Call MongoDB MCP server at runtime."""
    try:
        headers = {"Content-Type": "application/json", "apiKey": MONGO_API_KEY}
        body = {"collection": collection, "documentId": str(document_id)}
        requests.post(MONGO_MCP_URL, json=body, headers=headers, timeout=5)
    except Exception:
        pass

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body)
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]

@app.route("/", methods=["POST", "GET"])
def generate_insights(request):
    db = get_db()
    responses = list(db.responses.find({}, {"_id": 0}))

    if not responses:
        return jsonify({"insight": "No data yet."}), 200

    # Filter only responses with valid scores
    valid = [r for r in responses if r.get("boredom_score") is not None and r.get("focus_score") is not None]

    if not valid:
        return jsonify({"insight": "No valid scored responses yet."}), 200

    summary = []
    for r in valid:
        summary.append(
            f"- Activity: {r.get('activity_before', 'unknown')} | "
            f"Boredom: {r.get('boredom_score')}/10 | "
            f"Focus: {r.get('focus_score')}/10 | "
            f"Notes: {r.get('notes', 'none')} | "
            f"Time: {r.get('submitted_at', 'unknown')}"
        )

    data_str = "\n".join(summary)
    avg_boredom = sum(r["boredom_score"] for r in valid) / len(valid)
    avg_focus = sum(r["focus_score"] for r in valid) / len(valid)

    prompt = f"""You are an AI research assistant analyzing ESM (Experience Sampling Method) data from a boredom & creativity study.

Here is the latest data from {len(valid)} responses:
{data_str}

Overall averages: Boredom {avg_boredom:.1f}/10, Focus {avg_focus:.1f}/10

As an intelligent ESM agent, provide:
1. KEY PATTERN: The most significant pattern you notice (2-3 sentences)
2. ACTIVITY INSIGHT: Which activity correlates most with high/low boredom
3. AGENT RECOMMENDATION: One specific change to the study protocol or a follow-up question to ask participants
4. ALERT: Flag anything unusual or worth the researcher's immediate attention

Be concise, specific, and actionable. Write for a researcher, not a general audience."""

    insight = call_gemini(prompt)

    result = db.insights.insert_one({
        "insight": insight,
        "generated_at": datetime.utcnow().isoformat(),
        "based_on_responses": len(valid),
        "avg_boredom": avg_boredom,
        "avg_focus": avg_focus
    })
    log_to_mcp("insights", result.inserted_id)

    return jsonify({
        "insight": insight,
        "generated_at": datetime.utcnow().isoformat(),
        "based_on_responses": len(valid)
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
