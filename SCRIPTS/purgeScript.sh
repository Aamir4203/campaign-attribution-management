#!/bin/bash

# purgeScript.sh - Purges old requests and backs up data to S3
# Sources centralized configuration

MAIN_PATH="/u1/techteam/PFM_CUSTOM_SCRIPTS/Campaign-Attribution-Management"
source "$MAIN_PATH/SCRIPTS/config.properties"

HOMEPATH=$MAIN_PATH
SPOOLPATH=$HOMEPATH/PURGED_DATA
BKP_PATH=$HOMEPATH/PURGED_DATA

# Create required directories
mkdir -p "$SPOOLPATH"
mkdir -p "$MAIN_PATH/BKP"

echo "START TIME :: $(date)"

#=== CLIENT TABLE BACKUP ===#
echo "Backing up core tables..."

$CONNECTION_STRING -F'|' --pset footer -X -A -c "select * from $CLIENT_TABLE" > "$MAIN_PATH/BKP/$CLIENT_TABLE"
if [[ $? -ne 0 ]]; then
    echo "ERROR: Failed to backup $CLIENT_TABLE"
    echo -e "Hi Team,\n\nFailed to backup $CLIENT_TABLE.\n\nThanks,\nDataAttribution" | \
        mail -r "$ALERT_SENDER" -s "PURGING ERROR: Backup Failed" "$ALERT_TO"
    exit 1
fi

$CONNECTION_STRING -F'|' --pset footer -X -A -c "select * from $REQUEST_TABLE" > "$MAIN_PATH/BKP/$REQUEST_TABLE"
$CONNECTION_STRING -F'|' --pset footer -X -A -c "select * from $OLD_IP_TABLE" > "$MAIN_PATH/BKP/$OLD_IP_TABLE"
$CONNECTION_STRING -F'|' --pset footer -X -A -c "select * from $NEW_IP_TABLE" > "$MAIN_PATH/BKP/$NEW_IP_TABLE"

echo "Uploading backups to S3..."
/usr/local/bin/aws s3 cp "$MAIN_PATH/BKP/" s3://new-datateam/Campaign-Attribution-Management/IMP_FILES/ --recursive

if [[ $? -ne 0 ]]; then
    echo "WARNING: S3 upload failed for core table backups"
    echo -e "Hi Team,\n\nS3 upload failed for core table backups.\n\nThanks,\nDataAttribution" | \
        mail -r "$ALERT_SENDER" -s "PURGING WARNING: S3 Upload Failed" "$ALERT_TO"
fi

#=== BACKUP UNSUB TABLES ===#
echo "Fetching unsub tables list..."

$CONNECTION_STRING -qtAX -c "select posted_unsub_hards_table from $CLIENT_TABLE" > "$SPOOLPATH/unsub_files"

if [ $? -ne 0 ]; then
    echo "ERROR: Unable to fetch posted_unsub_hards_table data"
    echo -e "Hi Team,\n\nUnable to fetch posted_unsub_hards_table data from Client Table.\n\nThanks,\nDataAttribution" | \
        mail -r "$ALERT_SENDER" -s "PURGING ERROR: Client Table Query Failed" "$ALERT_TO"
    exit 1
fi

echo "Backing up unsub tables..."
while read -r file; do
    if [[ -n "$file" ]]; then
        echo "  Backing up $file..."
        $CONNECTION_STRING -qAX --pset footer -c "select * from $file" > "$BKP_PATH/$file"

        if [[ $? -eq 0 ]]; then
            /usr/local/bin/aws s3 cp "$BKP_PATH/$file" s3://new-datateam/Campaign-Attribution-Management/IMP_FILES/POSTED_UNSUBS/
            if [[ $? -eq 0 ]]; then
                rm -f "$BKP_PATH/$file"
            fi
        fi
    fi
done < "$SPOOLPATH/unsub_files"

#=== PURGE OLD REQUESTS ===#
echo "Fetching requests to purge (older than 45 days)..."

$CONNECTION_STRING -qtAX -c \
    "select request_id,client_id,upper(week) from $REQUEST_TABLE \
     where request_start_time<(CURRENT_DATE - INTERVAL '45 days') \
     and purged=0 and request_status='C'" > "$SPOOLPATH/request_id.txt"

if [ $? -ne 0 ]; then
    echo "ERROR: Unable to fetch data from Request Table"
    echo -e "Hi Team,\n\nUnable to fetch data from Request Table.\n\nThanks,\nDataAttribution" | \
        mail -r "$ALERT_SENDER" -s "PURGING ERROR: Request Table Query Failed" "$ALERT_TO"
    exit 1
fi

if [ -s "$SPOOLPATH/request_id.txt" ]; then
    echo "Processing requests for purging..."

    while read -r line; do
        REQUEST_ID=$(echo "$line" | cut -d'|' -f1)
        CLIENT_ID=$(echo "$line" | cut -d'|' -f2)
        WEEK=$(echo "$line" | cut -d'|' -f3)

        echo "  Processing request_id=$REQUEST_ID..."

        CLIENT_NAME=$($CONNECTION_STRING -qtAX -c \
            "select upper(client_name) from $CLIENT_TABLE where client_id=$CLIENT_ID")

        if [ $? -ne 0 ]; then
            echo "ERROR: Unable to fetch client name for client_id=$CLIENT_ID"
            echo -e "Hi Team,\n\nUnable to fetch client name for client_id=$CLIENT_ID.\n\nThanks,\nDataAttribution" | \
                mail -r "$ALERT_SENDER" -s "PURGING ERROR: Client Name Fetch Failed" "$ALERT_TO"
            continue
        fi

        GEN_TABLE="APT_CUSTOM_${REQUEST_ID}_${CLIENT_NAME}_GEN_TABLE"
        POSTBACK_TABLE="APT_CUSTOM_${REQUEST_ID}_${CLIENT_NAME}_${WEEK}_POSTBACK_TABLE"

        #=== BACKUP AND DROP GEN_TABLE ===#
        echo "    Backing up $GEN_TABLE..."
        $CONNECTION_STRING -qAX --pset footer -c "select * from $GEN_TABLE" > "$BKP_PATH/$GEN_TABLE" 2>/dev/null
        $CONNECTION_STRING -c "DROP TABLE IF EXISTS $GEN_TABLE" 2>/dev/null

        #=== BACKUP AND DROP POSTBACK_TABLE ===#
        echo "    Backing up $POSTBACK_TABLE..."
        $CONNECTION_STRING -qAX --pset footer -c "select * from $POSTBACK_TABLE" > "$BKP_PATH/$POSTBACK_TABLE" 2>/dev/null
        $CONNECTION_STRING -c "DROP TABLE IF EXISTS $POSTBACK_TABLE" 2>/dev/null

        #=== COMPRESS AND UPLOAD TO S3 ===#
        if [[ -f "$BKP_PATH/$GEN_TABLE" ]] || [[ -f "$BKP_PATH/$POSTBACK_TABLE" ]]; then
            echo "    Compressing and uploading to S3..."
            gzip -f "$BKP_PATH/$GEN_TABLE" 2>/dev/null
            gzip -f "$BKP_PATH/$POSTBACK_TABLE" 2>/dev/null

            /usr/local/bin/aws s3 cp "$BKP_PATH/$GEN_TABLE.gz" \
                s3://new-datateam/Campaign-Attribution-Management/$REQUEST_ID/ 2>/dev/null

            /usr/local/bin/aws s3 cp "$BKP_PATH/$POSTBACK_TABLE.gz" \
                s3://new-datateam/Campaign-Attribution-Management/$REQUEST_ID/ 2>/dev/null

            if [[ $? -eq 0 ]]; then
                # Safe cleanup - only remove specific files
                rm -f "$BKP_PATH/$GEN_TABLE.gz" "$BKP_PATH/$POSTBACK_TABLE.gz"
            fi
        fi

        #=== UPDATE PURGED STATUS ===#
        $CONNECTION_STRING -c "UPDATE $REQUEST_TABLE SET purged=1 WHERE request_id=$REQUEST_ID"

        if [ $? -ne 0 ]; then
            echo "ERROR: Unable to update purged status for request_id=$REQUEST_ID"
            echo -e "Hi Team,\n\nUnable to update purged status for request_id=$REQUEST_ID.\n\nThanks,\nDataAttribution" | \
                mail -r "$ALERT_SENDER" -s "PURGING ERROR: Update Failed" "$ALERT_TO"
            continue
        fi

        #=== CLEANUP REQUEST DIRECTORY ===#
        REQUEST_DIR="$MAIN_PATH/REQUEST_PROCESSING/$REQUEST_ID"
        if [ -d "$REQUEST_DIR" ]; then
            echo "    Removing request directory: $REQUEST_DIR"
            rm -rf "$REQUEST_DIR"
            echo "    Directory successfully deleted."
        else
            echo "    Directory not found or already deleted."
        fi

    done < "$SPOOLPATH/request_id.txt"

    echo "Purging completed successfully."
else
    echo "No requests found to purge."
fi

echo "END TIME :: $(date)"
