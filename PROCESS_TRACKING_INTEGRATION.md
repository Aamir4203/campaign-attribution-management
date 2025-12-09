# CENTRALIZED PROCESS TRACKING INTEGRATION

## ✅ **SOLUTION: No Code Duplication**

### **📁 Files Created:**
1. **`SCRIPTS/trackingHelper.sh`** - Centralized tracking functions
2. **`SCRIPTS/createTrackingTable.sh`** - Database table creation script

### **🏗️ Setup (Run Once):**

```bash
# Create the tracking table
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS
chmod +x createTrackingTable.sh
./createTrackingTable.sh
```

---

## 🔧 **How to Integrate in Each Module Script**

### **Simple 2-Line Integration:**

```bash
#!/bin/bash
# Source configuration and centralized tracking functions
source ./config.properties
source $TRACKING_HELPER

REQUEST_ID=$1

# Add process tracking
append_process_id $REQUEST_ID "MODULE_NAME"

# Your existing module logic here
# ...existing code...

# Error handling
if [ $? -ne 0 ]; then
    mark_request_failed $REQUEST_ID "MODULE_NAME" "Module failed"
    exit 1
fi
```

### **For Re-run Requests:**

```bash
# Check if re-run
REQUEST_STATUS=$($CONNECTION_STRING -t -c "SELECT request_status FROM $REQUEST_TABLE WHERE request_id = $REQUEST_ID" 2>/dev/null | xargs)

if [ "$REQUEST_STATUS" = "RE" ]; then
    clear_and_restart_tracking $REQUEST_ID "MODULE_NAME"
else
    append_process_id $REQUEST_ID "MODULE_NAME"
fi
```

### **For Final Module:**

```bash
# For the last module (e.g., deliveredScript.sh)
if [ $? -eq 0 ]; then
    mark_request_completed $REQUEST_ID
else
    mark_request_failed $REQUEST_ID "MODULE_NAME" "Module failed"
    exit 1
fi
```

---

## 📋 **Module Integration Checklist**

### **Module Names:**
- **trtPreparation.sh** → `"TRT"`
- **respondersPulling.sh** → `"RESP"`  
- **suppressionList.sh** → `"SUPP"`
- **srcPreparation.sh** → `"SRC"`
- **deliveredScript.sh** → `"DEL"`
- **timestampAppending.sh** → `"TS"`
- **ipAppending.sh** → `"IP"`

### **Integration Template:**
```bash
source ./config.properties
source $TRACKING_HELPER
REQUEST_ID=$1
append_process_id $REQUEST_ID "MODULE_NAME"
# ...existing module code...
```

---

## 📊 **Database Table Structure**

```sql
CREATE TABLE apt_custom_request_process_tracking (
    request_id INTEGER PRIMARY KEY,
    process_ids VARCHAR(1000),      -- "123,456,789"
    module_sequence VARCHAR(500),   -- "TRT,SUPP,SRC"  
    current_module VARCHAR(50),     -- "SRC"
    start_time TIMESTAMP,
    last_updated TIMESTAMP,
    status VARCHAR(10),             -- RUNNING/COMPLETED/ERROR/KILLED
    host_server VARCHAR(50),        -- hostname
    created_by VARCHAR(50)          -- user
);
```

---

## 🚀 **Quick Start Steps**

### **1. Setup (Run Once):**
```bash
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS  
./createTrackingTable.sh
```

### **2. Update Each Module Script:**
Add these 3 lines at the beginning:
```bash
source ./config.properties
source $TRACKING_HELPER  
append_process_id $REQUEST_ID "MODULE_NAME"
```

### **3. Test:**
```bash
./trtPreparation.sh 6989
psql -c "SELECT * FROM apt_custom_request_process_tracking WHERE request_id = 6989;"
```

## 🎯 **Benefits**

✅ **No Code Duplication** - Single source of truth  
✅ **Easy Maintenance** - Update one file affects all scripts  
✅ **Consistent Behavior** - Same logic across all modules  
✅ **Simple Integration** - Just 2 lines per script  
✅ **Centralized Logging** - All tracking logs in one place
