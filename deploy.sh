#!/bin/bash
gcloud run deploy papersage-api \
  --image us-central1-docker.pkg.dev/papersage/papersage/api:v2.5 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest" \
  --set-secrets="SUPABASE_URL=SUPABASE_URL:latest" \
  --set-secrets="SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:1" \
  --set-secrets="FRONTEND_URL=FRONTEND_URL:latest" \
  --set-secrets="SENTRY_DSN=SENTRY_DSN:latest"
