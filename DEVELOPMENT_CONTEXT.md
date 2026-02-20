# Development Context - Campaign Attribution Management

**Last Updated:** February 20, 2026
**Purpose:** Technical reference for developers and maintenance

---

## 🎯 Quick Reference

### Key Technical Decisions

1. **Validation Split:** Two-tier validation (frontend file checks + backend query/DB checks)
2. **Config Centralization:** All credentials and paths in `shared/config/app.yaml`
3. **Status Management:** `request_validation` field controls processing flow
4. **ReRun Safety:** Always reset `validation=NULL` on rerun to force fresh validation
5. **RLTP Processing:** V2 uses Snowflake staging with GZIP compression (20-30% faster)

---

## 🔄 Validation Status Workflow

### Status Values & Meanings

| Value | Field | Meaning | Set By | When |
|-------|-------|---------|--------|------|
| **NULL** | request_validation | Not yet validated | System | Initial request creation |
| **'V'** | request_validation | Validating | requestValidation.py | Validation starts (line 517) |
| **'Y'** | request_validation | Passed | requestValidation.py | All validations successful (line 601) |
| **'N'** | request_validation | Failed | requestValidation.py | Any validation fails (line 612) |

### requestPicker.sh Selection Logic

**Query (Lines 31-35):**
```bash
new_request_id=$($CONNECTION_STRING -qtAX -c \
    "select request_id from $REQUEST_TABLE \
     where upper(request_status) in ('W','RE','RW') \
     and (request_validation is null or upper(request_validation)='Y') \
     order by request_id limit 1")
```

**Selection Rules:**
- ✅ **Picks:** `validation=NULL` (needs validation) OR `validation='Y'` (already validated)
- ❌ **Skips:** `validation='V'` (validation in progress) OR `validation='N'` (validation failed)

**After Validation Check (Lines 44-52):**
```bash
python3 "$MAIN_SCRIPTS/requestValidation.py" "$new_request_id"

if [[ $? -eq 0 ]]; then
    validation_status=$($CONNECTION_STRING -qtAX -c \
        "select upper(request_validation) from $REQUEST_TABLE where request_id=$new_request_id")

    if [[ $validation_status == 'Y' ]]; then
        sh -x "$MAIN_SCRIPTS/requestConsumer.sh" "$new_request_id"  # Only runs if 'Y'
    fi
fi
```

### Why requestConsumer Doesn't Check Validation

**Answer:** requestPicker already acts as a gate.

```
requestPicker Gate:
    validation='Y'? → YES → Call requestConsumer
    validation='Y'? → NO  → Skip (stay in queue)

By the time requestConsumer runs:
    validation='Y' is GUARANTEED
```

---

## 🔄 ReRun Logic & Validation Reset

### Critical Rule
**When changing `request_status` to 'RE' or 'RW', ALWAYS set `request_validation=NULL`**

### Why?
- Query may have been edited
- Database tables may have changed
- RLTP IDs may be different
- Configuration may have changed
- **Fresh validation ensures data integrity**

### Backend Implementation

#### Endpoint 1: `/api/requests/<int:request_id>/rerun`
**File:** `backend/routes/request_routes.py` (Line 985-993)

```python
update_query = f"""
UPDATE {requests_table}
SET request_status = 'RE',
    error_code = %s,
    request_validation = NULL,  # ✅ CRITICAL: Reset validation
    request_desc = %s,
    request_start_time = NOW()
WHERE request_id = %s
"""

description = f"ReRun requested for {rerun_module} module"
cursor.execute(update_query, (error_code, description, request_id))
```

#### Endpoint 2: `/update_request/<int:request_id>`
**File:** `backend/routes/request_routes.py` (Line 546-553)

```python
update_fields.extend([
    "request_status = %s",
    "error_code = %s",
    "request_validation = NULL",  # ✅ CRITICAL: Reset validation
    "request_desc = %s",
    "request_start_time = NOW()"
])

description = f"Request updated and queued for rerun from {rerun_module} module"
update_values.extend(['RE', error_code, description, request_id])
```

### Module Error Codes

```python
module_error_codes = {
    'TRT': 1,                    # Start from TRT preparation
    'Responders': 2,             # Start from responders pulling
    'Suppression': 3,            # Start from suppression list
    'Source': 4,                 # Start from source preparation
    'Delivered Report': 5,       # Start from delivered report
    'TimeStamp Appending': 6,    # Start from timestamp appending
    'IP Appending': 7            # Start from IP appending
}
```

**Usage in requestConsumer.sh:**
```bash
request_error_code=`$CONNECTION_STRING -qtAX -c "select error_code from $REQUEST_TABLE where request_id=$new_request_id"`

if [[ $request_error_code == '1' ]]; then
    # Drop all tables and start from TRT
    sh -x trtPreparation.sh $new_request_id
elif [[ $request_error_code == '2' ]]; then
    # Start from responders pulling
    sh -x respondersPulling.sh $new_request_id
# ... etc
fi
```

---

## 🔍 requestValidation.py - Validation Details

### Status Update Locations

**1. Validation Starts (Line 517):**
```python
update_request_status(cur, request_table, request_id, 'V', 'Backend validation in progress')
```

**2. Validation Passes (Line 601):**
```python
update_request_status(cur, request_table, request_id, 'Y', 'Backend validation passed - Ready for processing')
```

**3. Validation Fails (Line 612):**
```python
update_request_status(cur, request_table, request_id, 'N', ve.user_message)
# ve.user_message examples:
# - "Failed while pulling sample data from Snowflake"
# - "Input query is incorrect - Table not found in Snowflake"
# - "Input query has syntax error"
# - "RLTP ID 25000 is same as last week"
# - "Database table xyz_table not found"
```

### ValidationError Class

```python
class ValidationError(Exception):
    """Custom exception for validation failures"""
    def __init__(self, user_message, technical_details=""):
        self.user_message = user_message  # Short, actionable (shown to user)
        self.technical_details = technical_details  # Full error (for logs/email)
        super().__init__(user_message)
```

**Usage Examples:**
```python
# Query execution failure
raise ValidationError(
    "Failed while pulling sample data from Snowflake",
    f"Query execution error: {str(e)[:200]}"
)

# Table not found
raise ValidationError(
    "Input query is incorrect - Table not found in Snowflake",
    f"Query execution error: {str(e)[:200]}"
)

# RLTP ID duplicate
raise ValidationError(
    f"RLTP ID {rltp_id} is same as last week",
    f"Last week RLTP ID: {last_rltp_id}"
)
```

### Email Notification on Failure

**Sent When:** `validation='N'` is set
**Recipients:** `vmarni@zetaglobal.com, datateam@aptroid.com`
**Subject:** `APT BACKEND VALIDATION FAILED :: <client> :: <user>`
**Content:** HTML table with all validation results (Pass/Failed) + technical details

---

## 🚀 RLTP Script Migration (V2)

### Files Changed

| Before | After | Size | Status |
|--------|-------|------|--------|
| `rltpDataPulling.py` | `rltpDataPulling_old_backup.py` | 17.5 KB | Backup |
| `rltpDataPulling_v2.py` | `rltpDataPulling.py` | 36.4 KB | Production |

### Key Improvements in V2

**1. Snowflake Staging**
```python
# Old approach: Direct SELECT, no staging
query = f"SELECT * FROM {table_name} WHERE ..."
df = pd.read_sql(query, snowflake_conn)

# New approach: Snowflake staging with GZIP
stage_name = f"@~/{stage_path}"
copy_query = f"""
    COPY INTO {stage_name}
    FROM (SELECT * FROM {table_name} WHERE ...)
    FILE_FORMAT = (TYPE=CSV COMPRESSION=GZIP)
"""
snowflake_cursor.execute(copy_query)
# Download and process staged files
```

**2. Performance Improvements**

| Metric | Old Version | New Version | Improvement |
|--------|-------------|-------------|-------------|
| Data Export | Direct SELECT | Snowflake Staging | 20-30% faster |
| Network Transfer | Uncompressed | GZIP compressed | 70-80% less |
| Processing | Sequential | Parallel | Multi-core utilization |
| Memory | Not optimized | Buffer flushing | Lower memory usage |

**3. Auto-Fallback**
```python
try:
    # Try staging approach
    use_snowflake_staging(...)
except Exception as e:
    logger.warning(f"Staging failed: {e}, falling back to direct fetch")
    # Falls back to direct SELECT approach
```

### Script References

**trtPreparation.sh** calls:
```bash
python3 "$SCRIPTPATH/rltpDataPulling.py" "$new_request_id"
```

✅ **No changes needed** - Script name remains `rltpDataPulling.py`

### Configuration

Uses centralized config from:
- `SCRIPTS/config.yaml` (via config_loader.py)
- Sources database connections
- Sources processing settings (parallel workers, chunk size, etc.)

### Rollback Procedure (if needed)

```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/SCRIPTS
mv rltpDataPulling.py rltpDataPulling_v2_restore.py
mv rltpDataPulling_old_backup.py rltpDataPulling.py
```

---

## 🗃️ Database Column Reference

### Important Column Name Preservation

**requestConsumer.sh (Line 36):**
```bash
clickstoclickspbreportedgencount from $REQUEST_TABLE
```

**Note:** Do NOT change to `clickstoclickspbreportedcount` - the table schema uses `clickstoclickspbreportedgencount` (with "gen" in the name).

This was initially changed and then reverted per user request.

---

## 🔧 Configuration System

### Master Configuration File

**File:** `shared/config/app.yaml`

**Sourced By:**
1. `backend/config/config.py` → Python scripts
2. `SCRIPTS/config.properties` (auto-generated) → Shell scripts

### Python Config Loader

**File:** `SCRIPTS/config_loader.py` or `backend/config/config.py`

**Usage:**
```python
from config_loader import get_config

config = get_config()

# Database connections
db_config = config.config.get('database', {})
postgres_cfg = db_config.get('postgres', {})

# Table names
request_table = config.get_table('requests')

# Email settings
email_config = config.config.get('email', {})
```

### Shell Config Loader

**File:** `SCRIPTS/config.properties` (auto-generated from app.yaml)

**Usage:**
```bash
# Source configuration
source "$SCRIPTPATH/config.properties"

# Use variables
$CONNECTION_STRING
$REQUEST_TABLE
$ALERT_TO
$MAIN_PATH
```

---

## 🎨 Frontend Validation Status Display

### StatusBadge Component Logic

**File:** `frontend/src/pages/RequestLogs.tsx`

```typescript
interface Request {
  request_validation?: string | null; // Y, N, V (Yes, No, Validating)
  request_status: string;
  // ... other fields
}

const StatusBadge: React.FC<{ status: string; validation?: string | null }> = ({ status, validation }) => {
  // If status is 'W' (Waiting) but validation is 'N' (No/Failed), show validation failed
  if (status === 'W' && validation === 'N') {
    return {
      text: 'Validation Failed',
      className: 'bg-red-100 text-red-800 border-red-300 font-semibold'
    };
  }

  // If status is 'W' and validation is 'V' (Validating), show validating status
  if (status === 'W' && validation === 'V') {
    return {
      text: 'Validating',
      className: 'bg-purple-100 text-purple-800 border-purple-200 animate-pulse'
    };
  }

  // Normal status badges...
};
```

### Edit Button Logic

```typescript
const isValidationFailed = request.request_status === 'W' && request.request_validation === 'N';
const canEdit = ['E', 'C'].includes(request.request_status) || isValidationFailed;

// Edit button is shown for:
// 1. Status 'E' (Error)
// 2. Status 'C' (Completed)
// 3. Status 'W' with validation='N' (Validation Failed)
```

---

## 📊 Request Status Transition Diagram

```
[User Submits Request]
        ↓
status='W', validation=NULL
        ↓
[requestPicker picks request]
        ↓
status='W', validation='V' (validating)
        ↓
[requestValidation.py runs]
        ↓
    ┌─────────┴─────────┐
    ↓                   ↓
PASSES              FAILS
validation='Y'      validation='N'
    ↓                   ↓
[requestConsumer]   [Stuck - Edit Required]
    ↓                   ↓
status='R'          [User Edits]
    ↓                   ↓
[Processing]        validation=NULL
    ↓                   ↓
status='C'/'E'      [Retry Validation]
    ↓
[User ReRuns]
    ↓
status='RE', validation=NULL
    ↓
[Loop back to validation]
```

---

## 🛠️ Shell Script Critical Fixes

### requestPicker.sh

**Fixed:**
- ✅ Invalid shebang: `#/bin/bash` → `#!/bin/bash`
- ✅ Hardcoded DB connections → `$CONNECTION_STRING`
- ✅ Added error handling with email notifications
- ✅ Connection failure recovery

**Key Variables:**
```bash
CONNECTION_STRING  # PostgreSQL connection
REQUEST_TABLE      # Request details table
MAIN_SCRIPTS       # Scripts directory path
ALERT_TO          # Email alert recipients
```

### requestConsumer.sh

**Fixed:**
- ✅ Invalid shebang
- ✅ Eliminated 64 lines of duplicate code
- ✅ Created `setup_request_environment()` function
- ✅ Fixed `$REQUEST_ID` → `$new_request_id` inconsistency
- ✅ Added `-p` flags to mkdir commands

**Function Added:**
```bash
setup_request_environment() {
    local request_id=$1
    # Setup directories, extract request details
    # Reusable for both W (new) and RE (rerun) statuses
}
```

### purgeScript.sh

**Fixed:**
- ✅ Dangerous wildcard: `rm $BKP_PATH/*` → specific file deletion
- ✅ Hardcoded emails → `$ALERT_TO`
- ✅ Added S3 upload error handling
- ✅ Safe directory cleanup

**Before (DANGEROUS):**
```bash
rm $BKP_PATH/*  # Deletes everything if BKP_PATH is empty string!
```

**After (SAFE):**
```bash
if [ -d "$BKP_PATH" ] && [ "$(ls -A $BKP_PATH)" ]; then
    # Delete specific files only
    find "$BKP_PATH" -type f -name "*.csv" -delete
fi
```

---

## 🔒 Security Improvements

### Before Refactoring
- ❌ Hardcoded database passwords in 22+ scripts
- ❌ Hardcoded email addresses
- ❌ Dangerous wildcard deletion commands
- ❌ No connection failure handling

### After Refactoring
- ✅ All credentials in centralized config
- ✅ Email addresses configurable
- ✅ Safe, specific file deletion
- ✅ Comprehensive error handling
- ✅ Connection validation before operations

---

## 🤖 Built-In Automation Scheduler

### Overview

**File:** `backend/services/automation.py`

The system includes a built-in automation scheduler that runs requestPicker.sh automatically. **No cron jobs required.**

### How It Works

```python
# Runs in background daemon thread
# Auto-starts when Flask starts (if enabled)
# Runs requestPicker.sh every 60 seconds
```

### Configuration

**File:** `shared/config/app.yaml`

```yaml
automation:
  enabled: true                    # ⚠️ Master switch - must be true
  interval_seconds: 60             # How often to run (60 = every minute)
  script_path: "./SCRIPTS/requestPicker.sh"
  script_timeout_seconds: 300      # Script timeout (5 minutes)
```

### Startup Flow

```
Flask app.py starts
    ↓
Checks automation.enabled in app.yaml
    ↓
If enabled=true:
    from services import automation
    automation.start()
    ↓
Background thread starts
    ↓
Every 60 seconds:
    subprocess.run(['bash', 'SCRIPTS/requestPicker.sh'])
    ↓
Loop continues until Flask stops
```

### API Endpoints

**Check Status:**
```bash
curl http://localhost:5000/api/automation/status

Response:
{
  "success": true,
  "automation": {
    "running": true,
    "interval_seconds": 60,
    "script_path": "./SCRIPTS/requestPicker.sh"
  }
}
```

**Emergency Stop:**
```bash
curl -X POST http://localhost:5000/api/automation/stop

Response:
{
  "success": true,
  "message": "Automation stopped"
}
```

### Flask Logs

**When automation starts:**
```
✅ Registered automation routes
🤖 Request automation started - requestPicker.sh will run every 60 seconds
```

**During operation:**
```
Running ./SCRIPTS/requestPicker.sh
Validation passed for request_id=12345
```

### Important Notes

1. **No Cron Jobs Required**: Automation runs within Flask process
2. **Daemon Thread**: Non-blocking, won't prevent Flask shutdown
3. **Auto-Restart**: If Flask restarts, automation restarts automatically
4. **Production Ready**: Handles script timeouts and errors gracefully

### Troubleshooting

**Issue: Automation not running**
```bash
# Check app.yaml
grep -A 4 "automation:" shared/config/app.yaml

# Should show:
# automation:
#   enabled: true  # ← Must be true
```

**Issue: Script timing out**
```yaml
# Increase timeout in app.yaml
automation:
  script_timeout_seconds: 600  # 10 minutes
```

---

## 📋 Development Checklist

### When Adding New Features

- [ ] Update `shared/config/app.yaml` if adding new config
- [ ] Regenerate `SCRIPTS/config.properties` after app.yaml changes
- [ ] Update requirements.txt if adding Python dependencies
- [ ] Add frontend validation if accepting user input
- [ ] Add backend validation if query/DB-related
- [ ] Update API endpoint list in PROJECT_SUMMARY.md
- [ ] Test ReRun logic if modifying request status
- [ ] Ensure `request_validation=NULL` on any status change to RE/RW

### When Modifying Validation

- [ ] Update both frontend and backend validation if needed
- [ ] Keep ValidationError messages user-friendly
- [ ] Test email notifications on failure
- [ ] Verify requestPicker still picks correctly
- [ ] Test Edit button shows for validation='N'

### When Modifying Database Schema

- [ ] Update all affected SQL queries
- [ ] Update TypeScript interfaces (if frontend-visible)
- [ ] Update PROJECT_SUMMARY.md database schema section
- [ ] Test both new and rerun requests

---

## 🐛 Common Issues & Solutions

### Issue 1: Request Stuck in Validation

**Symptoms:** Status 'W', validation='V' for extended time

**Causes:**
- requestValidation.py crashed mid-execution
- Database connection timeout during validation

**Solution:**
```sql
-- Manually reset validation to retry
UPDATE APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND
SET request_validation = NULL,
    request_desc = 'Validation reset - retry'
WHERE request_id = <id>;
```

### Issue 2: ReRun Skips Validation

**Symptoms:** Request processes without validation after ReRun

**Causes:**
- Backend forgot to set `request_validation=NULL`

**Fix:** Check both ReRun endpoints:
```python
# MUST include this line:
request_validation = NULL
```

### Issue 3: RLTP Script Fails

**Symptoms:** rltpDataPulling.py errors during staging

**Causes:**
- Snowflake permissions issue
- Network connectivity

**Solution:** V2 has auto-fallback to direct fetch

**Manual Rollback:**
```bash
cd SCRIPTS
mv rltpDataPulling.py rltpDataPulling_v2_restore.py
mv rltpDataPulling_old_backup.py rltpDataPulling.py
```

---

## 📞 Support Contacts

**Data Team:** datateam@aptroid.com
**Alerts:** vmarni@zetaglobal.com, datateam@aptroid.com

---

**Document Version:** 1.0
**Last Updated:** February 20, 2026
**Status:** Production Reference
