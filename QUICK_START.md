# Quick Start Guide - Campaign Attribution Management

## 🚀 **Getting Started**

### **Prerequisites**
- **Python 3.12+** with pip
- **Node.js 18+** with npm
- **PostgreSQL** database access

### **Installation**

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/campaign-attribution-management.git
cd campaign-attribution-management
```

2. **Set up Python environment**
```bash
# Create virtual environment
python -m venv CAM_Env

# Activate environment (Windows)
.\CAM_Env\Scripts\Activate.ps1

# Install dependencies
cd backend
pip install -r requirements.txt
```

3. **Set up Frontend**
```bash
cd ../frontend
npm install
```

4. **Database Configuration**
- Update database connection in `backend/config/config.py`
- Ensure PostgreSQL tables exist:
  - `apt_custom_postback_request_details_dnd`
  - `apt_custom_client_info_table_dnd`
  - `apt_custom_postback_qa_table_dnd`
  - `apt_custom_apt_tool_user_details_dnd`

### **Running the Application**

**Terminal 1 - Backend:**
```bash
cd backend
.\CAM_Env\Scripts\Activate.ps1  # (Windows)
python simple_api.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### **Access the Application**
- **Frontend**: http://localhost:3009
- **Backend API**: http://localhost:5000
- **Health Check**: http://localhost:5000/health

### **Default Login**
```
Username: akhan
Password: akhan$1209
```

## 📁 **Project Structure**
```
campaign-attribution-management/
├── backend/           # Flask API server
├── frontend/          # React TypeScript app
├── shared/            # Shared configuration
├── CAM_Env/          # Python virtual environment
├── .gitignore        # Git ignore rules
└── README.md         # Complete documentation
```

## 🔧 **Key Features**
- **7-Section Request Form** with live validation
- **Real-time Request Monitoring** with auto-refresh
- **Session-based Authentication** with protected routes
- **PostgreSQL Integration** with 3-table JOIN queries
- **Professional UI** with responsive design

## 🛠️ **Development**
- Frontend runs on port 3009 (Vite dev server)
- Backend runs on port 5000 (Flask development server)
- Hot reload enabled for both frontend and backend
- TypeScript compilation with error checking

## 📚 **Documentation**
- Full documentation in `README.md`
- API endpoints and database schema included
- Phase-by-phase development history documented

---
**Need Help?** Check the main README.md for detailed setup and configuration instructions.
