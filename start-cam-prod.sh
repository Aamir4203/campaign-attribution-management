#!/bin/bash
# CAM Production Deployment Script for Unix
# Optimized for production environment paths like /u1/techteam/...

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 CAM Production Deployment Starting...${NC}"

# Production Configuration - Update these paths for your Unix environment
PROD_BASE_PATH="/u1/techteam/CAM"  # Update this to your actual Unix path
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_ROOT/CAM_Env"

# Production Ports (different from dev to avoid conflicts)
BACKEND_PORT=8080
FRONTEND_PORT=3000

# Production specific settings
FLASK_ENV="production"
NODE_ENV="production"
LOG_DIR="$PROJECT_ROOT/logs/production"
PID_DIR="$PROJECT_ROOT/pids"

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR"

echo -e "${BLUE}📋 Production Configuration:${NC}"
echo -e "  Project Root: $PROJECT_ROOT"
echo -e "  Backend Port: $BACKEND_PORT"
echo -e "  Frontend Port: $FRONTEND_PORT"
echo -e "  Logs: $LOG_DIR"
echo ""

# Function to check if port is available
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to start backend in production mode
start_backend_prod() {
    echo -e "${BLUE}🔧 Starting Backend in Production Mode...${NC}"

    cd "$BACKEND_DIR"

    # Activate virtual environment
    source "$VENV_DIR/bin/activate"

    # Set production environment variables
    export FLASK_ENV=production
    export FLASK_DEBUG=0
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

    # Install/update dependencies if needed
    pip install -q -r requirements.txt

    # Start backend with gunicorn for production
    if command -v gunicorn >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Starting with Gunicorn (Production WSGI)...${NC}"
        nohup gunicorn -w 4 -b 0.0.0.0:$BACKEND_PORT simple_api:app \
            --access-logfile "$LOG_DIR/gunicorn_access.log" \
            --error-logfile "$LOG_DIR/gunicorn_error.log" \
            --daemon \
            --pid "$PID_DIR/backend.pid"
    else
        echo -e "${YELLOW}⚠️  Gunicorn not found, installing...${NC}"
        pip install gunicorn
        nohup gunicorn -w 4 -b 0.0.0.0:$BACKEND_PORT simple_api:app \
            --access-logfile "$LOG_DIR/gunicorn_access.log" \
            --error-logfile "$LOG_DIR/gunicorn_error.log" \
            --daemon \
            --pid "$PID_DIR/backend.pid"
    fi

    sleep 3

    if check_port $BACKEND_PORT; then
        echo -e "${GREEN}✅ Production Backend started on port $BACKEND_PORT${NC}"
    else
        echo -e "${RED}❌ Backend failed to start${NC}"
        return 1
    fi
}

# Function to build and serve frontend in production
start_frontend_prod() {
    echo -e "${BLUE}🎨 Building Frontend for Production...${NC}"

    cd "$FRONTEND_DIR"

    # Set production environment
    export NODE_ENV=production

    # Install dependencies
    npm ci --only=production

    # Build frontend for production
    echo -e "${BLUE}🏗️  Building optimized frontend bundle...${NC}"
    npm run build

    # Serve built frontend with serve package
    if ! command -v serve >/dev/null 2>&1; then
        echo -e "${YELLOW}📦 Installing serve package...${NC}"
        npm install -g serve
    fi

    echo -e "${GREEN}✅ Starting frontend server on port $FRONTEND_PORT...${NC}"
    nohup serve -s dist -l $FRONTEND_PORT > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"

    sleep 3

    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}✅ Production Frontend started on port $FRONTEND_PORT${NC}"
    else
        echo -e "${RED}❌ Frontend failed to start${NC}"
        return 1
    fi
}

# Main deployment
echo -e "${BLUE}🚀 Starting Production Services...${NC}"

# Stop any existing services
if [ -f "$PID_DIR/backend.pid" ]; then
    kill $(cat "$PID_DIR/backend.pid") 2>/dev/null || true
fi
if [ -f "$PID_DIR/frontend.pid" ]; then
    kill $(cat "$PID_DIR/frontend.pid") 2>/dev/null || true
fi

# Start services
start_backend_prod
start_frontend_prod

# Display final status
echo ""
echo -e "${GREEN}🎉 CAM Production Deployment Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Production Services:${NC}"
echo -e "  🔧 Backend API:  ${GREEN}http://$(hostname):$BACKEND_PORT${NC}"
echo -e "  🎨 Frontend UI:  ${GREEN}http://$(hostname):$FRONTEND_PORT${NC}"
echo ""
echo -e "${BLUE}📊 Process Management:${NC}"
echo -e "  Backend PID:  $(cat $PID_DIR/backend.pid 2>/dev/null || echo 'Not found')"
echo -e "  Frontend PID: $(cat $PID_DIR/frontend.pid 2>/dev/null || echo 'Not found')"
echo ""
echo -e "${BLUE}📝 Production Logs:${NC}"
echo -e "  Backend:  ${YELLOW}tail -f $LOG_DIR/gunicorn_*.log${NC}"
echo -e "  Frontend: ${YELLOW}tail -f $LOG_DIR/frontend.log${NC}"
echo ""
echo -e "${BLUE}🛑 To stop production services:${NC}"
echo -e "  ${YELLOW}./stop-cam-prod.sh${NC}"
echo ""
echo -e "${GREEN}✨ Production CAM is now live!${NC}"
