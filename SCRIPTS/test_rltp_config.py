#!/usr/bin/env python3
"""
Validation test for rltpDataPulling_v2.py config integration
Tests that all config values used by the script are accessible
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from config_loader import get_config

def test_rltp_config():
    """Test all config values used by rltpDataPulling_v2.py"""
    print("=" * 70)
    print("RLTP V2 CONFIG VALIDATION TEST")
    print("=" * 70)

    try:
        cfg = get_config()
        print("✅ Config loaded successfully\n")

        # Test processing configuration
        print("[PROCESSING CONFIG]")
        print(f"  Max Workers: {cfg.max_workers}")
        print(f"  Chunk Size: {cfg.chunk_size:,}")
        print(f"  Max Retries: {cfg.max_retries}")
        print(f"  Retry Delay: {cfg.retry_delay}s")
        print(f"  Audit Client IDs: {cfg.audit_client_ids}")
        print(f"  Audit TRT Buffer: {cfg.audit_trt_buffer:,}")

        # Test staging configuration
        print("\n[STAGING CONFIG]")
        print(f"  Enabled: {cfg.staging_enabled}")
        print(f"  Prefix: {cfg.stage_prefix}")
        print(f"  Max File Size: {cfg.stage_max_file_size:,} bytes")
        print(f"  Compression: {cfg.stage_compression}")

        # Test file paths
        print("\n[FILE PATHS]")
        print(f"  Python Modules: {cfg.python_modules_path}")
        print(f"  Tracking Helper: {cfg.tracking_helper_path}")
        print(f"  Request Processing: {cfg.request_processing_path}")
        print(f"  Request Path (12345): {cfg.get_request_path('12345')}")
        print(f"  Logs Path (12345): {cfg.get_logs_path('12345')}")
        print(f"  Files Path (12345): {cfg.get_files_path('12345')}")
        print(f"  Config Properties Path (12345): {cfg.get_config_properties_path('12345')}")

        # Test table names
        print("\n[TABLE NAMES]")
        print(f"  Requests: {cfg.requests_table}")
        print(f"  Clients: {cfg.clients_table}")
        print(f"  QA Stats: {cfg.qa_stats_table}")
        print(f"  TRT Table (12345, TestClient, W01): {cfg.get_trt_table('12345', 'TestClient', 'W01')}")

        # Test index names
        print("\n[INDEX TEMPLATES]")
        print(f"  Email Index: {cfg.get_index_name('email', '12345', '1')}")
        print(f"  Seg/Subseg Index: {cfg.get_index_name('seg_subseg', '12345', '1')}")
        print(f"  MD5 Index: {cfg.get_index_name('md5', '12345', '1')}")

        # Test query templates
        print("\n[QUERY TEMPLATES]")
        req_query = cfg.get_request_details_query('12345')
        print(f"  Request Details Query: {req_query[:80]}...")

        status_query = cfg.get_update_status_query('12345', 'Test error')
        print(f"  Update Status Query: {status_query[:80]}...")

        desc_query = cfg.get_update_desc_query('12345', 'Test description')
        print(f"  Update Desc Query: {desc_query[:80]}...")

        qa_query = cfg.get_update_qa_count_query('12345', 1000000)
        print(f"  Update QA Count Query: {qa_query[:80]}...")

        # Test audit client check
        print("\n[AUDIT CLIENT CHECKS]")
        for client_id in [180, 181, 190, 999]:
            is_audit = cfg.is_audit_client(client_id)
            print(f"  Client {client_id}: {'✅ AUDIT CLIENT' if is_audit else '❌ Regular Client'}")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED - Config ready for rltpDataPulling_v2.py!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_rltp_config()
    sys.exit(0 if success else 1)
