#!/usr/bin/env python3
"""Test different Snowflake account formats"""
import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

# Try different account formats
account_formats = [
    "zeta_hub_reader",
    "zeta_hub_reader.us-east-1",
    "ZETA_HUB_READER",
    "ZETA_HUB_READER.US-EAST-1",
]

sf_user = os.getenv('SF_USER')
sf_password = os.getenv('SF_PASSWORD')
sf_warehouse = os.getenv('SF_WAREHOUSE')
sf_database = os.getenv('SF_DATABASE')
sf_schema = os.getenv('SF_SCHEMA')

print("Testing different account formats...")
print()

for account in account_formats:
    print(f"Trying: {account}")
    try:
        conn = snowflake.connector.connect(
            account=account,
            user=sf_user,
            password=sf_password,
            warehouse=sf_warehouse,
            database=sf_database,
            schema=sf_schema
        )
        print(f"  ✅ SUCCESS with format: {account}")
        conn.close()
        break
    except Exception as e:
        error_str = str(e)
        if "404" in error_str:
            print(f"  ❌ 404 - Account not found")
        elif "Incorrect username or password" in error_str:
            print(f"  ❌ Auth failed - but account exists!")
        else:
            print(f"  ❌ Error: {error_str[:100]}")
    print()

print("\nIf all formats failed, you may need to:")
print("1. Check your Snowflake account URL in the Snowflake web console")
print("2. The account identifier might include an organization prefix (orgname-accountname)")
print("3. Contact your Snowflake administrator for the correct account identifier")
