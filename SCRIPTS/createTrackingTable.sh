#!/bin/bash
# createTrackingTable.sh - Create process tracking table in database
# Run this once to set up the tracking table

# Source configuration
source ./config.properties

echo "==========================================="
echo "    TRACKING TABLE CREATION SCRIPT"
echo "    Time: $(date)"
echo "==========================================="

# Create the tracking table
echo "Creating $TRACKING_TABLE table..."

$CONNECTION_STRING -c "
CREATE TABLE IF NOT EXISTS $TRACKING_TABLE (
    request_id INTEGER PRIMARY KEY,
    process_ids VARCHAR(1000),
    module_sequence VARCHAR(500),
    current_module VARCHAR(50),
    start_time TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),
    status VARCHAR(10) DEFAULT 'RUNNING',
    host_server VARCHAR(50) DEFAULT '$(hostname)',
    created_by VARCHAR(50) DEFAULT '$USER'
);
"

# Check if table was created successfully
if [ $? -eq 0 ]; then
    echo "✅ Table $TRACKING_TABLE created successfully!"

    # Create index for better performance
    echo "Creating indexes..."

    $CONNECTION_STRING -c "
    CREATE INDEX IF NOT EXISTS idx_tracking_request_id ON $TRACKING_TABLE(request_id);
    CREATE INDEX IF NOT EXISTS idx_tracking_status ON $TRACKING_TABLE(status);
    CREATE INDEX IF NOT EXISTS idx_tracking_module ON $TRACKING_TABLE(current_module);
    "

    if [ $? -eq 0 ]; then
        echo "✅ Indexes created successfully!"
    else
        echo "⚠️ Warning: Could not create indexes"
    fi

    # Show table structure
    echo ""
    echo "Table structure:"
    $CONNECTION_STRING -c "\d $TRACKING_TABLE"

    echo ""
    echo "==========================================="
    echo "    TABLE CREATION COMPLETE"
    echo "    Table: $TRACKING_TABLE"
    echo "    Status: READY FOR USE"
    echo "==========================================="

else
    echo "❌ Error: Could not create table $TRACKING_TABLE"
    exit 1
fi
