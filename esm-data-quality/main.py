import os
import json
import requests
from datetime import datetime, timedelta
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

def detect_issues(responses):
    issues = []
    flags = []

    # Check for batch submissions (multiple responses within 10 minutes)
    by_participant = defaultdict(list)
    for r in responses:
        pid = r.get("participant_id") or "unknown"
        by_participant[pid].append(r)

    for pid, resps in by_participant.items():
        sorted_resps = sorted(resps, key=lambda x: x.get("submitted_at", ""))
        for i in range(1, len(sorted_resps)):
            try:
                t1 = datetime.fromisoformat(sorted_resps[i-1]["submitted_at"])
                t2 = datetime.fromisoformat(sorted_resps[i]["submitted_at"])
                diff = abs((t2 - t1).total_seconds())
                if diff < 600:
                    flags.append({
                        "type": "batch_submission",
                        "severity": "high",
                        "participant": pid,
                        "detail": f"2 responses {int(diff/60)} min apart",
                        "timestamp": sorted_resps[i]["submitted_at"]
                    })
            except:
                pass

    # Check for straight-line responses (same score repeated)
    for pid, resps in by_participant.items():
        if len(resps) >= 4:
            boredom_scores = [r.get("boredom_score") for r in resps if r.get("boredom_score") is not None]
            if len(set(boredom_scores)) == 1 and len(boredom_scores) >= 4:
                flags.append({
                    "type": "straight_lining",
                    "severity": "medium",
                    "participant": pid,
                    "detail": f"Same boredom score ({boredom_scores[0]}) across {len(boredom_scores)} responses",
                    "timestamp": datetime.utcnow().isoformat()
                })

    # Check for missing data
    missing = [r for r in responses if r.get("boredom_score") is None or r.get("focus_score") is None]
    if missing:
        flags.append({
            "type": "missing_data",
            "severity": "medium",
            "participant": "multiple",
            "detail": f"{len(missing)} responses missing boredom or focus scores",
            "timestamp": datetime.utcnow().isoformat()
        })

    # Check for extreme scores (all 10s or all 0s)
    extremes = [r for r in responses if r.get("boredom_score") in [0, 10] and r.get("focus_score") in [0, 10]]
    if len(extremes) > len(responses) * 0.5:
        flags.append({
            "type": "extreme_responding",
            "severity": "medium",
            "participant": "multiple",
            "detail": f"{len(extremes)}/{len(responses)} responses use extreme scores only",
            "timestamp": datetime.utcnow().isoformat()
        })

    return flags

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def data_quality(request):
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    db = get_db()
    responses = list(db.responses.find({}, {"_id": 0, "raw": 0}))

    if not responses:
        res = jsonify({"error": "No data yet"})
        res.headers["Access-Control-Allow-Origin"] = "*"
        return res, 200

    flags = detect_issues(responses)

    prompt = f"""You are the Data Quality Agent in Momentra, an AI ESM research platform.

You have detected the following data quality issues in a boredom & creativity study with {len(responses)} responses:

{json.dumps(flags, indent=2)}

Provide:
1. QUALITY SCORE: Overall data quality score out of 10 with brief justification
2. CRITICAL ISSUES: Any issues that compromise study validity
3. RECOMMENDATIONS: Specific actions to improve data quality
4. VALID RESPONSES: Estimate of how many responses are usable for analysis

Be direct and actionable. Write for a researcher."""

    assessment = call_gemini(prompt)

    result = {
        "flags": flags,
        "assessment": assessment,
        "total_responses": len(responses),
        "flags_count": len(flags),
        "generated_at": datetime.utcnow().isoformat()
    }

    try:
        db.quality_reports.insert_one({
            "flags_count": len(flags),
            "assessment": assessment,
            "generated_at": datetime.utcnow().isoformat()
        })
    except:
        pass

    res = jsonify(result)
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
