#!/bin/bash

set -e

echo "🧹 SolverAI Google Cloud Cleanup Script"
echo "======================================="
echo ""
echo "⚠️  WARNING: This will DELETE all SolverAI resources from Google Cloud!"
echo ""

read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

read -p "Enter your GCP Project ID: " PROJECT_ID
REGION="us-central1"

gcloud config set project $PROJECT_ID

echo ""
echo "Deleting resources..."
echo ""

# Delete Cloud Run service
echo "🗑️  Deleting Cloud Run service..."
gcloud run services delete solverai-api --region=$REGION --quiet || echo "Service not found"

# Delete GPU VM
echo "🗑️  Deleting Ollama GPU VM..."
gcloud compute instances delete solverai-ollama --zone=us-central1-a --quiet || echo "VM not found"

# Delete Redis
echo "🗑️  Deleting Memorystore Redis..."
gcloud redis instances delete solverai-redis --region=$REGION --quiet || echo "Redis not found"

# Delete Cloud SQL (with backups)
echo "🗑️  Deleting Cloud SQL instance..."
read -p "Delete database backups too? (yes/no): " DELETE_BACKUPS
if [ "$DELETE_BACKUPS" = "yes" ]; then
    gcloud sql instances delete solverai-db --quiet || echo "Database not found"
else
    gcloud sql instances delete solverai-db --no-backup --quiet || echo "Database not found"
fi

# Delete container images
echo "🗑️  Deleting container images..."
gcloud container images delete gcr.io/$PROJECT_ID/solverai-api --quiet || echo "Images not found"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Note: Some resources (like networks) may still exist if used by other services."
