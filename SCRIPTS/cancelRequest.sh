#!/bin/bash
# cancelRequest.sh - Professional request cancellation script
# Usage: ./cancelRequest.sh <request_id>

REQUEST_ID=$1

if [ -z "$REQUEST_ID" ]; then
    echo "ERROR: Request ID required"
    echo "Usage: $0 <request_id>"
    exit 1
fi

# Source database configuration
source ./config.properties

# Create request-specific logs directory if it doesn't exist
mkdir -p "$LOGPATH"

echo "==========================================="
echo "    REQUEST CANCELLATION SYSTEM"
echo "    Request ID: $REQUEST_ID"
echo "    Time: $(date)"
echo "    Log File: $CANCEL_LOG_FILE"
echo "==========================================="

# Enhanced logging function that writes to both console and log file
log_message() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$message"
    echo "$message" >> "$CANCEL_LOG_FILE"
}

# Get comma-separated PIDs from tracking table
log_message "Retrieving process information for request $REQUEST_ID"

PIDS=$($CONNECTION_STRING -t -c "
    SELECT process_ids
    FROM $TRACKING_TABLE
    WHERE request_id = $REQUEST_ID
    AND status = 'RUNNING'
" 2>/dev/null)

# Clean up the result (remove whitespace)
PIDS=$(echo "$PIDS" | xargs)

if [ -z "$PIDS" ] || [ "$PIDS" = "" ]; then
    log_message "No running processes found for request $REQUEST_ID in tracking table"

    # Fallback: Search running processes manually
    log_message "Searching for processes manually..."
    MANUAL_PIDS=$(ps -aef | grep "$REQUEST_ID" | grep -E "(requestConsumer|trtPreparation|suppressionList|srcPreparation|deliveredScript|timestampAppending|ipAppending)" | grep -v grep | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')

    if [ ! -z "$MANUAL_PIDS" ]; then
        PIDS=$MANUAL_PIDS
        log_message "Found processes manually: $PIDS"
    else
        log_message "No active processes found for request $REQUEST_ID"

        # Check for any database connections still running for this request
        log_message "Checking for active database connections..."
        DB_PIDS=$($CONNECTION_STRING -t -c "
            SELECT pid
            FROM pg_stat_activity
            WHERE query LIKE '%$REQUEST_ID%'
            AND query NOT LIKE '%pg_stat_activity%'
            AND state = 'active'
        " 2>/dev/null | xargs)

        if [ ! -z "$DB_PIDS" ]; then
            log_message "Found active database connections: $DB_PIDS - terminating..."

            for db_pid in $DB_PIDS; do
                if [ ! -z "$db_pid" ] && [ "$db_pid" -gt 0 ] 2>/dev/null; then
                    log_message "Terminating database connection PID: $db_pid"
                    $CONNECTION_STRING -c "SELECT pg_terminate_backend($db_pid);" 2>/dev/null
                fi
            done

            log_message "Database connections terminated"
        else
            log_message "No active database connections found"
        fi

        # Update status to cancelled anyway (might be in database queue)
        $CONNECTION_STRING -c "
            UPDATE $REQUEST_TABLE
            SET request_status = 'E',
                request_desc = 'Cancelled by User (No Active Processes)',
                request_end_time = NOW()
            WHERE request_id = $REQUEST_ID
            AND request_status IN ('W', 'R', 'RE')
        " 2>/dev/null

        log_message "SUCCESS: Request $REQUEST_ID marked as cancelled"
        exit 0
    fi
fi

# Convert comma-separated PIDs to array
IFS=',' read -ra PID_ARRAY <<< "$PIDS"

log_message "Found ${#PID_ARRAY[@]} process(es) to kill: $PIDS"

# Kill each process with child process handling
KILLED_COUNT=0
for pid in "${PID_ARRAY[@]}"; do
    # Remove any whitespace
    pid=$(echo "$pid" | xargs)

    if [ ! -z "$pid" ] && [ "$pid" -gt 0 ] 2>/dev/null; then
        # Check if process exists
        if ps -p $pid > /dev/null 2>&1; then
            log_message "Killing process $pid and its children..."

            # Find and kill child processes first
            children=$(ps -o pid --ppid $pid --no-headers 2>/dev/null | xargs)
            if [ ! -z "$children" ]; then
                log_message "Killing child processes: $children"
                kill -9 $children 2>/dev/null
            fi

            # Kill main process
            kill -9 $pid 2>/dev/null

            # Wait and verify
            sleep 1
            if ! ps -p $pid > /dev/null 2>&1; then
                log_message "Process $pid killed successfully"
                ((KILLED_COUNT++))
            else
                log_message "WARNING: Process $pid might still be running"
            fi
        else
            log_message "Process $pid not found (already terminated)"
        fi
    fi
done

# Update database status
log_message "Updating database status..."

# Terminate any database connections/queries still running for this request
log_message "Checking for active database connections for request $REQUEST_ID..."

# Get PIDs of database connections running queries related to this request
DB_PIDS=$($CONNECTION_STRING -t -c "
    SELECT pid
    FROM pg_stat_activity
    WHERE query LIKE '%$REQUEST_ID%'
    AND query NOT LIKE '%pg_stat_activity%'
    AND state = 'active'
" 2>/dev/null | xargs)

DB_KILLED_COUNT=0
if [ ! -z "$DB_PIDS" ]; then
    log_message "Found active database connections: $DB_PIDS"

    # Terminate each database connection
    for db_pid in $DB_PIDS; do
        if [ ! -z "$db_pid" ] && [ "$db_pid" -gt 0 ] 2>/dev/null; then
            log_message "Terminating database connection PID: $db_pid"
            $CONNECTION_STRING -c "SELECT pg_terminate_backend($db_pid);" 2>/dev/null

            # Wait a moment for termination
            sleep 1

            # Check if connection still exists
            STILL_EXISTS=$($CONNECTION_STRING -t -c "
                SELECT COUNT(*) FROM pg_stat_activity WHERE pid = $db_pid
            " 2>/dev/null | xargs)

            if [ "$STILL_EXISTS" = "0" ]; then
                log_message "Database connection $db_pid terminated successfully"
                ((DB_KILLED_COUNT++))
            else
                log_message "WARNING: Database connection $db_pid might still be active"
            fi
        fi
    done
else
    log_message "No active database connections found for request $REQUEST_ID"
fi

# Update main request table
$CONNECTION_STRING -c "
    UPDATE $REQUEST_TABLE
    SET request_status = 'E',
        request_desc = 'Cancelled by User - $KILLED_COUNT processes killed',
        request_end_time = NOW()
    WHERE request_id = $REQUEST_ID
" 2>/dev/null

# Update tracking table
$CONNECTION_STRING -c "
    UPDATE $TRACKING_TABLE
    SET status = 'KILLED',
        current_module = 'CANCELLED',
        last_updated = NOW()
    WHERE request_id = $REQUEST_ID
" 2>/dev/null

log_message "Database updated successfully"

log_message "=========================================="
log_message "    CANCELLATION COMPLETE"
log_message "    Request ID: $REQUEST_ID"
log_message "    Processes Killed: $KILLED_COUNT"
log_message "    Database Connections Terminated: $DB_KILLED_COUNT"
log_message "    Status: CANCELLED"
log_message "=========================================="

exit 0
