#!/bin/bash

echo "🚀 Pull latest images..."
docker compose pull

echo "🔄 Restart containers..."
docker compose up -d

echo "✅ Update complete!"