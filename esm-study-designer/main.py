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
    res = requests.post(url, json=body, timeout=30)
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

    history_text = ""
    for turn in conversation_history:
        role = "Researcher" if turn["role"] == "user" else "Study Designer Agent"
        history_text += f"{role}: {turn['content']}\n"

    prompt = f"""You are the Study Designer Agent in Momentra, an AI-powered ESM (Experience Sampling Method) research platform.

Your job is to help researchers design rigorous ESM studies through conversation. You have deep knowledge of:
- ESM methodology and best practices
- Psychological measurement and validated scales
- Sampling strategies (random, event-contingent, signal-contingent)
- Common confounds and how to control for them
- ethical considerations in experience sampling research

Conversation so far:
{history_text}

Researcher: {researcher_input}

Respond as the Study Designer Agent. Be conversational but precise. Ask clarifying questions when needed.

If you have enough information to propose a study design, output it as a structured protocol in this exact JSON format wrapped in <PROTOCOL> tags:
<PROTOCOL>
{{
  "study_name": "",
  "research_question": "",
  "hypothesis": "",
  "duration_days": 0,
  "prompts_per_day": 0,
  "sampling_windows": [
    {{"start": 9, "end": 12}},
    {{"start": 14, "end": 17}},
    {{"start": 19, "end": 22}}
  ],
  "questions": [
    {{
      "text": "",
      "type": "scale_1_10",
      "variable": ""
    }}
  ],
  "inclusion_criteria": "",
  "potential_confounds": [],
  "recommended_sample_size": 0
}}
</PROTOCOL>

If you're still gathering information, just respond conversationally. Don't output a protocol until you have: research question, target population, and key variables."""

    response_text = call_gemini(prompt)

    protocol = None
    if "<PROTOCOL>" in response_text:
        try:
            protocol_str = response_text.split("<PROTOCOL>")[1].split("</PROTOCOL>")[0].strip()
            protocol = json.loads(protocol_str)
            display_text = response_text.split("<PROTOCOL>")[0].strip()
            if not display_text:
                display_text = "Here's your study protocol! Review it below and I can refine any part of it."

            db = get_db()
            db.study_designs.insert_one({
                "protocol": protocol,
                "created_at": datetime.utcnow().isoformat(),
                "researcher_input": researcher_input
            })
        except:
            display_text = response_text
    else:
        display_text = response_text

    res = jsonify({
        "response": display_text,
        "protocol": protocol
    })
    res.headers["Access-Control-Allow-Origin"] = "*"
    return res

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
