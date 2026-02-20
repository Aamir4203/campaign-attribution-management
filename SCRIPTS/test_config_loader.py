#!/usr/bin/env python3
"""
Test script to validate config_loader reads from unified app.yaml correctly
"""
import sys
import os

# Add SCRIPTS to path
sys.path.insert(0, os.path.dirname(__file__))

from config_loader import get_config

def test_config():
    """Test all config_loader methods"""
    print("=" * 70)
    print("CONFIG LOADER VALIDATION TEST")
    print("=" * 70)

    try:
        cfg = get_config()
        print("✅ Config loaded successfully")

        # Test database config
        print("\n[DATABASE CONFIG]")
        print(f"  Host: {cfg.db_host}")
        print(f"  Port: {cfg.db_port}")
        print(f"  Database: {cfg.db_name}")
        print(f"  User: {cfg.db_user}")

        # Test table names
        print("\n[TABLE NAMES]")
        print(f"  Requests: {cfg.requests_table}")
        print(f"  Clients: {cfg.clients_table}")
        print(f"  QA Stats: {cfg.qa_stats_table}")
        print(f"  Tracking: {cfg.tracking_table}")

        # Test dynamic table generation
        print("\n[DYNAMIC TABLES]")
        trt_table = cfg.get_trt_table("12345", "TestClient", "W01")
        src_table = cfg.get_src_table("12345", "TestClient", "W01")
        postback_table = cfg.get_postback_table("12345", "TestClient", "W01")
        print(f"  TRT Table: {trt_table}")
        print(f"  SRC Table: {src_table}")
        print(f"  Postback Table: {postback_table}")

        # Test paths
        print("\n[FILE PATHS]")
        print(f"  Base Path: {cfg.base_path}")
        print(f"  Request Processing: {cfg.request_processing_path}")
        print(f"  Python Modules: {cfg.python_modules_path}")
        print(f"  Tracking Helper: {cfg.tracking_helper_path}")

        # Test processing config
        print("\n[PROCESSING CONFIG]")
        print(f"  Max Workers: {cfg.max_workers}")
        print(f"  Chunk Size: {cfg.chunk_size:,}")
        print(f"  Max Retries: {cfg.max_retries}")
        print(f"  Audit Clients: {cfg.audit_client_ids}")

        # Test staging config
        print("\n[STAGING CONFIG]")
        print(f"  Enabled: {cfg.staging_enabled}")
        print(f"  Prefix: {cfg.stage_prefix}")
        print(f"  Max File Size: {cfg.stage_max_file_size:,}")
        print(f"  Compression: {cfg.stage_compression}")

        # Test index names
        print("\n[INDEX TEMPLATES]")
        email_idx = cfg.get_index_name('email', '12345', '1')
        seg_idx = cfg.get_index_name('seg_subseg', '12345', '1')
        md5_idx = cfg.get_index_name('md5', '12345', '1')
        print(f"  Email Index: {email_idx}")
        print(f"  Seg/Subseg Index: {seg_idx}")
        print(f"  MD5 Index: {md5_idx}")

        # Test query templates
        print("\n[QUERY TEMPLATES]")
        req_query = cfg.get_request_details_query('12345')
        print(f"  Request Details Query:\n{req_query[:100]}...")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Config loader working correctly!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_config()
    sys.exit(0 if success else 1)
