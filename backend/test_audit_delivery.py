#!/usr/bin/env python3
"""
Quick Validation Script for Audit Delivery Implementation
Tests LPT connection, configuration, and basic functionality
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_config():
    """Test configuration loading"""
    logger.info("=" * 60)
    logger.info("TEST 1: Configuration Loading")
    logger.info("=" * 60)

    try:
        from config.config import get_config
        config = get_config()

        # Test audit config
        audit_config = config.get_snowflake_audit_config()

        if not audit_config:
            logger.error("❌ Audit config not found in app.yaml")
            return False

        # Check required fields
        conn_config = audit_config.get('connection', {})
        required_fields = ['account', 'user', 'database', 'schema', 'warehouse', 'private_key_path']

        missing = [f for f in required_fields if not conn_config.get(f)]

        if missing:
            logger.error(f"❌ Missing required config fields: {missing}")
            return False

        logger.info(f"✅ Audit configuration loaded successfully")
        logger.info(f"   Account: {conn_config.get('account')}")
        logger.info(f"   User: {conn_config.get('user')}")
        logger.info(f"   Database: {conn_config.get('database')}")
        logger.info(f"   Schema: {conn_config.get('schema')}")
        logger.info(f"   Warehouse: {conn_config.get('warehouse')}")
        logger.info(f"   Private Key Path: {conn_config.get('private_key_path')}")

        # Check fixed header
        columns_config = audit_config.get('columns', {})
        fixed_header = columns_config.get('fixed_header', [])

        if len(fixed_header) != 10:
            logger.warning(f"⚠️ Expected 10 fixed header columns, found {len(fixed_header)}")
        else:
            logger.info(f"✅ Fixed header has 10 columns as expected")
            header_names = [col['name'] for col in fixed_header]
            logger.info(f"   Header: {' | '.join(header_names)}")

        # Check table schema
        table_schema = columns_config.get('table_schema', [])

        if len(table_schema) != 37:
            logger.warning(f"⚠️ Expected 37 table schema columns, found {len(table_schema)}")
        else:
            logger.info(f"✅ Table schema has 37 columns as expected")

        return True

    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_private_key():
    """Test private key loading"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Private Key Loading")
    logger.info("=" * 60)

    try:
        from services.snowflake_audit_service import SnowflakeAuditService

        logger.info("Initializing SnowflakeAuditService...")
        service = SnowflakeAuditService()

        logger.info("✅ Private key loaded and decrypted successfully")
        logger.info(f"   Key size: {len(service.private_key_bytes)} bytes")

        return True

    except FileNotFoundError as e:
        logger.error(f"❌ Private key file not found: {e}")
        logger.error("   Please verify private_key_path in app.yaml")
        return False
    except Exception as e:
        logger.error(f"❌ Private key loading failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_lpt_connection():
    """Test LPT Snowflake connection"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: LPT Snowflake Connection")
    logger.info("=" * 60)

    try:
        from services.snowflake_audit_service import SnowflakeAuditService

        logger.info("Connecting to LPT Snowflake...")
        service = SnowflakeAuditService()
        conn = service.connect()

        if not conn or conn.is_closed():
            logger.error("❌ Failed to establish connection")
            return False

        logger.info("✅ Connected to LPT Snowflake successfully")

        # Test query
        logger.info("Testing query execution...")
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION(), CURRENT_TIMESTAMP()")
        result = cursor.fetchone()

        logger.info(f"✅ Query executed successfully")
        logger.info(f"   Snowflake Version: {result[0]}")
        logger.info(f"   Server Time: {result[1]}")

        cursor.close()
        service.disconnect()

        logger.info("✅ Connection closed successfully")

        return True

    except Exception as e:
        logger.error(f"❌ LPT connection test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_table_naming():
    """Test table name generation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Table Name Generation")
    logger.info("=" * 60)

    try:
        from services.snowflake_audit_service import SnowflakeAuditService

        service = SnowflakeAuditService()

        test_cases = [
            (2026, 'JANUARY', 'CUSTOM_ZX_STATS_MASTER_2026_JANUARY'),
            (2026, 'FEBRUARY', 'CUSTOM_ZX_STATS_MASTER_2026_FEBRUARY'),
            (2025, 'DECEMBER', 'CUSTOM_ZX_STATS_MASTER_2025_DECEMBER'),
        ]

        all_passed = True
        for year, month, expected in test_cases:
            result = service.generate_audit_table_name(year, month)
            if result == expected:
                logger.info(f"✅ {year}-{month} → {result}")
            else:
                logger.error(f"❌ {year}-{month} → Expected: {expected}, Got: {result}")
                all_passed = False

        return all_passed

    except Exception as e:
        logger.error(f"❌ Table naming test failed: {e}")
        return False


def main():
    """Run all validation tests"""
    logger.info("\n" + "🚀 AUDIT DELIVERY VALIDATION SUITE")
    logger.info("=" * 60)

    results = {
        'Configuration Loading': test_config(),
        'Private Key Loading': test_private_key(),
        'LPT Connection': test_lpt_connection(),
        'Table Name Generation': test_table_naming(),
    }

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status} - {test_name}")

    total = len(results)
    passed = sum(results.values())
    failed = total - passed

    logger.info("\n" + "=" * 60)
    logger.info(f"Total Tests: {total}")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info("=" * 60)

    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED! Implementation is ready for production.")
        return 0
    else:
        logger.error(f"\n⚠️ {failed} test(s) failed. Please review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
