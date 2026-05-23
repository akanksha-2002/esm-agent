gcloud functions deploy esm-insights-v2 \
  --gen2 \
  --runtime python311 \
  --region asia-south1 \
  --source . \
  --entry-point generate_insights \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars MONGO_URI="mongodb+srv://esm-admin:Payment4%2Bcluster@esm-agent.l34vzte.mongodb.net/esm_agent?appName=esm-agent",GEMINI_API_KEY="AIzaSyDliGmeVlxmVaozKWWcPlBqgoB3defsC8I"