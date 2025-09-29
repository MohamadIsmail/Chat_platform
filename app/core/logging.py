import structlog
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get logger
logger = structlog.get_logger()

class ChatLogger:
    """Custom logger for chat platform with structured logging"""
    
    def __init__(self, name: str = "chat-platform"):
        self.logger = structlog.get_logger(name)
    
    def _create_context(self, **kwargs) -> Dict[str, Any]:
        """Create logging context with common fields"""
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "chat-platform",
            "trace_id": str(uuid.uuid4()),
        }
        context.update(kwargs)
        return context
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        context = self._create_context(**kwargs)
        self.logger.info(message, **context)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        context = self._create_context(**kwargs)
        self.logger.warning(message, **context)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        context = self._create_context(**kwargs)
        self.logger.error(message, **context)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        context = self._create_context(**kwargs)
        self.logger.debug(message, **context)
    
    # Business-specific logging methods
    def user_registered(self, user_id: int, username: str, email: str):
        """Log user registration event"""
        self.info(
            "User registered successfully",
            event_type="user_registration",
            user_id=user_id,
            username=username,
            email=email
        )
    
    def user_logged_in(self, user_id: int, username: str, ip_address: str = None):
        """Log user login event"""
        self.info(
            "User logged in",
            event_type="user_login",
            user_id=user_id,
            username=username,
            ip_address=ip_address
        )
    
    def user_logged_out(self, user_id: int, username: str):
        """Log user logout event"""
        self.info(
            "User logged out",
            event_type="user_logout",
            user_id=user_id,
            username=username
        )
    
    def message_sent(self, message_id: int, sender_id: int, recipient_id: int, message_type: str = "text"):
        """Log message sent event"""
        self.info(
            "Message sent",
            event_type="message_sent",
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type
        )
    
    def message_received(self, message_id: int, recipient_id: int, sender_id: int):
        """Log message received event"""
        self.info(
            "Message received",
            event_type="message_received",
            message_id=message_id,
            recipient_id=recipient_id,
            sender_id=sender_id
        )
    
    def message_read(self, message_id: int, user_id: int):
        """Log message read event"""
        self.info(
            "Message read",
            event_type="message_read",
            message_id=message_id,
            user_id=user_id
        )
    
    def cache_hit(self, operation: str, key: str, cache_type: str = "redis"):
        """Log cache hit event"""
        self.debug(
            "Cache hit",
            event_type="cache_hit",
            operation=operation,
            key=key,
            cache_type=cache_type
        )
    
    def cache_miss(self, operation: str, key: str, cache_type: str = "redis"):
        """Log cache miss event"""
        self.debug(
            "Cache miss",
            event_type="cache_miss",
            operation=operation,
            key=key,
            cache_type=cache_type
        )
    
    def database_query(self, operation: str, table: str, duration: float, success: bool = True):
        """Log database query event"""
        level = "info" if success else "error"
        getattr(self, level)(
            "Database query executed",
            event_type="database_query",
            operation=operation,
            table=table,
            duration=duration,
            success=success
        )
    
    def api_request(self, method: str, endpoint: str, status_code: int, duration: float, user_id: int = None):
        """Log API request event"""
        self.info(
            "API request",
            event_type="api_request",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration=duration,
            user_id=user_id
        )
    
    def api_error(self, method: str, endpoint: str, status_code: int, error_message: str, user_id: int = None):
        """Log API error event"""
        self.error(
            "API error",
            event_type="api_error",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            error_message=error_message,
            user_id=user_id
        )
    
    def performance_metric(self, metric_name: str, value: float, unit: str = None, **kwargs):
        """Log performance metric"""
        self.info(
            "Performance metric",
            event_type="performance_metric",
            metric_name=metric_name,
            value=value,
            unit=unit,
            **kwargs
        )
    
    def security_event(self, event_type: str, user_id: int = None, ip_address: str = None, details: str = None):
        """Log security event"""
        self.warning(
            "Security event",
            event_type="security_event",
            security_event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )
    
    def system_event(self, event_type: str, component: str, status: str, details: str = None):
        """Log system event"""
        self.info(
            "System event",
            event_type="system_event",
            system_event_type=event_type,
            component=component,
            status=status,
            details=details
        )

# Global logger instance
chat_logger = ChatLogger()

# Configure standard logging
def setup_logging(log_level: str = "INFO"):
    """Setup structured logging for the application"""
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        stream=sys.stdout
    )
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # Log startup
    chat_logger.system_event(
        event_type="application_startup",
        component="chat-platform",
        status="started",
        details="Structured logging initialized"
    )

# Context manager for request tracing
class RequestContext:
    """Context manager for request-level logging"""
    
    def __init__(self, request_id: str = None, user_id: int = None, **kwargs):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.context = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        # Bind context to logger
        self.logger = chat_logger.logger.bind(
            request_id=self.request_id,
            user_id=self.user_id,
            **self.context
        )
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.logger.info(
                "Request completed",
                event_type="request_completed",
                duration=duration
            )

# Decorator for automatic logging
def log_function_call(func):
    """Decorator to automatically log function calls"""
    def wrapper(*args, **kwargs):
        with RequestContext() as logger:
            logger.info(
                "Function called",
                event_type="function_call",
                function=func.__name__,
                module=func.__module__
            )
            try:
                result = func(*args, **kwargs)
                logger.info(
                    "Function completed",
                    event_type="function_completed",
                    function=func.__name__,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    "Function failed",
                    event_type="function_error",
                    function=func.__name__,
                    error=str(e),
                    success=False
                )
                raise
    return wrapper
