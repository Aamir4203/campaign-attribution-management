#!/bin/bash
# CAM Project Deployment Script
# Starts both frontend and backend services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting CAM (Campaign Attribution Management) Deployment...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Configuration
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/CAM_Env"
BACKEND_PORT=5000
FRONTEND_PORT=5173

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}⚠️  Killing existing process on port $port (PID: $pid)${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 2
    fi
}

# Function to start backend
start_backend() {
    echo -e "${BLUE}🔧 Starting Backend Service...${NC}"

    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}❌ Virtual environment not found at $VENV_DIR${NC}"
        echo -e "${YELLOW}📝 Please run: python -m venv CAM_Env${NC}"
        exit 1
    fi

    # Kill existing backend process
    if check_port $BACKEND_PORT; then
        kill_port $BACKEND_PORT
    fi

    cd "$BACKEND_DIR"

    # Activate virtual environment and start backend
    echo -e "${BLUE}🐍 Activating Python virtual environment...${NC}"
    source "$VENV_DIR/bin/activate" || source "$VENV_DIR/Scripts/activate"

    # Check if Flask is installed
    if ! python -c "import flask" 2>/dev/null; then
        echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
        pip install -r requirements.txt
    fi

    echo -e "${GREEN}✅ Starting Flask API on port $BACKEND_PORT...${NC}"
    nohup python simple_api.py > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!

    # Wait for backend to start
    sleep 3

    if check_port $BACKEND_PORT; then
        echo -e "${GREEN}✅ Backend started successfully (PID: $BACKEND_PID)${NC}"
        echo $BACKEND_PID > ../logs/backend.pid
    else
        echo -e "${RED}❌ Backend failed to start. Check logs/backend.log${NC}"
        return 1
    fi
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}🎨 Starting Frontend Service...${NC}"

    # Kill existing frontend process
    if check_port $FRONTEND_PORT; then
        kill_port $FRONTEND_PORT
    fi

    cd "$FRONTEND_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
        npm install
    fi

    echo -e "${GREEN}✅ Starting Vite dev server on port $FRONTEND_PORT...${NC}"
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!

    # Wait for frontend to start
    sleep 5

    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}✅ Frontend started successfully (PID: $FRONTEND_PID)${NC}"
        echo $FRONTEND_PID > ../logs/frontend.pid
    else
        echo -e "${RED}❌ Frontend failed to start. Check logs/frontend.log${NC}"
        return 1
    fi
}

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Start services
echo -e "${BLUE}🏁 Starting CAM Services...${NC}"

# Start backend first
start_backend

# Start frontend
start_frontend

# Display status
echo ""
echo -e "${GREEN}🎉 CAM Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Service Status:${NC}"
echo -e "  🔧 Backend API:  ${GREEN}http://localhost:$BACKEND_PORT${NC}"
echo -e "  🎨 Frontend UI:  ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo ""
echo -e "${BLUE}📊 Process IDs:${NC}"
echo -e "  Backend PID:  $(cat logs/backend.pid 2>/dev/null || echo 'Not found')"
echo -e "  Frontend PID: $(cat logs/frontend.pid 2>/dev/null || echo 'Not found')"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo -e "  Backend:  ${YELLOW}tail -f logs/backend.log${NC}"
echo -e "  Frontend: ${YELLOW}tail -f logs/frontend.log${NC}"
echo ""
echo -e "${BLUE}🛑 To stop services:${NC}"
echo -e "  ${YELLOW}./stop-cam.sh${NC}"
echo ""
echo -e "${GREEN}✨ Ready for testing!${NC}"
