# SolverAI on GCP (Open-Source LLM Only)

This guide walks through deploying SolverAI to Google Cloud while **only running open-source models**. All AI workloads stay on infrastructure you control (no per-token API fees).

## Outcome

- Cloud Run hosts the FastAPI backend (and optionally the Vite frontend).
- Cloud SQL (PostgreSQL) stores conversations, Memorystore (Redis) handles caching.
- A Compute Engine VM runs Ollama with your preferred open-source models (e.g., `llama3.1:8b`, `phi3`, `mistral`).
- Private VPC networking connects Cloud Run ↔ Cloud SQL ↔ Redis ↔ Ollama.

## Prerequisites

1. Active GCP project with billing.
2. `gcloud` CLI (latest) and Docker installed locally.
3. Project owner/Editor IAM role (or equivalent) plus Service Networking Admin for VPC resources.
4. Repo cloned locally (`solverai`).

> **Tip:** Run `gcloud components update` first to avoid version drift.

## Step 0 – Set Context

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"          # adjust if needed
export SERVICE_NAME="solverai-api"
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"
```

## Step 1 – Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  compute.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

## Step 2 – Create Artifact Registry (optional but recommended)

```bash
gcloud artifacts repositories create solverai \
  --repository-format=docker \
  --location="$REGION" \
  --description="SolverAI images"

gcloud auth configure-docker "$REGION-docker.pkg.dev"
```

## Step 3 – Provision Cloud SQL (PostgreSQL)

```bash
POSTGRES_PASSWORD=$(openssl rand -base64 32)

gcloud sql instances create solverai-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --root-password="$POSTGRES_PASSWORD"

gcloud sql databases create solverai --instance=solverai-db

gcloud sql users create solverai \
  --instance=solverai-db \
  --password="$POSTGRES_PASSWORD"
```

Store the password in Secret Manager:

```bash
echo -n "$POSTGRES_PASSWORD" | gcloud secrets create solverai-postgres --data-file=-
```

## Step 4 – Provision Memorystore (Redis)

```bash
gcloud redis instances create solverai-redis \
  --size=1 \
  --tier=basic \
  --region="$REGION" \
  --redis-version=redis_7_0
```

Note the private host/port from:

```bash
gcloud redis instances describe solverai-redis --region="$REGION"
```

## Step 5 – Create VPC Connector (Cloud Run ↔ Private Services)

```bash
gcloud compute networks vpc-access connectors create solverai-connector \
  --region="$REGION" \
  --network=default \
  --range=10.8.0.0/28
```

## Step 6 – Spin Up Ollama VM (Open-Source LLM Host)

```bash
gcloud compute instances create solverai-ollama \
  --zone="${REGION}-a" \
  --machine-type=e2-standard-4 \
  --boot-disk-size=80GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=ollama \
  --metadata-from-file startup-script=$(pwd)/deploy/gcp/ollama-startup.sh
```

What the startup script does:

- Installs Docker & Ollama.
- Starts the Ollama service.
- Pulls `llama3.1:8b` by default (edit script for another model).

After the VM is ready:

```bash
gcloud compute ssh solverai-ollama --zone="${REGION}-a"
# inside VM
ollama pull llama3.1:8b   # or another open-source model
exit
```

Grab the VM’s **internal** IP for private access:

```bash
OLLAMA_IP=$(gcloud compute instances describe solverai-ollama \
  --zone="${REGION}-a" \
  --format="value(networkInterfaces[0].networkIP)")
```

Ensure firewall rule allows Cloud Run to reach port `11434` internally (e.g., allow from VPC connector CIDR).

## Step 7 – Build and Push Backend Image

```bash
cd backend/app
gcloud builds submit \
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/solverai/backend:latest"
```

(Use `gcr.io/$PROJECT_ID/...` if skipping Artifact Registry.)

## Step 8 – Deploy Backend to Cloud Run

```bash
CONNECTION_NAME=$(gcloud sql instances describe solverai-db --format="value(connectionName)")
REDIS_HOST=$(gcloud redis instances describe solverai-redis --region="$REGION" --format="value(host)")

gcloud run deploy "$SERVICE_NAME" \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/solverai/backend:latest" \
  --vpc-connector solverai-connector \
  --add-cloudsql-instances "$CONNECTION_NAME" \
  --set-env-vars "DEBUG=False" \
  --set-env-vars "POSTGRES_HOST=/cloudsql/$CONNECTION_NAME" \
  --set-env-vars "POSTGRES_DB=solverai" \
  --set-env-vars "POSTGRES_USER=solverai" \
  --set-env-vars "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" \
  --set-env-vars "REDIS_HOST=$REDIS_HOST" \
  --set-env-vars "REDIS_PORT=6379" \
  --set-env-vars "OLLAMA_BASE_URL=http://$OLLAMA_IP:11434" \
  --set-env-vars "RAG_ENABLED=true" \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1
```

> **Security:** Replace inline passwords with Secret Manager via `--set-secrets` for production.

## Step 9 – Frontend Deployment (Optional Cloud Run)

```bash
cd frontend
npm install
VITE_API_BASE="https://$SERVICE_NAME-${REGION}.a.run.app" npm run build

gcloud builds submit --tag "$REGION-docker.pkg.dev/$PROJECT_ID/solverai/frontend:latest"

gcloud run deploy solverai-web \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/solverai/frontend:latest" \
  --allow-unauthenticated \
  --memory=512Mi
```

Point the frontend to the backend URL via `VITE_API_BASE`.

## Step 10 – Verify

```bash
curl https://$SERVICE_NAME-${REGION}.a.run.app/health

# Upload doc
curl -X POST https://$SERVICE_NAME-${REGION}.a.run.app/upload \
  -F "file=@documents/test.pdf"
```

Check Cloud Run logs if anything fails:

```bash
gcloud run services logs read "$SERVICE_NAME" --region="$REGION"
```

For Ollama status:

```bash
gcloud compute ssh solverai-ollama --zone="${REGION}-a" \
  --command="sudo systemctl status ollama -n 50"
```

## Cleanup

```bash
gcloud run services delete solverai-api --region="$REGION"
gcloud run services delete solverai-web --region="$REGION"
gcloud sql instances delete solverai-db
gcloud redis instances delete solverai-redis --region="$REGION"
gcloud compute instances delete solverai-ollama --zone="${REGION}-a"
```

## Notes

- All AI inference and embeddings stay on the Ollama VM (no OpenAI/closed APIs).
- Costs come solely from GCP infrastructure (Compute Engine, Cloud Run, Cloud SQL, Redis, Artifact Registry, storage).
- To minimize cost, shut down the Ollama VM during idle periods or switch to preemptible instances.

Need automation? Run `deploy/gcp/deploy.sh` and select the **Full deployment** option—it provisions the same architecture automatically.

