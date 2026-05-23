# ESM Agent — AI-Powered Experience Sampling Method Platform

## 🧠 What it does
ESM Agent automates the full scaffolding of Experience Sampling Method (ESM) studies — making rigorous psychological research accessible to independent researchers without institutional infrastructure or expensive tools.

Traditional ESM tools cost thousands of dollars. ESM Agent is the affordable, intelligent alternative.

## 🔬 The Research Problem
ESM requires:
- **Stratified random sampling** — prompts at unpredictable intervals so participants can't game their answers
- **Compliance tracking** — real-time monitoring of response rates per participant
- **Carryover effect detection** — tracking question order to statistically account for contamination

## 🏗️ Architecture

## 🛠️ Tech Stack
- **Google Cloud Functions** — serverless orchestration
- **Google Cloud Scheduler** — automated daily triggering
- **MongoDB Atlas** — study data storage (partner integration)
- **Gemini 2.0 Flash** — pattern detection and insight generation
- **Tally** — participant-facing survey forms

## 📦 Collections (MongoDB)
- `studies` — study design, hypothesis, randomization windows
- `participants` — enrollment, compliance tracking
- `prompts` — every scheduled prompt with random send time
- `responses` — participant answers with timestamps

## 🚀 Setup
1. Create MongoDB Atlas cluster
2. Deploy Cloud Functions (see `/esm-scheduler`, `/esm-webhook`, `/esm-insights`)
3. Set environment variables: `MONGO_URI`, `GEMINI_API_KEY`
4. Create Tally form and connect webhook to `esm-webhook` URL
5. Set up Cloud Scheduler to hit `esm-scheduler` daily at 8am

## 🎯 Target Users
Independent cognitive science researchers, psychology PhD students, and behavioral scientists without access to expensive institutional tools like Qualtrics + SPSS.

## 📄 License
MIT
