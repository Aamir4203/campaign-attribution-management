# Rerun Logic Improvement - Centralized Approach

**Date**: 2026-02-06
**Status**: Proposed Enhancement

---

## 🎯 Problem Statement

### Old Manual Process (Before UI)

**Two separate statuses**:

1. **RW (Rerun from Completed)**:
   - Used when: Request successfully completed (`status = 'C'`)
   - Purpose: Full rerun from TRT module
   - **Pre-execution cleanup**:
     ```sql
     -- Delete unsubs from posted table
     DELETE FROM apt_custom_posted_unsub_hards_dnd a
     USING <pb_table> b
     WHERE b.unsub_date IS NOT NULL
     AND a.email = b.email;

     -- If delete fails, mark as error
     UPDATE apt_custom_postback_request_details_dnd
     SET request_status = 'E',
         request_desc = 'Unable to delete unsubs from client table'
     WHERE request_id = <request_id>;
     ```
   - Then: Drop tables + Start from TRT module

2. **RE (Rerun from Module)**:
   - Used when: Request failed at some point (`status = 'E'` or partial)
   - Purpose: Restart from specific module (error_code)
   - **Pre-execution**: Drop required tables + Start from error_code module
   - **No cleanup queries** (data already partially processed)

---

## ✨ New Centralized Approach

### Single Status: 'RE' with Smart Cleanup

**Principle**: Always use `'RE'` status, but let the backend detect if cleanup is needed based on **previous status**.

---

## 🏗️ Implementation Plan

### Step 1: Add Tracking Field to Database

**Add new column** to track previous status:

```sql
ALTER TABLE apt_custom_postback_request_details_dnd
ADD COLUMN previous_status VARCHAR(5) NULL;
```

**Purpose**: Store the status before it was set to 'RE', so backend knows if cleanup is needed.

---

### Step 2: Update Edit/Rerun API Endpoint

**File**: `backend/routes/request_routes.py`

**Modify `update_request()` function**:

```python
@request_bp.route('/update_request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    """Update existing request with new form data and trigger rerun"""
    try:
        data = request.get_json()
        rerun_module = data.get('rerun_module', 'TRT')

        # Map rerun modules to error codes
        module_error_codes = {
            'TRT': 1,
            'Responders': 2,
            'Suppression': 3,
            'Source': 4,
            'Delivered Report': 5,
            'TimeStamp Appending': 6,
            'IP Appending': 7
        }
        error_code = module_error_codes.get(rerun_module, 1)

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor()
        requests_table = config.get_table_name('requests')

        # ============================================
        # NEW: Get current status BEFORE updating
        # ============================================
        cursor.execute(
            f"SELECT request_status FROM {requests_table} WHERE request_id = %s",
            (request_id,)
        )
        result = cursor.fetchone()
        if not result:
            cursor.close()
            release_db_connection(conn)
            return jsonify({'success': False, 'error': 'Request not found'}), 404

        current_status = result[0]
        logger.info(f"📊 Current status: {current_status}")

        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        update_values = []

        # ... (existing field mapping code) ...

        # ============================================
        # NEW: Store previous status for backend
        # ============================================
        update_fields.extend([
            "request_status = %s",
            "previous_status = %s",      # NEW: Track previous status
            "error_code = %s",
            "request_validation = NULL",
            "request_desc = %s",
            "request_start_time = NOW()"
        ])

        description = f"Request updated and queued for rerun from {rerun_module} module"
        update_values.extend([
            'RE',                         # New status
            current_status,               # NEW: Store old status
            error_code,
            description,
            request_id
        ])

        # Build and execute query
        update_query = f"""
            UPDATE {requests_table} SET
                {', '.join(update_fields)}
            WHERE request_id = %s
        """

        cursor.execute(update_query, tuple(update_values))
        conn.commit()

        logger.info(f"✅ Request {request_id} updated successfully!")
        logger.info(f"   Previous Status: {current_status}")
        logger.info(f"   New Status: RE (Rerun)")
        logger.info(f"   Error Code: {error_code} ({rerun_module})")

        cursor.close()
        release_db_connection(conn)

        return jsonify({
            'success': True,
            'message': f'Request {request_id} updated and queued for rerun from {rerun_module} module',
            'request_id': request_id
        })

    except Exception as e:
        logger.error(f"❌ Exception during request update: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

### Step 3: Update Backend Script (requestConsumer.sh)

**File**: `SCRIPTS/requestConsumer.sh`

**Add logic at the start** to check `previous_status` and perform cleanup if needed:

```bash
#!/bin/bash

REQUEST_ID=$1

# Load configuration
source /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/$REQUEST_ID/ETC/config.properties

# ============================================
# NEW: Check if this is a rerun from completed status
# ============================================
PREVIOUS_STATUS=$($CONNECTION_STRING -qtAX -c "
    SELECT previous_status
    FROM $REQUEST_TABLE
    WHERE request_id = $REQUEST_ID
")

CURRENT_STATUS=$($CONNECTION_STRING -qtAX -c "
    SELECT request_status
    FROM $REQUEST_TABLE
    WHERE request_id = $REQUEST_ID
")

echo "[INFO] Request ID: $REQUEST_ID"
echo "[INFO] Current Status: $CURRENT_STATUS"
echo "[INFO] Previous Status: $PREVIOUS_STATUS"

# ============================================
# If previous status was 'C' (Completed), perform cleanup
# ============================================
if [[ "$PREVIOUS_STATUS" == "C" && "$CURRENT_STATUS" == "RE" ]]; then
    echo "[INFO] This is a FULL RERUN from completed status - performing cleanup..."

    # Get the postback table name
    PB_TABLE=$($CONNECTION_STRING -qtAX -c "
        SELECT prev_week_pb_table
        FROM $QA_TABLE
        WHERE request_id = $REQUEST_ID
    ")

    if [[ -z "$PB_TABLE" ]]; then
        echo "[ERROR] Unable to fetch postback table name"
        $CONNECTION_STRING -c "
            UPDATE $REQUEST_TABLE
            SET request_status = 'E',
                request_desc = 'Unable to fetch postback table for cleanup'
            WHERE request_id = $REQUEST_ID
        "
        exit 1
    fi

    echo "[INFO] Postback table: $PB_TABLE"

    # Step 1: Delete unsubs from posted table
    echo "[INFO] Deleting unsubs from posted_unsub_hards table..."

    DELETE_RESULT=$($CONNECTION_STRING -vv -c "
        DELETE FROM $POSTED_UNSUB_HARDS_TABLE a
        USING $PB_TABLE b
        WHERE b.unsub_date IS NOT NULL
        AND a.email = b.email
    " 2>&1)

    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Failed to delete unsubs: $DELETE_RESULT"
        $CONNECTION_STRING -c "
            UPDATE $REQUEST_TABLE
            SET request_status = 'E',
                request_desc = 'Unable to delete unsubs from client table'
            WHERE request_id = $REQUEST_ID
        "
        exit 1
    fi

    DELETED_COUNT=$(echo "$DELETE_RESULT" | grep -oP 'DELETE \K\d+' || echo "0")
    echo "[INFO] Deleted $DELETED_COUNT unsub records from posted table"

    # Step 2: Drop required tables for full rerun
    echo "[INFO] Dropping tables for full rerun..."

    # Drop TRT tables
    $CONNECTION_STRING -c "DROP TABLE IF EXISTS $TRT_TABLE" 2>/dev/null
    echo "[INFO] Dropped TRT table: $TRT_TABLE"

    # Drop source table
    $CONNECTION_STRING -c "DROP TABLE IF EXISTS $SOURCE_TABLE" 2>/dev/null
    echo "[INFO] Dropped source table: $SOURCE_TABLE"

    # Drop postback table (will be recreated)
    $CONNECTION_STRING -c "DROP TABLE IF EXISTS $PB_TABLE" 2>/dev/null
    echo "[INFO] Dropped postback table: $PB_TABLE"

    # Reset QA stats
    $CONNECTION_STRING -c "
        UPDATE $QA_TABLE
        SET rltp_file_count = 0,
            unique_delivered_count = 0,
            totaldeliveredcount = 0
        WHERE request_id = $REQUEST_ID
    " 2>/dev/null
    echo "[INFO] Reset QA statistics"

    echo "[SUCCESS] Cleanup completed for full rerun"

else
    echo "[INFO] This is a PARTIAL RERUN from module - skipping full cleanup"

    # Drop only tables needed based on error_code
    ERROR_CODE=$($CONNECTION_STRING -qtAX -c "
        SELECT error_code
        FROM $REQUEST_TABLE
        WHERE request_id = $REQUEST_ID
    ")

    echo "[INFO] Error code: $ERROR_CODE - will start from module $ERROR_CODE"

    # Drop tables based on module (existing logic)
    case $ERROR_CODE in
        1)  # TRT module
            echo "[INFO] Dropping TRT table..."
            $CONNECTION_STRING -c "DROP TABLE IF EXISTS $TRT_TABLE" 2>/dev/null
            ;;
        2)  # Responders
            echo "[INFO] Dropping responders tables..."
            # Drop responder-specific tables
            ;;
        3)  # Suppression
            echo "[INFO] Dropping suppression tables..."
            # Drop suppression-specific tables
            ;;
        # ... other cases
    esac
fi

# ============================================
# Continue with normal request processing
# ============================================

echo "[INFO] Starting request processing from module $ERROR_CODE..."

# ... (rest of existing requestConsumer.sh logic)
```

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks "Edit" and selects rerun module                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend API: /update_request/<request_id>                  │
│                                                             │
│ 1. Get current request_status                              │
│ 2. Update all changed form fields                          │
│ 3. Set request_status = 'RE'                               │
│ 4. Set previous_status = <old_status>  ← NEW!             │
│ 5. Set error_code = <module_code>                          │
│ 6. Reset validation                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Request in queue with:                                      │
│ - request_status = 'RE'                                     │
│ - previous_status = 'C' or 'E' or other                    │
│ - error_code = 1-7                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ requestPicker.sh picks request (status IN ('W','RE','RW')) │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ requestValidation.py validates request                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ requestConsumer.sh starts                                   │
│                                                             │
│ Check: previous_status == 'C' && current_status == 'RE' ?  │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
    YES (Completed)    NO (Failed/Other)
        │                 │
        ▼                 ▼
┌─────────────────┐   ┌──────────────────────┐
│ FULL RERUN      │   │ PARTIAL RERUN        │
│                 │   │                      │
│ 1. Delete unsubs│   │ 1. Drop tables based │
│    from posted  │   │    on error_code     │
│    table        │   │                      │
│                 │   │ 2. Start from module │
│ 2. Drop ALL     │   │    (error_code)      │
│    tables (TRT, │   │                      │
│    source, PB)  │   └──────────────────────┘
│                 │
│ 3. Reset QA     │
│    stats        │
│                 │
│ 4. Start from   │
│    error_code   │
│    module       │
└─────────────────┘
        │
        └────────┬────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Process continues from specified module                     │
│ - Uses error_code to determine start point                 │
│ - Executes TRT, Responders, Suppression, etc.              │
│ - Updates status to 'R' (Running)                          │
│ - Eventually completes with 'C' or 'E'                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Database Changes

### New Column

```sql
ALTER TABLE apt_custom_postback_request_details_dnd
ADD COLUMN previous_status VARCHAR(5) NULL;
```

**Purpose**: Track the status before setting to 'RE', so backend knows cleanup requirements.

---

## 🎯 Benefits of Centralized Approach

### ✅ Advantages

1. **Single Status**: Only use 'RE' for all reruns (no RW vs RE confusion)
2. **Smart Cleanup**: Automatically determines cleanup based on previous status
3. **Consistent**: All reruns follow same path through API
4. **Auditable**: Can see previous status in database
5. **Flexible**: Can rerun from any module, with or without cleanup
6. **User-Friendly**: UI doesn't need to know about RW vs RE

### ✅ Logic Summary

| Previous Status | Current Status | Action |
|----------------|----------------|--------|
| `C` (Completed) | `RE` (Rerun) | **Full cleanup** + Drop tables + Start from module |
| `E` (Error) | `RE` (Rerun) | Drop required tables + Start from module |
| `R` (Running) | `RE` (Rerun) | Drop required tables + Start from module |
| `W` (Waiting) | `RE` (Rerun) | Drop required tables + Start from module |

---

## 🧪 Testing Scenarios

### Test 1: Rerun Completed Request (Full Rerun)

**Setup**:
1. Submit request, wait for completion (`status = 'C'`)
2. Edit request, select "TRT" module
3. Save

**Expected**:
- `previous_status` = `'C'`
- `request_status` = `'RE'`
- `error_code` = `1`

**Backend Actions**:
1. ✅ Delete unsubs from posted table
2. ✅ Drop TRT, source, postback tables
3. ✅ Reset QA stats
4. ✅ Start from TRT module
5. ✅ Full reprocessing

---

### Test 2: Rerun Failed Request (Partial Rerun)

**Setup**:
1. Submit request, let it fail at Suppression (`status = 'E'`, `error_code = 3`)
2. Edit request, fix suppression path, select "Suppression" module
3. Save

**Expected**:
- `previous_status` = `'E'`
- `request_status` = `'RE'`
- `error_code` = `3`

**Backend Actions**:
1. ✅ Drop suppression-specific tables only
2. ✅ Start from Suppression module
3. ✅ Partial reprocessing from that point

---

### Test 3: Rerun from Different Module

**Setup**:
1. Complete request (`status = 'C'`)
2. Edit, select "Responders" module (not TRT)
3. Save

**Expected**:
- `previous_status` = `'C'`
- `request_status` = `'RE'`
- `error_code` = `2`

**Backend Actions**:
1. ✅ Delete unsubs (because previous = 'C')
2. ✅ Drop ALL tables (full cleanup)
3. ✅ Reset QA stats
4. ✅ Start from Responders module (error_code = 2)

---

## 📋 Implementation Checklist

### Phase 1: Database Migration
- [ ] Add `previous_status` column to request table
- [ ] Test column addition in development
- [ ] Deploy to production

### Phase 2: API Updates
- [ ] Modify `update_request()` endpoint
- [ ] Add logic to capture current_status before update
- [ ] Store in `previous_status` field
- [ ] Test with completed and failed requests

### Phase 3: Backend Script Updates
- [ ] Update `requestConsumer.sh`
- [ ] Add previous_status check at start
- [ ] Implement full cleanup logic (delete unsubs, drop tables)
- [ ] Implement partial cleanup logic (drop module tables)
- [ ] Test both cleanup paths

### Phase 4: Testing
- [ ] Test rerun from completed request
- [ ] Test rerun from failed request
- [ ] Test different module selections
- [ ] Verify cleanup queries work correctly
- [ ] Verify table drops work correctly

### Phase 5: Documentation
- [ ] Update user guide
- [ ] Update API documentation
- [ ] Document cleanup logic for operations team

---

## 🚨 Important Notes

### Cleanup Queries

**Unsub deletion** is critical:
```sql
DELETE FROM apt_custom_posted_unsub_hards_dnd a
USING <postback_table> b
WHERE b.unsub_date IS NOT NULL
AND a.email = b.email;
```

**Why needed for completed requests**:
- Removes unsub records that were added during previous run
- Prevents duplicate unsub entries
- Ensures clean state for full reprocessing

### Table Drops

**Full rerun** (previous_status = 'C'):
- Drop TRT table
- Drop source preparation table
- Drop postback table
- Reset QA statistics

**Partial rerun** (previous_status = 'E' or other):
- Drop only tables related to error_code module
- Keep data from modules before the error point

---

## 🔄 Migration from Old Process

### Old System
```
Completed → Manual RW → Cleanup + Full rerun
Failed → Manual RE → Partial rerun from module
```

### New System
```
Any Status → Edit UI → RE (with previous_status) → Auto cleanup based on previous_status
```

**Backwards Compatibility**:
- Existing RW status in DB can be migrated: `UPDATE ... SET request_status = 'RE', previous_status = 'C' WHERE request_status = 'RW'`
- Existing RE status stays as-is (just add NULL previous_status)

---

## 💡 Future Enhancements

1. **Auto-detect failed module**: Set error_code automatically based on last successful module
2. **Cleanup preview**: Show user what will be cleaned up before execution
3. **Selective cleanup**: Let user choose which tables to drop
4. **Cleanup logs**: Store cleanup actions in separate log table

---

**Document Purpose**: Define centralized rerun logic that intelligently handles cleanup based on previous request status.

**Status**: Ready for implementation
**Priority**: High (improves robustness)
**Estimated Effort**: 4-6 hours
