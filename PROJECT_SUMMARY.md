# Campaign Attribution Management (CAM) - Complete Project Summary

**Version:** 2.0.0
**Status:** ✅ Production Ready
**Last Updated:** February 20, 2026

---

## 📊 Project Overview

A comprehensive web application for managing campaign attribution processing requests with real-time monitoring, dual Snowflake delivery, and automated backend validation.

---

## 🏗️ Architecture

### Technology Stack
```
Frontend:
├── React 19 with TypeScript
├── Vite build tooling
├── Tailwind CSS styling
├── React Hook Form + Yup validation
└── React Router navigation

Backend:
├── Flask 2.3.3 web framework
├── PostgreSQL database
├── Snowflake (Production + Audit)
├── Python 3.12+
└── RESTful API design

Processing:
├── 22+ Shell scripts (Bash)
├── Python data processing scripts
├── Scheduler-based request queue
└── Parallel processing pipelines
```

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (React)                    │
│  [Login] [Add Request] [Monitor] [Upload] [Download]       │
└───────────────────┬─────────────────────────────────────────┘
                    │ REST API
┌───────────────────▼─────────────────────────────────────────┐
│                   Flask Backend                              │
│  ┌──────────────┬─────────────┬──────────────────────┐     │
│  │ Auth Routes  │ API Routes  │ Validation Service  │     │
│  └──────────────┴─────────────┴──────────────────────┘     │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│              PostgreSQL Database                             │
│  [Request Table] [Client Table] [QA Table]                  │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│           Shell Script Processing Pipeline                   │
│  requestPicker.sh → requestValidation.py → requestConsumer.sh│
│       ↓                    ↓                      ↓           │
│  trtPreparation → srcPreparation → respondersPulling         │
│       ↓                    ↓                      ↓           │
│  [Various processing modules] → Snowflake Upload             │
└─────────────────────────────────────────────────────────────┘
```

### Configuration Hierarchy
```
shared/config/app.yaml (Master Configuration)
    ↓
┌───────────────────────┬──────────────────────────┐
│                       │                          │
backend/config/        SCRIPTS/                  .env
config.py              config.properties         (Credentials)
│                       │                          │
Python Scripts          Shell Scripts             Snowflake Keys
```

---

## ⚡ Key Features

### 🔐 Authentication System
- **Database-Driven Login**: Session-based authentication with 48-hour sessions
- **Protected Routes**: Automatic session validation across all endpoints
- **User Context**: Logged-in user tracked in all request forms
- **Session Management**: `/api/login`, `/api/logout`, `/api/session_info`

### 📝 Add Request Form (7 Sections)

1. **Client Information**
   - Live client dropdown with add-new functionality
   - Client validation against database

2. **Campaign Dates**
   - Start date, end date, residual date validation
   - Residual date must be >= max CPM date

3. **File Options**
   - File type selection (Delivered, Not Delivered, etc.)
   - Conditional path configuration

4. **Report Paths**
   - Report path configuration
   - Quality score path settings

5. **Suppression List**
   - Multiple suppression types
   - Request ID-based suppression support

6. **Data Priority Settings**
   - Priority file configuration
   - Percentage allocation

7. **SQL Query**
   - Custom SQL query input
   - Query validation (frontend + backend)

### 📊 Request Management

**Real-Time Monitoring:**
- Auto-refresh every 30 seconds
- Status tracking with color-coded badges:
  - **Waiting (W)**: Yellow - queued for processing
  - **Validating (V)**: Purple (pulsing) - validation in progress
  - **Running (R)**: Blue - actively processing
  - **Completed (C)**: Green - successfully finished
  - **Error (E)**: Red - processing failed
  - **Validation Failed (N)**: Red (bold) - backend validation failed
  - **ReRun (RE)**: Yellow - queued for rerun
  - **Rework (RW)**: Yellow - queued for rework

**Search & Filter:**
- Search by Request ID, Client Name, User
- Fixed headers with scrollable content
- Professional pagination

**Action Buttons:**
- **Kill**: Terminate running requests
- **ReRun**: Re-execute from specific modules (TRT, Responders, Source, etc.)
- **View**: View request details
- **Download**: Download processed files
- **Upload**: Upload to Snowflake (Production + Audit)
- **Edit**: Edit validation-failed requests

### ❄️ Snowflake Dual Upload System

**Features:**
- **Dual Delivery**: Upload to both Production and Audit (LPT) Snowflake accounts
- **Toggle Control**: Always-visible toggle in upload modal (ON/OFF per request)
- **Independent Uploads**: Production and Audit run in parallel threads
- **Selective Re-upload**: Re-upload only failed delivery (Production/Audit/Both)
- **Progress Tracking**: Separate progress bars with real-time status updates
- **Smart State Management**: Each upload maintains independent status

**Configuration:**
```yaml
# shared/config/app.yaml
features:
  dual_sf_upload: false  # Default: OFF (production only)
```

**Status Updates in request_desc:**
```
Production: 123,456 rows → APT_CUSTOM_CLIENT_WEEK_20260202_FINAL
Production: 123,456 rows → TABLE_NAME | Audit: 2 files, 123,456 rows
Production: SUCCESS | Audit: FAILED - IP not whitelisted
```

**Audit Delivery Details:**
- **Schema**: `GREEN.INFS_LPT` (LPT account)
- **FILE_NAME Tracking**: Source PostgreSQL table name stored for data lineage
- **Header Format**: 11 columns including FILE_NAME field
- **Authentication**: Private key authentication (separate keys for each account)

### 🤖 Built-In Automation Scheduler

**Features:**
- **Auto-Start with Flask**: No cron jobs required - scheduler starts when Flask starts
- **Configurable Interval**: Runs requestPicker.sh every 60 seconds (configurable)
- **Background Thread**: Non-blocking, runs in separate daemon thread
- **Emergency Stop**: API endpoint to stop automation if needed
- **Status Monitoring**: Real-time status via `/api/automation/status` endpoint

**Configuration:**
```yaml
# shared/config/app.yaml
automation:
  enabled: true                    # Master switch
  interval_seconds: 60             # Run every 60 seconds
  script_path: "./SCRIPTS/requestPicker.sh"
  script_timeout_seconds: 300      # 5 minute timeout
```

**How It Works:**
```
Flask App Starts
    ↓
Automation Thread Starts (if enabled=true)
    ↓
Every 60 seconds:
    → Run requestPicker.sh
    → Pick pending request (if any)
    → Start requestValidation.py
    → If validation='Y', start requestConsumer.sh
    → Loop back
```

**Control Endpoints:**
- `GET /api/automation/status` - Check if automation is running
- `POST /api/automation/stop` - Emergency stop (if needed)

**No Cron Jobs Needed!** Just enable in config and start Flask.

---

## 🔄 Validation Workflow

### Two-Tier Validation System

#### Frontend Validation (file_validation_service.py)
**Executed:** During file upload, before request submission

**Checks:**
- File format and structure validation
- Column count verification
- Data type consistency
- Cross-file validations:
  - CPM ↔ Decile segment matching
  - CPM ↔ Decile delivered sum comparison
  - Timestamp ↔ CPM date matching
- PostgreSQL compatibility (apostrophe escaping)
- Duplicate row detection
- Position-based column references (no header dependency)

#### Backend Validation (requestValidation.py)
**Executed:** After request queued, before processing starts

**Critical Validations:**
1. **Query Execution Testing** (MOST CRITICAL)
   - Tests queries against Snowflake
   - Validates column counts across all queries
   - Checks for duplicate column names
   - Automatic Snowflake connection based on RLTP ID

2. **RLTP ID Uniqueness**
   - Verifies RLTP ID differs from last week's request
   - Prevents stale data usage

3. **Database Table Existence**
   - `prev_week_pb_table`
   - `total_delivered_table`
   - `posted_unsub_hards_table`

4. **Server-Side File Validation**
   - Suppression file existence check

5. **Business Logic Validation**
   - Residual date >= max CPM date
   - Week name length <= 6 characters

**Validation Status Updates:**
```python
NULL → 'V' (Validating) → 'Y' (Passed) or 'N' (Failed)
```

**User-Friendly Error Messages:**
```
"Failed while pulling sample data from Snowflake"
"Input query is incorrect - Table not found in Snowflake"
"Input query has syntax error"
"RLTP ID 25000 is same as last week"
"Database table xyz_table not found"
```

**Email Notifications:**
- Sent on validation failure (`validation='N'`)
- Recipients: `vmarni@zetaglobal.com, datateam@aptroid.com`
- Includes technical details for debugging

---

## 🔄 Request Processing Workflow

```
1. User submits request via frontend
        ↓
2. Frontend validation (file_validation_service.py)
   ✓ File format checks
   ✓ Cross-file validations
   ✓ Data integrity
        ↓
3. Request saved to database
   status='W', validation=NULL
        ↓
4. Scheduler runs requestPicker.sh (every minute)
   Query: SELECT request_id WHERE status IN ('W','RE','RW')
          AND (validation IS NULL OR validation='Y')
        ↓
5. requestPicker picks request (if < 10 running)
        ↓
6. Backend validation (requestValidation.py)
   validation='V' (validating)
   ✓ Query execution tests
   ✓ Database table checks
   ✓ RLTP ID verification
   ✓ Server-side file validation
        ↓
   ┌─────────────┴──────────────┐
   │                            │
   PASS                       FAIL
   validation='Y'             validation='N'
   │                            │
   ↓                            ↓
7. requestConsumer starts      [STUCK - Edit Required]
   status='R' (Running)        User clicks Edit button
   │                            │
   ↓                            ↓
8. Processing Modules:         Fixes query/config
   - trtPreparation.sh         Resubmits → validation=NULL
   - srcPreparation.sh         Loop back to step 5
   - respondersPulling.sh
   - suppressionList.sh
   - deliveredReport.sh
   - timeStampAppending.sh
   - ipAppending.sh
   - openClickAdjustment.sh
        ↓
9. Request completes
   status='C' (Completed)
        ↓
10. User uploads to Snowflake
    - Production upload
    - Audit upload (if enabled)
        ↓
11. purgeScript.sh archives old requests (>45 days)
    - Archives to S3
    - Cleans local directories
```

---

## 🔧 Refactoring & Improvements

### Configuration Centralization

**Before:**
- ❌ 22+ shell scripts with hardcoded credentials
- ❌ Python scripts with embedded database passwords
- ❌ Email addresses scattered across scripts
- ❌ Paths hardcoded as `APT_TOOL_DB`

**After:**
- ✅ Single `shared/config/app.yaml` configuration file
- ✅ All scripts source configuration dynamically
- ✅ No hardcoded credentials anywhere
- ✅ Standardized paths: `Campaign-Attribution-Management`

### Shell Script Fixes

#### requestPicker.sh (Request Queue Manager)
- ✅ Fixed invalid shebang: `#/bin/bash` → `#!/bin/bash`
- ✅ Replaced 3 hardcoded database connections with `$CONNECTION_STRING`
- ✅ Added proper error handling with email notifications
- ✅ Connection failure recovery

#### requestConsumer.sh (Main Request Processor)
- ✅ Fixed invalid shebang
- ✅ Eliminated 64 lines of duplicate code
- ✅ Created reusable `setup_request_environment()` function
- ✅ Fixed variable inconsistency (`$REQUEST_ID` → `$new_request_id`)
- ✅ Added `-p` flags to mkdir commands
- ✅ Preserved column name: `clickstoclickspbreportedgencount`

#### purgeScript.sh (Data Archival & Cleanup)
- ✅ Fixed dangerous wildcard deletion: `rm $BKP_PATH/*` → specific file deletion
- ✅ Replaced hardcoded email addresses
- ✅ Added S3 upload error handling
- ✅ Safe directory cleanup with validation

### Python Script Refactoring

#### requestValidation.py (Complete Rewrite)
- ✅ Focused on backend-only validations
- ✅ Removed Presto database logic (Snowflake only)
- ✅ Added custom `ValidationError` class with dual messages:
  - `user_message`: Short, actionable (shown to user)
  - `technical_details`: Full error (for logs/email)
- ✅ User-friendly error messages in `request_desc`
- ✅ Email notifications on failure
- ✅ Config loader integration

#### rltpDataPulling.py (V2 Promoted to Main)
**Old Version (backup):** `rltpDataPulling_old_backup.py` (17.5 KB)
**New Version (production):** `rltpDataPulling.py` (36.4 KB)

**Key Improvements:**
- ✅ Snowflake staging for 20-30% faster data export
- ✅ GZIP compression (70-80% less network transfer)
- ✅ Parallel processing with multi-core utilization
- ✅ Memory-efficient with explicit buffer flushing
- ✅ Process isolation (stage isolation per process)
- ✅ Auto-fallback to direct fetch if staging fails

### Path Standardization
- ✅ 29 replacements across 20 shell scripts
- ✅ `APT_TOOL_DB` → `Campaign-Attribution-Management`
- ✅ Updated S3 backup paths
- ✅ Updated directory cleanup paths
- ✅ Zero syntax errors after replacement

---

## 🗄️ Database Schema

### Main Tables

**APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND** (Request Table)
```sql
request_id                      SERIAL PRIMARY KEY
client_name                     VARCHAR(255)
user_name                       VARCHAR(100)
query                          TEXT
request_status                 CHAR(2)  -- W, V, R, C, E, RE, RW
request_validation             CHAR(1)  -- NULL, V, Y, N
request_desc                   TEXT     -- User-friendly status messages
request_start_time             TIMESTAMP
request_end_time               TIMESTAMP
error_code                     INTEGER  -- Module restart point
prev_week_pb_table             VARCHAR(255)
total_delivered_table          VARCHAR(255)
posted_unsub_hards_table       VARCHAR(255)
... [50+ columns total]
```

**APT_CUSTOM_CLIENT_INFO_TABLE_DND** (Client Table)
```sql
client_id                      SERIAL PRIMARY KEY
client_name                    VARCHAR(255) UNIQUE
created_at                     TIMESTAMP
```

**APT_CUSTOM_QA_TABLE_DND** (QA Stats Table)
```sql
request_id                     INTEGER FOREIGN KEY
rltp_file_count               INTEGER  -- Live TRT count
qa_attribute_count            INTEGER
... [QA metrics]
```

### Request Status Values

| Status | Description | Can Edit | Can ReRun | Can Kill |
|--------|-------------|----------|-----------|----------|
| **W** | Waiting | ✅ | ✅ | ❌ |
| **V** | Validating | ❌ | ❌ | ❌ |
| **R** | Running | ❌ | ❌ | ✅ |
| **C** | Completed | ✅ | ✅ | ❌ |
| **E** | Error | ✅ | ✅ | ❌ |
| **RE** | ReRun | ❌ | ❌ | ❌ |
| **RW** | Rework | ❌ | ❌ | ❌ |

### Validation Status Values

| Status | Description | Picker Action |
|--------|-------------|---------------|
| **NULL** | Not validated | ✅ Pick → Validate |
| **V** | Validating | ❌ Skip |
| **Y** | Passed | ✅ Pick → Process |
| **N** | Failed | ❌ Skip (stuck until edited) |

---

## 📂 Project Structure

```
Campaign-Attribution-Management/
├── frontend/                          # React Frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx             # Authentication page
│   │   │   ├── AddRequest.tsx        # 7-section form
│   │   │   ├── RequestLogs.tsx       # Request monitoring
│   │   │   └── DownloadRequest.tsx   # File downloads
│   │   ├── components/               # Reusable components
│   │   ├── services/                 # API services
│   │   └── utils/                    # Utilities
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                           # Flask Backend
│   ├── app.py                        # Main Flask application
│   ├── config/
│   │   └── config.py                 # Python config loader
│   ├── routes/
│   │   ├── auth_routes.py           # Authentication endpoints
│   │   ├── request_routes.py        # Request CRUD + ReRun
│   │   ├── client_routes.py         # Client management
│   │   ├── upload_routes.py         # File upload handling
│   │   └── dashboard_routes.py      # Dashboard stats
│   ├── services/
│   │   ├── file_validation_service.py    # Frontend validation
│   │   ├── snowflake_service.py          # Snowflake uploads
│   │   └── snowflake_audit_service.py    # Audit uploads
│   └── .snowflake/
│       ├── rsa_key.p8               # Production private key
│       └── lpt_rsa_key.p8           # Audit private key
│
├── SCRIPTS/                           # Processing Scripts
│   ├── config.properties             # Shell config (auto-generated)
│   ├── config_loader.py              # Python config loader
│   │
│   ├── requestPicker.sh              # Request queue manager
│   ├── requestValidation.py          # Backend validation
│   ├── requestConsumer.sh            # Main processor
│   ├── purgeScript.sh                # Data archival
│   │
│   ├── trtPreparation.sh             # TRT module
│   ├── srcPreparation.sh             # Source preparation
│   ├── rltpDataPulling.py            # RLTP data processor (V2 - Production)
│   ├── rltpDataPulling_old_backup.py # RLTP V1 backup
│   ├── respondersPulling.sh          # Responders module
│   ├── suppressionList.sh            # Suppression module
│   ├── deliveredReport.sh            # Delivered report
│   ├── timeStampAppending.sh         # Timestamp appending
│   ├── ipAppending.sh                # IP appending
│   ├── openClickAdjustment.py        # Open/click adjustment
│   └── [20+ other scripts...]
│
├── shared/config/
│   ├── app.yaml                      # Master configuration file
│   └── schema.md                     # Configuration schema docs
│
├── .env                              # Environment variables & credentials
├── requirements.txt                  # Python dependencies
├── PROJECT_SUMMARY.md                # This file
├── DEVELOPMENT_CONTEXT.md            # Development reference
└── README.md                         # Setup & installation guide
```

---

## 📋 API Endpoints

### Authentication
- `POST /api/login` - User authentication
- `POST /api/logout` - Session termination
- `GET /api/session_info` - Session status

### Request Management
- `GET /api/requests` - List all requests
- `GET /api/requests/<id>` - Get request details
- `POST /submit_form` - Create new request
- `POST /update_request/<id>` - Update existing request
- `POST /api/requests/<id>/rerun` - ReRun with module selection
- `POST /api/requests/<id>/kill` - Terminate running request

### Client Management
- `GET /api/clients` - List all clients
- `POST /check_client` - Validate client name
- `POST /add_client` - Add new client

### File Operations
- `POST /upload` - Upload files with validation
- `GET /api/requests/<id>/files` - List request files
- `GET /download/<id>` - Download processed files

### Snowflake Operations
- `POST /api/snowflake/upload-dual/<id>` - Dual upload (Production + Audit)
- `GET /api/snowflake/progress/<task_id>` - Upload progress tracking

### Automation
- `GET /api/automation/status` - Get automation scheduler status
- `POST /api/automation/stop` - Emergency stop automation

### Utilities
- `GET /health` - Health check
- `GET /api/features` - Feature flags
- `GET /api/tables/<table_name>/columns` - Table schema info

---

## 🚀 Deployment

### System Requirements
- Linux server (Ubuntu 20.04+ or RHEL 8+)
- Python 3.8+ with pip
- PostgreSQL client tools (psql)
- Node.js 18+ and npm
- AWS CLI configured for S3 access
- Mail server (sendmail/postfix)

### Quick Start

1. **Deploy Code (No Git Tracking)**
```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS

# Option A: Clone and remove git tracking (recommended)
git clone <repository-url> Campaign-Attribution-Management
cd Campaign-Attribution-Management
rm -rf .git  # Remove git tracking for production

# Option B: Direct copy without git
# rsync -avz --exclude '.git' --exclude 'node_modules' \
#   ./ production-server:/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/
```

2. **Install Dependencies**
```bash
# Python (use virtual environment)
python3 -m venv CAM_Env
source CAM_Env/bin/activate
pip3 install -r requirements.txt
```

3. **Setup Snowflake RSA Keys**
```bash
# Create .snowflake directory in backend
mkdir -p backend/.snowflake
chmod 700 backend/.snowflake

# Copy your RSA private keys to the directory
# Production Snowflake Key
cp /path/to/your/production_key.p8 backend/.snowflake/rsa_key.p8

# Audit (LPT) Snowflake Key
cp /path/to/your/audit_key.p8 backend/.snowflake/lpt_rsa_key.p8

# Set proper permissions (CRITICAL - must be 600)
chmod 600 backend/.snowflake/rsa_key.p8
chmod 600 backend/.snowflake/lpt_rsa_key.p8
```

4. **Configure Application**
```bash
# Update master configuration
nano shared/config/app.yaml

# Enable automation scheduler
# automation:
#   enabled: true  # ✅ Set to true

# Update backend/.env with production values (CRITICAL)
# backend/.env overrides app.yaml via CAM_* environment variables
# Ensure these are set correctly:
#   CAM_DB_HOST=<your-database-server>   # Database server (may differ from app server)
#   CAM_ENVIRONMENT=production
#   CAM_DEBUG=false

# Generate shell config from app.yaml
cd SCRIPTS
python3 config_loader.py
cd ..
```

5. **Build Frontend with Production API URL (CRITICAL)**
```bash
# Create production env file for Vite (baked into JS bundle at build time)
cat > frontend/.env.production << 'EOF'
VITE_API_BASE_URL=http://<your-app-server-ip>:5000
VITE_ENVIRONMENT=production
VITE_DEBUG_MODE=false
EOF

# Build frontend (Vite auto-picks up .env.production)
cd frontend
npm install
npm run build
cd ..
```

> ⚠️ **Important:** `frontend/.env.production` must exist before running `npm run build`.
> Without it, `VITE_API_BASE_URL` defaults to `http://localhost:5000` — API calls will
> fail for any browser not on the server itself.

6. **Start Backend in Background**
```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/backend
source ../CAM_Env/bin/activate
nohup python app.py > logs/app.log 2>&1 &
echo $! > logs/backend.pid
```

7. **Start Frontend in Background**
```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/frontend
nohup npm run preview -- --port 3009 --host > /tmp/cam_frontend.log 2>&1 &
echo $! > /tmp/cam_frontend.pid
# Access at http://<your-app-server-ip>:3009
```

8. **Verify Services Running**
```bash
ss -tlnp | grep -E "3009|5000"
curl http://<your-app-server-ip>:5000/api/automation/status
tail -f backend/logs/app.log
```

9. **Stop Services**
```bash
kill $(cat backend/logs/backend.pid)
kill $(cat /tmp/cam_frontend.pid)
```

### ⚙️ Configuration Priority

`backend/.env` **overrides** `shared/config/app.yaml` for `CAM_*` variables:

| `.env` Variable | Overrides `app.yaml` Key | Notes |
|---|---|---|
| `CAM_DB_HOST` | `database.host` | Database server (not necessarily same as app server) |
| `CAM_DB_PORT` | `database.port` | |
| `CAM_DB_NAME` | `database.database` | |
| `CAM_ENVIRONMENT` | `environment` | Must be `production` |
| `CAM_DEBUG` | `debug` | Must be `false` |

### 🔁 Restart Requirements

| Change | Backend Restart | Frontend Rebuild |
|---|---|---|
| `app.yaml` changes | ✅ Yes | ❌ No |
| `backend/.env` changes | ✅ Yes | ❌ No |
| `frontend/.env.production` changes | ❌ No | ✅ Yes (`npm run build`) |
| Enable/disable automation | ✅ Yes | ❌ No |

---

## 🔐 Security Features

- ✅ Session-based authentication with secure cookies
- ✅ All credentials in centralized config (no hardcoding)
- ✅ Private key authentication for Snowflake
- ✅ .env file permission restricted (chmod 600)
- ✅ SQL injection prevention (parameterized queries)
- ✅ Input validation on frontend and backend
- ✅ XSS protection (React auto-escaping)
- ✅ CORS properly configured
- ✅ Secure file upload handling

---

## 📊 Performance Metrics

### RLTP Data Pulling (V2 vs V1)

| Metric | V1 (Old) | V2 (Current) | Improvement |
|--------|----------|--------------|-------------|
| Data Export | Direct SELECT | Snowflake Staging | 20-30% faster |
| Network Transfer | Uncompressed | GZIP compressed | 70-80% less |
| Processing | Sequential | Parallel | Multi-core utilization |
| Memory | Not optimized | Buffer flushing | Lower memory usage |
| Code Size | 17.5 KB | 36.4 KB | More features |

### Request Processing
- Average request validation: 30-60 seconds
- Average full processing: 2-5 hours (depending on data volume)
- Concurrent requests: Up to 10 simultaneous

---

## 📝 Important Notes

### ReRun Logic
When ReRun button is clicked:
1. Backend MUST set `request_validation=NULL`
2. Backend sets `request_status='RE'`
3. Backend sets `error_code` (1-7) for module restart point
4. requestPicker picks request again
5. requestValidation.py runs fresh validation
6. If validation='Y', processing starts from specified module

**Critical:** Never skip validation reset on ReRun!

### Module Error Codes
```python
1 = TRT                    # Start from TRT preparation
2 = Responders             # Start from responders pulling
3 = Suppression            # Start from suppression list
4 = Source                 # Start from source preparation
5 = Delivered Report       # Start from delivered report
6 = TimeStamp Appending    # Start from timestamp appending
7 = IP Appending           # Start from IP appending
```

### Validation Philosophy
- **Frontend**: Catch obvious errors early (file format, data integrity)
- **Backend**: Validate business logic, database connectivity, query correctness
- **Goal**: Fail fast, provide clear error messages, send notifications

---

## 👥 Team & Support

**Data Team:** datateam@aptroid.com
**Alerts:** vmarni@zetaglobal.com, datateam@aptroid.com

---

**Document Version:** 2.0
**Status:** Production Ready ✅
**License:** MIT
