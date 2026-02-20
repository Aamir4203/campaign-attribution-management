import psycopg2
from psycopg2 import sql
from multiprocessing import Pool, cpu_count
import re
import sys
import logging
import subprocess
import os

# Import configuration loader
from config_loader import get_config

# Load config
cfg = get_config()

# Add python modules path and import DbConns
import sys
sys.path.append(cfg.python_modules_path)
from DbConns import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def execute_query(query_and_request_id):
    query, request_id = query_and_request_id
    try:
        # Track this worker process
        if request_id:
            track_command = f"""
            track_process() {{
                source {cfg.get_config_properties_path(request_id)}
                source {cfg.tracking_helper_path}
                append_process_id $1 "DELETE_PARTITION_WORKER"
            }}
            track_process {request_id}
            """
            subprocess.run(
                ["bash", "-c", track_command],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Use DbConns for connection
        conn, cur = getPgConnection()
        conn.autocommit = True

        cur.execute(query)

        affected_rows = cur.rowcount

        cur.close()
        conn.close()

        return affected_rows

    except psycopg2.Error as e:
        logger.error(f"Error executing query: {e}")
        return None


def parse_query_and_get_table(query):
    try:
        match = re.search(r"delete\s+from\s+(\w+)\s+", query, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            return table_name
        else:
            raise ValueError("Table name not found in delete query.")

    except Exception as e:
        logger.error(f"Error parsing query: {e}")
        return None


def get_partition_names(table_name):
    try:
        # Use DbConns for connection
        conn, cur = getPgConnection()
        conn.autocommit = True

        cur.execute(
            sql.SQL(
                """
            SELECT child.relname
            FROM pg_inherits
            JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
            JOIN pg_class child ON pg_inherits.inhrelid = child.oid
            JOIN pg_namespace nmsp_parent ON nmsp_parent.oid = parent.relnamespace
            JOIN pg_namespace nmsp_child ON nmsp_child.oid = child.relnamespace
            WHERE parent.relname = lower({});
        """
            ).format(sql.Literal(table_name))
        )

        partition_names = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return partition_names

    except psycopg2.Error as e:
        logger.error(f"Error fetching partition names: {e}")
        return []


if __name__ == "__main__":
    try:
        if len(sys.argv) < 3:
            raise ValueError("Delete query and request_id not provided as arguments.")

        delete_query = sys.argv[1]
        request_id = sys.argv[2]

        # Track main process - create bash function to handle positional parameters
        track_command = f"""
        track_process() {{
            source {cfg.get_config_properties_path(request_id)}
            source {cfg.tracking_helper_path}
            append_process_id $1 "DELETE_PARTITION_MAIN"
        }}
        track_process {request_id}
        """
        subprocess.run(
            ["bash", "-c", track_command],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        table_name = parse_query_and_get_table(delete_query)
        if not table_name:
            raise ValueError("Failed to extract table name from query.")

        partition_names = get_partition_names(table_name)
        logger.info(f"Found partitions: {partition_names}")

        partition_queries = []
        for partition_name in partition_names:
            partition_query = delete_query.replace(table_name, partition_name)
            partition_queries.append((partition_query, request_id))

        max_processes = 5
        pool = Pool(processes=min(max_processes, cpu_count()))

        try:
            results = pool.map(execute_query, partition_queries)
            total_deleted_count = sum(results)
            logger.info(
                f"Total deleted count across all partitions: {total_deleted_count}"
            )

            print(total_deleted_count)

        finally:
            pool.close()
            pool.join()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
