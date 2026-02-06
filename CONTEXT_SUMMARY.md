# Project Context Summary

**Last Updated**: 2026-02-06
**Status**: Request Automation Implemented | Rerun Logic Enhancement Planned

---

## 📌 Quick Overview

**Campaign Attribution Management (CAM)** is a production-ready web application for managing campaign attribution processing requests with real-time monitoring.

### Tech Stack
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS
- **Backend**: Flask + Python + PostgreSQL
- **Database**: PostgreSQL (3-table JOIN architecture)
- **Auth**: Session-based (48-hour sessions)

---

## 🎯 Current Status

### ✅ Request Automation (Implemented)
**Status**: Complete and operational

**What's Working**:
- Auto-runs `requestPicker.sh` every 15 seconds
- Configuration-based enable/disable (`app.yaml`)
- Emergency stop API endpoint
- Graceful shutdown with Flask
- Background daemon thread execution

**Configuration** (`shared/config/app.yaml`):
```yaml
automation:
  enabled: true   # Set to false to disable for testing
  interval_seconds: 15
  script_path: "./SCRIPTS/requestPicker.sh"
  script_timeout_seconds: 300
```

**Files**:
- `backend/services/automation.py` - Scheduler service
- `backend/routes/automation_routes.py` - API endpoints
- `backend/app.py` - Auto-start integration

**Documentation**:
- `AUTOMATION_IMPLEMENTATION.md` - Complete implementation guide
- `HOW_TO_STOP_AUTOMATION.md` - Control and troubleshooting

---

## 🔄 Request Statuses

| Status | Meaning | Description |
|--------|---------|-------------|
| `W` | Waiting | Newly submitted, waiting to be picked |
| `R` | Running | Currently executing |
| `RE` | ReRun | Marked for rerun from specific module |
| `RW` | Rerun Waiting | Rerun request waiting (legacy, being phased out) |
| `C` | Completed | Successfully completed |
| `E` | Error/Cancelled | Failed or cancelled by user |

**Error Codes** (module start points for reruns):
- `1` = TRT module
- `2` = Responders
- `3` = Suppression
- `4` = Source
- `5` = Delivered Report
- `6` = TimeStamp Appending
- `7` = IP Appending

---

## 🚀 Pending Enhancements

### 🔄 Rerun Logic Improvement (Planned)
**Priority**: High
**Effort**: 4-6 hours
**Status**: Documented, ready for implementation

**Problem**:
- Old manual process used RW (full rerun) and RE (partial rerun) separately
- Need centralized approach with smart cleanup

**Solution**:
- Use only `RE` status for all reruns
- Add `previous_status` column to track what status was before RE
- Backend automatically determines cleanup based on previous status:
  - If `previous_status = 'C'` → Full cleanup (delete unsubs, drop all tables)
  - If `previous_status = 'E'` → Partial cleanup (drop module tables only)

**What Needs to be Done**:
1. Add `previous_status` column to database
2. Update `update_request()` API to capture current status before updating
3. Update `requestConsumer.sh` to check previous_status and perform appropriate cleanup
4. Test both full and partial rerun scenarios

**Documentation**: `RERUN_LOGIC_IMPROVEMENT.md`

---

## 📋 Historical Plans (Reference Only)

### MINIMAL_AUTOMATION_PLAN.md
- Simple 40-line solution
- **Status**: Evolved into actual implementation

### SIMPLE_AUTOMATION_PLAN.md
- 1-2 hour implementation with controls
- **Status**: Basis for final implementation

### REQUEST_AUTOMATION_PLAN.md
- Comprehensive 16-day plan with full architecture
- **Status**: Reference for future advanced features

---

## 📂 Current Project Structure

### Backend
```
backend/
├── app.py                      # Main Flask app (modular, blueprint-based)
├── db.py                       # Database connection pool
├── config/
│   └── config.py              # Configuration management
├── routes/                     # API endpoints
│   ├── auth_routes.py         # Authentication
│   ├── client_routes.py       # Client management
│   ├── request_routes.py      # Request CRUD (includes cancel/edit)
│   ├── snowflake_routes.py    # Snowflake uploads
│   ├── upload_routes.py       # File uploads
│   ├── utility_routes.py      # Health checks
│   ├── dashboard_routes.py    # Dashboard metrics
│   └── automation_routes.py   # Automation control (NEW)
└── services/                   # Business logic
    └── automation.py           # Request automation scheduler (NEW)
```

### Scripts
```
SCRIPTS/
├── requestPicker.sh           # Main automation target
├── requestConsumer.sh         # Request execution
├── requestValidation.py       # Request validation
└── [30+ other operational scripts]
```

### Frontend
```
frontend/src/
├── pages/
│   ├── LoginPage.tsx
│   ├── AddRequestForm.tsx
│   └── RequestsPage.tsx       # Request monitoring
└── components/
    └── [Various UI components]
```

---

## 🚀 What's Already Implemented

### ✅ Phase 1-6 Complete
1. **Form Implementation** - 7-section request submission form
2. **Authentication System** - Session-based login/logout
3. **Request Management** - Real-time table with search, filtering, actions
4. **Snowflake Dual Upload** - Production + Audit delivery system
5. **Audit Delivery Tracking** - FILE_NAME field for data lineage
6. **Request Automation** - Auto-execution of pending requests ✨ NEW

### Key Features
- Live client dropdown with add functionality
- Real-time request table (auto-refresh 30s)
- Status tracking with color-coded badges
- Action buttons (Kill, ReRun, View, Download, Upload)
- Dual Snowflake upload (Production + Audit/LPT)
- Configurable toggle (ON/OFF per request)
- Independent upload status tracking
- Selective re-upload (Production/Audit/Both)
- **Auto-scheduling of requests** (configurable enable/disable) ✨ NEW
- **Emergency stop API** for automation control ✨ NEW

### Cancel/Edit Request Operations
- **Cancel Request**: Kills running processes, terminates DB connections, sets status to 'E'
  - Direct cancel for waiting requests (W)
  - Script-based cancel for running requests (R, RE, RW)
- **Edit Request**: Updates form fields, sets status to 'RE' with error_code for module restart
  - All form fields updatable
  - Module selection (TRT, Responders, Suppression, etc.)
  - Automatic revalidation and reprocessing

**Documentation**: `REQUEST_CANCEL_AND_EDIT_FLOW.md`

---

## 🛠️ What's NOT Implemented Yet

### Rerun Logic Improvement
- ❌ No `previous_status` column in database
- ❌ Smart cleanup logic not implemented in `requestConsumer.sh`
- ❌ API doesn't capture previous status before update

**Current State**:
- RW and RE statuses both exist but cleanup logic is manual
- Need centralized approach with automatic cleanup detection

**Planned**: See "Pending Enhancements" section above

### Optional Future Enhancements
- ❌ Frontend automation status component (not needed - existing monitoring sufficient)
- ❌ Automation start API endpoint (restart Flask to re-enable is acceptable)
- ❌ Advanced metrics dashboard (database has all info)

---

## 📊 Database Schema

### Main Tables
1. **apt_custom_postback_request_details_dnd** - Request details
2. **apt_custom_client_info_table_dnd** - Client information
3. **apt_custom_postback_qa_table_dnd** - Quality assurance data

### Key Fields (Request Table)
- `request_id` - Primary key
- `request_status` - W/R/RE/RW/C/E
- `request_validation` - Y/N/NULL
- `request_desc` - Status messages, upload results
- `request_start_time` - Execution start
- `request_end_time` - Execution end
- `user_name` - Submitted by
- `client_name` - Client name

---

## 🔐 Environment Configuration

### Database (PostgreSQL)
- Host: `zds-prod-pgdb01-01.bo3.e-dialog.com`
- Database: `apt_tool_db`
- User: `datateam`

### Snowflake Accounts
- **Production**: `zeta_hub_reader.us-east-1` (SF_* env vars)
- **Audit/LPT**: `zetaglobal.us-east-1` (SF_AUDIT_* env vars)

### Configuration Files
- `.env` - Environment variables (Snowflake credentials)
- `shared/config/app.yaml` - Application config (features, CORS, etc.)

---

## 📖 Documentation Files

### Core Documents
- **`CONTEXT_SUMMARY.md`** - This file - Quick project context and status
- **`PROJECT_SUMMARY.md`** - Complete project overview

### Planning Documents (Historical)
- `MINIMAL_AUTOMATION_PLAN.md` - 40-line solution (evolved into implementation)
- `SIMPLE_AUTOMATION_PLAN.md` - 1-2 hour implementation (basis for final)
- `REQUEST_AUTOMATION_PLAN.md` - 16-day comprehensive plan (reference)
- `SERVER_REQUEST_DATA_FLOW_DIAGRAM.md` - Data flow documentation

### Feature Documentation
- **`AUTOMATION_IMPLEMENTATION.md`** - Request automation complete guide ✨ NEW
- **`HOW_TO_STOP_AUTOMATION.md`** - Automation control and troubleshooting ✨ NEW
- **`REQUEST_CANCEL_AND_EDIT_FLOW.md`** - Cancel/Edit operations complete flow ✨ NEW
- **`RERUN_LOGIC_IMPROVEMENT.md`** - Planned enhancement for smart rerun cleanup ✨ NEW
- `DUAL_UPLOAD_FIX_SUMMARY.md` - Dual upload implementation
- `SELECTIVE_REUPLOAD_GUIDE.md` - Re-upload workflows
- `TOGGLE_ALWAYS_VISIBLE.md` - Toggle behavior
- `FILE_NAME_FIELD_ADDITION.md` - Audit tracking

### Setup
- `README.md` - Setup and installation guide

---

## 🎯 Next Steps (When Ready)

### Priority 1: Rerun Logic Improvement (4-6 hours)
**Goal**: Centralize RW/RE logic with smart cleanup

**Tasks**:
1. **Database Migration**:
   - Add `previous_status` column to request table
   - Test in development environment

2. **API Update** (`backend/routes/request_routes.py`):
   - Modify `update_request()` to capture current status
   - Store in `previous_status` before setting to 'RE'

3. **Backend Script Update** (`SCRIPTS/requestConsumer.sh`):
   - Check `previous_status` at start
   - If `previous_status = 'C'` → Full cleanup (delete unsubs, drop all tables)
   - If `previous_status = 'E'` → Partial cleanup (drop module tables)
   - Start from error_code module

4. **Testing**:
   - Test full rerun from completed request
   - Test partial rerun from failed request
   - Verify cleanup queries work correctly

**Documentation**: `RERUN_LOGIC_IMPROVEMENT.md`

### Future Enhancements (Optional)
- Auto-detect failed module for error_code
- Cleanup preview in UI before execution
- Selective table drop choices
- Cleanup action logging

---

## 🔍 Key Files to Know

### Backend Core
- `backend/app.py:120-171` - Blueprint registration and automation auto-start
- `backend/db.py` - Database connection pool
- **`backend/services/automation.py`** - Request automation scheduler ✨ NEW
- **`backend/routes/automation_routes.py`** - Automation control API ✨ NEW

### Request Operations
- **`backend/routes/request_routes.py:444-594`** - Edit/update request (sets RE status)
- **`backend/routes/request_routes.py:1017-1151`** - Cancel/kill request

### Request Processing Scripts
- `SCRIPTS/requestPicker.sh` - Main queue processor (picks W/RE/RW requests)
- `SCRIPTS/requestValidation.py` - Validation logic (24KB)
- `SCRIPTS/requestConsumer.sh` - Request executor (15KB) - **NEEDS UPDATE for rerun logic**
- `SCRIPTS/cancelRequest.sh` - Process cancellation (kills PIDs, terminates DB connections)

### Configuration
- `shared/config/app.yaml` - Feature flags, CORS, backend config, **automation settings** ✨
- `.env` - Snowflake credentials, database config

---

## 💡 Important Notes

### Production Environment
- The SCRIPTS use hardcoded production paths: `/u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB`
- Database credentials are hardcoded in shell scripts
- Consider environment-specific path handling in automation

### Design Decisions
- **Why background thread?** Simple, no additional infrastructure (vs Celery/Redis)
- **Why polling?** Simple, reliable, 15s latency acceptable (vs event-driven)
- **Why max 10 parallel?** Resource management, prevents DB connection exhaustion

### Git Status
- **Current Branch**: `audit`
- **Untracked Files**: 4 planning documents (*.md)
- **Recent Work**: Dual upload feature, file upload color flagging

---

## 📞 Quick Commands

### Check Request Status
```bash
# Check running requests
psql -U datateam -h zds-prod-pgdb01-01.bo3.e-dialog.com -d apt_tool_db \
  -c "SELECT COUNT(*) FROM apt_custom_postback_request_details_dnd WHERE request_status='R'"

# Check waiting requests
psql -U datateam -h zds-prod-pgdb01-01.bo3.e-dialog.com -d apt_tool_db \
  -c "SELECT COUNT(*) FROM apt_custom_postback_request_details_dnd WHERE request_status IN ('W','RE','RW')"
```

### Automation Control
```bash
# Check automation status
curl http://localhost:5000/api/automation/status

# Emergency stop (keeps Flask running)
curl -X POST http://localhost:5000/api/automation/stop

# Disable automation for testing (edit app.yaml, then restart Flask)
# Set: automation.enabled: false
```

### Run Flask Dev Server
```bash
cd backend
python app.py
# Server: http://localhost:5000
# Automation auto-starts if enabled in app.yaml
```

### Manual Request Execution (if automation disabled)
```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS
./requestPicker.sh
```

---

## 🎓 Session Recovery Checklist

When resuming work on this project:

1. ✅ Read this document (CONTEXT_SUMMARY.md)
2. ✅ Check current status section - what's completed vs pending
3. ✅ Review "Pending Enhancements" section for next priorities
4. ✅ Check git status to see current branch and uncommitted changes
5. ✅ Review relevant documentation files:
   - For automation: `AUTOMATION_IMPLEMENTATION.md`, `HOW_TO_STOP_AUTOMATION.md`
   - For cancel/edit: `REQUEST_CANCEL_AND_EDIT_FLOW.md`
   - For rerun improvement: `RERUN_LOGIC_IMPROVEMENT.md` (not yet implemented)
6. ✅ Verify automation status:
   - Check `automation.enabled` in `app.yaml`
   - Test automation API if needed
7. ✅ Continue from "Next Steps" section

---

## 📌 Quick Status Summary

**What Works Now**:
- ✅ Request automation (runs every 15 seconds, configurable)
- ✅ Cancel request (kills processes, DB connections)
- ✅ Edit request (updates fields, sets RE status with module selection)
- ✅ Dual Snowflake upload
- ✅ Full web UI with authentication

**What's Next**:
- 🔄 Rerun logic improvement (smart cleanup based on previous_status)
- 📋 See `RERUN_LOGIC_IMPROVEMENT.md` for details

---

**Document Purpose**: This file serves as a comprehensive context document for both humans and AI assistants to quickly understand the project state, what's been done, and what needs to be done next.

**Maintained By**: Project team + Claude Code
**Update Frequency**: After major features or architectural decisions
