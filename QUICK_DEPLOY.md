# 🚀 CAM Quick Deployment Reference

## One-Command Deployment 

### **Current Environment (Windows Development):**
```bash
# START CAM (Frontend + Backend)
./start-cam.bat

# STOP CAM  
./stop-cam.bat
```

### **Unix Production Deployment:**
```bash
# First time setup
chmod +x *.sh

# START CAM PRODUCTION
./start-cam-prod.sh

# STOP CAM PRODUCTION  
./stop-cam-prod.sh
```

---

## 🔌 Access URLs

| Environment | Frontend | Backend | 
|------------|----------|---------|
| **Development** | http://localhost:5173 | http://localhost:5000 |
| **Production** | http://your-server:3000 | http://your-server:8080 |

---

## 📁 What Each Script Does

| Script | Purpose | Environment |
|--------|---------|-------------|
| `start-cam.bat` | Start dev services (Windows) | Development |
| `start-cam.sh` | Start dev services (Unix) | Development |  
| `start-cam-prod.sh` | Deploy to production (Unix) | Production |
| `stop-cam.bat` | Stop dev services (Windows) | Development |
| `stop-cam.sh` | Stop dev services (Unix) | Development |
| `stop-cam-prod.sh` | Stop production services (Unix) | Production |

---

## 🔧 Features

✅ **Automatic dependency installation**  
✅ **Port conflict resolution**  
✅ **Virtual environment activation**  
✅ **Process management**  
✅ **Comprehensive logging**  
✅ **Graceful shutdown**

---

## 📊 Quick Troubleshooting

**Port in use?**
- Scripts automatically kill conflicting processes

**Missing dependencies?**  
- Scripts auto-install Python/Node packages

**Permission denied?** (Unix)
- Run: `chmod +x *.sh`

**View logs:**
- Development: `logs/backend.log`, `logs/frontend.log`
- Production: `logs/production/`

---

**🎯 Just run the script for your environment and you're ready to go!** 🚀
