# Momentra

> The AI research platform that thinks while it listens.

Momentra is the first Experience Sampling Method (ESM) platform where AI participates in the entire research lifecycle — not just analysis after the fact.
Built for the Google Cloud Rapid Agent Hackathon 2026.

## What it does

Traditional ESM studies require researchers to manually send prompts, track compliance in spreadsheets, and analyze data days after collection — missing patterns as they emerge. Momentra does all of this automatically, and more.

**Before the study:** The Study Designer Agent designs a full ESM protocol from a plain-English research question and runs a pre-study simulation — predicting compliance rates, flagging methodological risks, and estimating data patterns before a single response is collected.

**During the study:** Participants respond via a lightweight Tally form at random times. Every response lands in MongoDB Atlas instantly. When boredom spikes ≥8/10, Gemini 2.5 Flash generates a personalized follow-up question based on that participant's specific activity and context.

**After every response:** The Statistician Agent generates testable hypotheses automatically. The Data Quality Agent flags anomalies and batch submissions with a real-time quality score. Everything syncs to BigQuery via Fivetran every 6 hours.

**Always:** Researchers can open Ask Your Data and chat directly with their MongoDB database — "which activity correlates most with boredom?" gets a specific, quantitative answer from real responses.

## Architecture

### Tech stack

- **MongoDB Atlas** — flexible document store for ESM responses, agent actions, and insights; integrated via MongoDB MCP server at runtime
- **Google Cloud Agent Builder** — orchestration and reasoning layer for all 5 agents, called at runtime
- **Gemini 2.5 Flash** — adaptive questioning, hypothesis generation, pre-study simulation
- **Google Cloud Run** — serverless compute for all agent functions
- **Fivetran** — MongoDB → BigQuery sync every 6 hours
- **BigQuery** — longitudinal analysis and deeper querying
- **Tally** — participant-facing form
- **GitHub Pages** — researcher dashboard

### Five agents, one platform

| Agent | Function | Cloud Run Service |
|-------|----------|-------------------|
| Study Designer | Protocol design + pre-study simulation | esm-study-designer |
| Statistician | Live hypothesis generation | esm-statistician + esm-analyst |
| Data Quality | Anomaly detection + quality scoring | esm-data-quality |
| Engagement | Compliance monitoring + adaptive questioning | esm-webhook + esm-scheduler |
| Ask Your Data | Natural language queries over live MongoDB data | esm-insights + esm-dashboard-api |

### The agent loop

1. Participant submits Tally form
2. `esm-webhook` saves response to MongoDB Atlas, tags participant by name
3. If boredom ≥ 8, Gemini generates a context-aware follow-up — stored as an agent action in MongoDB via MCP
4. `esm-insights` triggers — Gemini analyzes the full dataset, stores insight, calls MongoDB MCP server at runtime
5. Researcher sees updated dashboard with live data, agent actions, and AI analysis
6. Fivetran syncs all collections to BigQuery every 6 hours

## Live demo

- **Platform:** https://akanksha-2002.github.io/esm-agent
- **Dashboard:** https://akanksha-2002.github.io/esm-agent/dashboard.html
- **Study Designer:** https://akanksha-2002.github.io/esm-agent/study-designer.html
- **Study form:** https://tally.so/r/Y5xD0J

## Setup

### Prerequisites

- Google Cloud project with Cloud Run enabled
- MongoDB Atlas cluster
- Gemini API key
- Fivetran account connected to MongoDB Atlas and BigQuery

### Deploy

\`\`\`bash
git clone https://github.com/akanksha-2002/esm-agent.git
cd esm-agent

cd esm-webhook && gcloud functions deploy esm-webhook \
  --gen2 --runtime=python311 --region=asia-south1 \
  --source=. --entry-point=handle_webhook \
  --trigger-http --allow-unauthenticated
\`\`\`

### Environment variables

- \`MONGO_URI\` — MongoDB Atlas connection string
- \`GEMINI_API_KEY\` — Google AI Studio API key
- \`MONGODB_API_KEY\` — MongoDB Atlas API key for MCP server

## Current study

**Boredom & Creativity** — investigating how boredom fluctuates across activity types and how focus correlates with creativity in naturalistic settings. Real participants, real data, real agent decisions — not a mock demo.

## Made by

Akanksha Bhimte — incoming MSc Cognitive Science student, IIT Gandhinagar
