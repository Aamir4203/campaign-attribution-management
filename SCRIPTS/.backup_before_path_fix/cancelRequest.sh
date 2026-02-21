#!/bin/bash
# cancelRequest.sh - Professional request cancellation script
# Usage: ./cancelRequest.sh <request_id>
#
# NOTE: W (Waiting) state requests are handled directly by the API
# and do not reach this script. This script only handles running requests.

REQUEST_ID=$1

if [ -z "$REQUEST_ID" ]; then
    echo "ERROR: Request ID required"
    echo "Usage: $0 <request_id>"
    exit 1
fi

# Source database configuration from request-specific ETC directory (standard pattern)
source /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/$REQUEST_ID/ETC/config.properties

# Create request-specific logs directory if it doesn't exist
mkdir -p "$LOGPATH"


# Simple logging function
log_message() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$message" >> "$CANCEL_LOG_FILE"
}

# Function to terminate database connections for a request
terminate_db_connections() {
    local request_id=$1
    local verify_termination=${2:-true}

    # Get PIDs of database connections running queries related to this request
    local db_pids=$($CONNECTION_STRING -qtAX -c "
        SELECT pid
        FROM pg_stat_activity
        WHERE query LIKE '%$request_id%'
        AND query NOT LIKE '%pg_stat_activity%'
        AND state = 'active'
    " 2>/dev/null | xargs)

    local db_killed_count=0

    if [ ! -z "$db_pids" ]; then
        # Terminate each database connection
        for db_pid in $db_pids; do
            if [ ! -z "$db_pid" ] && [ "$db_pid" -gt 0 ] 2>/dev/null; then
                $CONNECTION_STRING -c "SELECT pg_terminate_backend($db_pid);" 2>/dev/null

                if [ "$verify_termination" = "true" ]; then
                    sleep 1
                    local still_exists=$($CONNECTION_STRING -qtAX -c "
                        SELECT COUNT(*) FROM pg_stat_activity WHERE pid = $db_pid
                    " 2>/dev/null)

                    if [ "$still_exists" = "0" ]; then
                        ((db_killed_count++))
                    fi
                else
                    ((db_killed_count++))
                fi
            fi
        done
    fi

    echo $db_killed_count
}

# Function to update request status to cancelled
update_request_status() {
    local request_id=$1
    local update_tracking=${2:-true}
    local status_desc=${3:-"Cancelled"}

    # Update main request table
    $CONNECTION_STRING -c "
        UPDATE $REQUEST_TABLE
        SET request_status = 'E',
            request_desc = '$status_desc',
            request_end_time = NOW()
        WHERE request_id = $request_id
        AND request_status IN ('W', 'R', 'RE','RW')
    " 2>/dev/null

    # Update tracking table if requested
    if [ "$update_tracking" = "true" ]; then
        $CONNECTION_STRING -c "
            UPDATE $TRACKING_TABLE
            SET status = 'Killed',
                current_module = 'Cancelled',
                last_updated = NOW()
            WHERE request_id = $request_id
        " 2>/dev/null
    fi
}

# Get comma-separated PIDs from tracking table
PIDS=$($CONNECTION_STRING -qtAX -c "
    SELECT process_ids
    FROM $TRACKING_TABLE
    WHERE request_id = $REQUEST_ID
    AND status = 'Running'
" 2>/dev/null)

# Clean up the result (remove whitespace)
PIDS=$(echo "$PIDS" | xargs)

if [ -z "$PIDS" ] || [ "$PIDS" = "" ]; then
    # Fallback: Search running processes manually
    MANUAL_PIDS=$(ps -aef | grep "$REQUEST_ID" | grep -E "(requestConsumer|trtPreparation|rltpDataPulling|suppressionList|delete_partitions|srcPreparation|partitioningSrc|deliveredScript|consumerDeliveredScript|timestampAppending|ipAppending)" | grep -v grep | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')

    if [ ! -z "$MANUAL_PIDS" ]; then
        PIDS=$MANUAL_PIDS
    else
        # Check for any database connections still running for this request
        terminate_db_connections $REQUEST_ID false

        # Update status to cancelled anyway (might be in database queue)
        update_request_status $REQUEST_ID false "Cancelled"

        exit 0
    fi
fi

# Convert comma-separated PIDs to array
IFS=',' read -ra PID_ARRAY <<< "$PIDS"

# Kill each process with child process handling and validation
KILLED_COUNT=0
SKIPPED_COUNT=0
for pid in "${PID_ARRAY[@]}"; do
    # Remove any whitespace
    pid=$(echo "$pid" | xargs)

    if [ ! -z "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        # Check if process exists
        if ps -p $pid > /dev/null 2>&1; then
            # Validate process belongs to our request (safety check for PID reuse)
            process_args=$(ps -p $pid -o args --no-headers 2>/dev/null)

            # Check if process is related to our request ID
            if echo "$process_args" | grep -q "$REQUEST_ID"; then
                # Find and kill child processes first
                children=$(ps -o pid --ppid $pid --no-headers 2>/dev/null | xargs)
                if [ ! -z "$children" ]; then
                    kill -9 $children 2>/dev/null
                fi

                # Kill main process
                kill -9 $pid 2>/dev/null

                # Wait and verify
                sleep 1
                if ! ps -p $pid > /dev/null 2>&1; then
                    ((KILLED_COUNT++))
                else
                    log_message "WARNING: Process $pid might still be running"
                fi
            else
                # PID exists but doesn't belong to our request (PID reuse case)
                log_message "WARNING: Process $pid doesn't belong to request $REQUEST_ID"
                ((SKIPPED_COUNT++))
            fi
        fi
    fi
done


# Update database status
# Terminate any database connections/queries still running for this request
DB_KILLED_COUNT=$(terminate_db_connections $REQUEST_ID true)

# Update request status and tracking table
update_request_status $REQUEST_ID true "Cancelled"


exit 0
