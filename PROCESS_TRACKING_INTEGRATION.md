# CENTRALIZED PROCESS TRACKING INTEGRATION

## ✅ **SOLUTION: No Code Duplication**

### **📁 Files Created:**
1. **`SCRIPTS/trackingHelper.sh`** - Centralized tracking functions
2. **`SCRIPTS/createTrackingTable.sh`** - Database table creation script

### **🏗️ Setup (Run Once):**

```bash
# 1. Create the tracking table
cd /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/SCRIPTS
chmod +x createTrackingTable.sh
./createTrackingTable.sh
```

---

## 🔧 **How to Integrate in Each Module Script**

### **Simple 2-Line Integration:**

```bash
#!/bin/bash
# Example: trtPreparation.sh

# Source configuration and centralized tracking functions
source ./config.properties
source $TRACKING_HELPER

# Get request ID
REQUEST_ID=$1

# ✅ SINGLE CALL - Add process tracking
append_process_id $REQUEST_ID "TRT"

# Your existing module logic here
echo "Starting TRT preparation for request $REQUEST_ID..."
# ...existing TRT preparation code...

# Error handling
if [ $? -ne 0 ]; then
    mark_request_failed $REQUEST_ID "TRT" "TRT preparation failed"
    exit 1
fi
```

### **For Re-run Requests:**

```bash
#!/bin/bash
# Example: srcPreparation.sh

source ./config.properties  
source $TRACKING_HELPER

REQUEST_ID=$1

# Check if re-run
REQUEST_STATUS=$($CONNECTION_STRING -t -c "SELECT request_status FROM $REQUEST_TABLE WHERE request_id = $REQUEST_ID" 2>/dev/null | xargs)

if [ "$REQUEST_STATUS" = "RE" ]; then
    # ✅ SINGLE CALL - Clear and restart for re-run
    clear_and_restart_tracking $REQUEST_ID "SRC"
else
    # ✅ SINGLE CALL - Normal append
    append_process_id $REQUEST_ID "SRC"
fi

# ...existing module logic...

if [ $? -ne 0 ]; then
    mark_request_failed $REQUEST_ID "SRC" "SRC preparation failed"
    exit 1
fi
```

### **For Final Module:**

```bash
#!/bin/bash
# Example: deliveredScript.sh (final module)

source ./config.properties
source $TRACKING_HELPER

REQUEST_ID=$1

# ✅ SINGLE CALL - Add process tracking
append_process_id $REQUEST_ID "DEL"

# ...existing delivered script logic...

if [ $? -eq 0 ]; then
    # ✅ SINGLE CALL - Mark entire request as completed
    mark_request_completed $REQUEST_ID
else
    mark_request_failed $REQUEST_ID "DEL" "Delivered script failed"
    exit 1
fi
```

---

## 📋 **Module Integration Checklist**

### **Integration Template:**
```bash
#!/bin/bash
# Add these 2 lines to every module script:
source ./config.properties
source $TRACKING_HELPER

REQUEST_ID=$1

# Add one function call:
append_process_id $REQUEST_ID "MODULE_NAME"

# ...existing module code...
```

### **Module Names:**
- **trtPreparation.sh** → `"TRT"`
- **respondersPulling.sh** → `"RESP"`  
- **suppressionList.sh** → `"SUPP"`
- **srcPreparation.sh** → `"SRC"`
- **deliveredScript.sh** → `"DEL"`
- **timestampAppending.sh** → `"TS"`
- **ipAppending.sh** → `"IP"`

---

## 🎯 **Benefits of Centralized Approach**

✅ **No Code Duplication** - Single source of truth  
✅ **Easy Maintenance** - Update one file affects all scripts  
✅ **Consistent Behavior** - Same logic across all modules  
✅ **Simple Integration** - Just 2 lines per script  
✅ **Centralized Logging** - All tracking logs in one place  

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
# Run any module script
./trtPreparation.sh 6989

# Check tracking
psql -c "SELECT * FROM apt_custom_request_process_tracking WHERE request_id = 6989;"
```

**Result:** Centralized tracking with zero code duplication! 🎉

### **For New Requests (First Time Execution):**

```bash
#!/bin/bash
# Example: trtPreparation.sh

# Source configuration and tracking functions
source ./config.properties

# Include the tracking functions here (copy from above)
# ... tracking functions ...

# Get request ID
REQUEST_ID=$1

# Add process to tracking at start of module
append_process_id $REQUEST_ID "TRT"

# Your existing module logic here
echo "Starting TRT preparation for request $REQUEST_ID..."

# ... existing TRT preparation code ...

# On successful completion
if [ $? -eq 0 ]; then
    echo "TRT preparation completed successfully"
    # Don't mark as completed here - only the final module should do this
else
    mark_request_failed $REQUEST_ID "TRT" "TRT preparation failed"
    exit 1
fi
```

### **For Re-run Requests (Module-specific restart):**

```bash
#!/bin/bash
# Example: srcPreparation.sh for re-run

# Source configuration and tracking functions
source ./config.properties

# Include the tracking functions here
# ... tracking functions ...

REQUEST_ID=$1

# Check if this is a re-run request
REQUEST_STATUS=$($CONNECTION_STRING -t -c "
    SELECT request_status 
    FROM $REQUEST_TABLE 
    WHERE request_id = $REQUEST_ID
" 2>/dev/null | xargs)

if [ "$REQUEST_STATUS" = "RE" ]; then
    # This is a re-run - clear and restart tracking
    clear_and_restart_tracking $REQUEST_ID "SRC"
    echo "Re-running SRC preparation for request $REQUEST_ID"
else
    # Normal execution - append PID
    append_process_id $REQUEST_ID "SRC"
    echo "Starting SRC preparation for request $REQUEST_ID"
fi

# Your existing module logic here
# ... existing SRC preparation code ...

# On successful completion
if [ $? -eq 0 ]; then
    echo "SRC preparation completed successfully"
else
    mark_request_failed $REQUEST_ID "SRC" "SRC preparation failed"
    exit 1
fi
```

### **For Final Module (e.g., deliveredScript.sh):**

```bash
#!/bin/bash
# Example: deliveredScript.sh (final module)

# Source configuration and tracking functions
source ./config.properties

# Include tracking functions
# ... tracking functions ...

REQUEST_ID=$1

# Add process to tracking
append_process_id $REQUEST_ID "DEL"

# Your existing module logic here
echo "Starting delivered script for request $REQUEST_ID..."

# ... existing delivered script code ...

# On successful completion of FINAL module
if [ $? -eq 0 ]; then
    echo "Delivered script completed successfully"
    mark_request_completed $REQUEST_ID  # ✅ Mark entire request as completed
else
    mark_request_failed $REQUEST_ID "DEL" "Delivered script failed"
    exit 1
fi
```

---

## 📋 **Module Integration Checklist**

### **Modules to Update:**

1. **trtPreparation.sh** → `append_process_id $REQUEST_ID "TRT"`
2. **respondersPulling.sh** → `append_process_id $REQUEST_ID "RESP"`
3. **suppressionList.sh** → `append_process_id $REQUEST_ID "SUPP"`
4. **srcPreparation.sh** → `append_process_id $REQUEST_ID "SRC"`
5. **deliveredScript.sh** → `append_process_id $REQUEST_ID "DEL"` + `mark_request_completed`
6. **timestampAppending.sh** → `append_process_id $REQUEST_ID "TS"`
7. **ipAppending.sh** → `append_process_id $REQUEST_ID "IP"`

### **Integration Points:**

✅ **Start of Each Module**: Call `append_process_id` or `clear_and_restart_tracking`  
✅ **Error Handling**: Call `mark_request_failed` on errors  
✅ **Final Module Only**: Call `mark_request_completed` on success  
✅ **Re-run Logic**: Check request status and use appropriate function  

---

## 🎯 **Example Complete Integration**

### **trtPreparation.sh with tracking:**

```bash
#!/bin/bash

source ./config.properties

# ... tracking functions (copy from above) ...

REQUEST_ID=$1

# Add process tracking
append_process_id $REQUEST_ID "TRT"

echo "[$(date)] Starting TRT preparation for request $REQUEST_ID, PID: $$"

# Your existing TRT logic
# ... existing code ...

if [ $? -eq 0 ]; then
    echo "[$(date)] TRT preparation completed successfully for request $REQUEST_ID"
else
    mark_request_failed $REQUEST_ID "TRT" "TRT preparation failed"
    echo "[$(date)] TRT preparation failed for request $REQUEST_ID"
    exit 1
fi
```

This will create a tracking record like:
```sql
request_id | process_ids | module_sequence | current_module | status
6989       | 123         | TRT            | TRT           | RUNNING
```

Then when suppressionList.sh runs:
```sql
request_id | process_ids | module_sequence | current_module | status  
6989       | 123,456     | TRT,SUPP       | SUPP          | RUNNING
```

And so on until completion or cancellation.
