#!/bin/bash

set -e  # Exit on any error

# Configuration
REPO_URL="https://github.com/elastic/mcp-server-elasticsearch.git"
LOCAL_DIR="mcp-server-elasticsearch"
IMAGE_NAME="elastic-mcp-server"
IMAGE_TAG="latest"
ECR_REPO_NAME="elastic-mcp-server"
AWS_REGION="us-west-2"  # Change this to your preferred region

echo "🚀 Starting Elastic MCP Server deployment process..."

# Step 1: Download the MCP server git repo
echo "📥 Step 1: Downloading MCP server repository..."
if [ -d "$LOCAL_DIR" ]; then
    echo "Directory $LOCAL_DIR already exists. Removing it..."
    rm -rf "$LOCAL_DIR"
fi

git clone "$REPO_URL" "$LOCAL_DIR"
cd "$LOCAL_DIR"

echo "✅ Repository downloaded successfully"

# Step 2: Build Docker container using Dockerfile-8000
echo "🐳 Step 2: Building Docker container..."
if [ ! -f "Dockerfile-8000" ]; then
    echo "❌ Error: Dockerfile-8000 not found in the repository"
    exit 1
fi

docker build -f Dockerfile-8000 -t "${IMAGE_NAME}:${IMAGE_TAG}" .
echo "✅ Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"

# Step 3: Create ECR repository
echo "☁️ Step 3: Creating ECR repository..."

# Check if repository already exists
if aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "📦 ECR repository '$ECR_REPO_NAME' already exists"
else
    echo "📦 Creating ECR repository '$ECR_REPO_NAME'..."
    aws ecr create-repository \
        --repository-name "$ECR_REPO_NAME" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    echo "✅ ECR repository created successfully"
fi

# Step 4: Upload container to ECR
echo "⬆️ Step 4: Uploading container to ECR..."

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "🏷️ Tagging image for ECR..."
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"

echo "📤 Pushing image to ECR..."
docker push "${ECR_URI}:${IMAGE_TAG}"

echo "✅ Container uploaded successfully to ECR!"
echo ""
echo "🎉 Deployment completed successfully!"
echo "📍 ECR Repository URI: ${ECR_URI}"
echo "🏷️ Image Tag: ${IMAGE_TAG}"
echo ""
echo "To pull this image later, use:"
echo "docker pull ${ECR_URI}:${IMAGE_TAG}"
