# Chat Platform

A distributed chat platform microservice built with FastAPI, featuring PostgreSQL with Citus extension for horizontal scaling, Redis caching for performance optimization, and comprehensive monitoring with Prometheus, Grafana, and Loki.

## 🏗️ Architecture Overview

The platform follows a microservices architecture with the following core components:

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

## 🚀 Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)

### Docker Deployment (Recommended)
```bash
# Clone the repository
git clone https://github.com/MohamadIsmail/Chat_platform.git
cd Chat_platform

# Make scripts executable
chmod +x scripts/*.sh

# Start development environment
./scripts/docker-setup.sh dev

# Access the application
curl http://localhost:8000/health
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp docker.env .env
# Edit .env with your settings

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📋 Features

- **User Management**: Registration, authentication, and profile management
- **Real-time Messaging**: Direct message system with conversation tracking
- **Distributed Database**: PostgreSQL with Citus extension for horizontal scaling
- **Intelligent Caching**: Redis-based caching with smart invalidation strategies
- **Comprehensive Monitoring**: Prometheus metrics, Grafana dashboards, and Loki log aggregation
- **Containerized Deployment**: Docker-based deployment with multiple environment profiles
- **Comprehensive Testing**: Unit, integration, and end-to-end tests with >90% coverage

## 🏛️ Architectural Decisions

### 1. Database Architecture: PostgreSQL + Citus

**Decision**: Use PostgreSQL with Citus extension for distributed data storage.

**Rationale**:
- **Horizontal Scaling**: Citus enables horizontal scaling by distributing data across multiple nodes
- **ACID Compliance**: Maintains ACID properties while providing distributed capabilities
- **SQL Compatibility**: Full PostgreSQL compatibility with existing tools and knowledge
- **Sharding Strategy**: Messages distributed by `sender_id` for optimal query performance

**Trade-offs**:
- Added complexity in deployment and maintenance
- Requires understanding of distributed database concepts
- Cross-shard queries may have higher latency

### 2. Caching Strategy: Redis with Smart Invalidation

**Decision**: Implement Redis-based caching with intelligent cache invalidation.

**Rationale**:
- **Performance**: Significant reduction in database load and query response times
- **Scalability**: Redis can handle high-frequency read operations efficiently
- **Smart Invalidation**: Cross-user cache invalidation ensures data consistency
- **TTL Strategy**: Different TTL values for different data types based on volatility

**Cache Key Patterns**:
```
user_profile:{user_id}           # User profiles (30 min TTL)
conversation:{user1}:{user2}:*   # Conversation data (10 min TTL)
message:{message_id}             # Individual messages (5 min TTL)
```

### 3. API Framework: FastAPI

**Decision**: Use FastAPI as the web framework.

**Rationale**:
- **Performance**: High performance with automatic async support
- **Type Safety**: Built-in Pydantic integration for request/response validation
- **Documentation**: Automatic OpenAPI/Swagger documentation generation
- **Modern Python**: Full support for Python 3.8+ features and async/await

### 4. Monitoring Stack: Prometheus + Grafana + Loki

**Decision**: Implement comprehensive observability with the "PLG" stack.

**Rationale**:
- **Metrics**: Prometheus for time-series metrics collection and alerting
- **Visualization**: Grafana for dashboard creation and visualization
- **Logs**: Loki for efficient log aggregation and querying
- **Integration**: Seamless integration between all components

### 5. Containerization: Docker with Multi-Profile Support

**Decision**: Use Docker Compose with environment-specific profiles.

**Rationale**:
- **Consistency**: Identical environments across development, staging, and production
- **Isolation**: Service isolation with proper networking
- **Scalability**: Easy horizontal scaling of services
- **Profiles**: Different configurations for different environments (dev, prod, monitoring)

## 🔧 Implementation Assumptions

### 1. Data Distribution Assumptions

**User Data Distribution**:
- Users are distributed by `user_id` for optimal user-specific queries
- User profiles are cached with 30-minute TTL (assumes infrequent profile updates)

**Message Distribution**:
- Messages are distributed by `sender_id` for optimal sent-message queries
- Assumes that users query their sent messages more frequently than received messages
- Cross-shard queries for conversation history are acceptable for the use case

### 2. Performance Assumptions

**Cache Performance**:
- Redis cache hit rate >80% for optimal performance
- Cache invalidation overhead is acceptable for data consistency
- Memory usage patterns allow for 512MB Redis allocation

**Database Performance**:
- Citus single-node setup sufficient for initial deployment
- Query patterns favor sender-based message retrieval
- Connection pooling handles concurrent user load

### 3. Scalability Assumptions

**Horizontal Scaling**:
- Initial deployment supports single-node Citus (co-ordinator + worker on same node)
- Future scaling will add dedicated worker nodes
- Redis can be clustered for high availability when needed

**Load Patterns**:
- Chat applications have bursty traffic patterns
- Cache warming strategies can handle traffic spikes
- Background tasks can handle cache maintenance

### 4. Security Assumptions

**Authentication**:
- JWT-based authentication is sufficient for the use case
- Token expiration and refresh mechanisms handle session management
- Password hashing with bcrypt provides adequate security

**Network Security**:
- Internal service communication uses Docker networks
- External access limited to necessary ports only
- SSL/TLS termination at reverse proxy level

### 5. Operational Assumptions

**Monitoring**:
- Prometheus retention of 200 hours sufficient for alerting and debugging
- Grafana dashboards provide sufficient visibility into system health
- Loki log retention of 7 days balances storage costs and debugging needs

**Deployment**:
- Docker-based deployment simplifies operations
- Environment variables provide sufficient configuration management
- Health checks enable reliable service monitoring

## 📚 Documentation

### Setup and Deployment
- **[Docker Deployment Guide](DOCKER_DEPLOYMENT.md)** - Complete Docker setup and deployment instructions
- **[PostgreSQL + Citus Setup](POSTGRES_CITUS_SETUP.md)** - Manual PostgreSQL and Citus configuration
- **[Redis Cache Setup](REDIS_CACHE_SETUP.md)** - Redis installation and caching strategy

### Testing and Quality
- **[Testing Guide](TESTING_GUIDE.md)** - Comprehensive testing setup and execution

### Monitoring and Observability
- **[Monitoring Setup](MONITORING_SETUP.md)** - Prometheus, Grafana, and Loki configuration

## 🛠️ Development

### Project Structure
```
app/
├── api/           # API routes and endpoints
├── core/          # Core functionality (database, cache, logging, metrics)
├── models/        # SQLAlchemy database models
├── schemas/       # Pydantic request/response schemas
└── services/      # Business logic services

tests/             # Comprehensive test suite
docker/            # Docker configuration files
scripts/           # Deployment and management scripts
```

### Running Tests
```bash
# Run all tests
./scripts/run-tests.sh

# Run with coverage
./scripts/run-tests.sh -c

# Run specific test types
./scripts/run-tests.sh -t unit
./scripts/run-tests.sh -t integration
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔍 Monitoring and Observability

### Metrics Endpoints
- **Application Metrics**: `/metrics` - Prometheus-compatible metrics
- **Health Check**: `/health` - Service health status
- **Cache Statistics**: `/cache/stats` - Redis cache performance

### Monitoring Dashboards
- **Grafana**: http://localhost:3000 (admin/admin_password)
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100

## 🚀 Deployment Profiles

### Development
```bash
./scripts/docker-setup.sh dev
```
Includes: FastAPI app, PostgreSQL+Citus, Redis, PgAdmin, Redis Commander

### Production
```bash
./scripts/docker-setup.sh prod
```
Includes: FastAPI app, PostgreSQL+Citus, Redis, Nginx reverse proxy

### Monitoring
```bash
./scripts/docker-setup.sh monitoring
```
Includes: All services + Prometheus, Grafana, Loki, Promtail

## 🔒 Security Considerations

- **Environment Variables**: All sensitive configuration via environment variables
- **Password Security**: Strong password requirements for all services
- **Network Isolation**: Internal Docker networks for service communication
- **SSL/TLS**: HTTPS termination at reverse proxy level
- **Input Validation**: Comprehensive input validation and sanitization

## 📈 Performance Characteristics

- **Response Time**: <100ms for cached operations, <500ms for database queries
- **Throughput**: Supports 1000+ concurrent users with proper scaling
- **Cache Hit Rate**: >80% target for optimal performance
- **Database**: Optimized for read-heavy workloads with intelligent caching

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `./scripts/run-tests.sh -c`
4. Ensure code coverage >90%
5. Submit a pull request

## 🆘 Support

For issues and questions:
1. Check the troubleshooting sections in the documentation
2. Review the logs: `./scripts/docker-manage.sh logs [service]`
3. Check service health: `./scripts/docker-manage.sh health`
4. Open an issue on GitHub

---

**Built with ❤️ using FastAPI, PostgreSQL, Citus, Redis, and modern DevOps practices.**