#!/bin/bash
# CAM Project Stop Script
# Stops both frontend and backend services gracefully

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping CAM Services...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Configuration
BACKEND_PORT=5000
FRONTEND_PORT=5173

# Function to kill process by PID file
kill_by_pid_file() {
    local pid_file=$1
    local service_name=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🔄 Stopping $service_name (PID: $pid)...${NC}"
            kill -TERM "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            sleep 2

            # Verify process is stopped
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✅ $service_name stopped successfully${NC}"
            else
                echo -e "${RED}❌ Failed to stop $service_name${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  $service_name process not running (PID: $pid)${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local service_name=$2

    local pids=$(lsof -ti:$port 2>/dev/null || echo "")
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}🔄 Stopping $service_name on port $port...${NC}"
        echo "$pids" | xargs kill -TERM 2>/dev/null || echo "$pids" | xargs kill -9 2>/dev/null
        sleep 2
        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${BLUE}ℹ️  No process running on port $port ($service_name)${NC}"
    fi
}

# Stop services using PID files first
if [ -d "$PROJECT_ROOT/logs" ]; then
    kill_by_pid_file "$PROJECT_ROOT/logs/backend.pid" "Backend"
    kill_by_pid_file "$PROJECT_ROOT/logs/frontend.pid" "Frontend"
fi

# Fallback: Stop by port
kill_port $BACKEND_PORT "Backend"
kill_port $FRONTEND_PORT "Frontend"

# Clean up any remaining Node.js processes (Vite)
echo -e "${BLUE}🧹 Cleaning up Node.js processes...${NC}"
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# Clean up Python processes (Flask)
echo -e "${BLUE}🧹 Cleaning up Python processes...${NC}"
pkill -f "simple_api.py" 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 CAM Services Stopped Successfully!${NC}"
echo ""
echo -e "${BLUE}📝 Logs preserved at:${NC}"
echo -e "  Backend:  logs/backend.log"
echo -e "  Frontend: logs/frontend.log"
echo ""
