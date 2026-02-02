-- Migration: Add Snowflake upload tracking columns to requests table
-- Description: Track upload status, table name, and upload timestamp for Snowflake uploads
-- Author: CAM Application
-- Date: 2026-01-30

-- Add columns for Snowflake upload tracking
ALTER TABLE APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST
ADD COLUMN IF NOT EXISTS sf_upload_status VARCHAR(20) DEFAULT NULL,  -- NULL, 'success', 'failed'
ADD COLUMN IF NOT EXISTS sf_table_name VARCHAR(255) DEFAULT NULL,    -- Snowflake table name
ADD COLUMN IF NOT EXISTS sf_upload_time TIMESTAMP DEFAULT NULL;      -- Upload timestamp

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_sf_upload_status ON APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST(sf_upload_status);

-- Add comments
COMMENT ON COLUMN APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST.sf_upload_status IS 'Snowflake upload status: NULL (not uploaded), success, failed';
COMMENT ON COLUMN APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST.sf_table_name IS 'Name of the Snowflake table where data was uploaded';
COMMENT ON COLUMN APT_CUSTOM_POSTBACK_REQUEST_DETAILS_DND_TEST.sf_upload_time IS 'Timestamp when data was uploaded to Snowflake';

-- Note: Error messages for failed uploads are stored in request_desc column
