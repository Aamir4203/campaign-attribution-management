# PROCESS TRACKING SETUP GUIDE

## 🎯 **Quick Setup (Run Once)**

### **1. Create Tracking Table**
```sql
CREATE TABLE IF NOT EXISTS APT_CUSTOM_REQUEST_PROCESS_TRACKING_DND (
    request_id INTEGER PRIMARY KEY,
    process_ids VARCHAR(1000),
    module_sequence VARCHAR(500),
    current_module VARCHAR(50),
    start_time TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),
    status VARCHAR(10) DEFAULT 'RUNNING',
    host_server VARCHAR(50),
    created_by VARCHAR(50)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tracking_request_id ON APT_CUSTOM_REQUEST_PROCESS_TRACKING_DND(request_id);
CREATE INDEX IF NOT EXISTS idx_tracking_status ON APT_CUSTOM_REQUEST_PROCESS_TRACKING_DND(status);
CREATE INDEX IF NOT EXISTS idx_tracking_module ON APT_CUSTOM_REQUEST_PROCESS_TRACKING_DND(current_module);
```

### **2. Files Created**
- ✅ **trackingHelper.sh** - Centralized tracking functions
- ✅ **config.properties** - Updated with TRACKING_HELPER variable

---

## 🔧 **Integration Template**

### **Add to Every Module Script:**

```bash
#!/bin/bash
# Example: trtPreparation.sh

# Source configuration and centralized tracking functions
source ./config.properties
source $TRACKING_HELPER

REQUEST_ID=$1

# ✅ SINGLE FUNCTION CALL - Track this process
append_process_id $REQUEST_ID "TRT"

# Your existing module code here...
# ...existing logic...

# Error handling (optional)
if [ $? -ne 0 ]; then
    mark_request_failed $REQUEST_ID "TRT" "TRT preparation failed"
    exit 1
fi
```

### **Module Names to Use:**
- **trtPreparation.sh** → `"TRT"`
- **suppressionList.sh** → `"SUPP"`  
- **srcPreparation.sh** → `"SRC"`
- **deliveredScript.sh** → `"DEL"` (+ call `mark_request_completed`)
- **timestampAppending.sh** → `"TS"`
- **ipAppending.sh** → `"IP"`
- **respondersPulling.sh** → `"RESP"`

---

## 🎯 **Result in Database**

```sql
-- After running modules for request 6989:
SELECT * FROM apt_custom_request_process_tracking WHERE request_id = 6989;

request_id | process_ids | module_sequence | current_module | status  
6989       | 123,456,789 | TRT,SUPP,SRC   | SRC           | RUNNING
```

**This gives cancelRequest.sh the comma-separated PIDs to kill: `123,456,789`**

---

## ✅ **Benefits**

✅ **No Code Duplication** - Single helper file  
✅ **Simple Integration** - Just 2 lines per script  
✅ **Centralized Maintenance** - Update one file affects all  
✅ **Automatic Logging** - All tracking logged to RequestCancel.log  
✅ **Production Ready** - Proper error handling and database integration

---

## 🚀 **Quick Test**

```bash
# 1. Run any module
./trtPreparation.sh 6989

# 2. Check tracking
psql -c "SELECT request_id, process_ids, current_module FROM apt_custom_request_process_tracking WHERE request_id = 6989;"

# 3. Test cancellation  
./cancelRequest.sh 6989
```

**Perfect centralized solution with zero code duplication!** 🎉
