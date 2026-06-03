# ESM Agent

An AI-powered Experience Sampling Method (ESM) agent for psychological research. ESM Agent automates the hardest parts of running an ESM study — randomized prompt scheduling, real-time data collection, compliance tracking, and AI-driven pattern analysis.

Built for the Google Cloud x MongoDB Hackathon 2026.

## What it does

Traditional ESM studies require researchers to manually send prompts, chase participants, and analyze spreadsheets after the fact. ESM Agent does all of this automatically:

- **Randomized scheduling** — prompts are sent at random times within configurable windows to prevent habituation
- **Real-time data collection** — participants respond via a lightweight Tally form; responses land in MongoDB Atlas instantly
- **Adaptive questioning** — when a participant reports high boredom (≥8/10), Gemini generates a personalized follow-up question based on their activity and context
- **Automatic insights** — after every new response, Gemini analyzes the full dataset and surfaces patterns, anomalies, and research recommendations
- **Live researcher dashboard** — hosted on GitHub Pages, showing trends, activity breakdowns, participant compliance, and agent actions in real time

## Architecture
## Tech stack

- **MongoDB Atlas** (GCP Mumbai) — flexible document store for ESM response data
- **Google Cloud Functions** — serverless compute for webhook, scheduler, insights, dashboard API
- **Gemini 2.5 Flash** — pattern analysis and adaptive question generation
- **Tally** — participant-facing form
- **GitHub Pages** — researcher dashboard

## Live demo

- Dashboard: https://akanksha-2002.github.io/esm-agent
- Study form: https://tally.so/r/Y5xD0J

## Current study

**Boredom & Creativity** — investigating how boredom levels fluctuate across different activity types (creative work, passive activity, physical activity, social interaction, work/studying) and how focus correlates with boredom in naturalistic settings.

## Setup

### Prerequisites
- Google Cloud project with Cloud Functions enabled
- MongoDB Atlas cluster
- Gemini API key
- Tally account

### Deploy

```bash
# Clone the repo
git clone https://github.com/akanksha-2002/esm-agent.git
cd esm-agent

# Deploy all functions
cd esm-webhook && gcloud functions deploy esm-webhook --runtime python311 --trigger-http --allow-unauthenticated --region asia-south1
cd ../esm-insights && gcloud functions deploy esm-insights --runtime python311 --trigger-http --allow-unauthenticated --region asia-south1
cd ../esm-dashboard-api && gcloud functions deploy esm-dashboard-api --runtime python311 --trigger-http --allow-unauthenticated --region asia-south1 --entry-point dashboard
```

Set environment variables:
- `MONGO_URI` — MongoDB Atlas connection string
- `GEMINI_API_KEY` — Google AI Studio API key

## What makes this an agent

ESM Agent doesn't just collect data — it reasons about it. After every form submission:

1. It checks if boredom is critically high (≥8/10)
2. If yes, it calls Gemini with the participant's full context and generates a specific follow-up question
3. It triggers a full dataset analysis and updates the insight store
4. The researcher sees both the raw data and the agent's reasoning on the dashboard

This closes the loop between data collection and research intelligence — something no existing ESM tool does automatically.

## Made by

Akanksha Bhimte — MSc Cognitive Science, IIT Gandhinagar
