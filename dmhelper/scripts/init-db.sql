-- Initialize database for DM Helper
-- This script runs when the PostgreSQL container starts

-- Create test database if it doesn't exist
SELECT 'CREATE DATABASE dmhelper_test_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dmhelper_test_db')\gexec

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE dmhelper_db TO dmhelper;
GRANT ALL PRIVILEGES ON DATABASE dmhelper_test_db TO dmhelper; 