# CAM Deployment Guide 🚀

## Single-Command Deployment

This guide provides **one-click deployment** for the CAM (Campaign Attribution Management) project, supporting both **development** and **production** environments.

---

## 📋 Quick Start

### **Windows Development:**
```bash
# Start both frontend and backend
./start-cam.bat

# Stop all services  
./stop-cam.bat
```

### **Unix Development:**
```bash
# Make scripts executable (first time only)
chmod +x start-cam.sh stop-cam.sh

# Start both frontend and backend
./start-cam.sh

# Stop all services
./stop-cam.sh
```

### **Unix Production:**
```bash
# Make scripts executable (first time only)  
chmod +x start-cam-prod.sh stop-cam-prod.sh

# Deploy to production
./start-cam-prod.sh

# Stop production services
./stop-cam-prod.sh
```

---

## 🔧 Prerequisites

### **Development Environment:**
- **Python 3.8+** with virtual environment
- **Node.js 16+** with npm
- **Git** (for cloning)

### **Production Environment (Unix):**
- **Python 3.8+** with virtual environment
- **Node.js 16+** with npm  
- **Gunicorn** (auto-installed)
- **serve** package (auto-installed)

---

## 📁 Project Structure
```
Campaign-Attribution-Management/
├── 🚀 start-cam.sh          # Unix development startup
├── 🚀 start-cam.bat         # Windows development startup  
├── 🚀 start-cam-prod.sh     # Unix production deployment
├── 🛑 stop-cam.sh           # Unix development stop
├── 🛑 stop-cam.bat          # Windows development stop
├── 🛑 stop-cam-prod.sh      # Unix production stop
├── 📁 frontend/             # React + Vite frontend
├── 📁 backend/              # Flask API backend
├── 📁 CAM_Env/              # Python virtual environment
└── 📁 logs/                 # Application logs
```

---

## 🔌 Default Ports

| Environment | Frontend | Backend |
|------------|----------|---------|
| **Development** | 5173 | 5000 |
| **Production** | 3000 | 8080 |

---

## 📋 Deployment Steps

### **First Time Setup:**

1. **Clone the project:**
   ```bash
   git clone <repository-url>
   cd Campaign-Attribution-Management
   ```

2. **Create Python virtual environment:**
   ```bash
   python -m venv CAM_Env
   ```

3. **Install Python dependencies:**
   ```bash
   # Windows
   CAM_Env\Scripts\activate
   pip install -r backend/requirements.txt

   # Unix  
   source CAM_Env/bin/activate
   pip install -r backend/requirements.txt
   ```

4. **Install Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### **Daily Usage:**

**Development (Windows):**
```bash
# Start everything
./start-cam.bat

# Access application
# Frontend: http://localhost:5173
# Backend:  http://localhost:5000

# Stop everything
./stop-cam.bat
```

**Development (Unix):**
```bash
# Start everything
./start-cam.sh

# Stop everything  
./stop-cam.sh
```

**Production (Unix):**
```bash
# Deploy to production
./start-cam-prod.sh

# Access application
# Frontend: http://your-server:3000  
# Backend:  http://your-server:8080

# Stop production
./stop-cam-prod.sh
```

---

## 🔧 Configuration

### **Unix Production Paths:**
Edit `start-cam-prod.sh` to update paths for your environment:
```bash
# Update this path in start-cam-prod.sh
PROD_BASE_PATH="/u1/techteam/CAM"  # Change to your actual path
```

### **Port Configuration:**
Edit the scripts to change default ports:
```bash
# In start-cam.sh (development)
BACKEND_PORT=5000
FRONTEND_PORT=5173

# In start-cam-prod.sh (production)  
BACKEND_PORT=8080
FRONTEND_PORT=3000
```

---

## 📊 Monitoring

### **View Logs:**
```bash
# Development logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Production logs (Unix)
tail -f logs/production/gunicorn_*.log
tail -f logs/production/frontend.log
```

### **Check Service Status:**
```bash
# Check if ports are in use
netstat -tuln | grep :5000  # Backend
netstat -tuln | grep :5173  # Frontend (dev)
netstat -tuln | grep :3000  # Frontend (prod)
netstat -tuln | grep :8080  # Backend (prod)
```

### **Process Management:**
```bash
# View running processes
ps aux | grep python    # Backend processes
ps aux | grep node      # Frontend processes
ps aux | grep gunicorn  # Production backend
```

---

## 🚨 Troubleshooting

### **Port Already in Use:**
```bash
# Kill process on specific port (Unix)
lsof -ti:5000 | xargs kill -9

# Kill process on specific port (Windows)
netstat -ano | findstr :5000
taskkill /PID <process_id> /F
```

### **Virtual Environment Issues:**
```bash
# Recreate virtual environment
rm -rf CAM_Env
python -m venv CAM_Env
source CAM_Env/bin/activate  # Unix
# or CAM_Env\Scripts\activate  # Windows
pip install -r backend/requirements.txt
```

### **Node Modules Issues:**
```bash
# Clean install
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### **Permission Issues (Unix):**
```bash
# Make scripts executable
chmod +x *.sh

# Fix file permissions
chown -R $USER:$USER .
```

---

## 🔄 Updates & Maintenance

### **Update Dependencies:**
```bash
# Python dependencies
source CAM_Env/bin/activate
pip install -r backend/requirements.txt --upgrade

# Node.js dependencies  
cd frontend
npm update
```

### **Database Updates:**
The deployment scripts automatically use the configuration from:
- `backend/config/app.yaml` - Main application config
- `SCRIPTS/config.properties` - Legacy script config

---

## 🌟 Features

✅ **Single-command deployment**  
✅ **Automatic dependency installation**  
✅ **Port conflict resolution**  
✅ **Comprehensive logging**  
✅ **Graceful service shutdown**  
✅ **Development & Production modes**  
✅ **Cross-platform support (Windows/Unix)**  
✅ **Process monitoring & management**  

---

## 📞 Support

If you encounter issues:

1. **Check logs:** `logs/backend.log` and `logs/frontend.log`
2. **Verify ports:** Ensure no conflicts with other services
3. **Check permissions:** Make sure scripts are executable (Unix)
4. **Environment:** Verify Python and Node.js versions

---

**🎉 Ready to deploy! Choose your platform and run the appropriate script.** 🚀
