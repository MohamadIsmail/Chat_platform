# Docker Deployment Guide for Chat Platform

## Overview
This guide covers deploying your distributed chat platform using Docker containers. The setup includes PostgreSQL with Citus extension, Redis cache, FastAPI application, and optional Nginx reverse proxy.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   FastAPI App   │    │   PostgreSQL    │
│  (Reverse Proxy)│◄──►│   (Chat API)    │◄──►│   + Citus       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Cache)       │
                       └─────────────────┘
```

## Prerequisites

### System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### Install Docker

#### Ubuntu/Debian
```bash
# Update package index
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y docker docker-compose

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/MohamadIsmail/Chat_platform.git
cd Chat_platform

# Make scripts executable
chmod +x scripts/*.sh

# Run setup script
./scripts/docker-setup.sh dev
```

### 2. Access Services
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **PgAdmin**: http://localhost:5050 (admin@chatplatform.com / admin_password)
- **Redis Commander**: http://localhost:8081

## Detailed Setup

### 1. Environment Configuration

The application uses environment variables for configuration. Copy the Docker environment file:

```bash
cp docker.env .env
```

Edit `.env` for your specific needs:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres_password@postgres:5432/chat_platform
USE_SQLITE_FALLBACK=false

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=redis_password

# Application Settings
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=false

# Cache Settings
CACHE_ENABLED=true
CACHE_USER_TTL=1800
CACHE_MESSAGE_TTL=300
```

### 2. Service Profiles

The Docker Compose setup supports different profiles:

#### Development Profile
```bash
# Start with development tools
docker-compose --profile development up -d

# Or use the script
./scripts/docker-setup.sh dev
```

Includes:
- FastAPI application
- PostgreSQL with Citus
- Redis cache
- PgAdmin (database management)
- Redis Commander (cache management)

#### Production Profile
```bash
# Start production setup
docker-compose --profile production up -d

# Or use the script
./scripts/docker-setup.sh prod
```

Includes:
- FastAPI application
- PostgreSQL with Citus
- Redis cache
- Nginx reverse proxy with SSL

#### Core Profile
```bash
# Start only core services
docker-compose up -d postgres redis app

# Or use the script
./scripts/docker-setup.sh core
```

Includes:
- FastAPI application
- PostgreSQL with Citus
- Redis cache

### 3. Service Management

Use the management script for common operations:

```bash
# Start services
./scripts/docker-manage.sh start dev

# Stop services
./scripts/docker-manage.sh stop

# Restart services
./scripts/docker-manage.sh restart dev

# Check status
./scripts/docker-manage.sh status

# View logs
./scripts/docker-manage.sh logs app

# Open shell in container
./scripts/docker-manage.sh shell postgres

# Check health
./scripts/docker-manage.sh health

# View resource usage
./scripts/docker-manage.sh stats
```

## Service Details

### PostgreSQL with Citus

**Configuration**:
- Image: `citusdata/citus:12.1`
- Port: 5432
- Database: `chat_platform`
- User: `postgres`
- Password: `postgres_password`

**Features**:
- Citus extension enabled
- Optimized for distributed queries
- Automatic sharding configuration
- Connection pooling

**Access**:
```bash
# Connect via Docker
docker-compose exec postgres psql -U postgres -d chat_platform

# Connect from host
psql -h localhost -p 5432 -U postgres -d chat_platform
```

### Redis Cache

**Configuration**:
- Image: `redis:7-alpine`
- Port: 6379
- Password: `redis_password`
- Persistence: AOF + RDB

**Features**:
- In-memory caching
- Persistence for reliability
- Connection pooling
- Memory management with LRU eviction

**Access**:
```bash
# Connect via Docker
docker-compose exec redis redis-cli -a redis_password

# Connect from host
redis-cli -h localhost -p 6379 -a redis_password
```

### FastAPI Application

**Configuration**:
- Custom Dockerfile
- Port: 8000
- Health checks enabled
- Auto-reload in development

**Features**:
- Async database operations
- Redis caching integration
- Automatic table creation
- Citus distribution setup

### Nginx (Production)

**Configuration**:
- Reverse proxy
- SSL termination
- Rate limiting
- Security headers
- Load balancing ready

**Features**:
- HTTP/HTTPS support
- Rate limiting for API endpoints
- Security headers
- Gzip compression
- WebSocket support

## Data Management

### Backup

```bash
# Create backup
./scripts/docker-manage.sh backup

# Backup will be created in backups/YYYYMMDD_HHMMSS/
```

### Restore

```bash
# Restore from backup
./scripts/docker-manage.sh restore backups/20240101_120000
```

### Database Migrations

The application automatically creates tables and sets up Citus distribution on startup. For manual operations:

```bash
# Access PostgreSQL
./scripts/docker-manage.sh shell postgres

# Run SQL commands
psql -U postgres -d chat_platform
```

## Monitoring and Logs

### View Logs

```bash
# Application logs
docker-compose logs -f app

# All services
docker-compose logs -f

# Specific service
./scripts/docker-manage.sh logs postgres
```

### Health Monitoring

```bash
# Check service health
./scripts/docker-manage.sh health

# Application health endpoint
curl http://localhost:8000/health

# Cache statistics
curl http://localhost:8000/cache/stats
```

### Resource Monitoring

```bash
# View resource usage
./scripts/docker-manage.sh stats

# Docker system info
docker system df
```

## Security Considerations

### Production Security

1. **Change Default Passwords**:
   ```bash
   # Update in .env file
   POSTGRES_PASSWORD=strong_postgres_password
   REDIS_PASSWORD=strong_redis_password
   SECRET_KEY=very-long-random-secret-key
   ```

2. **SSL Certificates**:
   ```bash
   # Replace self-signed certificates
   cp your-cert.pem docker/nginx/ssl/cert.pem
   cp your-key.pem docker/nginx/ssl/key.pem
   ```

3. **Network Security**:
   - Use Docker networks for service isolation
   - Configure firewall rules
   - Limit exposed ports

4. **Container Security**:
   - Run containers as non-root users
   - Use specific image tags
   - Regular security updates

### Environment Variables Security

```bash
# Use secrets management in production
docker-compose --env-file .env.production up -d
```

## Scaling

### Horizontal Scaling

1. **Application Scaling**:
   ```yaml
   # In docker-compose.yml
   app:
     deploy:
       replicas: 3
   ```

2. **Database Scaling**:
   - Add Citus worker nodes
   - Configure connection pooling
   - Implement read replicas

3. **Cache Scaling**:
   - Redis Cluster setup
   - Cache sharding
   - Memory optimization

### Load Balancing

```yaml
# Add to docker-compose.yml
nginx:
  # Configure upstream servers
  # Add load balancing algorithms
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Change ports in docker-compose.yml
   ```

2. **Memory Issues**:
   ```bash
   # Check memory usage
   docker stats
   
   # Increase memory limits
   # Adjust Redis maxmemory setting
   ```

3. **Database Connection Issues**:
   ```bash
   # Check PostgreSQL logs
   docker-compose logs postgres
   
   # Test connection
   docker-compose exec postgres pg_isready -U postgres
   ```

4. **Cache Issues**:
   ```bash
   # Check Redis logs
   docker-compose logs redis
   
   # Test Redis connection
   docker-compose exec redis redis-cli -a redis_password ping
   ```

### Performance Optimization

1. **Database Optimization**:
   - Adjust PostgreSQL configuration
   - Optimize Citus settings
   - Monitor query performance

2. **Cache Optimization**:
   - Tune TTL values
   - Monitor hit rates
   - Optimize memory usage

3. **Application Optimization**:
   - Connection pooling
   - Async operations
   - Resource limits

## Production Deployment

### 1. Environment Setup

```bash
# Create production environment
cp docker.env .env.production

# Update with production values
nano .env.production
```

### 2. SSL Configuration

```bash
# Generate or obtain SSL certificates
openssl req -x509 -newkey rsa:4096 -keyout docker/nginx/ssl/key.pem -out docker/nginx/ssl/cert.pem -days 365 -nodes
```

### 3. Deploy

```bash
# Deploy production setup
./scripts/docker-setup.sh prod

# Or manually
docker-compose --profile production up -d
```

### 4. Monitoring Setup

```bash
# Set up monitoring
docker-compose --profile monitoring up -d

# Configure alerts
# Set up log aggregation
```

## Maintenance

### Regular Tasks

1. **Updates**:
   ```bash
   # Update images
   docker-compose pull
   docker-compose up -d
   ```

2. **Backups**:
   ```bash
   # Schedule regular backups
   crontab -e
   # Add: 0 2 * * * /path/to/scripts/docker-manage.sh backup
   ```

3. **Cleanup**:
   ```bash
   # Clean up unused resources
   docker system prune -f
   ```

### Health Checks

```bash
# Automated health checks
./scripts/docker-manage.sh health

# Monitor logs
docker-compose logs -f --tail=100
```

## Support

### Getting Help

1. **Check Logs**: Always check service logs first
2. **Health Checks**: Use built-in health check endpoints
3. **Documentation**: Refer to service-specific documentation
4. **Community**: Check Docker and service communities

### Useful Commands

```bash
# Quick status check
docker-compose ps

# Resource usage
docker stats

# System information
docker system info

# Clean up
docker system prune -a
```

This Docker setup provides a complete, production-ready deployment of your distributed chat platform with PostgreSQL, Citus, Redis, and FastAPI.
