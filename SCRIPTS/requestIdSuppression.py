import os
import sys
import logging
import pandas as pd
import psycopg2
import subprocess

# Import configuration loader
from config_loader import get_config

# Load config
cfg = get_config()

# Add python modules path from config
sys.path.append(cfg.python_modules_path)
from DbConns import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# if len(sys.argv) != 4:
#    logger.error("Usage: python3 script.py <SCRIPTPATH> <REQUEST_ID> <TRT_TABLE>")
#    sys.exit(1)

SCRIPTPATH = sys.argv[1]
REQUEST_ID = sys.argv[2]
TRT_TABLE = sys.argv[3]
QA_TABLE = sys.argv[4]

# Track this process
track_command = f"""
track_process() {{
    source {cfg.get_config_properties_path(REQUEST_ID)}
    source {cfg.tracking_helper_path}
    append_process_id $1 "REQUEST_ID_SUPPRESSION"
}}
track_process {REQUEST_ID}
"""
subprocess.run(["bash", "-c", track_command], check=False)

logger.info(f"Started Request Suppression Script for REQUEST_ID={REQUEST_ID}")

script_path = os.path.join(SCRIPTPATH, "delete_partitions.py")
if not os.path.isfile(script_path):
    logger.error(f"delete_partitions.py not found in {SCRIPTPATH}")
    sys.exit(1)

conn = None
cur = None

try:
    conn, cur = getPgConnection()

    # Use config for table name
    df = pd.read_sql(
        f"SELECT * FROM {cfg.requests_table} WHERE request_id = %s",
        params=[REQUEST_ID],
        con=conn,
    )
except Exception as e:
    logger.error(f"Failed to load request details for request_id={REQUEST_ID}: {e}")
    if cur:
        cur.close()
    if conn:
        conn.close()
    sys.exit(1)

if df.empty:
    logger.error(f"No record found for request_id={REQUEST_ID}")
    cur.close()
    conn.close()
    sys.exit(1)

logger.info("Loaded request details successfully.")

request_id_supp = df["request_id_supp"].iloc[0]

if not request_id_supp or pd.isna(request_id_supp):
    logger.info("No supplementary request_ids found. Nothing to suppress.")
    cur.close()
    conn.close()
    sys.exit(0)

try:
    supp_ids_raw = [x.strip() for x in request_id_supp.split(",") if x.strip()]
    supp_ids = [int(x) for x in supp_ids_raw]
except Exception:
    logger.error(f"Invalid request_id_supp values: {request_id_supp}")
    cur.close()
    conn.close()
    sys.exit(1)

logger.info(f"Suppression Request IDs: {supp_ids}")

supp_client_ids = []
for req_id in supp_ids:
    cur.execute(
        f"SELECT client_id FROM {cfg.requests_table} WHERE request_id = %s",
        (req_id,),
    )
    row = cur.fetchone()
    if not row:
        logger.warning(f"No client_id found for request_id={req_id}, skipping")
        continue
    supp_client_ids.append(row[0])

logger.info(f"Suppression Client IDs: {supp_client_ids}")

if not supp_client_ids:
    logger.info("No valid supplementary client IDs found. Exiting.")
    cur.close()
    conn.close()
    sys.exit(0)

total_suppressed = 0

for cli_id in supp_client_ids:
    cur.execute(
        f"SELECT prev_week_pb_table FROM {cfg.clients_table} WHERE client_id = %s",
        (cli_id,),
    )
    row = cur.fetchone()
    if not row:
        logger.warning(f"No prev_week_pb_table found for client_id={cli_id}, skipping")
        continue

    prev_pb_table = row[0]
    logger.info(f"Processing suppression using PB_TABLE={prev_pb_table}")

    query = f"delete from {TRT_TABLE} a using {prev_pb_table} b where a.email=b.email "

    try:
        output = subprocess.check_output(
            ["python3", script_path, query, str(REQUEST_ID)], text=True
        ).strip()

        deleted_count = int(output)
        total_suppressed += deleted_count
        logger.info(f"Suppressed {deleted_count} records for client_id={cli_id}")
        update_query = (
            f"UPDATE {QA_TABLE} SET REQUEST_ID_SUPP_COUNT = %s WHERE REQUEST_ID = %s"
        )
        cur.execute(update_query, (total_suppressed, REQUEST_ID))
        conn.commit()

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running delete_partitions.py: {e}")
    except ValueError:
        logger.error(f"Invalid output from delete_partitions.py: '{output}'")

logger.info(f"TOTAL SUPPRESSED COUNT = {total_suppressed}")
logger.info("Request Suppression Script Completed Successfully.")

# Close connection
if cur:
    cur.close()
if conn:
    conn.close()
