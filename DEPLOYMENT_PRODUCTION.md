# Production Deployment Guide
## Campaign Attribution Management (CAM) - v2.0

**Target Server:** zds-prod-pgdb03-01.bo3.e-dialog.com (10.100.86.22)
**Created:** February 23, 2026
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Production Configuration Template](#production-configuration-template)
3. [Snowflake RSA Keys Setup](#snowflake-rsa-keys-setup)
4. [Centralized Email Configuration](#centralized-email-configuration)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting](#troubleshooting)

---

## 🔍 Pre-Deployment Checklist

### System Requirements
- ✅ Linux server (Ubuntu 20.04+ or RHEL 8+)
- ✅ Python 3.8+ with pip
- ✅ PostgreSQL client tools (psql)
- ✅ Node.js 18+ and npm
- ✅ AWS CLI configured for S3 access
- ✅ Mail server (sendmail/postfix) configured
- ✅ Access to zds-prod-pgdb03-01.bo3.e-dialog.com

### Required Credentials
- ✅ Database credentials for PostgreSQL (datateam user)
- ✅ Snowflake RSA private keys (production + audit)
- ✅ Snowflake account passphrases
- ✅ External database connection strings (Presto, Impala, MySQL)

### Network Access
- ✅ Port 5432: PostgreSQL database access
- ✅ Port 5000: Flask backend API
- ✅ Port 3009: React frontend
- ✅ Snowflake endpoints: zeta_hub_reader.us-east-1, zetaglobal.us-east-1
- ✅ External databases: Presto, Impala, MySQL (Orange)

---

## 🎯 Production Configuration Template

A production-ready configuration template has been created at:
```
shared/config/app.production.yaml
```

### Key Production Differences

| Setting | Development | Production |
|---------|-------------|------------|
| **Database Host** | zds-prod-pgdb01-01 | zds-prod-pgdb03-01 |
| **Database Name** | apt_tool_db | apt_tool_db |
| **Requests Table** | APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST | APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND |
| **Debug Mode** | true | false |
| **Logging Level** | DEBUG | INFO |
| **Environment** | development | production |
| **Auto-reload** | true | false |
| **Automation** | false | true |
| **Base Path** | /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management | (same) |

### Configuration Steps

1. **Copy production template:**
   ```bash
   cd /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management
   cp shared/config/app.production.yaml shared/config/app.yaml
   ```

2. **Update production-specific values:**
   ```bash
   nano shared/config/app.yaml
   ```

3. **Verify configuration:**
   ```bash
   # Check database connectivity
   psql -U datateam -h zds-prod-pgdb03-01.bo3.e-dialog.com -d apt_tool_db -c "SELECT 1"

   # Regenerate shell config
   cd SCRIPTS
   python3 config_loader.py
   ```

---

## 🔐 Snowflake RSA Keys Setup

### Why RSA Keys?
Snowflake uploads use private key authentication (more secure than passwords). The application requires two separate keys:
- **Production Key**: For main Snowflake uploads (HUBUSERS.ZX_DATAOPS)
- **Audit Key**: For LPT account uploads (GREEN.INFS_LPT)

### Setup Instructions

1. **Create .snowflake directory:**
   ```bash
   cd backend
   mkdir -p .snowflake
   chmod 700 .snowflake
   ```

2. **Copy RSA private keys:**
   ```bash
   # Production Snowflake Key (HUBUSERS account)
   cp /secure/location/production_key.p8 backend/.snowflake/rsa_key.p8

   # Audit Snowflake Key (LPT account)
   cp /secure/location/audit_key.p8 backend/.snowflake/lpt_rsa_key.p8
   ```

3. **Set proper permissions (CRITICAL):**
   ```bash
   chmod 600 backend/.snowflake/rsa_key.p8
   chmod 600 backend/.snowflake/lpt_rsa_key.p8
   ```

4. **Verify keys exist:**
   ```bash
   ls -la backend/.snowflake/
   # Should show:
   # -rw------- 1 techteam techteam 1766 Feb 23 rsa_key.p8
   # -rw------- 1 techteam techteam 1766 Feb 23 lpt_rsa_key.p8
   ```

### Configuration References

Keys are referenced in `shared/config/app.yaml`:

```yaml
snowflake:
  production:
    connection:
      private_key_path: "backend/.snowflake/rsa_key.p8"
      private_key_passphrase: "Snowfl@ke12#$"

  audit:
    connection:
      private_key_path: "backend/.snowflake/lpt_rsa_key.p8"
      private_key_passphrase: "Jsw44QTLRYYGLGBgfhXQR7webwaxArWx"
```

### Testing Snowflake Connectivity

**Important:** Snowsql requires the passphrase via environment variable `$SNOWSQL_PRIVATE_KEY_PASSPHRASE`

```bash
# Test production connection
SNOWSQL_PRIVATE_KEY_PASSPHRASE="Snowfl@ke12#$" \
  snowsql -a zeta_hub_reader.us-east-1 \
  -u zx_dataops_service \
  --private-key-path backend/.snowflake/rsa_key.p8 \
  -q "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()"

# Expected output:
# +--------------------+------------------+---------------------+
# | CURRENT_DATABASE() | CURRENT_SCHEMA() | CURRENT_WAREHOUSE() |
# |--------------------+------------------+---------------------|
# | HUBUSERS           | ZX_DATAOPS       | ZX_DATAOPS_WH       |
# +--------------------+------------------+---------------------+

# Test audit connection
SNOWSQL_PRIVATE_KEY_PASSPHRASE="Jsw44QTLRYYGLGBgfhXQR7webwaxArWx" \
  snowsql -a zetaglobal.us-east-1 \
  -u green_lp_service \
  --private-key-path backend/.snowflake/lpt_rsa_key.p8 \
  -q "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()"

# Expected output:
# +--------------------+------------------+---------------------+
# | CURRENT_DATABASE() | CURRENT_SCHEMA() | CURRENT_WAREHOUSE() |
# |--------------------+------------------+---------------------|
# | GREEN              | NULL             | GREEN_LPT           |
# +--------------------+------------------+---------------------+
```

### Security Best Practices

- ✅ **Never commit RSA keys to git** - Add to .gitignore
- ✅ **Use 600 permissions** - Owner read/write only
- ✅ **Store passphrases securely** - Use environment variables or secrets manager
- ✅ **Rotate keys periodically** - Follow Snowflake security guidelines
- ✅ **Limit key access** - Only techteam user should have access
- ✅ **Backup keys securely** - Store encrypted backups in secure location

---

## 📧 Centralized Email Configuration

### Problem Statement
Email recipients were scattered across multiple files with different terminologies:
- Shell scripts: `alert_to`, `ALERT_TO`, or hardcoded addresses
- Python scripts: `receiver_email`, `alert_to`
- Different email addresses in different scripts

### Solution: Single Source of Truth

All email configuration is now centralized in `shared/config/app.yaml`:

```yaml
alerts:
  email_recipients: "akhan@zetaglobal.com,attributionteam@zetaglobal.com"
  sender: "attributionalerts@zds-prod-pgdb03-01.bo3.e-dialog.com"
```

### How It Works

#### For Shell Scripts:

1. **config.properties** (auto-generated from app.yaml):
   ```bash
   ALERT_TO="akhan@zetaglobal.com,attributionteam@zetaglobal.com"
   ```

2. **Scripts source config.properties:**
   ```bash
   #!/bin/bash

   # Source centralized configuration
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   source "$SCRIPT_DIR/config.properties"

   # Use $ALERT_TO for all email notifications
   echo "Alert message" | mail -s "Subject" $ALERT_TO
   ```

#### For Python Scripts:

1. **config_loader.py** provides email methods:
   ```python
   from config_loader import ConfigLoader

   config = ConfigLoader()
   recipients = config.alert_recipients  # Returns centralized email list
   sender = config.alert_sender         # Returns sender address
   ```

2. **Example usage in requestValidation.py:**
   ```python
   # Get email config from centralized alerts configuration
   receiver_email = config.alert_recipients

   # Send validation failure email
   send_email(receiver_email, subject, body)
   ```

### Updated Scripts

The following scripts have been updated to use centralized email:

**Shell Scripts:**
- ✅ `addClient.sh` - Replaced `alert_to="datateam@aptroid.com"` with `$ALERT_TO`
- ✅ `trtDrop.sh` - Replaced `alert_to="akhan@aptroid.com"` with `$ALERT_TO`
- ✅ `error.sh` - Replaced `alert_to="akhan@aptroid.com"` with `$ALERT_TO`

**Python Scripts:**
- ✅ `requestValidation.py` - Now uses `config.alert_recipients`
- ✅ `config_loader.py` - Added `alert_recipients`, `alert_sender`, and `get_alert_config()` methods

### Changing Email Recipients

To update email recipients system-wide:

1. **Edit app.yaml:**
   ```bash
   nano shared/config/app.yaml
   ```

2. **Update alerts section:**
   ```yaml
   alerts:
     email_recipients: "new_email@example.com,team@example.com"
     sender: "alerts@yourserver.com"
   ```

3. **Regenerate config.properties:**
   ```bash
   cd SCRIPTS
   python3 config_loader.py
   ```

4. **Restart application:**
   ```bash
   # Backend will pick up new config automatically
   # Shell scripts will use updated $ALERT_TO on next run
   ```

---

## 🚀 Deployment Steps

### 1. Deploy Code

```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS

# Option A: Clone repository (recommended)
git clone <repository-url> Campaign-Attribution-Management
cd Campaign-Attribution-Management
rm -rf .git  # Remove git tracking for production

# Option B: Direct copy without git
# rsync -avz --exclude '.git' --exclude 'node_modules' \
#   ./ production-server:/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/
```

### 2. Install Dependencies

```bash
# Python virtual environment
python3 -m venv CAM_Env
source CAM_Env/bin/activate
pip3 install -r requirements.txt

# Frontend
cd frontend
npm install
npm run build
cd ..
```

### 3. Setup Snowflake RSA Keys

```bash
# Follow instructions in "Snowflake RSA Keys Setup" section above
mkdir -p backend/.snowflake
chmod 700 backend/.snowflake
cp /secure/location/*.p8 backend/.snowflake/
chmod 600 backend/.snowflake/*.p8
```

### 4. Configure Application

```bash
# Copy production template
cp shared/config/app.production.yaml shared/config/app.yaml

# Update production-specific values
nano shared/config/app.yaml

# Important settings to verify:
# - database.host: zds-prod-pgdb03-01.bo3.e-dialog.com
# - database.tables.requests: APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND (no _TEST)
# - environment: production
# - debug: false
# - automation.enabled: true
# - alerts.email_recipients: <correct emails>

# Set environment variables
cp .env.example .env
nano .env

# Generate shell config from app.yaml
cd SCRIPTS
python3 config_loader.py
cd ..
```

### 5. Create Required Directories

```bash
# Create request processing directory
mkdir -p REQUEST_PROCESSING

# Create log directories
mkdir -p backend/logs
mkdir -p SCRIPTS/logs

# Set proper permissions
chmod 755 REQUEST_PROCESSING
chmod 755 backend/logs
chmod 755 SCRIPTS/logs
```

### 6. Start Backend (Automation Auto-Starts)

```bash
cd backend
python3 app.py

# Expected output:
# 🤖 Request automation started - requestPicker.sh will run every 60 seconds
# * Running on http://0.0.0.0:5000
```

### 7. Verify Automation Running

```bash
# Check automation status via API
curl http://10.100.86.22:5000/api/automation/status

# Or check logs
tail -f backend/logs/app.log
```

### 8. Setup System Service (Optional but Recommended)

Create systemd service for auto-start on reboot:

```bash
sudo nano /etc/systemd/system/cam-backend.service
```

```ini
[Unit]
Description=Campaign Attribution Management Backend
After=network.target postgresql.service

[Service]
Type=simple
User=techteam
WorkingDirectory=/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/backend
Environment="PATH=/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/CAM_Env/bin"
ExecStart=/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management/CAM_Env/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cam-backend
sudo systemctl start cam-backend
sudo systemctl status cam-backend
```

---

## ✅ Post-Deployment Verification

### 1. Health Check

```bash
# Backend health
curl http://10.100.86.22:5000/health

# Expected output:
# {"status":"healthy","timestamp":"2026-02-23T10:30:00"}
```

### 2. Database Connectivity

```bash
# Test PostgreSQL connection
curl http://10.100.86.22:5000/api/clients

# Should return list of clients
```

### 3. Snowflake Connectivity

```bash
# Test production connection
SNOWSQL_PRIVATE_KEY_PASSPHRASE="Snowfl@ke12#$" \
  snowsql -a zeta_hub_reader.us-east-1 \
  -u zx_dataops_service \
  --private-key-path backend/.snowflake/rsa_key.p8 \
  -q "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()"

# Test audit connection
SNOWSQL_PRIVATE_KEY_PASSPHRASE="Jsw44QTLRYYGLGBgfhXQR7webwaxArWx" \
  snowsql -a zetaglobal.us-east-1 \
  -u green_lp_service \
  --private-key-path backend/.snowflake/lpt_rsa_key.p8 \
  -q "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()"
```

### 4. Automation Status

```bash
# Check automation is running
curl http://10.100.86.22:5000/api/automation/status

# Expected output:
# {"running":true,"enabled":true,"interval_seconds":60}
```

### 5. Email Configuration

```bash
# Verify email recipients in config
cd SCRIPTS
grep "ALERT_TO" config.properties

# Should show:
# ALERT_TO="akhan@zetaglobal.com,attributionteam@zetaglobal.com"
```

### 6. Test Request Submission

```bash
# Access frontend
http://10.100.86.22:3009

# Login with valid credentials
# Submit a test request
# Verify it appears in Request Monitor
# Check automation picks it up
```

### 7. Monitor Logs

```bash
# Backend logs
tail -f backend/logs/app.log

# Request processing logs
tail -f REQUEST_PROCESSING/{request_id}/LOGS/*.log

# Automation logs
tail -f SCRIPTS/logs/requestPicker.log
```

---

## 🔧 Troubleshooting

### Issue: Snowflake Upload Fails

**Symptoms:**
- Upload button returns error
- Error: "Failed to connect to Snowflake"

**Solutions:**
1. Check RSA key permissions:
   ```bash
   ls -la backend/.snowflake/
   # Must be 600 (-rw-------)
   ```

2. Verify key path in config:
   ```bash
   grep "private_key_path" shared/config/app.yaml
   ```

3. Test Snowflake connectivity:
   ```bash
   SNOWSQL_PRIVATE_KEY_PASSPHRASE="Snowfl@ke12#$" \
     snowsql -a zeta_hub_reader.us-east-1 \
     -u zx_dataops_service \
     --private-key-path backend/.snowflake/rsa_key.p8 \
     -q "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA()"
   ```

### Issue: Automation Not Running

**Symptoms:**
- Requests stuck in "Waiting" status
- Automation status returns `running: false`

**Solutions:**
1. Check automation enabled in config:
   ```bash
   grep -A 4 "automation:" shared/config/app.yaml
   ```

2. Verify script path exists:
   ```bash
   ls -la SCRIPTS/requestPicker.sh
   ```

3. Check script permissions:
   ```bash
   chmod +x SCRIPTS/requestPicker.sh
   ```

4. Restart backend:
   ```bash
   # Stop backend (Ctrl+C)
   python3 backend/app.py
   ```

### Issue: Email Alerts Not Sending

**Symptoms:**
- No email notifications received
- Validation failures not reported

**Solutions:**
1. Verify email recipients:
   ```bash
   grep "ALERT_TO" SCRIPTS/config.properties
   ```

2. Test mail command:
   ```bash
   echo "Test" | mail -s "Test Subject" $ALERT_TO
   ```

3. Check sendmail service:
   ```bash
   systemctl status sendmail
   # or
   systemctl status postfix
   ```

4. Regenerate config.properties:
   ```bash
   cd SCRIPTS
   python3 config_loader.py
   ```

### Issue: Database Connection Errors

**Symptoms:**
- Cannot connect to database
- Error: "Connection refused"

**Solutions:**
1. Verify database host in config:
   ```bash
   grep "host:" shared/config/app.yaml | head -1
   # Should be: zds-prod-pgdb03-01.bo3.e-dialog.com
   ```

2. Test database connection:
   ```bash
   psql -U datateam -h zds-prod-pgdb03-01.bo3.e-dialog.com -d apt_tool_db -c "SELECT 1"
   ```

3. Check network connectivity:
   ```bash
   ping zds-prod-pgdb03-01.bo3.e-dialog.com
   telnet zds-prod-pgdb03-01.bo3.e-dialog.com 5432
   ```

### Issue: Frontend Not Loading

**Symptoms:**
- 404 errors
- Cannot access http://10.100.86.22:3009

**Solutions:**
1. Verify frontend build:
   ```bash
   ls -la frontend/dist/
   ```

2. Rebuild frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

3. Check backend serving static files:
   ```python
   # In backend/app.py
   # Verify static folder configuration
   app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
   ```

---

## 📊 Production Monitoring

### Key Metrics to Monitor

1. **Request Processing Rate**
   - Requests picked per minute
   - Average processing time
   - Success/failure ratio

2. **Database Performance**
   - Connection pool usage
   - Query execution times
   - Table sizes

3. **System Resources**
   - CPU usage
   - Memory consumption
   - Disk space

4. **Automation Health**
   - Scheduler uptime
   - Script execution success rate
   - Error frequency

### Monitoring Commands

```bash
# Active requests
psql -U datateam -h zds-prod-pgdb03-01.bo3.e-dialog.com -d apt_tool_db \
  -c "SELECT COUNT(*) FROM APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND WHERE request_status='R'"

# Recent errors
psql -U datateam -h zds-prod-pgdb03-01.bo3.e-dialog.com -d apt_tool_db \
  -c "SELECT request_id, client_name, request_desc FROM APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND WHERE request_status='E' ORDER BY request_id DESC LIMIT 10"

# Disk space
df -h /u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management

# Process monitoring
ps -aef | grep requestPicker
ps -aef | grep requestConsumer

# Log monitoring
tail -f backend/logs/app.log
tail -f SCRIPTS/logs/requestPicker.log
```

---

## 📝 Change Log

### February 23, 2026
- ✅ Created production configuration template (app.production.yaml)
- ✅ Updated deployment guide with RSA key setup instructions
- ✅ Centralized email configuration across all scripts
- ✅ Updated shell scripts (addClient.sh, trtDrop.sh, error.sh) to use $ALERT_TO
- ✅ Added email configuration methods to config_loader.py
- ✅ Updated requestValidation.py to use centralized email config
- ✅ Enhanced config.properties with comprehensive email documentation
- ✅ Documented production deployment process

---

## 🔗 Related Documentation

- **Project Summary:** `project_summary.md`
- **Development Context:** `DEVELOPMENT_CONTEXT.md`
- **Configuration Schema:** `shared/config/schema.md`
- **README:** `README.md`

---

**Deployment Guide Version:** 1.0
**Last Updated:** February 23, 2026
**Maintained By:** DataAttribution Team
