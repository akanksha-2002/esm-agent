import os
import json
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

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body, timeout=55)
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

@app.route("/", methods=["POST", "OPTIONS"])
def design_study(request):
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return res

    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "No message provided"}), 400

    researcher_input = data.get("message")
    conversation_history = data.get("history", [])
    recent_history = conversation_history[-6:]

    history_text = ""
    for turn in recent_history:
        role = "Researcher" if turn["role"] == "user" else "Study Designer Agent"
        content = turn["content"][:400] + "..." if len(turn["content"]) > 400 else turn["content"]
        history_text += f"{role}: {content}\n"

    prompt = f"""You are the Study Designer Agent in Momentra, an AI ESM research platform.

Recent conversation:
{history_text}

Researcher: {researcher_input}

Based on the conversation, generate a complete study protocol AND a pre-study simulation.

Output in this exact format:

<PROTOCOL>
{{
  "study_name": "",
  "research_question": "",
  "hypothesis": "",
  "duration_days": 0,
  "prompts_per_day": 0,
  "sampling_windows": [{{"start": 9, "end": 13}}, {{"start": 14, "end": 18}}, {{"start": 19, "end": 22}}],
  "questions": [{{"text": "", "type": "scale_1_7", "variable": ""}}],
  "inclusion_criteria": "",
  "potential_confounds": [],
  "recommended_sample_size": 0
}}
</PROTOCOL>

<SIMULATION>
{{
  "predicted_patterns": [
    "Pattern 1 based on existing ESM literature",
    "Pattern 2 you are likely to observe",
    "Pattern 3 that may surprise you"
  ],
  "risk_flags": [
    "Risk 1 that could compromise validity",
    "Risk 2 to watch out for"
  ],
  "expected_compliance_rate": "X%",
  "statistical_power_note": "Brief note on whether recommended sample size is sufficient",
  "similar_studies_found": "Brief reference to what similar ESM studies have found",
  "agent_recommendation": "One specific thing to change or watch before launching"
}}
</SIMULATION>

After both tags, write 2-3 sentences summarizing the design and what the simulation predicts."""

    response_text = call_gemini(prompt)

    protocol = None
    simulation = None
    display_text = response_text

    if "<PROTOCOL>" in response_text:
        try:
            protocol_str = response_text.split("<PROTOCOL>")[1].split("</PROTOCOL>")[0].strip()
            protocol = json.loads(protocol_str)
        except:
            pass

    if "<SIMULATION>" in response_text:
        try:
            sim_str = response_text.split("<SIMULATION>")[1].split("</SIMULATION>")[0].strip()
            simulation = json.loads(sim_str)
        except:
            pass

    if "</SIMULATION>" in response_text:
        parts = response_text.split("</SIMULATION>")
        display_text = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "Your study protocol and pre-study simulation are ready!"
    elif "</PROTOCOL>" in response_text:
        parts = response_text.split("</PROTOCOL>")
        display_text = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "Your study protocol is ready!"

    if protocol:
        try:
            db = get_db()
            db.study_designs.insert_one({
                "protocol": protocol,
                "simulation": simulation,
                "created_at": datetime.utcnow().isoformat()
            })
        except:
            pass

    res = jsonify({
        "response": display_text,
        "protocol": protocol,
        "simulation": simulation
    })
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
