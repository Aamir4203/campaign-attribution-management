#!/bin/bash
#==== Check PostgreSQL Settings Script ====#

CONNECTION_STRING="psql -U datateam -h zds-prod-pgdb01-01.bo3.e-dialog.com -d apt_tool_db"

echo "=========================================="
echo "PostgreSQL Performance Settings Check"
echo "=========================================="
echo ""

echo "1. work_mem (memory per operation):"
$CONNECTION_STRING -c "SHOW work_mem;"
echo ""

echo "2. maintenance_work_mem (for VACUUM, CREATE INDEX):"
$CONNECTION_STRING -c "SHOW maintenance_work_mem;"
echo ""

echo "3. effective_cache_size (OS cache hint):"
$CONNECTION_STRING -c "SHOW effective_cache_size;"
echo ""

echo "4. random_page_cost (disk I/O cost estimate):"
$CONNECTION_STRING -c "SHOW random_page_cost;"
echo ""

echo "5. shared_buffers (PostgreSQL buffer pool):"
$CONNECTION_STRING -c "SHOW shared_buffers;"
echo ""

echo "6. max_parallel_workers_per_gather:"
$CONNECTION_STRING -c "SHOW max_parallel_workers_per_gather;"
echo ""

echo "7. Join strategies enabled:"
$CONNECTION_STRING -c "SHOW enable_hashjoin;"
$CONNECTION_STRING -c "SHOW enable_mergejoin;"
echo ""

echo "=========================================="
echo "Checking indexes on TRT_TABLE (Request 7773)"
echo "=========================================="

# Check TRT table structure and indexes
$CONNECTION_STRING -c "SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'apt_custom_7773%trt%'
ORDER BY tablename, indexname;"

echo ""
echo "=========================================="
echo "Checking TRT table partitions"
echo "=========================================="

$CONNECTION_STRING -c "SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_size_pretty(pg_total_relation_size(child.oid)) AS size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname LIKE 'apt_custom_7773%trt%'
ORDER BY parent.relname, child.relname;"

echo ""
echo "=========================================="
echo "Check Complete"
echo "=========================================="
