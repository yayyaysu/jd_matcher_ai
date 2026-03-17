Write-Host "🚀 Pull latest images..."
docker compose pull

Write-Host "🔄 Restart containers..."
docker compose up -d

Write-Host "✅ Update complete!"