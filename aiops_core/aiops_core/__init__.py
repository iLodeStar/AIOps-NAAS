"""
AIOps Core - Shared library for Version 3 Architecture
Provides data contracts, Pydantic models, and utilities for all services
"""

__version__ = "3.0.0"

from .models import (
    LogMessage,
    AnomalyDetected,
    AnomalyEnriched,
    IncidentCreated,
    EnrichmentRequest,
    EnrichmentCompleted,
    AuditEvent,
)
from .utils import (
    generate_tracking_id,
    get_logger,
    format_timestamp,
)

__all__ = [
    "LogMessage",
    "AnomalyDetected",
    "AnomalyEnriched",
    "IncidentCreated",
    "EnrichmentRequest",
    "EnrichmentCompleted",
    "AuditEvent",
    "generate_tracking_id",
    "get_logger",
    "format_timestamp",
]
