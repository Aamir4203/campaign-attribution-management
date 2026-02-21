-- ============================================================================
-- SNOWFLAKE STAGING TEST QUERIES
-- ============================================================================
-- Use these queries to validate the staging implementation in rltpDataPulling_v2.py
--
-- Run these queries in Snowflake while the script is executing to see stages
-- being created, used, and cleaned up in real-time.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. CHECK IF STAGES ARE CREATED
-- ----------------------------------------------------------------------------
-- Run this DURING script execution to see active stages
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- Expected output: Should show one or more stages like:
-- apt_rltp_temp_stage_req12345_dec1_pid98765
-- apt_rltp_temp_stage_req12345_dec2_pid98766
-- etc.

-- Run this AFTER script completes - should be empty (all cleaned up)
SHOW STAGES LIKE 'apt_rltp_temp_stage%';


-- ----------------------------------------------------------------------------
-- 2. LIST ALL TEMPORARY STAGES (More Details)
-- ----------------------------------------------------------------------------
SHOW TEMPORARY STAGES IN SCHEMA;

-- Or with filtering
SHOW TEMPORARY STAGES LIKE 'apt_rltp%' IN SCHEMA;


-- ----------------------------------------------------------------------------
-- 3. CHECK STAGE CONTENTS (Files in Stage)
-- ----------------------------------------------------------------------------
-- Replace with actual stage name from logs or SHOW STAGES output
LIST @apt_rltp_temp_stage_req12345_dec1_pid98765;

-- Expected output: Shows CSV.GZ files like:
-- decile_1_0_0_0.csv.gz | 1234567 | md5hash | timestamp

-- Check specific file pattern
LIST @apt_rltp_temp_stage_req12345_dec1_pid98765/decile_1*;


-- ----------------------------------------------------------------------------
-- 4. CHECK STAGE FILE SIZE AND COUNT
-- ----------------------------------------------------------------------------
-- See how many files and total size
LIST @apt_rltp_temp_stage_req12345_dec1_pid98765;

-- Get aggregated info
SELECT
    COUNT(*) as file_count,
    SUM(size) as total_bytes,
    SUM(size) / 1024 / 1024 as total_mb,
    SUM(size) / 1024 / 1024 / 1024 as total_gb
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));


-- ----------------------------------------------------------------------------
-- 5. MANUALLY TEST STAGE CREATION (Simulate Script Behavior)
-- ----------------------------------------------------------------------------
-- Create a test stage (like the script does)
CREATE TEMPORARY STAGE IF NOT EXISTS test_apt_rltp_stage
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '|'
    COMPRESSION = 'GZIP'
    RECORD_DELIMITER = '\n'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    ESCAPE_UNENCLOSED_FIELD = NONE
);

-- Verify it was created
SHOW STAGES LIKE 'test_apt_rltp_stage';

-- Drop it (cleanup)
DROP STAGE IF EXISTS test_apt_rltp_stage;


-- ----------------------------------------------------------------------------
-- 6. TEST DATA EXPORT TO STAGE (Full Simulation)
-- ----------------------------------------------------------------------------
-- Example: Export sample data to stage
-- Replace with your actual RLTP query

-- Step 1: Create stage
CREATE TEMPORARY STAGE IF NOT EXISTS test_export_stage
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '|'
    COMPRESSION = 'GZIP'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    ESCAPE_UNENCLOSED_FIELD = NONE
);

-- Step 2: Export data to stage (replace with your actual query)
COPY INTO @test_export_stage/test_file
FROM (
    SELECT
        'md5hash123' as md5hash,
        'test@example.com' as email,
        'segment1' as segment,
        'subseg1' as subseg,
        '1' as decile,
        '5' as priority
    LIMIT 1000
)
MAX_FILE_SIZE = 500000000
OVERWRITE = TRUE;

-- Step 3: List exported files
LIST @test_export_stage;

-- Step 4: View file details
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- Step 5: Cleanup
DROP STAGE IF EXISTS test_export_stage;


-- ----------------------------------------------------------------------------
-- 7. CHECK FOR ORPHANED STAGES (Should Be Empty After Script)
-- ----------------------------------------------------------------------------
-- Run this after all scripts complete
-- Should return no rows if cleanup is working correctly
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- If you find orphaned stages, manually clean them up:
-- DROP STAGE IF EXISTS apt_rltp_temp_stage_req12345_dec1_pid98765;


-- ----------------------------------------------------------------------------
-- 8. MONITOR STAGES IN REAL-TIME
-- ----------------------------------------------------------------------------
-- Run this in a loop while script is executing to see stages appear/disappear

-- Terminal 1: Run the Python script
-- python SCRIPTS/rltpDataPulling_v2.py 12345

-- Terminal 2: Run this query every few seconds
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- You should see:
-- Before: No stages
-- During: Stages appear (apt_rltp_temp_stage_req12345_dec1_pid98765)
-- After: No stages (all cleaned up)


-- ----------------------------------------------------------------------------
-- 9. CHECK STAGE PERMISSIONS
-- ----------------------------------------------------------------------------
-- Verify you have permission to create stages
SHOW GRANTS TO USER CURRENT_USER();

-- Look for:
-- CREATE STAGE | SCHEMA | <your_schema> | <your_role>

-- If missing, ask DBA to grant:
-- GRANT CREATE STAGE ON SCHEMA <your_schema> TO ROLE <your_role>;


-- ----------------------------------------------------------------------------
-- 10. TEST TEMPORARY STAGE AUTO-CLEANUP
-- ----------------------------------------------------------------------------
-- Test that TEMPORARY stages auto-cleanup on session close

-- Session 1:
CREATE TEMPORARY STAGE test_temp_cleanup
FILE_FORMAT = (TYPE = CSV);

-- Note the stage name
SHOW STAGES LIKE 'test_temp_cleanup';
-- Stage exists

-- Now close this session/connection
-- Open a new session and run:
SHOW STAGES LIKE 'test_temp_cleanup';
-- Stage should NOT exist (auto-cleaned)


-- ----------------------------------------------------------------------------
-- 11. CHECK STAGE USAGE HISTORY
-- ----------------------------------------------------------------------------
-- See recent COPY INTO operations to stages
SELECT
    query_text,
    start_time,
    end_time,
    total_elapsed_time / 1000 as seconds,
    rows_produced,
    bytes_written / 1024 / 1024 as mb_written
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE query_text ILIKE '%COPY INTO @apt_rltp_temp_stage%'
ORDER BY start_time DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- 12. VALIDATE FILE FORMAT
-- ----------------------------------------------------------------------------
-- Check the file format being used by stages
SHOW FILE FORMATS;

-- Or check inline format from stage
DESC STAGE apt_rltp_temp_stage_req12345_dec1_pid98765;


-- ----------------------------------------------------------------------------
-- 13. TEST GET COMMAND (Download Simulation)
-- ----------------------------------------------------------------------------
-- This simulates what the script does to download files
-- Note: GET command works from SnowSQL CLI, not web UI

-- From SnowSQL CLI:
-- snowsql -c <your_connection>

-- GET @apt_rltp_temp_stage_req12345_dec1_pid98765/decile_1*
-- file:///tmp/test_download/;

-- Then check local filesystem:
-- ls -lh /tmp/test_download/


-- ----------------------------------------------------------------------------
-- 14. FULL END-TO-END TEST
-- ----------------------------------------------------------------------------
-- Complete workflow test (adjust query to your actual data)

-- 1. Create stage
CREATE TEMPORARY STAGE IF NOT EXISTS e2e_test_stage
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '|'
    COMPRESSION = 'GZIP'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    ESCAPE_UNENCLOSED_FIELD = NONE
);

-- 2. Export sample data
COPY INTO @e2e_test_stage/test_export
FROM (
    SELECT
        MD5('test' || ROW_NUMBER() OVER (ORDER BY SEQ4())) as md5hash,
        'email' || ROW_NUMBER() OVER (ORDER BY SEQ4()) || '@test.com' as email,
        'SEG' || (UNIFORM(1, 5, RANDOM())::INT) as segment,
        'SUBSEG' || (UNIFORM(1, 10, RANDOM())::INT) as subseg,
        (UNIFORM(1, 10, RANDOM())::INT)::VARCHAR as decile,
        (UNIFORM(1, 10, RANDOM())::INT)::VARCHAR as priority
    FROM TABLE(GENERATOR(ROWCOUNT => 10000))
)
MAX_FILE_SIZE = 500000000
OVERWRITE = TRUE;

-- 3. List files
LIST @e2e_test_stage;

-- 4. Check file sizes
SELECT
    COUNT(*) as file_count,
    SUM(size) / 1024 / 1024 as total_mb
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- 5. Cleanup
DROP STAGE IF EXISTS e2e_test_stage;


-- ----------------------------------------------------------------------------
-- 15. PERFORMANCE TESTING
-- ----------------------------------------------------------------------------
-- Compare timing: Direct SELECT vs COPY INTO stage

-- Method 1: Direct SELECT (simulates cursor.fetchmany())
SET start_time = CURRENT_TIMESTAMP();

SELECT *
FROM apt_rltp_request_raw_30463_postback_file
LIMIT 1000000;

SET end_time = CURRENT_TIMESTAMP();
SELECT DATEDIFF('second', $start_time, $end_time) as direct_select_seconds;


-- Method 2: COPY INTO stage (what our script does)
SET start_time = CURRENT_TIMESTAMP();

CREATE TEMPORARY STAGE IF NOT EXISTS perf_test_stage
FILE_FORMAT = (
    TYPE = CSV
    FIELD_DELIMITER = '|'
    COMPRESSION = 'GZIP'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'NULL')
    ESCAPE_UNENCLOSED_FIELD = NONE
);

COPY INTO @perf_test_stage/perf_test
FROM (
    SELECT *
    FROM apt_rltp_request_raw_30463_postback_file
    LIMIT 1000000
);

SET end_time = CURRENT_TIMESTAMP();
SELECT DATEDIFF('second', $start_time, $end_time) as copy_into_seconds;

-- Cleanup
DROP STAGE IF EXISTS perf_test_stage;

-- Compare results: COPY INTO should be faster!


-- ----------------------------------------------------------------------------
-- 16. CHECK COMPRESSION EFFECTIVENESS
-- ----------------------------------------------------------------------------
-- See how much compression is saving

-- Export uncompressed
CREATE TEMPORARY STAGE IF NOT EXISTS test_uncompressed
FILE_FORMAT = (TYPE = CSV COMPRESSION = 'NONE');

COPY INTO @test_uncompressed/data
FROM (SELECT * FROM RLTP.apt_rltp_request_raw_30463_postback_file LIMIT 100000);

LIST @test_uncompressed;
-- Note the size

-- Export compressed
CREATE TEMPORARY STAGE IF NOT EXISTS test_compressed
FILE_FORMAT = (TYPE = CSV COMPRESSION = 'GZIP');

COPY INTO @test_compressed/data
FROM (SELECT * FROM your_table LIMIT 100000);

LIST @test_compressed;
-- Note the size (should be 70-80% smaller!)

-- Cleanup
DROP STAGE IF EXISTS test_uncompressed;
DROP STAGE IF EXISTS test_compressed;


-- ----------------------------------------------------------------------------
-- 17. TROUBLESHOOTING QUERIES
-- ----------------------------------------------------------------------------

-- A) Check if stage exists
SELECT COUNT(*) as stage_exists
FROM INFORMATION_SCHEMA.STAGES
WHERE stage_name = 'APT_RLTP_TEMP_STAGE_REQ12345_DEC1_PID98765';

-- B) Find all stages matching pattern
SELECT stage_name, stage_type, created
FROM INFORMATION_SCHEMA.STAGES
WHERE stage_name LIKE 'APT_RLTP_TEMP_STAGE%'
ORDER BY created DESC;

-- C) Check for failed COPY operations
SELECT
    query_id,
    query_text,
    error_message,
    start_time
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE query_text ILIKE '%COPY INTO @apt_rltp%'
AND error_message IS NOT NULL
ORDER BY start_time DESC
LIMIT 10;

-- D) Find long-running COPY operations
SELECT
    query_id,
    LEFT(query_text, 100) as query_snippet,
    start_time,
    end_time,
    total_elapsed_time / 1000 as seconds,
    rows_produced,
    execution_status
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE query_text ILIKE '%COPY INTO @apt_rltp%'
AND total_elapsed_time > 60000  -- More than 60 seconds
ORDER BY start_time DESC
LIMIT 10;


-- ----------------------------------------------------------------------------
-- 18. CLEANUP OLD/ORPHANED STAGES (Emergency)
-- ----------------------------------------------------------------------------
-- If stages somehow get orphaned, clean them up manually

-- List all apt_rltp stages
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- Drop specific stage
DROP STAGE IF EXISTS apt_rltp_temp_stage_req12345_dec1_pid98765;

-- Drop all matching (BE CAREFUL!)
-- Note: Can't do this in a single query, need to drop individually
-- Get list first:
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- Then drop each one:
-- DROP STAGE IF EXISTS <stage_name_from_list>;


-- ----------------------------------------------------------------------------
-- 19. MONITORING DASHBOARD (Run Periodically)
-- ----------------------------------------------------------------------------
-- Quick health check of staging operations

SELECT
    'Active Stages' as metric,
    COUNT(*) as value
FROM INFORMATION_SCHEMA.STAGES
WHERE stage_name LIKE 'APT_RLTP_TEMP_STAGE%'

UNION ALL

SELECT
    'COPY Operations (Last Hour)' as metric,
    COUNT(*) as value
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
    END_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
))
WHERE query_text ILIKE '%COPY INTO @apt_rltp%'

UNION ALL

SELECT
    'Failed COPY Operations (Last Hour)' as metric,
    COUNT(*) as value
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
    END_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
))
WHERE query_text ILIKE '%COPY INTO @apt_rltp%'
AND error_message IS NOT NULL;


-- ============================================================================
-- TESTING CHECKLIST
-- ============================================================================
/*

□ Stage Creation
  - Run SHOW STAGES during script execution
  - Verify stage name includes: req{id}_dec{num}_pid{pid}
  - Confirm TEMPORARY keyword is used

□ Data Export
  - Check COPY INTO completes successfully
  - Verify files appear in stage (LIST @stage)
  - Confirm GZIP compression is applied

□ File Download
  - Verify GET command works (from SnowSQL)
  - Check downloaded files exist locally
  - Confirm .gz files are created

□ Cleanup
  - Run SHOW STAGES after script completes
  - Verify all stages are removed
  - Check no orphaned stages remain

□ Performance
  - Compare COPY INTO vs direct SELECT timing
  - Verify compression reduces file size 70-80%
  - Check memory usage is lower with staging

□ Error Handling
  - Test what happens if stage creation fails
  - Verify fallback to direct fetch works
  - Confirm cleanup happens even on errors

*/

-- ============================================================================
-- QUICK REFERENCE
-- ============================================================================
/*

-- Check active stages
SHOW STAGES LIKE 'apt_rltp_temp_stage%';

-- List files in stage
LIST @apt_rltp_temp_stage_req12345_dec1_pid98765;

-- Drop orphaned stage
DROP STAGE IF EXISTS apt_rltp_temp_stage_req12345_dec1_pid98765;

-- Check COPY history
SELECT query_text, start_time, rows_produced
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
WHERE query_text ILIKE '%COPY INTO @apt_rltp%'
ORDER BY start_time DESC LIMIT 5;

*/
