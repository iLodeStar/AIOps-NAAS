"""
AIOps Core Utilities - Version 3
Shared utility functions for all services
"""

import uuid
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager


def generate_tracking_id(prefix: str = "req") -> str:
    """
    Generate unique tracking ID for end-to-end request tracing
    Format: {prefix}-{timestamp}-{uuid}
    Example: req-20250102-103045-a1b2c3d4
    """
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}-{ts}-{uid}"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime to ISO8601 string"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"


class StructuredLogger:
    """
    Structured logger with tracking_id context
    Ensures all logs include tracking_id for end-to-end tracing
    """
    
    def __init__(self, name: str, tracking_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.tracking_id = tracking_id or "unknown"
        self.context: Dict[str, Any] = {}
    
    def set_tracking_id(self, tracking_id: str):
        """Update tracking ID context"""
        self.tracking_id = tracking_id
    
    def add_context(self, **kwargs):
        """Add additional context to all log messages"""
        self.context.update(kwargs)
    
    def _format_message(self, msg: str, extra: Optional[Dict] = None) -> str:
        """Format message with tracking_id and context"""
        ctx = {"tracking_id": self.tracking_id, **self.context}
        if extra:
            ctx.update(extra)
        
        # Format as key=value pairs for easy parsing
        ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items())
        return f"{msg} | {ctx_str}"
    
    def debug(self, msg: str, **kwargs):
        self.logger.debug(self._format_message(msg, kwargs))
    
    def info(self, msg: str, **kwargs):
        self.logger.info(self._format_message(msg, kwargs))
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(self._format_message(msg, kwargs))
    
    def error(self, msg: str, error: Optional[Exception] = None, **kwargs):
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_msg"] = str(error)
        self.logger.error(self._format_message(msg, kwargs))
    
    def critical(self, msg: str, error: Optional[Exception] = None, **kwargs):
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_msg"] = str(error)
        self.logger.critical(self._format_message(msg, kwargs))


def get_logger(name: str, tracking_id: Optional[str] = None) -> StructuredLogger:
    """
    Get structured logger with tracking context
    
    Usage:
        logger = get_logger(__name__, tracking_id="req-123")
        logger.info("Processing event", event_type="anomaly", service="comms")
    """
    return StructuredLogger(name, tracking_id)


def setup_logging(level: str = "INFO", format_json: bool = False):
    """
    Setup root logging configuration
    
    Args:
        level: Log level (DEBUG/INFO/WARNING/ERROR)
        format_json: Use JSON format (for production) vs human-readable (dev)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if format_json:
        # JSON format for production log aggregation
        fmt = '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    else:
        # Human-readable format for development
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


@contextmanager
def tracked_operation(logger: StructuredLogger, operation: str, **context):
    """
    Context manager for tracked operations with automatic timing and error logging
    
    Usage:
        with tracked_operation(logger, "process_anomaly", service="comms"):
            process_anomaly(event)
    """
    start = datetime.utcnow()
    logger.info(f"Starting {operation}", **context)
    
    try:
        yield
        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        logger.info(f"Completed {operation}", duration_ms=f"{duration_ms:.2f}", **context)
    except Exception as e:
        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        logger.error(
            f"Failed {operation}",
            error=e,
            duration_ms=f"{duration_ms:.2f}",
            **context
        )
        raise


def sanitize_ship_id(ship_id: str) -> str:
    """Sanitize ship ID for safe use in identifiers"""
    return ship_id.replace(" ", "_").replace("/", "-").lower()


def compute_suppress_key(
    incident_type: str,
    device_id: Optional[str],
    service: str,
    ship_id: str
) -> str:
    """
    Compute suppression key for incident deduplication
    Format: {type}:{ship}:{device}:{service}
    """
    device = device_id or "none"
    return f"{incident_type}:{ship_id}:{device}:{service}"


def compute_correlation_keys(
    incident_type: str,
    device_id: Optional[str],
    service: str,
    ship_id: str,
    domain: str
) -> list[str]:
    """
    Compute correlation keys for incident grouping
    Returns multiple keys at different granularities for flexible correlation
    """
    device = device_id or "none"
    
    keys = [
        f"{incident_type}:{ship_id}",  # Type + Ship
        f"{domain}:{ship_id}",  # Domain + Ship
        f"{service}:{ship_id}",  # Service + Ship
        f"{device}:{ship_id}",  # Device + Ship
        f"{incident_type}:{service}:{ship_id}",  # Type + Service + Ship
    ]
    
    return keys


def truncate_message(msg: str, max_length: int = 500) -> str:
    """Truncate message to max length with ellipsis"""
    if len(msg) <= max_length:
        return msg
    return msg[:max_length - 3] + "..."


def extract_error_message(exception: Exception, include_traceback: bool = False) -> str:
    """
    Extract clean error message from exception
    Propagates error messages end-to-end for debugging
    """
    error_msg = f"{type(exception).__name__}: {str(exception)}"
    
    if include_traceback:
        import traceback
        tb = traceback.format_exc()
        error_msg += f"\n{tb}"
    
    return error_msg
