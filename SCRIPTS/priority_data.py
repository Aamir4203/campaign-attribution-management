#!/usr/bin/env python3

import io
import os
import sys
import re
import logging
from datetime import datetime

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from snowflake.connector.pandas_tools import write_pandas

sys.path.append('/u1/techteam/PFM_CUSTOM_SCRIPTS/PYTHON_MODULES')
from DbConns1 import getConfig, getSnowflakeDT

# ================= LOGGING ================= #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================= ARGUMENTS ================= #
if len(sys.argv) < 2:
    raise SystemExit("Usage: python script.py <REQUEST_ID>")

REQUEST_ID = sys.argv[1]

# ================= CONSTANTS ================= #
SF_WAREHOUSE = "GREEN_DATA_TEAM"
SF_DATABASE = "GREEN"
SF_SCHEMA = "DT_DATA"

# ================= CONNECTIONS ================= #
PG_CONFIG = getConfig('pgdb01')
engine = create_engine(f"postgresql+psycopg2://{PG_CONFIG['user']}@{PG_CONFIG['host']}/{PG_CONFIG['dbname']}")
# ================= HELPERS ================= #

def sanitize_identifier(value: str) -> str:
    return re.sub(r'[^A-Z0-9_]', '_', value.upper())

def split_columns(select_str):
    cols, par, cur = [], 0, ''
    for ch in select_str:
        if ch == '(':
            par += 1
        elif ch == ')':
            par -= 1
        if ch == ',' and par == 0:
            cols.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur:
        cols.append(cur.strip())
    return cols

def extract_alias(col):
    parts = col.strip().split()
    alias = parts[-1] if len(parts) > 1 else parts[0].split('.')[-1]
    return 'decile' if alias.lower() == 'decile_' else alias

def read_headerless_md5_file(path):
    df = pd.read_csv(path, header=None, dtype=str, names=['md5hash'], low_memory=False)
    df['md5hash'] = df['md5hash'].str.strip().str.lower()
    return df.drop_duplicates(subset=['md5hash']).reset_index(drop=True)

def df_to_pg_copy(df, table_name):
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)

    with psycopg2.connect(**PG_CONFIG) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            cur.execute(f'CREATE TABLE "{table_name}" (md5hash TEXT)')
            cur.copy_expert(
                f'COPY "{table_name}"(md5hash) FROM STDIN WITH (FORMAT csv, HEADER TRUE)',
                buf
            )

def insert_df_to_snowflake(df, sf_conn, fq_table):
    df2 = df[['md5hash']].astype(str)
    ok, nchunks, nrows, _ = write_pandas(sf_conn, df2, table_name=fq_table.split('.')[-1], quote_identifiers=False)
    if not ok:
        raise RuntimeError("Snowflake write_pandas failed")
    logger.info(f"Loaded {nrows} rows into Snowflake table {fq_table}")

# ================= MAIN ================= #

def main():
    logger.info(f"Started processing for request_id={REQUEST_ID}")

    # ---- Fetch metadata safely ---- #
    client_df = pd.read_sql(text("""SELECT upper(client_name) AS client_name FROM APT_CUSTOM_CLIENT_INFO_TABLE_DND a JOIN APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND b ON a.client_id = b.client_id WHERE b.request_id = :rid """),con=engine,params={"rid": REQUEST_ID} )
    if client_df.empty:
        raise SystemExit("Invalid REQUEST_ID - no client found")

    CLIENT_NAME = sanitize_identifier(client_df['client_name'].iat[0])
    PRIORITY_TABLE = f"APT_CUSTOM_{REQUEST_ID}_{CLIENT_NAME}_PRIORITY_DATA"

    logger.info(f"Using priority table: {PRIORITY_TABLE}")

    meta_df = pd.read_sql(text(""" SELECT priority_file, query FROM APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND WHERE request_id = :rid """),con=engine,params={"rid": REQUEST_ID} )

    priority_file, query = meta_df.iloc[0]

    if not os.path.exists(priority_file):
        raise SystemExit(f"Priority file missing: {priority_file}")

    df = read_headerless_md5_file(priority_file)
    if df.empty:
        raise SystemExit("No md5 values found in file")

    # ---- Load into Postgres ---- #
    try:
        df_to_pg_copy(df, PRIORITY_TABLE)
        logger.info(f"Loaded {len(df)} md5s into Postgres table {PRIORITY_TABLE}")
    except Exception:
        logger.exception("Postgres load failed")
        raise

    # ---- Load into Snowflake ---- #
    try:
        sf_conn, sf_cur = getSnowflakeDT('DataTeamSf1', warehouse=SF_WAREHOUSE, dbname=SF_DATABASE, schema=SF_SCHEMA)
        fq_table = f"{SF_DATABASE}.{SF_SCHEMA}.{PRIORITY_TABLE}"
        sf_cur.execute(f'DROP TABLE IF EXISTS {fq_table}')
        sf_cur.execute(f'CREATE TABLE {fq_table} (md5hash VARCHAR)')

        insert_df_to_snowflake(df, sf_conn, fq_table)

    except Exception:
        logger.exception("Snowflake operation failed")
        raise
    finally:
        sf_cur.close()
        sf_conn.close()

    # ---- Query Rewrite ---- #
    wrapped_queries = []

    for q in [x.strip() for x in query.split(';') if x.strip()]:
        m = re.search(r"select\s+(.*)\s+from", q, re.I | re.S)
        if not m:
            raise Exception("Cannot parse SELECT clause")

        col_list = split_columns(m.group(1))
        mapped_cols = []

        for col in col_list:
            if re.search(r'\bpriority\b', col, re.I):
                mapped_cols.append("CASE WHEN p.md5hash IS NOT NULL THEN 1 ELSE inner_q.priority + 1 END AS priority")
            elif re.match(r"^('.*'|\d+|case\s+when|\(.*\))", col, re.I):
                mapped_cols.append(re.sub(r"\bdecile_\b", "decile", col, flags=re.I))
            else:
                alias = extract_alias(col)
                mapped_cols.append(f"inner_q.{alias}")

        wrapped = f"""SELECT {", ".join(mapped_cols)} FROM ({q}) inner_q LEFT JOIN {fq_table} p ON inner_q.md5hash = p.md5hash """
        wrapped_queries.append(" ".join(wrapped.split()))

    final_query = "; ".join(wrapped_queries) + ";"

    with engine.begin() as conn:
        conn.execute(text("""UPDATE APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND SET query = :q WHERE request_id = :r """),{"q": final_query, "r": REQUEST_ID})
    logger.info("Query updated successfully")
    logger.info("Process completed successfully")

# ================= RUN ================= #
if __name__ == "__main__":
    main()
