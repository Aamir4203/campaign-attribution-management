# Project Summary: Campaign Attribution Management (CAM)

## 📊 **Project Overview**
A comprehensive web application for managing campaign attribution processing requests with real-time monitoring capabilities.

## 🏗️ **Architecture**
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS
- **Backend**: Flask + Python with PostgreSQL database
- **Authentication**: Session-based security with 48-hour sessions
- **Database**: PostgreSQL with 3-table JOIN architecture

## ⚡ **Key Features**

### 🔐 **Authentication System**
- Database-driven login with session management
- Protected routes with automatic session validation
- User context integration across all forms

### 📝 **Add Request Form (7 Sections)**
1. **Client Information** - Live client dropdown with add functionality
2. **Campaign Dates** - Date validation with residual date logic
3. **File Options** - File type selection with conditional paths
4. **Report Paths** - Report and quality score path configuration
5. **Suppression List** - Multiple suppression types including Request ID
6. **Data Priority Settings** - Priority file and percentage configuration
7. **SQL Query** - Custom query input with validation

### 📊 **Request Management & Monitoring**
- Real-time request table with auto-refresh (30s intervals)
- Status tracking with color-coded badges
- Comprehensive search (Request ID, Client Name, User)
- Action buttons (Kill, ReRun, View, Download, Upload)
- Fixed headers with scrollable content
- Professional pagination system

## 🗄️ **Database Integration**
- **Tables**: `apt_custom_postback_request_details_dnd`, `apt_custom_client_info_table_dnd`, `apt_custom_postback_qa_table_dnd`
- **TRT Count**: Live `RLTP_FILE_COUNT` from qa_stats table
- **Query Structure**: 3-table JOIN matching LogStreamr architecture

## 🛡️ **Production Ready**
- Input validation and error handling
- Responsive design with professional UI
- TypeScript for type safety
- Optimized performance and clean code architecture
- Session security and route protection

## 📈 **Development Phases**
- **Phase 1**: Form Implementation ✅
- **Phase 2**: Authentication System ✅  
- **Phase 3**: Request Management ✅

## 🚀 **Technology Stack**
```
Frontend:
- React 19 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- React Hook Form + Yup validation
- React Router for navigation

Backend:
- Flask web framework
- PostgreSQL database
- Session-based authentication
- RESTful API design

Development:
- Node.js 18+
- Python 3.12+
- Git version control
```

## 📋 **API Endpoints**
- Authentication: `/api/login`, `/api/logout`, `/api/session_info`
- Application: `/health`, `/api/clients`, `/check_client`, `/add_client`, `/submit_form`
- Requests: `/api/requests`, `/api/requests/{id}/*` (details, rerun, kill)

---
**Status**: Production Ready | **License**: MIT | **Version**: 1.0.0
