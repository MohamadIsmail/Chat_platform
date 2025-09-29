from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import Request, Response
import time
import logging

logger = logging.getLogger(__name__)

# Business Metrics
messages_created_total = Counter(
    'chat_messages_created_total',
    'Total number of messages created',
    ['message_type', 'sender_id']
)

users_registered_total = Counter(
    'chat_users_registered_total',
    'Total number of users registered'
)

users_logged_in_total = Counter(
    'chat_users_logged_in_total',
    'Total number of user logins'
)

conversations_created_total = Counter(
    'chat_conversations_created_total',
    'Total number of conversations created'
)

# Cache Metrics
cache_requests_total = Counter(
    'chat_cache_requests_total',
    'Total number of cache requests',
    ['operation', 'cache_type']
)

cache_hits_total = Counter(
    'chat_cache_hits_total',
    'Total number of cache hits',
    ['operation', 'cache_type']
)

cache_misses_total = Counter(
    'chat_cache_misses_total',
    'Total number of cache misses',
    ['operation', 'cache_type']
)

cache_operations_duration = Histogram(
    'chat_cache_operations_duration_seconds',
    'Duration of cache operations',
    ['operation', 'cache_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Database Metrics
database_queries_total = Counter(
    'chat_database_queries_total',
    'Total number of database queries',
    ['operation', 'table']
)

database_query_duration = Histogram(
    'chat_database_query_duration_seconds',
    'Duration of database queries',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

database_connections_active = Gauge(
    'chat_database_connections_active',
    'Number of active database connections'
)

# Application Metrics
active_users = Gauge(
    'chat_active_users',
    'Number of currently active users'
)

online_users = Gauge(
    'chat_online_users',
    'Number of currently online users'
)

unread_messages_total = Gauge(
    'chat_unread_messages_total',
    'Total number of unread messages',
    ['user_id']
)

# Error Metrics
errors_total = Counter(
    'chat_errors_total',
    'Total number of errors',
    ['error_type', 'endpoint', 'status_code']
)

# Application Info
app_info = Info(
    'chat_app_info',
    'Application information'
)

# Custom metrics for specific business logic
def record_message_created(message_type: str = "text", sender_id: int = None):
    """Record a message creation event"""
    messages_created_total.labels(
        message_type=message_type,
        sender_id=str(sender_id) if sender_id else "unknown"
    ).inc()

def record_user_registered():
    """Record a user registration event"""
    users_registered_total.inc()

def record_user_logged_in():
    """Record a user login event"""
    users_logged_in_total.inc()

def record_conversation_created():
    """Record a conversation creation event"""
    conversations_created_total.inc()

def record_cache_operation(operation: str, cache_type: str, hit: bool, duration: float):
    """Record cache operation metrics"""
    cache_requests_total.labels(operation=operation, cache_type=cache_type).inc()
    
    if hit:
        cache_hits_total.labels(operation=operation, cache_type=cache_type).inc()
    else:
        cache_misses_total.labels(operation=operation, cache_type=cache_type).inc()
    
    cache_operations_duration.labels(operation=operation, cache_type=cache_type).observe(duration)

def record_database_query(operation: str, table: str, duration: float):
    """Record database query metrics"""
    database_queries_total.labels(operation=operation, table=table).inc()
    database_query_duration.labels(operation=operation, table=table).observe(duration)

def record_error(error_type: str, endpoint: str, status_code: int):
    """Record error metrics"""
    errors_total.labels(
        error_type=error_type,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()

def update_active_users(count: int):
    """Update active users count"""
    active_users.set(count)

def update_online_users(count: int):
    """Update online users count"""
    online_users.set(count)

def update_unread_messages(user_id: int, count: int):
    """Update unread messages count for a user"""
    unread_messages_total.labels(user_id=str(user_id)).set(count)

def set_app_info(version: str, environment: str):
    """Set application information"""
    app_info.info({
        'version': version,
        'environment': environment,
        'service': 'chat-platform'
    })

# Custom metrics for Prometheus FastAPI Instrumentator
def custom_metrics(app):
    """Add custom metrics to the FastAPI app"""
    
    # Add business metrics
    @app.middleware("http")
    async def business_metrics_middleware(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record business-specific metrics based on endpoint
        if request.url.path == "/send" and request.method == "POST":
            record_message_created()
        elif request.url.path == "/register" and request.method == "POST":
            record_user_registered()
        elif request.url.path == "/login" and request.method == "POST":
            record_user_logged_in()
        
        # Record error metrics
        if response.status_code >= 400:
            record_error(
                error_type="http_error",
                endpoint=request.url.path,
                status_code=response.status_code
            )
        
        return response

# Initialize Prometheus FastAPI Instrumentator
def setup_metrics(app):
    """Setup Prometheus metrics for the FastAPI app"""
    
    # Create instrumentator
    instrumentator = Instrumentator()
    
    # Add default metrics
    instrumentator.add(metrics.default())
    
    # Add custom metrics
    instrumentator.add(custom_metrics)
    
    # Instrument the app
    instrumentator.instrument(app)
    
    # Expose metrics endpoint
    @app.get("/metrics")
    async def metrics_endpoint():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    
    # Set app info
    set_app_info(version="1.0.0", environment="production")
    
    logger.info("Prometheus metrics setup completed")
