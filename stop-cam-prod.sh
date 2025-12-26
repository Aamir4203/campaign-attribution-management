#!/bin/bash
# CAM Production Stop Script for Unix

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 Stopping CAM Production Services...${NC}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$PROJECT_ROOT/pids"

# Function to stop service by PID
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/$service_name.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🔄 Stopping $service_name (PID: $pid)...${NC}"
            kill -TERM "$pid"
            sleep 3

            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}⚠️  Force stopping $service_name...${NC}"
                kill -9 "$pid"
            fi

            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name not running (PID: $pid)${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${BLUE}ℹ️  No PID file found for $service_name${NC}"
    fi
}

# Stop services
stop_service "backend"
stop_service "frontend"

# Cleanup any remaining processes
echo -e "${BLUE}🧹 Cleaning up remaining processes...${NC}"

# Kill any remaining gunicorn processes
pkill -f "gunicorn.*simple_api" 2>/dev/null || true

# Kill any remaining serve processes for CAM
pkill -f "serve.*dist" 2>/dev/null || true

# Kill processes on specific ports
for port in 8080 3000; do
    local pids=$(lsof -ti:$port 2>/dev/null || echo "")
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}🔄 Cleaning up processes on port $port...${NC}"
        echo "$pids" | xargs kill -TERM 2>/dev/null || echo "$pids" | xargs kill -9 2>/dev/null
    fi
done

echo ""
echo -e "${GREEN}🎉 CAM Production Services Stopped!${NC}"
echo ""
echo -e "${BLUE}📝 Logs preserved at:${NC}"
echo -e "  Production logs: logs/production/"
echo ""
