#!/bin/bash

# requestPicker.sh - Picks and validates new requests for processing
# Sources centralized configuration

MAIN_PATH="/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management"
source "$MAIN_PATH/SCRIPTS/config.properties"

# Check running request count
running_request_count=$($CONNECTION_STRING -qtAX -c "select count(request_id) from $REQUEST_TABLE where upper(request_status)='R'")

if [[ $? -ne 0 ]]; then
    echo "ERROR: UNABLE TO CONNECT POSTGRES DB SERVER"

    # Create temp directory if needed and log error
    mkdir -p "$MAIN_PATH/TMP"
    echo "ERROR: UNABLE TO CONNECT POSTGRES DB SERVER at $(date)" > "$MAIN_PATH/TMP/db_error.log"

    # Send alert email
    if [ -n "$ALERT_TO" ]; then
        echo -e "Database connection failed at $(date)\n\nPlease check database connectivity." | \
            mail -r "$ALERT_SENDER" -s "APT: Database Connection Error" $ALERT_TO
    fi
    exit 1
fi

# Check if we can pick new requests (limit to 10 running requests)
if [[ $running_request_count -lt 8 ]]; then

    # Pick next request in queue
    new_request_id=$($CONNECTION_STRING -qtAX -c \
        "select request_id from $REQUEST_TABLE \
         where upper(request_status) in ('W','RE','RW') \
         and (request_validation is null or upper(request_validation)='Y') \
         order by request_id limit 1")

    if [[ -n "$new_request_id" ]]; then
        echo "Picked request_id=$new_request_id for processing"

        # Run validation
        "$MAIN_PATH/CAM_Env/bin/python3" "$MAIN_SCRIPTS/requestValidation.py" "$new_request_id"

        if [[ $? -eq 0 ]]; then
            # Check validation status
            validation_status=$($CONNECTION_STRING -qtAX -c \
                "select upper(request_validation) from $REQUEST_TABLE where request_id=$new_request_id")

            if [[ $validation_status == 'Y' ]]; then
                echo "Validation passed for request_id=$new_request_id"
                # Start request processing
                sh -x "$MAIN_SCRIPTS/requestConsumer.sh" "$new_request_id"
            else
                echo "Validation failed for request_id=$new_request_id (status: $validation_status)"
            fi
        else
            echo "ERROR: Request Validation Script Execution Failed for request_id=$new_request_id"

            # Send alert email
            if [ -n "$ALERT_TO" ]; then
                echo -e "Request validation script failed for request_id=$new_request_id at $(date)\n\nPlease check validation logs." | \
                    mail -r "$ALERT_SENDER" -s "APT: Validation Failed" $ALERT_TO
            fi
        fi
    else
        echo "No requests in queue (W, RE, or RW status)"
    fi
else
    echo "Maximum concurrent requests reached ($running_request_count running, limit is 10)"
fi
