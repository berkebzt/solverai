# Google Cloud Platform Deployment Guide

Complete guide for deploying SolverAI to Google Cloud Platform with GPU-enabled LLM support.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌─────────────────┐              │
│  │  Cloud Run   │────────▶│  Cloud SQL      │              │
│  │  (FastAPI)   │         │  (PostgreSQL)   │              │
│  └──────┬───────┘         └─────────────────┘              │
│         │                                                    │
│         │                 ┌─────────────────┐              │
│         └────────────────▶│  Memorystore    │              │
│         │                 │  (Redis)        │              │
│         │                 └─────────────────┘              │
│         │                                                    │
│         │                 ┌─────────────────┐              │
│         └────────────────▶│  Compute Engine │              │
│                           │  (Ollama + GPU) │              │
│                           └─────────────────┘              │
│                                                               │
│  ┌──────────────────────────────────────────┐              │
│  │  Cloud Storage (Documents & Models)      │              │
│  └──────────────────────────────────────────┘              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Services Used

1. **Cloud Run** - Serverless FastAPI backend (auto-scaling)
2. **Cloud SQL** - Managed PostgreSQL database
3. **Memorystore** - Managed Redis cache
4. **Compute Engine** - GPU VM for Ollama LLM
5. **Cloud Storage** - Document and model storage
6. **VPC** - Private networking between services

## Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed
3. Docker installed locally
4. Project with required APIs enabled

## Cost Estimate (Monthly)

- **Cloud Run**: ~$10-50 (depends on usage)
- **Cloud SQL (db-f1-micro)**: ~$15
- **Memorystore (1GB)**: ~$40
- **Compute Engine (n1-standard-2 + T4 GPU)**: ~$200-300
- **Cloud Storage**: ~$5
- **Total**: ~$270-410/month

### Cost Optimization Options

1. **Use Preemptible GPU VM**: Save 60-80% on GPU costs
2. **Use OpenAI API instead**: ~$5-20/month depending on usage
3. **Use smaller Cloud SQL**: db-f1-micro for $10/month
4. **Shutdown GPU VM when not in use**: Save during idle time

## Quick Start

### 1. Set Environment Variables

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="solverai-api"
```

### 2. Run Deployment Script

```bash
cd deploy/gcp
chmod +x deploy.sh
./deploy.sh
```

### 3. Manual Deployment (Step by Step)

See detailed steps below.

## Detailed Deployment Steps

### Step 1: Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    compute.googleapis.com \
    storage.googleapis.com \
    vpcaccess.googleapis.com \
    servicenetworking.googleapis.com
```

### Step 2: Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create solverai-db \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password="CHANGE_THIS_PASSWORD"

# Create database
gcloud sql databases create solverai \
    --instance=solverai-db

# Create user
gcloud sql users create solverai \
    --instance=solverai-db \
    --password="CHANGE_THIS_PASSWORD"
```

### Step 3: Create Memorystore Redis

```bash
gcloud redis instances create solverai-redis \
    --size=1 \
    --region=$REGION \
    --redis-version=redis_7_0
```

### Step 4: Create GPU VM for Ollama

```bash
gcloud compute instances create solverai-ollama \
    --zone=us-central1-a \
    --machine-type=n1-standard-2 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --maintenance-policy=TERMINATE \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --metadata=startup-script='#!/bin/bash
        # Install NVIDIA drivers
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit nvidia-driver-535

        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh

        # Install Ollama
        curl -fsSL https://ollama.ai/install.sh | sh

        # Start Ollama
        sudo systemctl enable ollama
        sudo systemctl start ollama

        # Pull model
        ollama pull llama3.1:8b
    '
```

### Step 5: Build and Deploy API to Cloud Run

```bash
# Build image
gcloud builds submit --tag gcr.io/$PROJECT_ID/solverai-api

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/solverai-api \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --add-cloudsql-instances=solverai-db \
    --set-env-vars="POSTGRES_HOST=/cloudsql/solverai-db"
```

### Step 6: Configure Networking

Create VPC connector for private access:

```bash
gcloud compute networks vpc-access connectors create solverai-connector \
    --region=$REGION \
    --range=10.8.0.0/28
```

## Alternative: Cost-Effective Deployment

### Use OpenAI API Instead of Local LLM

```bash
# Set OpenAI API key
gcloud run services update $SERVICE_NAME \
    --set-env-vars="OPENAI_API_KEY=your-key-here" \
    --region=$REGION
```

**Cost**: ~$5-20/month instead of $200-300 for GPU VM

### Use Cloud Run for Everything

```yaml
# docker-compose.gcp.yml - Simplified
services:
  api:
    # Only deploy API to Cloud Run
    # Use Cloud SQL, Memorystore
    # Use OpenAI API for LLM
```

**Total Cost**: ~$70-100/month

## Monitoring & Logging

### View Logs

```bash
# API logs
gcloud run services logs read $SERVICE_NAME --region=$REGION

# Ollama VM logs
gcloud compute ssh solverai-ollama --zone=us-central1-a --command="journalctl -u ollama -f"
```

### Monitoring Dashboard

```bash
# Open Cloud Console
open "https://console.cloud.google.com/monitoring/dashboards"
```

## Scaling Configuration

### Auto-scaling Cloud Run

```bash
gcloud run services update $SERVICE_NAME \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=80 \
    --region=$REGION
```

### GPU VM Auto-shutdown

Create a Cloud Scheduler job to shutdown VM during off-hours:

```bash
gcloud scheduler jobs create http shutdown-ollama \
    --schedule="0 22 * * *" \
    --uri="https://compute.googleapis.com/compute/v1/projects/$PROJECT_ID/zones/us-central1-a/instances/solverai-ollama/stop" \
    --http-method=POST
```

## Security

### Secrets Management

```bash
# Store secrets in Secret Manager
echo -n "your-postgres-password" | gcloud secrets create postgres-password --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding postgres-password \
    --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Private Services

```bash
# Make API require authentication
gcloud run services update $SERVICE_NAME \
    --no-allow-unauthenticated \
    --region=$REGION
```

## Troubleshooting

### Common Issues

1. **Cloud Run can't connect to Cloud SQL**
   - Check VPC connector is configured
   - Verify Cloud SQL proxy settings

2. **Ollama VM out of memory**
   - Increase machine type to n1-standard-4 or higher
   - Use smaller model (phi3:mini)

3. **High costs**
   - Use preemptible GPU VM
   - Enable auto-shutdown
   - Use OpenAI API instead

## Cleanup

```bash
# Delete all resources
gcloud run services delete $SERVICE_NAME --region=$REGION --quiet
gcloud sql instances delete solverai-db --quiet
gcloud redis instances delete solverai-redis --region=$REGION --quiet
gcloud compute instances delete solverai-ollama --zone=us-central1-a --quiet
```

## Next Steps

1. Set up CI/CD with Cloud Build
2. Add custom domain
3. Configure CDN
4. Set up monitoring alerts
5. Implement backup strategy
