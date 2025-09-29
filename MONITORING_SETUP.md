# Monitoring Setup Guide for Chat Platform

## Overview
This guide covers setting up comprehensive monitoring for your distributed chat platform using Prometheus for metrics collection, Grafana for visualization, and Loki for log aggregation.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Grafana      │    │   Prometheus    │    │      Loki       │
│ (Visualization) │◄──►│  (Metrics)      │    │ (Log Aggregation)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chat App      │    │  Exporters      │    │   Promtail      │
│  (Metrics)      │    │ (Postgres/Redis)│    │ (Log Collection)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Start Monitoring Stack
```bash
# Start all services including monitoring
docker-compose --profile monitoring up -d

# Or use the management script
./scripts/docker-manage.sh start monitoring
```

### 2. Access Monitoring Tools
- **Grafana**: http://localhost:3000 (admin/admin_password)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

## Monitoring Components

### 1. Prometheus (Metrics Collection)

**Purpose**: Collects and stores time-series metrics from all services

**Configuration**: `docker/prometheus/prometheus.yml`

**Key Features**:
- Scrapes metrics from all services every 15 seconds
- Stores metrics for 200 hours
- Alert rules for proactive monitoring
- Service discovery for dynamic targets

**Metrics Sources**:
- FastAPI application (`/metrics` endpoint)
- PostgreSQL exporter (port 9187)
- Redis exporter (port 9121)
- Node exporter (system metrics)
- cAdvisor (container metrics)

### 2. Grafana (Visualization)

**Purpose**: Creates dashboards and visualizations from Prometheus metrics

**Configuration**: `docker/grafana/provisioning/`

**Key Features**:
- Pre-configured data sources (Prometheus, Loki, PostgreSQL)
- Custom dashboards for chat platform
- Alerting and notification rules
- User management and access control

**Default Dashboards**:
- Chat Platform Overview
- System Resources
- Database Performance
- Cache Performance
- Application Metrics

### 3. Loki (Log Aggregation)

**Purpose**: Collects, stores, and queries application logs

**Configuration**: `docker/loki/loki.yml`

**Key Features**:
- Efficient log storage and compression
- LogQL query language
- Integration with Grafana
- Retention policies

### 4. Promtail (Log Collection)

**Purpose**: Collects logs from various sources and sends to Loki

**Configuration**: `docker/promtail/promtail.yml`

**Log Sources**:
- Application logs (structured JSON)
- PostgreSQL logs
- Redis logs
- Nginx logs
- Docker container logs
- System logs

## Metrics and Logging

### Application Metrics

The FastAPI application exposes comprehensive metrics:

#### Business Metrics
- `chat_messages_created_total` - Total messages created
- `chat_users_registered_total` - Total user registrations
- `chat_users_logged_in_total` - Total user logins
- `chat_conversations_created_total` - Total conversations

#### Cache Metrics
- `chat_cache_requests_total` - Cache requests by operation
- `chat_cache_hits_total` - Cache hits by operation
- `chat_cache_misses_total` - Cache misses by operation
- `chat_cache_operations_duration_seconds` - Cache operation duration

#### Database Metrics
- `chat_database_queries_total` - Database queries by operation
- `chat_database_query_duration_seconds` - Query duration
- `chat_database_connections_active` - Active connections

#### Application Metrics
- `chat_active_users` - Currently active users
- `chat_online_users` - Currently online users
- `chat_unread_messages_total` - Unread messages per user

#### Error Metrics
- `chat_errors_total` - Errors by type and endpoint

### Structured Logging

The application uses structured JSON logging with the following event types:

#### User Events
- `user_registration` - User account creation
- `user_login` - User authentication
- `user_logout` - User session end

#### Message Events
- `message_sent` - Message creation
- `message_received` - Message delivery
- `message_read` - Message read status

#### System Events
- `api_request` - HTTP request processing
- `api_error` - HTTP error responses
- `database_query` - Database operations
- `cache_hit`/`cache_miss` - Cache operations
- `performance_metric` - Custom performance data

#### Security Events
- `security_event` - Authentication failures, suspicious activity

## Dashboard Configuration

### Chat Platform Overview Dashboard

**Location**: `docker/grafana/dashboards/chat-platform-overview.json`

**Panels**:
1. **HTTP Request Rate** - Requests per second by method and endpoint
2. **HTTP Response Time** - 95th and 50th percentile response times
3. **Business Metrics** - Messages and user registrations per second
4. **Cache Performance** - Cache hit rate percentage
5. **Redis Memory Usage** - Memory consumption and limits
6. **PostgreSQL Connections** - Active vs max connections
7. **System Resources** - CPU and memory usage

### Custom Queries

#### High Error Rate
```promql
rate(http_requests_total{status=~"5.."}[5m]) > 0.1
```

#### Cache Hit Rate
```promql
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100
```

#### Database Connection Usage
```promql
pg_stat_database_numbackends / pg_settings_max_connections * 100
```

#### Message Volume
```promql
rate(chat_messages_created_total[5m])
```

## Alerting Rules

### Critical Alerts
- **ChatAppDown**: Application is down for >1 minute
- **PostgreSQLDown**: Database is down for >1 minute
- **RedisDown**: Cache is down for >1 minute

### Warning Alerts
- **HighErrorRate**: Error rate >10% for 2 minutes
- **HighResponseTime**: 95th percentile >1 second for 5 minutes
- **HighMemoryUsage**: Memory usage >85% for 5 minutes
- **LowCacheHitRate**: Cache hit rate <80% for 10 minutes

### Info Alerts
- **HighMessageVolume**: >100 messages/second for 5 minutes
- **HighUserRegistration**: >10 registrations/second for 5 minutes

## Log Analysis

### LogQL Queries

#### Application Errors
```logql
{service="chat-app"} |= "error" | json | level="error"
```

#### User Activity
```logql
{service="chat-app"} | json | event_type="user_login"
```

#### Performance Issues
```logql
{service="chat-app"} | json | event_type="performance_metric" | value > 1.0
```

#### Database Queries
```logql
{service="chat-app"} | json | event_type="database_query" | duration > 0.5
```

### Log Patterns

#### Structured Log Format
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "info",
  "service": "chat-platform",
  "event_type": "message_sent",
  "message_id": 123,
  "sender_id": 456,
  "recipient_id": 789,
  "trace_id": "abc-123-def"
}
```

## Monitoring Setup

### 1. Environment Configuration

Update your `.env` file:
```bash
# Monitoring Configuration
GRAFANA_PASSWORD=your_grafana_password
PROMETHEUS_RETENTION=200h
LOKI_RETENTION=168h

# Logging Configuration
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

### 2. Start Monitoring

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f loki
```

### 3. Verify Setup

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Loki health
curl http://localhost:3100/ready

# Check Grafana health
curl http://localhost:3000/api/health
```

## Performance Optimization

### 1. Prometheus Tuning

**Memory Usage**:
```yaml
# In prometheus.yml
storage:
  tsdb:
    retention.time: 200h
    retention.size: 1GB
```

**Scrape Intervals**:
```yaml
global:
  scrape_interval: 15s  # Adjust based on needs
  evaluation_interval: 15s
```

### 2. Loki Tuning

**Retention**:
```yaml
# In loki.yml
limits_config:
  retention_period: 168h  # 7 days
```

**Compression**:
```yaml
compactor:
  working_directory: /loki/boltdb-shipper-compactor
  shared_store: filesystem
  compaction_interval: 10m
```

### 3. Grafana Tuning

**Dashboard Refresh**:
- Set appropriate refresh intervals
- Use template variables for dynamic queries
- Limit time ranges for heavy queries

## Troubleshooting

### Common Issues

1. **Prometheus Not Scraping**:
   ```bash
   # Check targets
   curl http://localhost:9090/api/v1/targets
   
   # Check configuration
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

2. **Grafana Not Loading Dashboards**:
   ```bash
   # Check data source connectivity
   curl http://localhost:3000/api/datasources
   
   # Check dashboard provisioning
   docker-compose logs grafana
   ```

3. **Loki Not Receiving Logs**:
   ```bash
   # Check Promtail status
   docker-compose logs promtail
   
   # Check log files
   docker-compose exec promtail ls -la /var/log/
   ```

### Performance Issues

1. **High Memory Usage**:
   - Reduce retention periods
   - Optimize query intervals
   - Use recording rules for complex queries

2. **Slow Queries**:
   - Add indexes to log labels
   - Use more specific time ranges
   - Optimize LogQL queries

3. **Storage Issues**:
   - Implement log rotation
   - Use compression
   - Set up retention policies

## Security Considerations

### 1. Access Control
- Change default passwords
- Use strong authentication
- Implement role-based access control

### 2. Network Security
- Use internal networks for service communication
- Expose only necessary ports
- Implement TLS/SSL where possible

### 3. Data Privacy
- Sanitize logs of sensitive information
- Implement log retention policies
- Use secure log transmission

## Maintenance

### 1. Regular Tasks
- Monitor disk usage
- Update monitoring components
- Review and tune alert rules
- Clean up old data

### 2. Backup
- Backup Grafana dashboards
- Backup Prometheus configuration
- Backup Loki data

### 3. Updates
```bash
# Update monitoring stack
docker-compose pull
docker-compose --profile monitoring up -d
```

## Advanced Features

### 1. Custom Dashboards
- Create business-specific dashboards
- Add custom metrics
- Implement drill-down functionality

### 2. Alerting
- Configure notification channels
- Set up escalation policies
- Implement alert correlation

### 3. Log Analysis
- Create custom log queries
- Set up log-based alerts
- Implement log correlation

This monitoring setup provides comprehensive observability for your chat platform, enabling proactive monitoring, troubleshooting, and performance optimization.
