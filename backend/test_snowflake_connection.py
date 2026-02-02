#!/usr/bin/env python3
"""
Test Snowflake Connection
Quick script to verify Snowflake credentials and connection
"""

import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

print("=" * 80)
print("SNOWFLAKE CONNECTION TEST")
print("=" * 80)
print()

# Check if credentials are loaded
print("📋 Checking environment variables...")
sf_account = os.getenv('SF_ACCOUNT')
sf_user = os.getenv('SF_USER')
sf_password = os.getenv('SF_PASSWORD')
sf_warehouse = os.getenv('SF_WAREHOUSE')
sf_database = os.getenv('SF_DATABASE')
sf_schema = os.getenv('SF_SCHEMA')
sf_private_key_path = os.getenv('SF_PRIVATE_KEY_PATH')
sf_private_key_passphrase = os.getenv('SF_PRIVATE_KEY_PASSPHRASE')

# Check for either password or private key auth
has_password = bool(sf_password)
has_private_key = bool(sf_private_key_path and sf_private_key_passphrase)

if not all([sf_account, sf_user, sf_warehouse, sf_database, sf_schema]):
    print("❌ Missing required Snowflake credentials in .env file")
    print(f"   SF_ACCOUNT: {'✓' if sf_account else '✗'}")
    print(f"   SF_USER: {'✓' if sf_user else '✗'}")
    print(f"   SF_WAREHOUSE: {'✓' if sf_warehouse else '✗'}")
    print(f"   SF_DATABASE: {'✓' if sf_database else '✗'}")
    print(f"   SF_SCHEMA: {'✓' if sf_schema else '✗'}")
    sys.exit(1)

if not has_password and not has_private_key:
    print("❌ Must provide either password or private key authentication")
    print(f"   SF_PASSWORD: {'✓' if has_password else '✗'}")
    print(f"   SF_PRIVATE_KEY_PATH: {'✓' if sf_private_key_path else '✗'}")
    print(f"   SF_PRIVATE_KEY_PASSPHRASE: {'✓' if sf_private_key_passphrase else '✗'}")
    sys.exit(1)

print("✅ All credentials found in environment")
print()
print(f"   Account:   {sf_account}")
print(f"   User:      {sf_user}")

if has_private_key:
    print(f"   Auth:      Private Key ({sf_private_key_path})")
    print(f"   Passphrase: {'*' * 10}")
elif has_password:
    print(f"   Auth:      Password")
    print(f"   Password:  {'*' * len(sf_password)}")

print(f"   Warehouse: {sf_warehouse}")
print(f"   Database:  {sf_database}")
print(f"   Schema:    {sf_schema}")
print()

# Try to import snowflake connector
print("📦 Checking snowflake-connector-python...")
try:
    import snowflake.connector
    print("✅ snowflake-connector-python installed")
except ImportError as e:
    print(f"❌ snowflake-connector-python not installed: {e}")
    print("   Run: pip install snowflake-connector-python")
    sys.exit(1)

print()
print("🔌 Attempting connection to Snowflake...")
print()

try:
    # Import and use the SnowflakeService class
    from services.snowflake_service import SnowflakeService

    sf_service = SnowflakeService()
    conn = sf_service.connect()

    print("✅ CONNECTION SUCCESSFUL!")
    print()

    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_VERSION()")
    version = cursor.fetchone()[0]
    print(f"   Snowflake Version: {version}")

    cursor.execute("SELECT CURRENT_WAREHOUSE()")
    warehouse = cursor.fetchone()[0]
    print(f"   Current Warehouse: {warehouse}")

    cursor.execute("SELECT CURRENT_DATABASE()")
    database = cursor.fetchone()[0]
    print(f"   Current Database: {database}")

    cursor.execute("SELECT CURRENT_SCHEMA()")
    schema = cursor.fetchone()[0]
    print(f"   Current Schema: {schema}")

    cursor.execute("SELECT CURRENT_ROLE()")
    role = cursor.fetchone()[0]
    print(f"   Current Role: {role}")

    cursor.close()
    sf_service.disconnect()

    print()
    print("=" * 80)
    print("✅ ALL TESTS PASSED - Snowflake connection is working!")
    print("=" * 80)

except Exception as e:
    print(f"❌ CONNECTION FAILED: {e}")
    print()
    print("Common issues:")
    print("  1. Check account format (should be: account_locator.region)")
    print("  2. Verify credentials are correct")
    print("  3. Check network/firewall settings")
    print("  4. Ensure warehouse is running")
    print("  5. For private key auth: verify key file exists and passphrase is correct")
    print()
    import traceback
    print("Full error trace:")
    traceback.print_exc()
    print()
    sys.exit(1)
