#!/bin/bash
set -e  # Exit immediately if any command fails

# Navigate to the project root (one level up from scripts/)
cd "$(dirname "$0")/.." 

echo "🚀 Starting deployment..."

# Ensure Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

echo "🧹 Stopping and removing old containers..."
docker compose -f compose.yaml -f deploy.yaml down --remove-orphans

echo "🧱 Building new images..."
docker compose -f compose.yaml -f deploy.yaml build --no-cache

echo "⬆️ Starting new containers..."
docker compose -f compose.yaml -f deploy.yaml up -d

echo "✅ Deployment complete!"
