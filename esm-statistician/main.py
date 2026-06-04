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

def compute_stats(responses):
    valid = [r for r in responses if r.get("boredom_score") is not None and r.get("focus_score") is not None]
    if not valid:
        return {}

    by_activity = defaultdict(list)
    for r in valid:
        act = r.get("activity_before") or "Unknown"
        by_activity[act].append(r)

    activity_stats = {}
    for act, items in by_activity.items():
        activity_stats[str(act)] = {
            "count": len(items),
            "avg_boredom": round(sum(i["boredom_score"] for i in items) / len(items), 2),
            "avg_focus": round(sum(i["focus_score"] for i in items) / len(items), 2)
        }

    overall_avg_boredom = round(sum(r["boredom_score"] for r in valid) / len(valid), 2)
    overall_avg_focus = round(sum(r["focus_score"] for r in valid) / len(valid), 2)
    high_boredom = [r for r in valid if r["boredom_score"] >= 8]
    low_boredom = [r for r in valid if r["boredom_score"] <= 3]

    return {
        "total_responses": len(valid),
        "overall_avg_boredom": overall_avg_boredom,
        "overall_avg_focus": overall_avg_focus,
        "by_activity": activity_stats,
        "high_boredom_count": len(high_boredom),
        "low_boredom_count": len(low_boredom)
    }

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def statistician(request):
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    db = get_db()
    responses = list(db.responses.find({}, {"_id": 0, "raw": 0}))
    stats = compute_stats(responses)

    if not stats:
        res = jsonify({"error": "Not enough data yet"})
        res.headers["Access-Control-Allow-Origin"] = "*"
        return res, 200

    prompt = f"""You are the Statistician Agent in Momentra, an AI ESM research platform for a boredom and creativity study.

Statistics from live data:
{json.dumps(stats, indent=2)}

Generate:
1. HYPOTHESES: 3 testable hypotheses (H1, H2, H3)
2. KEY FINDINGS: 3 quantitative findings referencing actual numbers
3. ANOMALIES: data quality issues or unexpected patterns
4. NEXT STEPS: 2 specific recommendations

Be precise and quantitative."""

    analysis = call_gemini(prompt)

    try:
        db.statistician_reports.insert_one({
            "analysis": analysis,
            "total_responses": stats["total_responses"],
            "avg_boredom": stats["overall_avg_boredom"],
            "avg_focus": stats["overall_avg_focus"],
            "generated_at": datetime.utcnow().isoformat()
        })
    except Exception:
        pass

    res = jsonify({
        "stats": stats,
        "analysis": analysis,
        "generated_at": datetime.utcnow().isoformat()
    })
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
