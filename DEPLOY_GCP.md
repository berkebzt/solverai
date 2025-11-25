# Deploy SolverAI to Google Cloud

Quick start guide for deploying to Google Cloud Platform.

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed ([install guide](https://cloud.google.com/sdk/docs/install))
3. **Project created** in Google Cloud Console

## Quick Deploy (5 minutes)

```bash
# 1. Clone and navigate to project
cd solverai

# 2. Authenticate with Google Cloud
gcloud auth login

# 3. Run deployment script
cd deploy/gcp
chmod +x deploy.sh
./deploy.sh
```

The script will guide you through:
- Selecting deployment type (Full/Cost-effective/Minimal)
- Creating all necessary resources
- Deploying the API

## Deployment Options

### Option 1: Full Deployment (~$270-410/month)

**Includes:**
- Cloud Run (API)
- Cloud SQL (PostgreSQL)
- Memorystore (Redis)
- GPU VM (Llama 3.1)

**Best for:** Production with local LLM

```bash
# Select option 1 in the script
./deploy.sh
```

### Option 2: Cost-Effective (~$70-100/month)

**Includes:**
- Cloud Run (API)
- Cloud SQL (PostgreSQL)
- Memorystore (Redis)
- OpenAI API (for LLM)

**Best for:** Production with cloud LLM

```bash
# Select option 2 in the script
# You'll need an OpenAI API key
./deploy.sh
```

### Option 3: Minimal (~$15-30/month)

**Includes:**
- Cloud Run (API only)
- OpenAI API (for LLM)

**Best for:** Testing/Development

```bash
# Select option 3 in the script
./deploy.sh
```

## Manual Deployment

If you prefer manual control, see [deploy/gcp/README.md](deploy/gcp/README.md) for detailed step-by-step instructions.

## After Deployment

### 1. Test Your API

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe solverai-api --region=us-central1 --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Test chat endpoint
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Introduce yourself."}'
```

### 2. View API Documentation

```bash
open "$SERVICE_URL/docs"
```

### 3. Monitor Logs

```bash
# View API logs
gcloud run services logs read solverai-api --region=us-central1

# Follow logs in real-time
gcloud run services logs tail solverai-api --region=us-central1
```

## Cost Management

### Reduce Costs

1. **Use Preemptible GPU VM** (60-80% savings)
   ```bash
   gcloud compute instances create solverai-ollama --preemptible ...
   ```

2. **Auto-shutdown during off-hours**
   ```bash
   # Create shutdown schedule
   gcloud scheduler jobs create http shutdown-ollama \
       --schedule="0 22 * * *" \
       --uri="https://compute.googleapis.com/compute/v1/projects/PROJECT_ID/zones/us-central1-a/instances/solverai-ollama/stop" \
       --http-method=POST
   ```

3. **Use smaller Cloud SQL instance**
   ```bash
   --tier=db-f1-micro  # $10/month instead of $50/month
   ```

4. **Scale to zero** when not in use
   ```bash
   gcloud run services update solverai-api --min-instances=0
   ```

### Monitor Costs

```bash
# View current costs
open "https://console.cloud.google.com/billing"

# Set budget alerts
gcloud billing budgets create --display-name="SolverAI Budget" \
    --budget-amount=100 \
    --threshold-rule=percent=90
```

## CI/CD Setup

### Automatic Deployment on Git Push

1. **Connect GitHub repository**
   ```bash
   gcloud builds triggers create github \
       --repo-name=solverai \
       --repo-owner=YOUR_GITHUB_USERNAME \
       --branch-pattern="^main$" \
       --build-config=cloudbuild.yaml
   ```

2. **Push to deploy**
   ```bash
   git push origin main
   # Deployment happens automatically!
   ```

## Custom Domain

### Add Your Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service=solverai-api \
    --domain=api.yourdomain.com \
    --region=us-central1
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
gcloud run services logs read solverai-api --region=us-central1 --limit=50

# Check service status
gcloud run services describe solverai-api --region=us-central1
```

### Can't Connect to Database

```bash
# Verify Cloud SQL connection
gcloud sql instances describe solverai-db

# Test connection
gcloud sql connect solverai-db --user=solverai
```

### Ollama Not Responding

```bash
# SSH into VM
gcloud compute ssh solverai-ollama --zone=us-central1-a

# Check Ollama status
sudo systemctl status ollama

# View logs
sudo journalctl -u ollama -f

# Restart if needed
sudo systemctl restart ollama
```

### High Costs

```bash
# Check what's consuming resources
gcloud billing projects describe PROJECT_ID

# Stop GPU VM
gcloud compute instances stop solverai-ollama --zone=us-central1-a

# Scale down Cloud SQL
gcloud sql instances patch solverai-db --tier=db-f1-micro
```

## Cleanup

### Delete Everything

```bash
# Run cleanup script
./cleanup.sh

# Or manually:
gcloud run services delete solverai-api --region=us-central1 --quiet
gcloud sql instances delete solverai-db --quiet
gcloud redis instances delete solverai-redis --region=us-central1 --quiet
gcloud compute instances delete solverai-ollama --zone=us-central1-a --quiet
```

## Support

- **Documentation**: [deploy/gcp/README.md](deploy/gcp/README.md)
- **Google Cloud Console**: https://console.cloud.google.com
- **Cloud Run Docs**: https://cloud.google.com/run/docs

## Next Steps

1. ✅ Deploy to Google Cloud
2. ⬜ Add custom domain
3. ⬜ Set up monitoring alerts
4. ⬜ Configure backup strategy
5. ⬜ Add CI/CD pipeline
6. ⬜ Implement authentication
