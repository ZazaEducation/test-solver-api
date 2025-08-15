#!/bin/bash

# AI Test Solver - Google Cloud Run Deployment Script

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
SERVICE_NAME="ai-test-solver"
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Deploying AI Test Solver to Google Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Check if logged into gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 | grep -q .; then
    echo "❌ Not logged into Google Cloud. Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    vision.googleapis.com \
    customsearch.googleapis.com \
    storage.googleapis.com

# Create storage bucket if it doesn't exist
BUCKET_NAME="$PROJECT_ID-test-files"
echo "📦 Creating storage bucket: $BUCKET_NAME"
gsutil mb gs://$BUCKET_NAME 2>/dev/null || echo "Bucket already exists"

# Set CORS configuration for the bucket
echo "🔧 Configuring bucket CORS..."
cat > bucket-cors.json << EOF
[
  {
    "origin": ["*"],
    "method": ["GET", "POST", "PUT", "DELETE"],
    "responseHeader": ["Content-Type", "Access-Control-Allow-Origin"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set bucket-cors.json gs://$BUCKET_NAME
rm bucket-cors.json

# Build and push the image
echo "🏗️ Building Docker image..."
docker build -t $IMAGE_NAME:latest .

echo "📤 Pushing image to Container Registry..."
docker push $IMAGE_NAME:latest

# Create secrets (you'll need to set these values)
echo "🔐 Creating secrets..."
# Note: Replace these with actual secret values
cat > secrets.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ai-test-solver-secrets
type: Opaque
data:
  api-secret-key: $(echo -n 'your-api-secret-key-change-this' | base64)
  supabase-url: $(echo -n 'https://your-project.supabase.co' | base64)
  supabase-key: $(echo -n 'your-supabase-anon-key' | base64)
  supabase-service-key: $(echo -n 'your-supabase-service-key' | base64)
  google-search-api-key: $(echo -n 'your-google-search-api-key' | base64)
  google-search-engine-id: $(echo -n 'your-search-engine-id' | base64)
  openai-api-key: $(echo -n 'your-openai-api-key' | base64)
EOF

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
sed "s/PROJECT_ID/$PROJECT_ID/g" cloud-run.yaml > deployment.yaml

gcloud run services replace deployment.yaml \
    --region=$REGION \
    --platform=managed

# Clean up
rm deployment.yaml secrets.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform=managed --region=$REGION --format='value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📖 API Documentation: $SERVICE_URL/docs"
echo "🏥 Health Check: $SERVICE_URL/api/v1/health"
echo ""
echo "📝 Next steps:"
echo "1. Update the secrets with your actual API keys:"
echo "   kubectl patch secret ai-test-solver-secrets -p='{\"data\":{\"openai-api-key\":\"$(echo -n YOUR_OPENAI_KEY | base64)\"}\"}}'"
echo "2. Test the API endpoints"
echo "3. Set up monitoring and alerting"
echo ""
echo "🎉 Your AI Test Solver API is now live!"