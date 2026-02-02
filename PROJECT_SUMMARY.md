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

### ❄️ **Snowflake Dual Upload System**
- **Dual Delivery**: Upload to both Production and Audit (LPT) Snowflake accounts
- **Configurable Toggle**: Always-visible toggle in upload modal (ON/OFF per request)
- **Independent Uploads**: Production and Audit run in parallel threads
- **Selective Re-upload**: Re-upload only failed delivery (Production/Audit/Both)
- **Progress Tracking**: Separate progress bars for each upload with real-time status
- **Smart State Management**: Each upload maintains independent status (success/failure)
- **Default Configuration**: Set default toggle state in `app.yaml` (`dual_sf_upload: true/false`)
- **Request Status Updates**: Success/failure messages written to `request_desc` field
  - Production: `Production: X,XXX rows → TABLE_NAME`
  - Audit: `| Audit: N files, X,XXX rows`
  - Failures: Detailed error messages appended

### 🔧 **Snowflake Configuration**
- **Environment-Based Credentials**: All credentials in `.env` file
- **Production Account**: `SF_*` prefix (zeta_hub_reader.us-east-1)
- **Audit Account**: `SF_AUDIT_*` prefix (zetaglobal.us-east-1)
- **Private Key Authentication**: Separate keys for each account
- **Audit Schema**: `GREEN.INFS_LPT` (LPT account)
- **FILE_NAME Tracking**: Source PostgreSQL table name stored in audit records
- **Fixed Header Format**: 11 columns including FILE_NAME for data lineage

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
- **Phase 4**: Snowflake Dual Upload System ✅
- **Phase 5**: Audit Delivery & Tracking ✅

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
- **Authentication**: `/api/login`, `/api/logout`, `/api/session_info`
- **Application**: `/health`, `/api/clients`, `/check_client`, `/add_client`, `/submit_form`
- **Requests**: `/api/requests`, `/api/requests/{id}/*` (details, rerun, kill)
- **Snowflake**: `/api/snowflake/upload-dual/{id}`, `/api/snowflake/progress/{task_id}`
- **Features**: `/api/features` (feature flags configuration)
- **Utilities**: `/api/tables/{table_name}/columns`

---

## 🆕 **Recent Feature Additions**

### Dual Snowflake Upload System (Phase 4)
**Features:**
- Toggle control for enabling/disabling dual upload per request
- Parallel uploads to Production and Audit Snowflake accounts
- Independent status tracking and error handling
- Selective re-upload capabilities (Production only, Audit only, or Both)
- Real-time progress monitoring with separate progress bars

**Configuration:**
```yaml
# shared/config/app.yaml
features:
  dual_sf_upload: false  # Default: OFF (production only)
```

**Documentation:**
- `DUAL_UPLOAD_FIX_SUMMARY.md` - Technical implementation details
- `SELECTIVE_REUPLOAD_GUIDE.md` - User guide for selective re-uploads
- `TOGGLE_ALWAYS_VISIBLE.md` - Toggle behavior and configuration

### Request Status Tracking Enhancement
**Feature:** Automatic status updates in `request_desc` field

**Examples:**
```
# Production Success:
Production: 123,456 rows → APT_CUSTOM_CLIENT_WEEK_20260202_FINAL

# Both Success:
Production: 123,456 rows → APT_CUSTOM_CLIENT_WEEK_20260202_FINAL | Audit: 2 files, 123,456 rows

# With Failure:
Production: 123,456 rows → APT_CUSTOM_CLIENT_WEEK_20260202_FINAL | Audit: FAILED - IP not whitelisted
```

### Audit Delivery File Tracking (Phase 5)
**Feature:** FILE_NAME column tracks source PostgreSQL table

**Purpose:**
- Data lineage tracking
- Issue debugging and investigation
- Source table identification for audit records

**Schema:**
```
FILE_NAME: apt_custom_7379_theory_q4_w6_postback_table
```

**Documentation:** `FILE_NAME_FIELD_ADDITION.md`

### Environment-Based Configuration
**Migration:** Moved Snowflake credentials from `app.yaml` to `.env`

**Structure:**
```bash
# Production Account (SF_* prefix)
SF_ACCOUNT=zeta_hub_reader.us-east-1
SF_PRIVATE_KEY_PATH=backend/.snowflake/rsa_key.p8

# Audit Account (SF_AUDIT_* prefix)
SF_AUDIT_ACCOUNT=zetaglobal.us-east-1
SF_AUDIT_PRIVATE_KEY_PATH=backend/.snowflake/lpt_rsa_key.p8
```

---

## 📚 **Documentation Files**
- `PROJECT_SUMMARY.md` - This file
- `DUAL_UPLOAD_FIX_SUMMARY.md` - Dual upload implementation
- `DUAL_UPLOAD_TOGGLE_GUIDE.md` - Toggle feature guide
- `TOGGLE_ALWAYS_VISIBLE.md` - Toggle visibility behavior
- `SELECTIVE_REUPLOAD_GUIDE.md` - Re-upload workflows
- `FILE_NAME_FIELD_ADDITION.md` - Audit tracking feature
- `README.md` - Setup and installation guide

---
**Status**: Production Ready | **License**: MIT | **Version**: 2.0.0
