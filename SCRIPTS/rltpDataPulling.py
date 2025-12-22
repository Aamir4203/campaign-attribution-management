import os
import re
import sys
import csv
import time
import logging
from datetime import datetime
from multiprocessing import Pool, Manager, cpu_count
import pandas as pd
import psycopg2
import snowflake.connector
from sqlalchemy import create_engine, inspect
import configparser
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import serialization
import snowflake.connector
import yaml
import warnings
import log_module
import subprocess

sys.path.append('/u1/techteam/PFM_CUSTOM_SCRIPTS/PYTHON_MODULES/')
from DbConns import *
from DB_conns import *

warnings.filterwarnings("ignore", category=UserWarning)

def killPid():
    os.kill(os.getpid(), signal.SIGTERM)

def init_worker(shared_event):
    global event
    event = shared_event


def status_up(desc):
    conn, cur = getPgConnection()
    cur.execute(
        f"update APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND set request_status='E',request_desc='{desc}',error_code=1 where request_id={sys.argv[1]}"
    )
    conn.commit()
    cur.close()
    conn.close()


def main(args):
    client, trt_tb, qr, sup_l, n, deciles_, path, client_id, Audit_TRT_limit, indx_val, indx_creation, = args
    sf_conn, sf_cursor = getSnowflake()
    pgdb1_conn, pgdb1_cursor = getPgConnection()
    audit_ids = [180, 181, 182, 183, 184, 185, 187, 188, 189, 190]
    try:
        # Track this worker process
        track_command = f"""
        track_process() {{
            source /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/$1/ETC/config.properties
            source $TRACKING_HELPER
            append_process_id $1 "RLTP_WORKER_{client}"
        }}
        track_process {sys.argv[1]}
        """
        subprocess.run(["bash", "-c", track_command], check=False)

        if event.is_set():
            return
        if deciles_ == 'True':
            de = qr.split(',')[4].strip().split(' ')[0]
            if not re.findall('where', qr, re.IGNORECASE):
                qr = f"{qr} WHERE {de}='{client}' order by random()"
            else:
                qr = f"{qr} AND {de}='{client}' order by random()"
        dstart_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"RLTP Data pulling started for decile {client} at: {dstart_time}")
        if client_id in audit_ids:
            qr = f"{qr} order by random() limit {Audit_TRT_limit}"
        d_file = f"{path}/FILES/decile_{client}.csv"
        attempt = 1
        while attempt <= 3:
            try:
                logger.info(f"Execution query :: {qr}")
                sf_cursor.execute(qr)
                with open(d_file, 'wt', newline='') as f:
                    writer = csv.writer(f, delimiter='|')
                    while True:
                        rows = sf_cursor.fetchmany(size=5000000)
                        if not rows:
                            break
                        writer.writerows(rows)
                logger.info(f"File written: {d_file} on attempt {attempt}")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt}: Unable to pull RLTP data for {client}: {e}", exc_info=True)
                if attempt == 3:
                    event.set()
                    return
                else:
                    logger.info(f"Retrying to pull RLTP data for {client} after 5 seconds...")
                    time.sleep(5)
                    attempt += 1
                    killPid()
        # --- PostgreSQL load with COPY  ---
        with open(d_file, 'r') as f:
            decile_tb = f"{trt_tb}_{client}".lower()
            pgdb1_cursor.copy_expert(f"COPY {decile_tb} FROM STDIN WITH DELIMITER '|' CSV", f)
            pgdb1_conn.commit()
            if indx_val == indx_creation:
                pgdb1_cursor.execute(
                    f"""SELECT indexname FROM pg_indexes WHERE tablename ='{decile_tb}'  AND indexname ='{decile_tb}_email_idx'""")
                result = pgdb1_cursor.fetchone()
                if not result:
                    try:
                        logger.info(f"Adding index on email level on {decile_tb}")
                        pgdb1_cursor.execute(f"create index {decile_tb}_email_idx on  {decile_tb} (email) ")
                        pgdb1_conn.commit()  # Commit after index creation
                    except Exception as e:
                        logger.info("Unable to create index on table")
                        status_up("Unable to create index on TRT")
                        event.set()
                        return
                        killPid()
                        sys.exit(1)
                if sup_l == 'True':
                    pgdb1_cursor.execute(
                        f"""SELECT indexname FROM pg_indexes WHERE tablename ='{decile_tb}'  AND indexname ='{decile_tb}_md5_idx'""")
                    mresult = pgdb1_cursor.fetchone()
                    if not mresult:
                        try:
                            logger.info(f"Adding index on md5 level on {decile_tb}")
                            pgdb1_cursor.execute(f"create index {decile_tb}_md5_idx on  {decile_tb} (md5hash) ")
                            pgdb1_conn.commit()
                        except Exception as e:
                            logger.info("Unable to create Md5 index on table")
                            status_up("Unable to create md5 index on TRT")  # status_up is not defined
                            event.set()
                            return
                            killPid()
                            sys.exit(1)
        os.remove(d_file)
        logger.info(f"Temporary file {d_file} removed")
        dend_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_ex = datetime.strptime(dend_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(dstart_time,"%Y-%m-%d %H:%M:%S")
        logger.info(f"Execution time for decile {client}: {total_ex}")
    except Exception as e:
        logger.error(f"Error processing {client}: {e}", exc_info=True)
        status_up("Unable to pull data from RLTP")
        event.set()
        return
        killPid()
        sys.exit(1)
    finally:
        if 'sf_cursor' in locals() and sf_cursor:
            sf_cursor.close()
        if 'sf_conn' in locals() and sf_conn:
            sf_conn.close()
        if 'pgdb1_cursor' in locals() and pgdb1_cursor:
            pgdb1_cursor.close()
        if 'pgdb1_conn' in locals() and pgdb1_conn:
            pgdb1_conn.close()


if __name__ == "__main__":
    try:
        global logger, path, df
        n = 1
        request_id = sys.argv[1]

        # Track main process
        track_command = f"""
        track_process() {{
            source /u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/$1/ETC/config.properties
            source $TRACKING_HELPER
            append_process_id $1 "RLTP_MAIN"
        }}
        track_process {request_id}
        """
        subprocess.run(["bash", "-c", track_command], check=False)

        path = (
                "/u1/techteam/PFM_CUSTOM_SCRIPTS/APT_TOOL_DB/REQUEST_PROCESSING/"
                + request_id
        )

        lpath = f"{path}/LOGS"
        logger = log_module.setup_logging(lpath)
        logger.info("Logs path: {}".format(lpath))
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("RLTP data pulling started at : " + start_time)

        pgdb1_conn, pgdb1_cursor = getPgConnection()
        df = pd.read_sql(
            "SELECT a.request_id,a.week,a.query,a.decile_wise_report_path,b.client_name,a.SUPP_PATH,a.client_id FROM APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND a,apt_custom_client_info_table_dnd b  WHERE request_id="
            + request_id
            + " and a.client_id=b.client_id",
            con=pgdb1_conn,
        )
        trt_tb = (f"apt_custom_{df['request_id'][0]}_{df['client_name'][0]}_{df['week'][0]}_trt_table").lower()
        decile_report = pd.read_csv(df['decile_wise_report_path'][0], sep='|', header=None, thousands=',')
        decile_report.columns = ['Delivered', 'Opens', 'clicks', 'unsubs', 'segment', 'sub_seg', 'decile', 'old_per']
        dcnt = len(decile_report['decile'].drop_duplicates())
        client_id = int(df["client_id"][0])
        Audit_TRT_limit = decile_report["Delivered"].sum() + 5000000

        client = ""
        sup_l = 'True'
        sup_p = df['supp_path'][0]
        if sup_p != '':
            sup = pd.read_csv(sup_p, nrows=10, header=None)
            if not sup[0].str.contains('@').any():
                logger.info("Adding index on md5 level")
                sup_l = 'True'

        # Extract the number from df['query'] and modify the query string
        modified_queries = []
        extracted_numbers = []
        for query_string in df['query'][0].split(';'):
            match = re.search(r'apt_rltp_request_raw_(\d+)_postback_file', query_string)
            if match:
                extracted_number = match.group(1)
                extracted_numbers.append(extracted_number)
                # Insert the rltpid into the select clause
                modified_query = query_string.replace("priority", f"priority,'{extracted_number}' as rltpid", 1)
                modified_queries.append(modified_query)
            else:
                # Handle the case where no number was extracted (e.g., log an error or keep the original query)
                logger.warning(f"No number extracted from query: {query_string}. Keeping original query.")
                modified_queries.append(query_string)

        df['query'] = ";".join(modified_queries)
        qry = df['query'][0].split(';')
        qry = [item for item in qry if re.search(r"apt_rltp_request_raw_", item)]
        indx_creation = len(qry)
        sf_conn, sf_cursor = getSnowflake()
        if qry:
            sqr = qry[0] + ' LIMIT 3'
            try:
                samp = pd.read_sql(sqr, con=sf_conn)
            except Exception as e:
                logger.error("Unable to pull sample data from presto ::{}".format(e))
                status_up("Unable to pull data from RLTP")
                killPid()
                sys.exit(1)
            logger.info(samp)
            sf_conn.close()  # Close connection after sample pull
        else:
            logger.error("Snowflake query is not valid. Exiting.")
            status_up("Unable to pull data from RLTP")
            sys.exit(1)

        std_cols = ['md5hash', 'email', 'segment', 'subseg', 'decile', 'priority']
        req_cols = std_cols + list(samp.columns)[6::]  # Ensure no duplicates
        colsn = ' varchar,'.join(req_cols) + ' varchar'

        engine = create_engine('postgresql+psycopg2://datateam:@zds-prod-pgdb01-01.bo3.e-dialog.com/apt_tool_db')
        inspector = inspect(engine)
        try:
            if not inspector.has_table(trt_tb):
                pgdb1_cursor.execute(f"CREATE TABLE {trt_tb} ({colsn}) PARTITION BY LIST(decile)")
                for i in list(decile_report['decile'].drop_duplicates()):
                    pgdb1_cursor.execute(f"CREATE TABLE {trt_tb}_{i} PARTITION OF {trt_tb} FOR VALUES IN ('{i}')")
                pgdb1_conn.commit()
                logger.info('Tables created')
        except Exception as e:
            logger.error("Unable to create TRT tables")
            status_up("Unable to create TRT tables")
            killPid()
            sys.exit(1)
        indx_val = 1
        for qr in qry:
            if re.findall('apt_rltp_request_raw_', qr):
                dec = str(qr.split(",")[4].strip().split()[0])
                deciles_ = 'False'
                decilel = sorted(list(decile_report['decile'].drop_duplicates()), reverse=True)
                if decilel[0] == 1 or dec == "'1'":
                    decilel = [1]
                if dcnt != 1 and dec != "'1'":
                    deciles_ = 'True'
                    decilel = sorted(list(decile_report['decile'].drop_duplicates()), reverse=True)
                logger.info('Executing single decile function')
                try:
                    manager = Manager()
                    shared_event = manager.Event()
                    with Pool(processes=min(cpu_count(), 5), initializer=init_worker, initargs=(shared_event,)) as pool:
                        pool.map(main,
                                 [(client, trt_tb, qr, sup_l, n, deciles_, path, client_id, Audit_TRT_limit, indx_val, indx_creation) for client
                                  in decilel])
                    indx_val = indx_val + 1
                    logger.info("All threads for TRT are completed.")
                except Exception as e:
                    logger.error("An error occurred: %s", str(e), exc_info=True)
                    status_up("Failed to Launch Worker nodes for TRT")
                    killPid()
                    sys.exit(1)
                time.sleep(2)
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Script ended at: {end_time}")
        total_ex = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        logger.info(f"Total Time taken: {total_ex}")
        pgdb1_cursor.execute(f"update APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND set request_desc='TRT Imported' where  request_id={sys.argv[1]}")
        pgdb1_cursor.execute(f"select count(email) from {trt_tb}")
        cnt = list(pgdb1_cursor.fetchone())[0]
        pgdb1_cursor.execute(f" update apt_custom_postback_qa_table_dnd set RLTP_FILE_COUNT={cnt} where request_id={sys.argv[1]}")
        logger.info(f"RLTP data pulling ended at : {total_ex}")
    except Exception as e:
        logger.error("Unable to pull data from RLTP ::{}".format(e))
        status_up("Unable to pull data from RLTP")
        pool.terminate()
        pool.join()
        killPid()
        sys.exit(1)
    finally:
        pgdb1_cursor.close()
        pgdb1_conn.close()