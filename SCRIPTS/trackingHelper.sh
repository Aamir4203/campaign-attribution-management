#!/bin/bash
# trackingHelper.sh - Centralized Process Tracking Functions
# Source this file in each module script to use tracking functions

# Source configuration if not already loaded
if [ -z "$CONNECTION_STRING" ]; then
    source ./config.properties
fi

# Function to append current process ID to tracking table
append_process_id() {
    local request_id=$1
    local module_name=$2
    local current_pid=$$

    # Check if record exists - extract only the count number
    existing_count=$($CONNECTION_STRING -qtAX -c "
        SELECT COUNT(1)
        FROM $TRACKING_TABLE
        WHERE request_id=$request_id
    " 2>/dev/null)

    # Default to 0 if no number found
    existing_count=${existing_count:-0}

    if [ "$existing_count" -eq 0 ]; then
        # Create new record
        $CONNECTION_STRING -c "
            INSERT INTO $TRACKING_TABLE
            (request_id, process_ids, module_sequence, current_module, start_time, last_updated, status, created_by)
            VALUES ($request_id, '$current_pid', '$module_name', '$module_name', NOW(), NOW(), 'RUNNING', '$USER')
        " 2>/dev/null
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
    affected_rows=$($CONNECTION_STRING -qtAX -c "
        SELECT COUNT(1) FROM $TRACKING_TABLE WHERE request_id = $request_id
    " 2>/dev/null)

    # Default to 0 if no number found
    affected_rows=${affected_rows:-0}

    if [ "$affected_rows" -eq 0 ]; then
        $CONNECTION_STRING -c "
            INSERT INTO $TRACKING_TABLE
            (request_id, process_ids, module_sequence, current_module, start_time, last_updated, status, host_server, created_by)
            VALUES ($request_id, '$current_pid', '$module_name', '$module_name', NOW(), NOW(), 'RUNNING', '$(hostname)', '$USER')
        " 2>/dev/null
    fi
}

# Function to mark request as completed
mark_request_completed() {
    local request_id=$1

    # Update main request table
    $CONNECTION_STRING -c "
        UPDATE $REQUEST_TABLE
        SET request_status = 'C',
            request_desc = 'Request Completed',
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
}
