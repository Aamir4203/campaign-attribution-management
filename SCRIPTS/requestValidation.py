#!/usr/bin/env python3
"""
Backend Request Validation Script for Campaign Attribution Management
Performs validations that frontend cannot handle:
- Query execution validation against Snowflake
- Database table existence checks
- RLTP ID verification
- Server-side file validation
- Database status updates

Frontend handles: file format, cross-file validations, data integrity
Backend handles: database connectivity, query correctness, business logic
"""

import sys
import os
import pandas as pd
import psycopg2
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from sqlalchemy import create_engine, inspect
import warnings

# Add current directory to path to import config_loader
sys.path.insert(0, os.path.dirname(__file__))
from config_loader import get_config

# Add Python modules path
sys.path.append("/u1/techteam/PFM_CUSTOM_SCRIPTS/PYTHON_MODULES")
from DbConns import getSnowflake

warnings.filterwarnings("ignore", category=UserWarning)

# Load configuration
config = get_config()

# Validation tracking
validation_results = []


class ValidationError(Exception):
    """Custom exception for validation failures"""
    def __init__(self, user_message, technical_details=""):
        self.user_message = user_message
        self.technical_details = technical_details
        super().__init__(user_message)


def add_validation(level: str, status: str):
    """Add validation result to tracking list"""
    validation_results.append({"level": level, "status": status})


def send_validation_email(validation_df, client_name, added_by, receiver_email):
    """Send validation failure email notification"""
    try:
        # Get email config from centralized configuration
        email_config = config.config.get('email', {})
        smtp_config = email_config.get('smtp', {})

        sender_email = email_config.get('sender', 'attributionalerts@zds-db3-02.bo3.e-dialog.com')
        smtp_host = smtp_config.get('host', 'localhost')
        smtp_port = smtp_config.get('port', 25)

        subject = f"APT BACKEND VALIDATION FAILED :: {client_name} :: {added_by}"

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject

        # Style cells based on status
        def style_cell(value):
            if value == "Failed":
                return "background-color: #EC7063; font-weight: bold"
            elif value == "Pass":
                return "background-color:#82E0AA"
            else:
                return ""

        styles = [
            {"selector": "th, td", "props": [("white-space", "nowrap"), ("border", "1px solid black")]},
            {"selector": "th", "props": [("background-color", "lightblue"), ("color", "black"), ("white-space", "nowrap")]},
            {"selector": "td", "props": [("border", "1px solid black"), ("color", "black"), ("text-align", "center")]}
        ]

        html_table = (
            validation_df.style
            .applymap(style_cell, subset=["Validation Status"])
            .set_table_styles(styles)
            .hide()
            .to_html(index=False)
        )

        html_content = f"""
        <html>
        <body>
        <p>Hi Team,</p><br>
        <p><b>Backend validation failed for request.</b> Please find the details below.</p><br>
        {html_table}
        <p><b>Action Required:</b> Review the failed validations and correct the request configuration.</p>
        <p><b>Note:</b> Frontend validation passed, but backend validation detected issues that require attention.</p>
        <p><b>Regards,<br>DataTeam - Automated Alert</b></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.sendmail(sender_email, receiver_email.split(","), msg.as_string())
        server.quit()
        print("✅ Validation failure email sent successfully")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def validate_query_execution(query_string, request_id, engine):
    """
    Validate that queries execute successfully against Snowflake
    This is the MOST CRITICAL validation - frontend cannot test this

    All RLTP data is now in Snowflake only (no Presto)
    """
    print("\n🔍 Validating query execution...")

    queries = [q.strip() for q in query_string.split(";") if q.strip()]

    if not queries:
        add_validation("Query Validation", "Failed")
        raise ValidationError("Input query is empty", "No queries found in query string")

    # Track RLTP IDs used in queries
    current_rltp_ids = []

    # Test first query for column structure
    test_query = queries[0] + " LIMIT 3"

    # Extract RLTP ID from query
    rltp_match = re.findall(r"apt_rltp_request_raw_(\d+)_postback_file", test_query)
    if not rltp_match:
        add_validation("Query Validation", "Failed")
        raise ValidationError(
            "Input query is incorrect - RLTP ID not found",
            "No apt_rltp_request_raw_*_postback_file pattern found in query"
        )

    rltp_id = int(rltp_match[0])
    current_rltp_ids.append(str(rltp_id))

    # Connect to Snowflake (all RLTP data is now in Snowflake)
    try:
        econn, _ = getSnowflake()
        print(f"   Connected to Snowflake for RLTP ID: {rltp_id}")
    except Exception as e:
        add_validation("Database Connection", "Failed")
        raise ValidationError(
            "Failed to connect to Snowflake database",
            f"Snowflake connection error: {str(e)}"
        )

    try:
        # Test first query and get column structure
        print(f"   Testing primary query...")
        try:
            sample_df = pd.read_sql(test_query, con=econn)
        except Exception as e:
            econn.close()
            error_str = str(e).lower()

            # User-friendly error messages based on common issues
            if 'does not exist' in error_str or 'not found' in error_str:
                add_validation("Query Validation", "Failed")
                raise ValidationError(
                    "Input query is incorrect - Table not found in Snowflake",
                    f"Query execution error: {str(e)[:200]}"
                )
            elif 'syntax' in error_str or 'parse' in error_str:
                add_validation("Query Validation", "Failed")
                raise ValidationError(
                    "Input query has syntax error",
                    f"SQL syntax error: {str(e)[:200]}"
                )
            elif 'column' in error_str:
                add_validation("Query Validation", "Failed")
                raise ValidationError(
                    "Input query is incorrect - Invalid column name",
                    f"Column error: {str(e)[:200]}"
                )
            else:
                add_validation("Query Validation", "Failed")
                raise ValidationError(
                    "Failed while pulling sample data from Snowflake",
                    f"Query execution error: {str(e)[:200]}"
                )

        expected_column_count = len(sample_df.columns)
        print(f"   ✓ Primary query executed successfully ({expected_column_count} columns)")

        # Check for duplicate column names
        col_list = list(sample_df.columns)
        seen = set()
        duplicates = set()
        for col in col_list:
            if col in seen:
                duplicates.add(col)
            else:
                seen.add(col)

        if duplicates:
            econn.close()
            dup_cols = ', '.join(list(duplicates)[:3])  # Show first 3
            add_validation("Query Validation", "Failed")
            raise ValidationError(
                f"Input query has duplicate columns: {dup_cols}",
                f"Duplicate columns found: {', '.join(list(duplicates))}"
            )

        print(f"   ✓ No duplicate column names")

        # Test remaining queries (if any)
        for i, query in enumerate(queries[1:], start=2):
            if not query:
                continue

            if "apt_rltp_request_raw_" in query:
                rltp_match = re.findall(r"apt_rltp_request_raw_(\d+)_postback_file", query)
                if rltp_match:
                    rltp_id = int(rltp_match[0])
                    current_rltp_ids.append(str(rltp_id))

                    test_sub_query = query + " LIMIT 3"
                    try:
                        print(f"   Testing query {i}...")
                        sub_df = pd.read_sql(test_sub_query, con=econn)

                        # Verify column count matches
                        if len(sub_df.columns) != expected_column_count:
                            econn.close()
                            add_validation(f"Query {i} Validation", "Failed")
                            raise ValidationError(
                                f"Query {i} has mismatched column count",
                                f"Query {i} column count ({len(sub_df.columns)}) != expected ({expected_column_count})"
                            )

                        print(f"   ✓ Query {i} executed successfully")
                    except ValidationError:
                        raise
                    except Exception as e:
                        econn.close()
                        add_validation(f"Query {i} Validation", "Failed")
                        raise ValidationError(
                            f"Failed while pulling sample data from query {i}",
                            f"Query {i} error: {str(e)[:200]}"
                        )

        econn.close()
        add_validation("Query Validation", "Pass")
        print("✅ All queries validated successfully")
        return current_rltp_ids

    except ValidationError:
        raise
    except Exception as e:
        try:
            econn.close()
        except:
            pass
        add_validation("Query Validation", "Failed")
        raise ValidationError(
            "Failed while pulling sample data from Snowflake",
            f"Unexpected error: {str(e)[:200]}"
        )


def validate_rltp_id_uniqueness(current_rltp_ids, client_id, engine, weekly_new_rltp_flag):
    """
    Verify RLTP ID is different from last week's request
    Prevents using stale data
    """
    print("\n🔍 Validating RLTP ID uniqueness...")

    if int(weekly_new_rltp_flag) != 1:
        print("   ⊘ RLTP ID uniqueness check skipped (weeklynewrltpid != 1)")
        return

    try:
        # Get table name from config
        request_table = config.get_table('requests')

        # Get last completed request's RLTP IDs
        prev_query = f"""
            SELECT query FROM {request_table}
            WHERE client_id={client_id}
            AND request_status='C'
            ORDER BY request_id DESC
            LIMIT 1 OFFSET 1
        """

        prev_df = pd.read_sql(prev_query, con=engine)

        if not prev_df.empty:
            prev_queries = prev_df["query"][0].split(";")
            prev_rltp_ids = []

            for query in prev_queries:
                rltp_match = re.findall(r"apt_rltp_request_raw_(\d+)_postback_file", query)
                if rltp_match:
                    prev_rltp_ids.append(rltp_match[0])

            # Check for overlap
            overlap = set(current_rltp_ids) & set(prev_rltp_ids)
            if overlap:
                overlap_str = ', '.join(overlap)
                add_validation("RLTP ID Uniqueness", "Failed")
                raise ValidationError(
                    f"RLTP ID {overlap_str} is same as last week",
                    f"RLTP ID(s) {overlap_str} already used in previous request"
                )

            print(f"   ✓ RLTP IDs are unique (current: {current_rltp_ids}, previous: {prev_rltp_ids})")
            add_validation("RLTP ID Uniqueness", "Pass")
        else:
            print("   ⊘ No previous completed request found, skipping uniqueness check")

    except ValidationError:
        raise
    except Exception as e:
        print(f"   ⚠ Warning: Could not verify RLTP ID uniqueness: {e}")


def validate_database_tables(client_info, engine):
    """
    Verify that required client tables exist in database
    Frontend cannot check this
    """
    print("\n🔍 Validating database table existence...")

    inspector = inspect(engine)
    tables_to_check = [
        ("prev_week_pb_table", client_info.get("prev_week_pb_table")),
        ("total_delivered_table", client_info.get("total_delivered_table")),
        ("posted_unsub_hards_table", client_info.get("posted_unsub_hards_table"))
    ]

    for table_type, table_name in tables_to_check:
        if not table_name or pd.isna(table_name):
            print(f"   ⊘ {table_type} not configured, skipping")
            continue

        table_name = str(table_name).strip()
        if inspector.has_table(table_name.lower()):
            print(f"   ✓ {table_name} exists")
            add_validation(table_name, "Pass")
        else:
            add_validation(table_name, "Failed")
            raise ValidationError(
                f"Database table {table_name} not found",
                f"Required table {table_name} does not exist in PostgreSQL database"
            )

    print("✅ All database tables validated successfully")


def validate_suppression_file(supp_path):
    """
    Validate suppression file exists on server filesystem
    Frontend only validates uploaded files, not server files
    """
    print("\n🔍 Validating suppression file...")

    if not supp_path or "/" not in str(supp_path) or pd.isna(supp_path):
        print("   ⊘ No suppression file path provided")
        return

    supp_path = str(supp_path).strip()
    if os.path.isfile(supp_path):
        print(f"   ✓ Suppression file exists: {supp_path}")
        add_validation("Suppression File", "Pass")
    else:
        add_validation("Suppression File", "Failed")
        raise ValidationError(
            "Suppression file not found on server",
            f"File not found: {supp_path}"
        )


def validate_residual_date(residual_date, cpm_report_path):
    """
    Validate residual date >= max CPM report date
    """
    print("\n🔍 Validating residual date...")

    if not cpm_report_path or pd.isna(cpm_report_path):
        print("   ⊘ CPM report path not provided, skipping residual date validation")
        return

    cpm_report_path = str(cpm_report_path).strip()
    if not os.path.isfile(cpm_report_path):
        print("   ⊘ CPM report file not found, skipping residual date validation")
        return

    try:
        # Read CPM report to get max date
        cpm_df = pd.read_csv(cpm_report_path, sep="|", header=0)

        # Column 1 is the date column
        max_cpm_date = pd.to_datetime(cpm_df.iloc[:, 1]).max()
        residual_dt = pd.to_datetime(residual_date)

        if residual_dt >= max_cpm_date:
            print(f"   ✓ Residual date ({residual_dt.date()}) >= max CPM date ({max_cpm_date.date()})")
            add_validation("Residual Date", "Pass")
        else:
            add_validation("Residual Date", "Failed")
            raise ValidationError(
                f"Residual date {residual_dt.date()} is before max CPM date {max_cpm_date.date()}",
                f"Residual date must be >= max CPM date"
            )

    except ValidationError:
        raise
    except Exception as e:
        print(f"   ⚠ Warning: Could not validate residual date: {e}")


def validate_week_name(week_name):
    """
    Validate week name length (must be <= 6 characters)
    """
    print("\n🔍 Validating week name...")

    if not week_name or pd.isna(week_name):
        add_validation("Week Name", "Failed")
        raise ValidationError(
            "Week name is required",
            "Week name field is empty"
        )

    week_name = str(week_name).strip()
    if len(week_name) > 6:
        add_validation("Week Name", "Failed")
        raise ValidationError(
            f"Week name '{week_name}' is too long (max 6 characters)",
            f"Week name length: {len(week_name)}"
        )

    print(f"   ✓ Week name '{week_name}' is valid (length: {len(week_name)})")


def update_request_status(cur, request_table, request_id, validation_status, description):
    """Update request validation status in database"""
    try:
        # Escape single quotes in description
        description = str(description).replace("'", "''")

        update_query = f"""
            UPDATE {request_table}
            SET request_validation='{validation_status}',
                request_desc='{description}'
            WHERE request_id={request_id}
        """
        cur.execute(update_query)
        print(f"   ✓ Request validation status updated to '{validation_status}'")
    except Exception as e:
        print(f"   ❌ Failed to update request status: {e}")
        raise


def main():
    """Main validation workflow"""
    if len(sys.argv) < 2:
        print("❌ Usage: python3 requestValidation.py <request_id>")
        sys.exit(1)

    request_id = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"Backend Request Validation - Request ID: {request_id}")
    print(f"{'='*60}")

    # Get database configuration from centralized config
    db_config = config.config.get('database', {})
    postgres_cfg = db_config.get('postgres', {})

    pg_config = {
        "host": postgres_cfg.get('host'),
        "port": postgres_cfg.get('port', 5432),
        "dbname": postgres_cfg.get('database'),
        "user": postgres_cfg.get('user')
    }

    # Build connection string
    connection_string = f"postgresql+psycopg2://{pg_config['user']}:@{pg_config['host']}/{pg_config['dbname']}"
    engine = create_engine(connection_string)

    conn = None
    cur = None

    # Get table names from config
    request_table = config.get_table('requests')
    client_table = config.get_table('clients')

    # Get email config
    email_config = config.config.get('email', {})
    receiver_email = email_config.get('alert_to', 'vmarni@zetaglobal.com,datateam@aptroid.com')

    try:
        # Connect to database
        conn = psycopg2.connect(**pg_config)
        conn.autocommit = True
        cur = conn.cursor()

        # Set initial validation status
        update_request_status(cur, request_table, request_id, 'V', 'Backend validation in progress')

        # Load request details
        print("\n📋 Loading request details...")
        request_df = pd.read_sql(
            f"SELECT * FROM {request_table} WHERE request_id={request_id}",
            con=engine
        )

        if request_df.empty:
            raise ValidationError(
                "Request not found in database",
                f"Request ID {request_id} not found"
            )

        request_data = request_df.iloc[0]

        # Load client info
        client_df = pd.read_sql(
            f"SELECT * FROM {client_table} WHERE client_id={request_data['client_id']}",
            con=engine
        )

        if client_df.empty:
            raise ValidationError(
                "Client not found in database",
                f"Client ID {request_data['client_id']} not found"
            )

        client_info = client_df.iloc[0]

        print(f"   ✓ Request ID: {request_id}")
        print(f"   ✓ Client: {client_info['client_name']} (ID: {client_info['client_id']})")
        print(f"   ✓ Added by: {request_data['added_by']}")

        # Add basic info to validation results
        add_validation("Request ID", request_id)
        add_validation("Client ID", str(client_info['client_id']))
        add_validation("Client Name", client_info['client_name'])

        # Run backend validations
        print(f"\n{'='*60}")
        print("Starting Backend Validations")
        print(f"{'='*60}")

        # 1. Query execution validation (MOST CRITICAL) - Snowflake only
        current_rltp_ids = validate_query_execution(
            request_data["query"],
            request_id,
            engine
        )

        # 2. RLTP ID uniqueness check
        validate_rltp_id_uniqueness(
            current_rltp_ids,
            request_data["client_id"],
            engine,
            client_info["weeklynewrltpid"]
        )

        # 3. Database table existence
        validate_database_tables(client_info, engine)

        # 4. Suppression file validation
        validate_suppression_file(request_data.get("supp_path"))

        # 5. Residual date validation
        validate_residual_date(
            request_data.get("residual_date"),
            request_data.get("cpm_report_path")
        )

        # 6. Week name validation
        validate_week_name(request_data.get("week"))

        # Add "Added by" at the end
        add_validation("Added by", request_data['added_by'])

        # All validations passed
        print(f"\n{'='*60}")
        print("✅ ALL BACKEND VALIDATIONS PASSED")
        print(f"{'='*60}")

        # Update request status to success
        update_request_status(cur, request_table, request_id, 'Y', 'Backend validation passed - Ready for processing')

        sys.exit(0)

    except ValidationError as ve:
        print(f"\n{'='*60}")
        print(f"❌ VALIDATION FAILED: {ve.user_message}")
        print(f"{'='*60}")

        # Update request status with user-friendly message
        if cur:
            update_request_status(cur, request_table, request_id, 'N', ve.user_message)

        # Create validation report
        validation_df = pd.DataFrame(validation_results)
        validation_df.columns = ["Validation Case", "Validation Status"]

        print("\nValidation Report:")
        print(validation_df.to_string(index=False))

        # Send email notification with technical details
        if 'request_data' in locals() and 'client_info' in locals():
            # Add technical details to validation report for email
            if ve.technical_details:
                print(f"\nTechnical Details: {ve.technical_details}")

            send_validation_email(
                validation_df,
                client_info['client_name'],
                request_data['added_by'],
                receiver_email
            )

        sys.exit(1)

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ UNEXPECTED ERROR: {e}")
        print(f"{'='*60}")

        error_msg = f"Validation error: {str(e)[:100]}"
        add_validation("System Error", "Failed")

        if cur:
            update_request_status(cur, request_table, request_id, 'N', error_msg)

        sys.exit(1)

    finally:
        # Cleanup
        if cur:
            cur.close()
        if conn:
            conn.close()
        if engine:
            engine.dispose()


if __name__ == "__main__":
    main()
