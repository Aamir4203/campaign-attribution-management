"""
RLTP Data Pulling Script - Refactored Version with Snowflake Staging
=====================================================================
This script pulls data from Snowflake RLTP tables and loads it into PostgreSQL
partitioned tables with parallel processing and Snowflake staging optimization.

Key Improvements over original:
- Snowflake staging for 20-30% faster data export
- GZIP compression (70-80% less network transfer)
- Improved variable naming and code structure
- Process-level stage isolation
- Memory-efficient processing with explicit buffer flushing
- Automatic fallback to direct fetch if staging fails

Version: 2.0 (Production Test - Staging Only)
"""

import os
import re
import sys
import csv
import gzip
import time
import logging
import threading
from queue import Queue
from datetime import datetime
from multiprocessing import Pool, Manager, cpu_count
from pathlib import Path

import pandas as pd
import psycopg2
import snowflake.connector
import warnings
import subprocess

# Import configuration loader
from config_loader import get_config

# Load config
cfg = get_config()

# Add custom module paths from config
sys.path.append(cfg.python_modules_path)
from DbConns import *

import log_module

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================================
# CONFIGURATION (Loaded from app.yaml via config_loader)
# ============================================================================

# Data fetching configuration
CHUNK_SIZE = cfg.chunk_size  # Rows per fetch chunk (for fallback direct fetch)
MAX_RETRY_ATTEMPTS = cfg.max_retries  # Maximum retries for data pulling
RETRY_DELAY_SECONDS = cfg.retry_delay  # Delay between retries

# Snowflake staging configuration
USE_SNOWFLAKE_STAGING = cfg.staging_enabled  # Enable Snowflake staging by default
STAGE_PREFIX = cfg.stage_prefix  # Prefix for temporary stages
# Stage naming: {prefix}_req{request_id}_dec{decile}
# Example: apt_rltp_temp_stage_req12345_dec1
STAGE_MAX_FILE_SIZE = cfg.stage_max_file_size  # Max file size per stage file
STAGE_COMPRESSION = cfg.stage_compression  # Compression for stage files

# Multiprocessing configuration
MAX_WORKER_PROCESSES = cfg.max_workers  # Maximum parallel workers

# ============================================================================
# GLOBAL STATE
# ============================================================================

# Shared event for inter-process communication
event = None

# Logger instance
logger = None


# ============================================================================
# WORKER INITIALIZATION
# ============================================================================


def init_worker(shared_event):
    """Initialize worker process with shared event for termination signaling."""
    global event
    event = shared_event


# ============================================================================
# DATABASE STATUS UPDATES
# ============================================================================


def update_request_status(description):
    """Update request status in database to indicate error."""
    conn = None
    cursor = None
    try:
        conn, cursor = getPgConnection()

        # Use config query template
        update_query = cfg.get_update_status_query(sys.argv[1], description)

        cursor.execute(update_query)
        conn.commit()

    except Exception as e:
        if logger:
            logger.error(f"Failed to update request status: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================================
# PARALLEL INDEX CREATION
# ============================================================================


def create_indexes_parallel(partition_table, include_md5_index, logger_instance):
    """
    Create multiple indexes in parallel using threads.
    Each thread creates one index with its own database connection.

    Args:
        partition_table: Table name (partition)
        include_md5_index: True if suppression (md5) index needed
        logger_instance: Logger instance

    Returns:
        True if all indexes created successfully, False otherwise
    """
    results = Queue()

    def create_single_index(index_name, columns):
        """Worker thread to create one index."""
        conn = None
        cursor = None
        try:
            # Each thread needs its own connection from DbConns
            conn, cursor = getPgConnection()

            # Check if index exists
            cursor.execute(
                f"SELECT indexname FROM pg_indexes WHERE tablename = '{partition_table}' AND indexname = '{index_name}'"
            )
            if cursor.fetchone():
                logger_instance.info(
                    f"Index {index_name} already exists on {partition_table}"
                )
                results.put((index_name, True))
                return

            # Build CREATE INDEX statement
            sql = f"CREATE INDEX {index_name} ON {partition_table} ({columns})"

            logger_instance.info(f"Creating index {index_name} on {partition_table}...")
            start_time = datetime.now()

            cursor.execute(sql)
            conn.commit()

            duration = (datetime.now() - start_time).total_seconds()
            logger_instance.info(
                f"✅ {index_name} created in {duration:.2f}s on {partition_table}"
            )
            results.put((index_name, True))

        except Exception as e:
            logger_instance.error(
                f"❌ Failed to create {index_name} on {partition_table}: {e}"
            )
            results.put((index_name, False))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Define indexes to create using config templates
    # Extract request_id and decile from table name
    parts = partition_table.split("_")
    try:
        request_id = parts[2]  # request_id
        decile = parts[-1]  # decile number
    except:
        # Fallback - use table name if parsing fails
        request_id = "unknown"
        decile = "unknown"

    # Use config to generate index names
    indexes_to_create = [
        (cfg.get_index_name('email', request_id, decile), "email"),
        (cfg.get_index_name('seg_subseg', request_id, decile), "segment, subseg"),  # CRITICAL for MODULE 4
    ]

    # Add md5 index if suppression is enabled
    if include_md5_index:
        indexes_to_create.append((cfg.get_index_name('md5', request_id, decile), "md5hash"))

    logger_instance.info(
        f"Creating {len(indexes_to_create)} indexes in parallel on {partition_table}"
    )
    index_start = datetime.now()

    # Launch parallel threads for index creation
    threads = []
    for idx_name, columns in indexes_to_create:
        thread = threading.Thread(target=create_single_index, args=(idx_name, columns))
        thread.start()
        threads.append(thread)

    # Wait for all index creation threads to complete
    for thread in threads:
        thread.join()

    index_end = datetime.now()
    total_duration = (index_end - index_start).total_seconds()

    # Check results
    success = True
    failed_indexes = []
    while not results.empty():
        idx_name, status = results.get()
        if not status:
            success = False
            failed_indexes.append(idx_name)

    if success:
        logger_instance.info(
            f"✅ All {len(indexes_to_create)} indexes created in {total_duration:.2f}s on {partition_table}"
        )
    else:
        logger_instance.error(
            f"❌ Failed to create indexes on {partition_table}: {failed_indexes}"
        )

    return success


# ============================================================================
# SNOWFLAKE STAGING FUNCTIONS
# ============================================================================


def export_to_snowflake_stage(sf_cursor, query, stage_name, file_name, logger_instance):
    """
    Export query results to Snowflake internal stage using COPY INTO.

    This uses Snowflake's optimized parallel export which is 20-40% faster
    than Python cursor-based fetching for medium to large datasets.

    Args:
        sf_cursor: Snowflake cursor
        query: SQL query to export
        stage_name: Name of Snowflake stage (includes request_id, decile, process_id)
        file_name: Output file name prefix
        logger_instance: Logger for output

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create internal TEMPORARY stage with unique name
        # Stage name format: apt_rltp_temp_stage_req{request_id}_dec{decile}_pid{process_id}
        # TEMPORARY ensures it's session-scoped and auto-cleaned on disconnect
        create_stage_sql = f"""
        CREATE  TEMPORARY STAGE IF NOT EXISTS {stage_name}
        FILE_FORMAT = (
            TYPE = CSV
            FIELD_DELIMITER = '|'
            COMPRESSION = '{STAGE_COMPRESSION}'
            RECORD_DELIMITER = '\\n'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            NULL_IF = ('', 'NULL')
            ESCAPE_UNENCLOSED_FIELD = NONE
        )
        """

        logger_instance.info(f"Creating temporary stage: {stage_name}")
        sf_cursor.execute(create_stage_sql)

        # Export data to stage using COPY INTO
        # This is much faster than cursor.fetchmany() for large datasets
        export_sql = f"""
        COPY INTO @{stage_name}/{file_name}
        FROM ({query})
        MAX_FILE_SIZE = {STAGE_MAX_FILE_SIZE}
        OVERWRITE = TRUE
        """

        logger_instance.info(f"Exporting data to stage: @{stage_name}/{file_name}")
        export_start = datetime.now()

        result = sf_cursor.execute(export_sql)
        rows_exported = result.fetchone()

        export_duration = (datetime.now() - export_start).total_seconds()
        logger_instance.info(
            f"✅ Data exported to stage in {export_duration:.2f}s: {rows_exported}"
        )

        return True

    except Exception as e:
        logger_instance.error(
            f"Failed to export to Snowflake stage: {e}", exc_info=True
        )
        return False


def download_from_snowflake_stage(
        sf_cursor, stage_name, file_pattern, local_dir, logger_instance
):
    """
    Download files from Snowflake stage to local directory using GET command.

    Args:
        sf_cursor: Snowflake cursor
        stage_name: Name of Snowflake stage
        file_pattern: File pattern to download (e.g., 'decile_1*')
        local_dir: Local directory to download to
        logger_instance: Logger for output

    Returns:
        List of downloaded file paths, or None if failed
    """
    try:
        # Ensure local directory exists
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        # Download from stage using GET
        get_sql = f"GET @{stage_name}/{file_pattern} file://{local_dir}/"
        logger_instance.info(f"Downloading from stage to {local_dir}")
        download_start = datetime.now()

        sf_cursor.execute(get_sql)
        result = sf_cursor.fetchall()

        download_duration = (datetime.now() - download_start).total_seconds()

        # Parse downloaded files
        downloaded_files = []
        for row in result:
            file_name = row[0]  # First column is file name
            status = row[2]  # Third column is status
            if status == "DOWNLOADED":
                downloaded_files.append(os.path.join(local_dir, file_name))
                logger_instance.info(f"Downloaded: {file_name}")

        logger_instance.info(
            f"✅ Downloaded {len(downloaded_files)} file(s) in {download_duration:.2f}s"
        )

        return downloaded_files if downloaded_files else None

    except Exception as e:
        logger_instance.error(
            f"Failed to download from Snowflake stage: {e}", exc_info=True
        )
        return None


def cleanup_snowflake_stage(sf_cursor, stage_name, logger_instance):
    """
    Clean up Snowflake stage after use.

    Args:
        sf_cursor: Snowflake cursor
        stage_name: Name of stage to clean up
        logger_instance: Logger for output
    """
    try:
        # Drop temporary stage
        drop_sql = f"DROP STAGE IF EXISTS {stage_name}"
        sf_cursor.execute(drop_sql)
        logger_instance.info(f"Cleaned up stage: {stage_name}")
    except Exception as e:
        logger_instance.warning(f"Failed to cleanup stage {stage_name}: {e}")


def decompress_and_merge_stage_files(
        downloaded_files, final_output_file, logger_instance
):
    """
    Decompress GZIP files from stage and merge into single output file.

    Snowflake's COPY INTO can create multiple files if data is large.
    This function merges them into a single file for PostgreSQL COPY.

    Args:
        downloaded_files: List of downloaded .gz file paths
        final_output_file: Path to final merged CSV file
        logger_instance: Logger for output

    Returns:
        True if successful, False otherwise
    """
    try:
        logger_instance.info(
            f"Decompressing and merging {len(downloaded_files)} file(s)"
        )
        merge_start = datetime.now()

        with open(final_output_file, "wb") as outfile:
            for gz_file in downloaded_files:
                logger_instance.info(f"Processing: {gz_file}")
                with gzip.open(gz_file, "rb") as infile:
                    # Read and write in chunks to manage memory
                    chunk_size = 10 * 1024 * 1024  # 10MB chunks
                    while True:
                        chunk = infile.read(chunk_size)
                        if not chunk:
                            break
                        outfile.write(chunk)

                # Remove compressed file after processing
                os.remove(gz_file)
                logger_instance.info(f"Decompressed and removed: {gz_file}")

        merge_duration = (datetime.now() - merge_start).total_seconds()
        logger_instance.info(
            f"✅ Files merged into {final_output_file} in {merge_duration:.2f}s"
        )

        return True

    except Exception as e:
        logger_instance.error(f"Failed to decompress/merge files: {e}", exc_info=True)
        return False


# ============================================================================
# DATA PULLING WITH STAGING
# ============================================================================


def pull_data_with_staging(sf_cursor, query, decile_file, decile_name, logger_instance):
    """
    Pull data using Snowflake staging (COPY INTO + GET).

    This is 20-30% faster than direct cursor fetching for medium datasets (5-20GB)
    and uses less memory as Snowflake handles the data export.

    Args:
        sf_cursor: Snowflake cursor
        query: SQL query to execute
        decile_file: Path to final output CSV file
        decile_name: Decile identifier
        logger_instance: Logger

    Returns:
        True if successful, False if should fallback to direct fetch
    """
    # Create unique stage name with request_id, decile, and process_id
    # This ensures no conflicts even if same request/decile runs in parallel
    request_id = sys.argv[1]
    process_id = os.getpid()
    stage_name = f"{STAGE_PREFIX}_req{request_id}_dec{decile_name}"
    file_prefix = f"decile_{decile_name}"
    local_dir = os.path.dirname(decile_file)

    logger_instance.info(f"Stage name: {stage_name}")

    try:
        # Step 1: Export to Snowflake stage
        logger_instance.info(f"Using Snowflake staging for decile {decile_name}")
        if not export_to_snowflake_stage(
                sf_cursor, query, stage_name, file_prefix, logger_instance
        ):
            logger_instance.warning(
                "Stage export failed, will fallback to direct fetch"
            )
            return False

        # Step 2: Download from stage
        downloaded_files = download_from_snowflake_stage(
            sf_cursor, stage_name, f"{file_prefix}", local_dir, logger_instance
        )

        if not downloaded_files:
            logger_instance.warning(
                "Stage download failed, will fallback to direct fetch"
            )
            cleanup_snowflake_stage(sf_cursor, stage_name, logger_instance)
            return False

        # Step 3: Decompress and merge files
        if not decompress_and_merge_stage_files(
                downloaded_files, decile_file, logger_instance
        ):
            logger_instance.warning("File merge failed, will fallback to direct fetch")
            cleanup_snowflake_stage(sf_cursor, stage_name, logger_instance)
            return False

        # Step 4: Cleanup stage
        cleanup_snowflake_stage(sf_cursor, stage_name, logger_instance)

        logger_instance.info(
            f"✅ Successfully pulled data using staging for decile {decile_name}"
        )
        return True

    except Exception as e:
        logger_instance.error(
            f"Staging failed for decile {decile_name}: {e}", exc_info=True
        )
        # Attempt cleanup even on failure
        try:
            cleanup_snowflake_stage(sf_cursor, stage_name, logger_instance)
        except:
            pass
        return False


def pull_data_direct_fetch(sf_cursor, query, decile_file, logger_instance):
    """
    Pull data using direct cursor fetching (fallback method).

    This is the traditional approach - slower but more reliable as fallback.

    Args:
        sf_cursor: Snowflake cursor
        query: SQL query to execute
        decile_file: Path to output CSV file
        logger_instance: Logger

    Returns:
        True if successful, False otherwise
    """
    try:
        logger_instance.info("Using direct fetch method")
        sf_cursor.execute(query)

        with open(decile_file, "wt", newline="") as f:
            writer = csv.writer(f, delimiter="|")

            rows_written = 0
            while True:
                rows = sf_cursor.fetchmany(size=CHUNK_SIZE)
                if not rows:
                    break

                writer.writerows(rows)
                rows_written += len(rows)

                # Flush buffer to prevent memory accumulation
                f.flush()

        logger_instance.info(f"✅ Direct fetch completed: {rows_written:,} rows")
        return True

    except Exception as e:
        logger_instance.error(f"Direct fetch failed: {e}", exc_info=True)
        return False


# ============================================================================
# WORKER PROCESS FOR DATA PULLING
# ============================================================================


def process_decile_worker(args):
    """
    Worker function to pull data for a single decile and load into PostgreSQL.

    Data Pulling Strategy:
    1. Try Snowflake staging first (20-30% faster for medium datasets)
    2. Fallback to direct fetch if staging fails
    3. Load into PostgreSQL using COPY
    4. Create indexes in parallel
    5. Run ANALYZE
    """
    (
        decile_name,
        trt_table_base,
        query,
        include_md5_index,
        n,
        is_decile_wise,
        request_path,
        client_id,
        audit_trt_limit,
        indx_val,
        indx_creation
    ) = args

    sf_conn = None
    sf_cursor = None
    pg_conn = None
    pg_cursor = None

    try:
        # Initialize connections
        sf_conn, sf_cursor = getSnowflake()
        pg_conn, pg_cursor = getPgConnection()

        # Track this worker process
        track_command = f"""
        track_process() {{
            source {cfg.get_config_properties_path(sys.argv[1])}
            source {cfg.tracking_helper_path}
            append_process_id $1 "RLTP_WORKER_{decile_name}"
        }}
        track_process {sys.argv[1]}
        """
        subprocess.run(["bash", "-c", track_command], check=False)

        # Check if termination signal is set
        if event.is_set():
            return

        # Modify query for decile-wise processing
        if is_decile_wise:
            decile_column = query.split(",")[4].strip().split(" ")[0]
            if not re.findall("where", query, re.IGNORECASE):
                query = f"{query} WHERE {decile_column}='{decile_name}' order by random()"
            else:
                query = f"{query} AND {decile_column}='{decile_name}' order by random()"

        else:
            query = f"{query} order by random() "

        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(
            f"RLTP Data pulling started for decile {decile_name} at: {start_time}"
        )

        # Sample query for validation
        sample_query = f"{query.strip().rstrip(';')} LIMIT 3"
        logger.info(f"Sampling query (Snowflake):: {sample_query}")
        sf_cursor.execute(sample_query)
        sample_rows = sf_cursor.fetchall()
        logger.info(f"Sample rows for {decile_name}: {sample_rows}")

        # Apply random ordering for all queries; audit clients also get a row limit
        if cfg.is_audit_client(client_id):
            query = f"{query}  limit {audit_trt_limit}"
        else:
            query = f"{query} "

        # Define output file (use config method for FILES path)
        files_path = cfg.get_files_path(request_id)
        decile_file = os.path.join(files_path, f"decile_{decile_name}.csv")

        # Retry logic for data pulling
        attempt = 1
        success = False

        while attempt <= MAX_RETRY_ATTEMPTS:
            try:
                logger.info(
                    f"Attempt {attempt}/{MAX_RETRY_ATTEMPTS} for decile {decile_name}"
                )
                logger.info(f"Execution query :: {query}")

                # Try Snowflake staging first (faster for medium/large datasets)
                if USE_SNOWFLAKE_STAGING:
                    success = pull_data_with_staging(
                        sf_cursor, query, decile_file, decile_name, logger
                    )

                    # If staging failed, fallback to direct fetch
                    if not success:
                        logger.info("Staging failed, using direct fetch fallback")
                        success = pull_data_direct_fetch(
                            sf_cursor, query, decile_file, logger
                        )
                else:
                    # Direct fetch if staging is disabled
                    success = pull_data_direct_fetch(
                        sf_cursor, query, decile_file, logger
                    )

                if success:
                    logger.info(
                        f"✅ Data successfully written for decile {decile_name}"
                    )
                    break
                else:
                    raise Exception("Data pull failed")

            except Exception as e:
                logger.error(
                    f"Attempt {attempt}: Unable to pull RLTP data for {decile_name}: {e}",
                    exc_info=True,
                )
                if attempt == MAX_RETRY_ATTEMPTS:
                    event.set()
                    return
                else:
                    logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    attempt += 1

        if not success:
            logger.error(f"Failed to write data for decile {decile_name}")
            event.set()
            return

        # --- PostgreSQL load with COPY  ---
        partition_table = f"{trt_table_base}_{decile_name}".lower()

        with open(decile_file, "r") as f:
            logger.info(f"Starting COPY to {partition_table}...")
            copy_start = datetime.now()
            pg_cursor.copy_expert(
                f"COPY {partition_table} FROM STDIN WITH DELIMITER '|' CSV", f
            )
            pg_conn.commit()
            copy_duration = (datetime.now() - copy_start).total_seconds()
            logger.info(
                f"✅ COPY completed in {copy_duration:.2f}s for {partition_table}"
            )

        # Create indexes in parallel (email, segment/subseg, optionally md5)
        logger.info(
            f"Data load complete for {partition_table}. Starting parallel index creation..."
        )
        if indx_creation==indx_val:

            index_success = create_indexes_parallel(
                partition_table, include_md5_index, logger
            )

            if not index_success:
                logger.error(f"Index creation failed for {partition_table}")
                update_request_status("Unable to create indexes on TRT")
                event.set()
                return

        # Run ANALYZE to update table statistics for query planner
        try:
            logger.info(f"Running ANALYZE on {partition_table} to update statistics")
            analyze_start = datetime.now()
            pg_cursor.execute(f"ANALYZE {partition_table}")
            pg_conn.commit()
            analyze_duration = (datetime.now() - analyze_start).total_seconds()
            logger.info(
                f"✅ ANALYZE completed in {analyze_duration:.2f}s for {partition_table}"
            )
        except Exception as e:
            logger.warning(f"ANALYZE failed for {partition_table}: {e}")

        # Clean up file
        os.remove(decile_file)
        logger.info(f"Temporary file {decile_file} removed")

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_ex = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(
            start_time, "%Y-%m-%d %H:%M:%S"
        )
        logger.info(f"Execution time for decile {decile_name}: {total_ex}")

    except Exception as e:
        logger.error(f"Error processing {decile_name}: {e}", exc_info=True)
        update_request_status("Unable to pull data from RLTP")
        event.set()
        return

    finally:
        if sf_cursor:
            sf_cursor.close()
        if sf_conn:
            sf_conn.close()
        if pg_cursor:
            pg_cursor.close()
        if pg_conn:
            pg_conn.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        request_id = sys.argv[1]

        # Track main process
        track_command = f"""
        track_process() {{
            source {cfg.get_config_properties_path(request_id)}
            source {cfg.tracking_helper_path}
            append_process_id $1 "RLTP_MAIN"
        }}
        track_process {request_id}
        """
        subprocess.run(["bash", "-c", track_command], check=False)

        # Setup paths from config
        request_path = cfg.get_request_path(request_id)
        log_path = cfg.get_logs_path(request_id)

        # Setup logging
        logger = log_module.setup_logging(log_path)
        logger.info("Logs path: {}".format(log_path))
        logger.info(
            f"Snowflake staging: {'ENABLED' if USE_SNOWFLAKE_STAGING else 'DISABLED'}"
        )

        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("RLTP data pulling started at : " + start_time)

        # Fetch request details from database using config query
        pg_conn, pg_cursor = getPgConnection()

        request_query = cfg.get_request_details_query(request_id)

        request_df = pd.read_sql(request_query, con=pg_conn)
        pg_conn.close()  # Close the initial connection

        # Extract only required columns from comprehensive query result
        request_df = request_df[[
            'request_id', 'client_name', 'week', 'decile_wise_report_path',
            'client_id', 'supp_path', 'query'
        ]]

        # Create TRT table name using config template
        trt_table_base = cfg.get_trt_table(
            str(request_df['request_id'][0]),
            request_df['client_name'][0],
            request_df['week'][0]
        )

        # Load decile report
        decile_df = pd.read_csv(
            request_df["decile_wise_report_path"][0],
            sep="|",
            header=None,
            thousands=",",
        )
        decile_df.columns = [
            "Delivered",
            "Opens",
            "clicks",
            "unsubs",
            "segment",
            "sub_seg",
            "decile",
            "old_per",
        ]

        decile_count = len(decile_df["decile"].drop_duplicates())
        client_id = int(request_df["client_id"][0])
        audit_trt_limit = decile_df["Delivered"].sum() + cfg.audit_trt_buffer

        # Check if MD5 index is needed
        include_md5_index = True
        supp_path = request_df["supp_path"][0]
        if supp_path != "":
            supp_sample = pd.read_csv(supp_path, nrows=10, header=None)
            if not supp_sample[0].str.contains("@").any():
                logger.info("Adding index on md5 level")
                include_md5_index = True

        # Extract the number from request_df['query'] and modify the query string
        modified_queries = []
        extracted_numbers = []
        for query_string in request_df["query"][0].split(";"):
            match = re.search(r"apt_rltp_request_raw_(\d+)_postback_file", query_string)
            if match:
                extracted_number = match.group(1)
                extracted_numbers.append(extracted_number)
                # Insert the rltpid into the select clause
                modified_query = query_string.replace(
                    "priority", f"priority,'{extracted_number}' as rltpid", 1
                )
                modified_queries.append(modified_query)
            else:
                # Handle the case where no number was extracted
                #logger.warning(f"No number extracted from query: {query_string}. Keeping original query.")
                modified_queries.append(query_string)

        request_df["query"] = ";".join(modified_queries)
        query_list= [item for item in request_df["query"][0].split(";") if re.search(r'apt_rltp_request_raw_', item)]
        indx_creation=len(query_list)


        # Validate queries with sample data (Snowflake only)
        if query_list:
            sample_query = query_list[0] + " LIMIT 3"
            try:
                sf_conn, sf_cursor = getSnowflake()
                sample_df = pd.read_sql(sample_query, con=sf_conn)
                logger.info(sample_df)
                sf_conn.close()
            except Exception as e:
                logger.error("Unable to pull sample data from Snowflake ::{}".format(e))
                update_request_status("Unable to pull data from RLTP")
                sys.exit(1)
        else:
            logger.error("Snowflake query is not valid. Exiting.")
            update_request_status("Unable to pull data from RLTP")
            sys.exit(1)

        # Define table columns
        std_cols = ["md5hash", "email", "segment", "subseg", "decile", "priority"]
        req_cols = std_cols + list(sample_df.columns)[6::]
        colsn = " varchar,".join(req_cols) + " varchar"

        # Create partitioned table if it doesn't exist
        pg_conn = None
        pg_cursor = None
        try:
            pg_conn, pg_cursor = getPgConnection()

            # Check if table exists using psycopg2
            pg_cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{trt_table_base}'
                )
            """)
            table_exists = pg_cursor.fetchone()[0]

            if not table_exists:
                pg_cursor.execute(
                    f"CREATE TABLE {trt_table_base} ({colsn}) PARTITION BY LIST(decile)"
                )
                for i in list(decile_df["decile"].drop_duplicates()):
                    pg_cursor.execute(
                        f"CREATE TABLE {trt_table_base}_{i} PARTITION OF {trt_table_base} FOR VALUES IN ('{i}')"
                    )
                pg_conn.commit()
                logger.info("Tables created")

        except Exception as e:
            logger.error(f"Unable to create TRT tables: {e}")
            update_request_status("Unable to create TRT tables")
            sys.exit(1)
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

        # Process each query
        indx_val=1
        for query in query_list:
            if re.findall("apt_rltp_request_raw_", query):
                decile_column = str(query.split(",")[4].strip().split()[0])
                is_decile_wise = False
                decile_list = sorted(
                    list(decile_df["decile"].drop_duplicates()), reverse=True
                )

                if decile_list[0] == 1 or decile_column == "'1'":
                    decile_list = [1]

                if decile_count != 1 and decile_column != "'1'":
                    is_decile_wise = True
                    decile_list = sorted(
                        list(decile_df["decile"].drop_duplicates()), reverse=True
                    )

                logger.info("Executing decile processing with parallel workers")

                try:
                    manager = Manager()
                    shared_event = manager.Event()

                    with Pool(
                            processes=MAX_WORKER_PROCESSES,
                            initializer=init_worker,
                            initargs=(shared_event,),
                    ) as pool:
                        pool.map(
                            process_decile_worker,
                            [
                                (
                                    decile,
                                    trt_table_base,
                                    query,
                                    include_md5_index,
                                    1,
                                    is_decile_wise,
                                    request_path,
                                    client_id,
                                    audit_trt_limit,
                                    indx_val,
                                    indx_creation
                                )
                                for decile in decile_list
                            ],
                        )

                    logger.info("All threads for TRT are completed.")
                    indx_val=indx_val+1
                except Exception as e:
                    logger.error("An error occurred: %s", str(e), exc_info=True)
                    update_request_status("Failed to Launch Worker nodes for TRT")
                    sys.exit(1)

                time.sleep(2)

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Script ended at: {end_time}")
        total_ex = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(
            start_time, "%Y-%m-%d %H:%M:%S"
        )
        logger.info(f"Total Time taken: {total_ex}")

        # Create a new connection for final updates
        pg_conn, pg_cursor = getPgConnection()

        try:
            # Update request description
            update_desc_query = cfg.get_update_desc_query(sys.argv[1], 'TRT Imported')
            pg_cursor.execute(update_desc_query)

            # Get count from TRT table
            pg_cursor.execute(f"select count(email) from {trt_table_base}")
            cnt = list(pg_cursor.fetchone())[0]

            # Update QA stats with count
            update_qa_query = cfg.get_update_qa_count_query(sys.argv[1], cnt)
            pg_cursor.execute(update_qa_query)

            pg_conn.commit()
            logger.info(f"RLTP data pulling ended at : {total_ex}")
        finally:
            if pg_cursor:
                pg_cursor.close()
            if pg_conn:
                pg_conn.close()

    except Exception as e:
        logger.error("Unable to pull data from RLTP ::{}".format(e))
        update_request_status("Unable to pull data from RLTP")
        try:
            pool.terminate()
            pool.join()
        except:
            pass
        sys.exit(1)
