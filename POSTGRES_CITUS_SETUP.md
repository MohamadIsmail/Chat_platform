# PostgreSQL + Citus Setup Guide for Chat Platform

## Overview
This guide will help you set up PostgreSQL with Citus extension for your distributed chat platform. Citus is a PostgreSQL extension that transforms PostgreSQL into a distributed database, perfect for handling large-scale chat applications.

## Installation Steps

### 1. Install PostgreSQL and Citus on Ubuntu

```bash
# Update package list
sudo apt update

# Install PostgreSQL 15 (recommended for Citus)
sudo apt install -y postgresql-15 postgresql-client-15 postgresql-contrib-15

# Add Citus repository
curl https://install.citusdata.com/community/deb.sh | sudo bash

# Install Citus extension
sudo apt install -y postgresql-15-citus

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Configure PostgreSQL for Citus

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell, run:
```

```sql
-- Create database for your chat platform
CREATE DATABASE chat_platform;

-- Connect to the database
\c chat_platform;

-- Enable Citus extension
CREATE EXTENSION citus;

-- Create a user for your application
CREATE USER chat_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE chat_platform TO chat_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO chat_user;

-- Exit PostgreSQL
\q
```

### 3. Configure PostgreSQL for Better Performance

Edit PostgreSQL configuration:

```bash
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Add/modify these settings:

```conf
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 200

# Logging
log_statement = 'all'
log_min_duration_statement = 1000

# Citus settings
citus.shard_count = 32
citus.shard_replication_factor = 1
```

### 4. Configure PostgreSQL Access

Edit the authentication file:

```bash
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

Add this line for local connections:

```conf
# Allow local connections with password
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 5. Install Python Dependencies

```bash
# Activate your virtual environment
source env/bin/activate

# Install the updated requirements
pip install -r requirements.txt
```

### 6. Environment Configuration

Create a `.env` file in your project root:

```bash
# Database configuration
DATABASE_URL=postgresql+asyncpg://chat_user:your_secure_password@localhost:5432/chat_platform

# Application settings
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=true
CITUS_ENABLED=true

# Optional: Disable SQLite fallback in production
USE_SQLITE_FALLBACK=false
```

## Citus Distribution Strategy

### For Chat Platform

1. **Users Table**: Distributed by `id` (user_id)
   - Ensures user data is co-located
   - Good for user-specific queries

2. **Messages Table**: Distributed by `sender_id`
   - Messages from the same sender are on the same shard
   - Optimizes queries for user's sent messages
   - Recipient queries may require cross-shard operations

### Alternative Distribution Strategies

If you expect more recipient-based queries, consider:

```sql
-- Alternative: Distribute by recipient_id
SELECT create_distributed_table('direct_messages', 'recipient_id');

-- Or use a composite distribution key
-- (requires modifying the table structure)
```

## Testing the Setup

### 1. Test Database Connection

```bash
# Test connection
psql -h localhost -U chat_user -d chat_platform -c "SELECT version();"
```

### 2. Test Citus Extension

```bash
psql -h localhost -U chat_user -d chat_platform -c "SELECT * FROM citus_version();"
```

### 3. Run Your Application

```bash
# Activate virtual environment
source env/bin/activate

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Check Application Health

Visit: `http://localhost:8000/health`

## Scaling with Citus

### Single Node Setup (Current)
- All data on one PostgreSQL instance
- Good for development and small-scale production

### Multi-Node Setup (Future)
When you need to scale:

1. **Add Worker Nodes**:
   ```sql
   SELECT citus_add_node('worker1.example.com', 5432);
   SELECT citus_add_node('worker2.example.com', 5432);
   ```

2. **Re-balance Data**:
   ```sql
   SELECT rebalance_table_shards();
   ```

## Monitoring and Maintenance

### Useful Citus Queries

```sql
-- Check cluster status
SELECT * FROM citus_get_active_worker_nodes();

-- Check shard distribution
SELECT * FROM citus_shards;

-- Check table distribution
SELECT * FROM citus_tables;

-- Monitor query performance
SELECT * FROM citus_stat_statements;
```

### Performance Optimization

1. **Indexes**: Already optimized in the models
2. **Connection Pooling**: Consider using PgBouncer
3. **Monitoring**: Use Citus dashboard or pgAdmin

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify connection settings in `.env`

2. **Citus Extension Not Found**:
   - Ensure Citus is installed: `sudo apt list --installed | grep citus`
   - Check extension in database: `\dx` in psql

3. **Permission Denied**:
   - Verify user permissions in PostgreSQL
   - Check `pg_hba.conf` configuration

### Logs

```bash
# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Application logs
# Check your application console output
```

## Security Considerations

1. **Change Default Passwords**: Use strong passwords
2. **Network Security**: Configure firewall rules
3. **SSL/TLS**: Enable SSL for production
4. **Regular Backups**: Set up automated backups
5. **Updates**: Keep PostgreSQL and Citus updated

## Next Steps

1. Set up monitoring and alerting
2. Configure automated backups
3. Plan for horizontal scaling
4. Implement connection pooling
5. Set up SSL certificates for production

## Resources

- [Citus Documentation](https://docs.citusdata.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Citus Best Practices](https://docs.citusdata.com/en/stable/admin_guide/performance_tuning.html)
