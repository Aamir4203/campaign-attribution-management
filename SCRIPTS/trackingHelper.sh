#!/bin/bash
# trackingHelper.sh - Centralized Process Tracking Functions
# Source this file in each module script to use tracking functions

# Function to append current process ID to tracking table
append_process_id() {
    local request_id=$1
    local module_name=$2
    local current_pid=$$

    # Check if record exists
    existing_count=$($CONNECTION_STRING -t -c "
        SELECT COUNT(1)
        FROM $TRACKING_TABLE
        WHERE request_id=$request_id
    " 2>/dev/null | xargs)

    if [ "$existing_count" -eq 0 ]; then
        # Create new record
        $CONNECTION_STRING -c "
            INSERT INTO $TRACKING_TABLE
            (request_id, process_ids, module_sequence, current_module, start_time, last_updated, status, host_server, created_by)
            VALUES ($request_id, '$current_pid', '$module_name', '$module_name', NOW(), NOW(), 'RUNNING', '$(hostname)', '$USER')
        " 2>/dev/null

        echo "[$(date)] New tracking record created for request $request_id, PID: $current_pid, Module: $module_name" >> "$CANCEL_LOG_FILE"
    else
        # Update existing record - append PID
        $CONNECTION_STRING -c "
            UPDATE $TRACKING_TABLE
            SET process_ids = CASE
                    WHEN process_ids IS NULL OR process_ids = ''
                    THEN '$current_pid'
                    ELSE process_ids || ',$current_pid'
                END,
                module_sequence = CASE
                    WHEN module_sequence IS NULL OR module_sequence = ''
                    THEN '$module_name'
                    ELSE module_sequence || ',$module_name'
                END,
                current_module = '$module_name',
                last_updated = NOW(),
                status = 'RUNNING'
            WHERE request_id = $request_id
        " 2>/dev/null

        echo "[$(date)] Updated tracking record for request $request_id, added PID: $current_pid, Module: $module_name" >> "$CANCEL_LOG_FILE"
    fi
}

# Function to clear and restart tracking for re-run requests
clear_and_restart_tracking() {
    local request_id=$1
    local module_name=$2
    local current_pid=$$

    # Clear existing PIDs and restart tracking
    $CONNECTION_STRING -c "
        UPDATE $TRACKING_TABLE
        SET process_ids = '$current_pid',
            module_sequence = '$module_name',
            current_module = '$module_name',
            start_time = NOW(),
            last_updated = NOW(),
            status = 'RUNNING'
        WHERE request_id = $request_id
    " 2>/dev/null

    # If no existing record (shouldn't happen in re-run, but safety)
    affected_rows=$($CONNECTION_STRING -t -c "
        SELECT COUNT(1) FROM $TRACKING_TABLE WHERE request_id = $request_id
    " 2>/dev/null | xargs)

    if [ "$affected_rows" -eq 0 ]; then
        $CONNECTION_STRING -c "
            INSERT INTO $TRACKING_TABLE
            (request_id, process_ids, module_sequence, current_module, start_time, last_updated, status, host_server, created_by)
            VALUES ($request_id, '$current_pid', '$module_name', '$module_name', NOW(), NOW(), 'RUNNING', '$(hostname)', '$USER')
        " 2>/dev/null
    fi

    echo "[$(date)] Cleared and restarted tracking for request $request_id, PID: $current_pid, Module: $module_name" >> "$CANCEL_LOG_FILE"
}

# Function to mark request as completed
mark_request_completed() {
    local request_id=$1

    # Update main request table
    $CONNECTION_STRING -c "
        UPDATE $REQUEST_TABLE
        SET request_status = 'C',
            request_desc = 'Completed Successfully',
            request_end_time = NOW()
        WHERE request_id = $request_id
    " 2>/dev/null

    # Update tracking table
    $CONNECTION_STRING -c "
        UPDATE $TRACKING_TABLE
        SET status = 'COMPLETED',
            current_module = 'FINISHED',
            last_updated = NOW()
        WHERE request_id = $request_id
    " 2>/dev/null

    echo "[$(date)] Request $request_id marked as completed" >> "$CANCEL_LOG_FILE"
}

# Function to mark request as failed/error
mark_request_failed() {
    local request_id=$1
    local error_module=$2
    local error_desc="$3"

    # Update main request table
    $CONNECTION_STRING -c "
        UPDATE $REQUEST_TABLE
        SET request_status = 'E',
            request_desc = '$error_desc',
            request_end_time = NOW()
        WHERE request_id = $request_id
    " 2>/dev/null

    # Update tracking table
    $CONNECTION_STRING -c "
        UPDATE $TRACKING_TABLE
        SET status = 'ERROR',
            current_module = '$error_module',
            last_updated = NOW()
        WHERE request_id = $request_id
    " 2>/dev/null

    echo "[$(date)] Request $request_id marked as failed in module: $error_module" >> "$CANCEL_LOG_FILE"
}
