#!/bin/bash

# Visual styling
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹  Cleaning up previous state...${NC}"
docker compose down --remove-orphans

echo -e "${BLUE}🏗️   Building Core Services (Python, Nginx, Frontend)...${NC}"
docker compose build backend frontend loadbalancer

echo -e "${BLUE}🏗️   Building Node.js Image (for Heterogeneity Demo)...${NC}"
# We must explicitly build this because of the 'donotstart' profile
docker compose build backend_node

echo -e "${BLUE}🚀  Launching System...${NC}"
docker compose up -d

echo -e "${BLUE}🔓  Configuring Control Plane Permissions...${NC}"
# Allows the Frontend container to talk to the Docker Engine
sudo chmod 666 /var/run/docker.sock

echo -e "\n${GREEN}✅  SYSTEM READY!${NC}"
echo -e "    Access the Dashboard here: http://192.168.1.62:9000"
echo -e "    (If using VS Code Ports, click the globe icon for port 9000)"