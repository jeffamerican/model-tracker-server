# Deployment Guide: Google Cloud Run

This guide walks you through deploying the Pricing Service to Google Cloud Run, a serverless platform that offers a generous free tier and automatic scaling.

## Prerequisites

1. **Google Cloud Account**: Sign up at [cloud.google.com](https://cloud.google.com)
2. **gcloud CLI**: Install from [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Install from [docs.docker.com/get-docker](https://docs.docker.com/get-docker/)
4. **GCP Project**: Create a new project or use an existing one

## Initial Setup

### 1. Install and Configure gcloud CLI

```bash
# Install gcloud CLI (if not already installed)
# macOS: brew install google-cloud-sdk
# Linux: Follow instructions at cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set your project (replace with your project ID)
gcloud config set project YOUR_PROJECT_ID

# Enable billing (required even for free tier)
# Visit: https://console.cloud.google.com/billing
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## Deployment Methods

### Method 1: Using the Deployment Script (Recommended)

The easiest way to deploy is using the provided `deploy.sh` script:

```bash
# Basic usage (uses defaults)
./deploy.sh YOUR_PROJECT_ID

# With custom service name and region
./deploy.sh YOUR_PROJECT_ID pricing-service us-central1
```

The script will:
- Build the Docker image
- Push it to Google Container Registry
- Deploy to Cloud Run with optimized settings
- Display the service URL

### Method 2: Manual Deployment

#### Step 1: Build the Docker Image

```bash
# Build locally
docker build -t gcr.io/YOUR_PROJECT_ID/pricing-service .

# Or use Cloud Build (recommended for production)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pricing-service
```

#### Step 2: Push to Container Registry

```bash
# Authenticate Docker with GCR
gcloud auth configure-docker

# Push the image
docker push gcr.io/YOUR_PROJECT_ID/pricing-service
```

#### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy pricing-service \
    --image gcr.io/YOUR_PROJECT_ID/pricing-service \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --timeout 600 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080
```

### Method 3: Using Cloud Build (CI/CD)

For automated deployments, use the `cloudbuild.yaml` configuration:

```bash
# Trigger a build
gcloud builds submit --config cloudbuild.yaml
```

This will automatically build and deploy on every push to your repository.

## Configuration Options

### Memory and CPU

- **Free Tier**: 512MB memory, 1 vCPU (default)
- **Production**: Increase if needed:
  ```bash
  --memory 1Gi --cpu 2
  ```

### Scaling

- **Min Instances**: 0 (scales to zero when idle - free tier)
- **Max Instances**: 10 (adjust based on traffic)
- **Concurrency**: 80 requests per instance (default)

### Timeout

- **Default**: 600 seconds (10 minutes) - increased for first deployment with data scraping
- Decrease after initial deployment if needed:
  ```bash
  --timeout 300
  ```

### Environment Variables

Set custom environment variables:

```bash
--set-env-vars REFRESH_INTERVAL=21600
```

**Note**: The `PORT` environment variable is automatically set by Cloud Run and should not be specified manually.

## Monitoring and Logging

### View Logs

```bash
# Real-time logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=pricing-service"

# Recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pricing-service" --limit 50
```

### View Metrics

Visit the [Cloud Run Console](https://console.cloud.google.com/run) to see:
- Request count
- Latency
- Error rate
- CPU and memory usage

### Health Checks

The service includes a health endpoint:

```bash
curl https://YOUR_SERVICE_URL/api/health
```

## Cost Estimation

### Free Tier (Always Free)

- **2 million requests/month**
- **360,000 GB-seconds** (memory × time)
- **180,000 vCPU-seconds** (CPU × time)

### Typical Usage

With default settings (512MB, 1 vCPU):
- **~1,000 requests/day**: Free
- **~10,000 requests/day**: ~$0.50/month
- **~100,000 requests/day**: ~$5/month

### Cost Optimization Tips

1. **Scale to zero**: Already configured (min-instances=0)
2. **Optimize memory**: Start with 512MB, increase only if needed
3. **Use Cloud CDN**: Cache static assets (optional)
4. **Monitor usage**: Set up billing alerts

## Custom Domain Setup (Optional)

If you want to use your `pr0ta.com` domain:

### 1. Map Domain to Cloud Run

```bash
gcloud run domain-mappings create \
    --service pricing-service \
    --domain pricing.pr0ta.com \
    --region us-central1
```

### 2. Update DNS

Add the CNAME record provided by Cloud Run to your DNS provider.

## Troubleshooting

### Service Won't Start

**Issue**: Container fails to start or listen on port

**Solutions**:
- Check logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=pricing-service" --limit 50`
- Verify Docker image builds locally: `docker build -t test . && docker run -e PORT=8080 -p 8080:8080 test`
- Check port configuration: Cloud Run sets PORT automatically - don't set it manually
- Ensure entrypoint script is executable: The Dockerfile should include `RUN chmod +x /entrypoint.sh`
- If startup is slow, increase timeout: `--timeout 600` (10 minutes) for first deployment

### Slow First Request

**Issue**: First request after idle period is slow

**Explanation**: This is expected behavior. When the service scales to zero, the first request triggers a cold start:
- Container initialization: ~5-10 seconds
- Data scraping: ~30-60 seconds (first time)
- Subsequent requests are fast

**Solutions**:
- Set `--min-instances 1` to keep one instance warm (costs ~$10/month)
- Accept cold starts (free, but slower first request)
- Use Cloud Scheduler to ping the service periodically (keeps it warm)

### Out of Memory Errors

**Issue**: Service crashes with OOM errors

**Solutions**:
- Increase memory: `--memory 1Gi` or `--memory 2Gi`
- Optimize scrapers to use less memory
- Check for memory leaks in code

### Timeout Errors

**Issue**: Requests timeout after 5 minutes

**Solutions**:
- Increase timeout: `--timeout 600` (10 minutes)
- Optimize scraper performance
- Consider async processing for long-running tasks

### Build Failures

**Issue**: Docker build fails

**Solutions**:
- Check `.dockerignore` excludes unnecessary files
- Verify all dependencies in `pyproject.toml`
- Test build locally: `docker build -t test .`

### Authentication Errors

**Issue**: "Permission denied" errors

**Solutions**:
- Verify authentication: `gcloud auth list`
- Check project permissions: `gcloud projects get-iam-policy YOUR_PROJECT_ID`
- Ensure billing is enabled

## Updating the Service

### Update Code and Redeploy

```bash
# Make your changes, then:
./deploy.sh YOUR_PROJECT_ID pricing-service us-central1
```

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service pricing-service --region us-central1

# Rollback to specific revision
gcloud run services update-traffic pricing-service \
    --to-revisions REVISION_NAME=100 \
    --region us-central1
```

## Security Considerations

1. **CORS**: Currently allows all origins (`*`). For production:
   - Update `server.py` to restrict origins
   - Use environment variables for allowed origins

2. **Authentication**: Service is publicly accessible. To restrict:
   ```bash
   --no-allow-unauthenticated
   ```
   Then use Cloud IAM or API keys for access

3. **Secrets**: For API keys or sensitive data:
   - Use Google Secret Manager
   - Set via: `--set-secrets KEY_NAME=SECRET_NAME:VERSION`

## Next Steps

1. **Set up monitoring alerts** in Cloud Console
2. **Configure custom domain** (if desired)
3. **Set up CI/CD** with Cloud Build
4. **Add Cloud Storage** for persistent data (optional)
5. **Implement rate limiting** if needed
6. **Add authentication** for production use

## Support

- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator
- **Status Dashboard**: https://status.cloud.google.com/

