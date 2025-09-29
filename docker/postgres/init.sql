-- Initialize Citus extension
CREATE EXTENSION IF NOT EXISTS citus;

-- Create application user
CREATE USER chat_user WITH PASSWORD 'chat_user_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE chat_platform TO chat_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO chat_user;

-- Set up Citus configuration
-- For single-node setup, we'll configure it as a coordinator
SELECT citus_set_coordinator_host('postgres', 5432);

-- Configure Citus settings
ALTER SYSTEM SET citus.shard_count = 32;
ALTER SYSTEM SET citus.shard_replication_factor = 1;
ALTER SYSTEM SET citus.max_adaptive_executor_pool_size = 8;
ALTER SYSTEM SET citus.max_adaptive_executor_task_pool_size = 8;

-- Reload configuration
SELECT pg_reload_conf();

-- Create indexes for better performance
-- These will be created after tables are created by the application
-- but we can prepare the database structure

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'Citus extension initialized successfully';
    RAISE NOTICE 'Database: chat_platform';
    RAISE NOTICE 'User: chat_user';
    RAISE NOTICE 'Citus shard count: 32';
END $$;
