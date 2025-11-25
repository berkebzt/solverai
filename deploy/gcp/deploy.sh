#!/bin/bash

set -e

echo "🚀 SolverAI Google Cloud Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if required tools are installed
command -v gcloud >/dev/null 2>&1 || { echo -e "${RED}❌ gcloud CLI is required but not installed. Visit: https://cloud.google.com/sdk/docs/install${NC}" >&2; exit 1; }

# Get project configuration
echo "📋 Configuration"
echo "================"

read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter region (default: us-central1): " REGION
REGION=${REGION:-us-central1}
SERVICE_NAME="solverai-api"

echo ""
echo -e "${GREEN}Project ID: $PROJECT_ID${NC}"
echo -e "${GREEN}Region: $REGION${NC}"
echo -e "${GREEN}Service Name: $SERVICE_NAME${NC}"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Ask deployment type
echo "🎯 Deployment Options"
echo "===================="
echo "1) Full deployment (Cloud Run + Cloud SQL + Redis + GPU VM for Ollama) - ~\$270-410/month"
echo "2) Cost-effective (Cloud Run + Cloud SQL + Redis + OpenAI API) - ~\$70-100/month"
echo "3) Minimal (Cloud Run + OpenAI API only) - ~\$15-30/month"
echo ""
read -p "Select deployment type (1-3): " DEPLOY_TYPE

echo ""
echo "🔧 Step 1: Enabling Required APIs"
echo "=================================="

gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    compute.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"

# Generate secure passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
echo ""
echo -e "${YELLOW}📝 Generated secure PostgreSQL password (save this!)${NC}"
echo -e "${YELLOW}$POSTGRES_PASSWORD${NC}"
echo ""

if [ "$DEPLOY_TYPE" = "1" ] || [ "$DEPLOY_TYPE" = "2" ]; then
    echo "🗄️  Step 2: Creating Cloud SQL Instance"
    echo "======================================="

    gcloud sql instances create solverai-db \
        --database-version=POSTGRES_16 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password="$POSTGRES_PASSWORD" || echo "Database instance may already exist"

    gcloud sql databases create solverai \
        --instance=solverai-db || echo "Database may already exist"

    gcloud sql users create solverai \
        --instance=solverai-db \
        --password="$POSTGRES_PASSWORD" || echo "User may already exist"

    echo -e "${GREEN}✓ Cloud SQL created${NC}"
fi

if [ "$DEPLOY_TYPE" = "1" ] || [ "$DEPLOY_TYPE" = "2" ]; then
    echo ""
    echo "🔴 Step 3: Creating Memorystore Redis"
    echo "====================================="

    gcloud redis instances create solverai-redis \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_7_0 || echo "Redis instance may already exist"

    echo -e "${GREEN}✓ Memorystore Redis created${NC}"
fi

if [ "$DEPLOY_TYPE" = "1" ]; then
    echo ""
    echo "🖥️  Step 4: Creating GPU VM for Ollama"
    echo "======================================"
    echo -e "${YELLOW}This will take 5-10 minutes...${NC}"

    gcloud compute instances create solverai-ollama \
        --zone=us-central1-a \
        --machine-type=n1-standard-2 \
        --accelerator=type=nvidia-tesla-t4,count=1 \
        --maintenance-policy=TERMINATE \
        --image-family=ubuntu-2204-lts \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size=50GB \
        --metadata-from-file=startup-script=./ollama-startup.sh || echo "VM may already exist"

    echo -e "${GREEN}✓ GPU VM created${NC}"
    echo -e "${YELLOW}⏳ Ollama installation will complete in ~10 minutes${NC}"
fi

if [ "$DEPLOY_TYPE" = "2" ] || [ "$DEPLOY_TYPE" = "3" ]; then
    echo ""
    echo "🔑 OpenAI API Key Required"
    echo "=========================="
    read -p "Enter your OpenAI API key: " OPENAI_KEY

    # Store in Secret Manager
    echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key \
        --data-file=- \
        --replication-policy="automatic" || \
    echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key \
        --data-file=-
fi

echo ""
echo "🐳 Step 5: Building Container Image"
echo "===================================="

cd ../..
gcloud builds submit --tag gcr.io/$PROJECT_ID/solverai-api

echo -e "${GREEN}✓ Container image built${NC}"

echo ""
echo "☁️  Step 6: Deploying to Cloud Run"
echo "==================================="

# Build env vars based on deployment type
ENV_VARS="DEBUG=False"

if [ "$DEPLOY_TYPE" = "1" ] || [ "$DEPLOY_TYPE" = "2" ]; then
    CONNECTION_NAME=$(gcloud sql instances describe solverai-db --format="value(connectionName)")
    REDIS_HOST=$(gcloud redis instances describe solverai-redis --region=$REGION --format="value(host)")

    ENV_VARS="$ENV_VARS,POSTGRES_HOST=/cloudsql/$CONNECTION_NAME"
    ENV_VARS="$ENV_VARS,POSTGRES_USER=solverai"
    ENV_VARS="$ENV_VARS,POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    ENV_VARS="$ENV_VARS,POSTGRES_DB=solverai"
    ENV_VARS="$ENV_VARS,REDIS_HOST=$REDIS_HOST"
fi

if [ "$DEPLOY_TYPE" = "1" ]; then
    OLLAMA_IP=$(gcloud compute instances describe solverai-ollama --zone=us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
    ENV_VARS="$ENV_VARS,OLLAMA_BASE_URL=http://$OLLAMA_IP:11434"
    ENV_VARS="$ENV_VARS,OLLAMA_MODEL=llama3.1:8b"
fi

if [ "$DEPLOY_TYPE" = "2" ] || [ "$DEPLOY_TYPE" = "3" ]; then
    ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_KEY"
fi

# Deploy to Cloud Run
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/solverai-api \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=10 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars=\"$ENV_VARS\""

if [ "$DEPLOY_TYPE" = "1" ] || [ "$DEPLOY_TYPE" = "2" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --add-cloudsql-instances=$CONNECTION_NAME"
fi

eval $DEPLOY_CMD

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "===================="
echo ""
echo -e "${GREEN}🌐 API URL: $SERVICE_URL${NC}"
echo -e "${GREEN}📚 API Docs: $SERVICE_URL/docs${NC}"
echo ""
echo "🧪 Test your deployment:"
echo "curl $SERVICE_URL/health"
echo ""

if [ "$DEPLOY_TYPE" = "1" ]; then
    echo -e "${YELLOW}⚠️  Note: Ollama VM is still installing. Wait 10 minutes before testing LLM features.${NC}"
    echo "Check status: gcloud compute ssh solverai-ollama --zone=us-central1-a --command='systemctl status ollama'"
fi

echo ""
echo "💰 Estimated Monthly Cost:"
case $DEPLOY_TYPE in
    1) echo "  ~\$270-410 (Full deployment with GPU)" ;;
    2) echo "  ~\$70-100 (Cloud SQL + Redis + OpenAI)" ;;
    3) echo "  ~\$15-30 (Minimal with OpenAI)" ;;
esac

echo ""
echo "📖 For more information, see: deploy/gcp/README.md"
