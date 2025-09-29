# Redis Cache Setup Guide for Chat Platform

## Overview
This guide will help you set up Redis as an in-memory cache for your distributed chat platform. Redis will significantly improve performance by caching frequently accessed data like user profiles, messages, and conversation lists.

## Installation Steps

### 1. Install Redis on Ubuntu

```bash
# Update package list
sudo apt update

# Install Redis
sudo apt install -y redis-server

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Check Redis status
sudo systemctl status redis-server
```

### 2. Configure Redis for Production

Edit Redis configuration:

```bash
sudo nano /etc/redis/redis.conf
```

Key configuration settings:

```conf
# Network settings
bind 127.0.0.1
port 6379
timeout 300

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (optional for cache)
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security (recommended for production)
requirepass your_redis_password_here
```

### 3. Secure Redis (Production)

```bash
# Set a strong password
sudo nano /etc/redis/redis.conf
# Add: requirepass your_strong_password_here

# Restart Redis
sudo systemctl restart redis-server

# Test connection with password
redis-cli -a your_strong_password_here ping
```

### 4. Install Python Dependencies

```bash
# Activate your virtual environment
source env/bin/activate

# Install Redis dependencies
pip install -r requirements.txt
```

### 5. Environment Configuration

Update your `.env` file:

```bash
# Redis configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password_here
REDIS_MAX_CONNECTIONS=20
REDIS_RETRY_ON_TIMEOUT=true

# Cache settings
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600
CACHE_USER_TTL=1800
CACHE_MESSAGE_TTL=300
CACHE_CONVERSATION_TTL=600
```

## Cache Strategy Implementation

### 1. Cache Key Patterns

The system uses structured cache keys for different data types:

```
user_profile:{user_id}           # User profile data
user_username:{username}         # User lookup by username
user_email:{email}              # User lookup by email
message:{message_id}            # Individual message
conversation:{user1}:{user2}:messages:{limit}:{offset}  # Conversation messages
user_messages:{user_id}:{limit}:{offset}  # User's messages
conversation_partners:{user_id}  # User's conversation partners
unread_count:{user_id}          # Unread message count
online_users                    # List of online users
user_online:{user_id}           # User online status
```

### 2. Cache Invalidation Strategies

#### User Data Invalidation
- **On user update**: Invalidates all user-related cache entries
- **On user deletion**: Removes all cached user data
- **Pattern**: `user:{user_id}:*`, `user_profile:{user_id}`, etc.

#### Message Data Invalidation
- **On new message**: Invalidates conversation caches for both users
- **On message update**: Updates message cache and conversation caches
- **On message deletion**: Removes message and invalidates conversation caches
- **Pattern**: `conversation:{user1}:{user2}:*`, `user_messages:{user_id}:*`

#### Smart Invalidation
- **Cross-user invalidation**: When user A sends message to user B, invalidates:
  - `conversation:{A}:{B}:*`
  - `conversation:{B}:{A}:*`
  - `user_messages:{A}:*`
  - `user_messages:{B}:*`
  - `unread_count:{B}`

### 3. TTL (Time To Live) Strategy

```python
# Different TTLs for different data types
CACHE_USER_TTL = 1800        # 30 minutes - User data changes infrequently
CACHE_MESSAGE_TTL = 300      # 5 minutes - Messages need recent data
CACHE_CONVERSATION_TTL = 600 # 10 minutes - Conversation lists
CACHE_DEFAULT_TTL = 3600     # 1 hour - General data
```

## Testing the Setup

### 1. Test Redis Connection

```bash
# Test basic connection
redis-cli ping
# Should return: PONG

# Test with password (if configured)
redis-cli -a your_password ping
```

### 2. Test Application Integration

```bash
# Run your application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Check Cache Endpoints

Visit these endpoints to test caching:

- `GET /health` - Check Redis connection status
- `GET /cache/stats` - View Redis statistics
- `GET /conversations` - Test conversation caching
- `GET /unread-count` - Test unread count caching

### 4. Monitor Cache Performance

```bash
# Monitor Redis in real-time
redis-cli monitor

# Check Redis info
redis-cli info

# Check memory usage
redis-cli info memory
```

## Performance Optimization

### 1. Memory Management

```conf
# In redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### 2. Connection Pooling

The application uses connection pooling:

```python
# Configured in config.py
redis_max_connections = 20
redis_retry_on_timeout = True
```

### 3. Serialization Strategy

- **JSON**: For simple data structures (user profiles, messages)
- **Pickle**: For complex objects (fallback)
- **Compression**: Consider for large data sets

## Monitoring and Maintenance

### 1. Redis Monitoring Commands

```bash
# Check Redis status
redis-cli info

# Monitor commands in real-time
redis-cli monitor

# Check memory usage
redis-cli info memory

# List all keys (use carefully in production)
redis-cli keys "*"

# Check key TTL
redis-cli ttl "user_profile:123"
```

### 2. Cache Hit Rate Monitoring

Monitor these metrics:
- **Keyspace hits**: Successful cache lookups
- **Keyspace misses**: Cache misses
- **Hit rate**: `hits / (hits + misses)`

### 3. Memory Usage Monitoring

```bash
# Check memory usage
redis-cli info memory | grep used_memory_human

# Check key count
redis-cli dbsize
```

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   ```bash
   # Check if Redis is running
   sudo systemctl status redis-server
   
   # Check Redis logs
   sudo tail -f /var/log/redis/redis-server.log
   ```

2. **Authentication Error**:
   ```bash
   # Check password in config
   sudo grep requirepass /etc/redis/redis.conf
   
   # Test with password
   redis-cli -a your_password ping
   ```

3. **Memory Issues**:
   ```bash
   # Check memory usage
   redis-cli info memory
   
   # Clear cache if needed (use carefully)
   redis-cli flushdb
   ```

4. **High Memory Usage**:
   - Adjust `maxmemory` setting
   - Review TTL values
   - Check for memory leaks in application

### Performance Issues

1. **Slow Cache Operations**:
   - Check network latency
   - Monitor Redis CPU usage
   - Review serialization overhead

2. **High Miss Rate**:
   - Review TTL settings
   - Check invalidation patterns
   - Analyze access patterns

## Production Considerations

### 1. Security

```conf
# In redis.conf
requirepass strong_password
bind 127.0.0.1
protected-mode yes
```

### 2. Persistence

```conf
# For cache data, you might want to disable persistence
save ""

# Or use RDB for backup
save 900 1
save 300 10
save 60 10000
```

### 3. High Availability

For production, consider:
- **Redis Sentinel**: For automatic failover
- **Redis Cluster**: For horizontal scaling
- **Backup Strategy**: Regular RDB/AOF backups

### 4. Monitoring

Set up monitoring for:
- Redis memory usage
- Cache hit rates
- Connection counts
- Response times

## Cache Warming Strategies

### 1. Application Startup

```python
# Warm frequently accessed data on startup
async def warm_cache():
    # Pre-load active users
    # Pre-load recent conversations
    # Pre-load online users
```

### 2. Background Tasks

```python
# Periodic cache warming
async def periodic_cache_warm():
    # Update online users list
    # Refresh popular conversations
    # Update user activity data
```

## Best Practices

1. **Key Naming**: Use consistent, descriptive key patterns
2. **TTL Management**: Set appropriate TTLs based on data volatility
3. **Invalidation**: Implement smart invalidation strategies
4. **Monitoring**: Monitor cache performance and hit rates
5. **Error Handling**: Gracefully handle Redis unavailability
6. **Serialization**: Choose appropriate serialization methods
7. **Memory Management**: Monitor and manage Redis memory usage

## Integration with Citus

The Redis cache works seamlessly with your Citus-distributed PostgreSQL:

1. **Query Optimization**: Cache reduces load on distributed database
2. **Cross-Shard Queries**: Cache results of expensive cross-shard operations
3. **User Data**: Cache user profiles to avoid cross-shard lookups
4. **Message Aggregation**: Cache conversation lists and message counts

## Next Steps

1. Set up Redis monitoring and alerting
2. Implement cache warming strategies
3. Configure Redis persistence for critical data
4. Set up Redis backup and recovery procedures
5. Consider Redis clustering for high availability
6. Implement cache analytics and reporting
