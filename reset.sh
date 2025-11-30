#!/bin/bash

echo "🛑  Stopping main services..."
docker compose down

echo "👻  Hunting down auto-scaled nodes..."
# Finds any container starting with "backend-node-" or "backend-python-" and kills it
docker ps -a --filter "name=backend-node-" -q | xargs -r docker rm -f
docker ps -a --filter "name=backend-python-" -q | xargs -r docker rm -f
docker ps -a --filter "name=backend-auto-" -q | xargs -r docker rm -f

echo "🧹  Pruning networks..."
docker network prune -f

echo "✨  Environment is clean."