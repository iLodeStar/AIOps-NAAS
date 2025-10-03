"""
AIOps Core Data Models - Version 3
Based on DATA_CONTRACTS_Version2.md

All models use Pydantic v2 for validation and serialization.
Compact field names for NATS efficiency.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class Severity(str, Enum):
    """Incident severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    """Incident lifecycle status"""
    OPEN = "open"
    ACK = "ack"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class Domain(str, Enum):
    """Data source domains"""
    COMMS = "comms"
    APP = "app"
    NET = "net"
    SECURITY = "security"
    SYSTEM = "system"


class BaseMessage(BaseModel):
    """Base message with common fields for all events"""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    schema_version: str = Field(default="3.0", description="Schema version")
    tracking_id: str = Field(..., description="End-to-end request tracking ID")
    ts: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    ship_id: str = Field(..., description="Ship identifier")


class LogMessage(BaseMessage):
    """Raw log message from ingestion - logs.ingested.{domain}.{service}"""
    domain: Domain = Field(..., description="Log domain")
    service: str = Field(..., description="Service name")
    level: str = Field(..., description="Log level (info/warn/error/fatal)")
    msg: str = Field(..., description="Log message content")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AnomalyDetected(BaseMessage):
    """Anomaly detection event - anomaly.detected.{domain}"""
    domain: Domain = Field(..., description="Detection domain")
    anomaly_type: str = Field(..., description="Type of anomaly detected")
    metric_name: Optional[str] = Field(None, description="Metric name if metric-based")
    metric_value: Optional[float] = Field(None, description="Metric value")
    threshold: Optional[float] = Field(None, description="Threshold crossed")
    score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score 0-1")
    detector: str = Field(..., description="Detector name (threshold/ewma/pattern)")
    service: str = Field(..., description="Affected service")
    device_id: Optional[str] = Field(None, description="Device ID if applicable")
    raw_msg: Optional[str] = Field(None, description="Original log message if log-based")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional detection metadata")


class ContextData(BaseModel):
    """Historical context from ClickHouse"""
    similar_count_1h: int = Field(default=0, description="Similar anomalies in last 1h")
    similar_count_24h: int = Field(default=0, description="Similar anomalies in last 24h")
    metric_p50: Optional[float] = Field(None, description="Metric P50 baseline")
    metric_p95: Optional[float] = Field(None, description="Metric P95 baseline")
    top_error_rank: Optional[int] = Field(None, description="Rank in top errors")
    last_incident_ts: Optional[datetime] = Field(None, description="Last incident timestamp")


class AnomalyEnriched(BaseMessage):
    """Enriched anomaly with context - anomaly.enriched"""
    domain: Domain = Field(..., description="Detection domain")
    anomaly_type: str = Field(..., description="Type of anomaly")
    service: str = Field(..., description="Affected service")
    device_id: Optional[str] = Field(None, description="Device ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Anomaly score")
    detector: str = Field(..., description="Detector name")
    
    # Original detection data
    metric_name: Optional[str] = Field(None)
    metric_value: Optional[float] = Field(None)
    threshold: Optional[float] = Field(None)
    raw_msg: Optional[str] = Field(None)
    
    # Enrichment data
    context: ContextData = Field(..., description="Historical context from ClickHouse")
    severity: Severity = Field(..., description="Computed severity based on score+context")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    meta: Optional[Dict[str, Any]] = Field(default=None)


class Evidence(BaseModel):
    """Evidence reference for incidents"""
    ref: str = Field(..., description="ClickHouse reference: clickhouse://table/query")
    summary: Optional[str] = Field(None, description="Evidence summary")
    weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Evidence confidence weight")


class RunbookRef(BaseModel):
    """Runbook reference"""
    id: str = Field(..., description="Runbook identifier")
    title: str = Field(..., description="Runbook title")
    risk: Literal["low", "medium", "high"] = Field(..., description="Risk level")


class TimelineEntry(BaseModel):
    """Timeline entry for incidents"""
    ts: datetime = Field(..., description="Entry timestamp")
    event: str = Field(..., description="Event type (created/enriched/updated/resolved)")
    description: Optional[str] = Field(None, description="Event description")
    source: Optional[str] = Field(None, description="Source service")
    meta: Optional[Dict[str, Any]] = Field(default=None)


class ScopeEntry(BaseModel):
    """Incident scope - affected resources"""
    device_id: str = Field(..., description="Device identifier")
    service: str = Field(..., description="Service name")


class IncidentCreated(BaseMessage):
    """Incident creation event - incidents.created"""
    incident_id: str = Field(..., description="Unique incident ID")
    incident_type: str = Field(..., description="Incident type (link_degradation/resource_pressure/etc)")
    severity: Severity = Field(..., description="Incident severity")
    
    scope: List[ScopeEntry] = Field(..., description="Affected devices/services")
    corr_keys: List[str] = Field(..., description="Correlation keys for grouping")
    suppress_key: str = Field(..., description="Suppression key for dedup")
    
    timeline: List[TimelineEntry] = Field(default_factory=list, description="Event timeline")
    evidence: List[Evidence] = Field(default_factory=list, description="Evidence references")
    runbook_refs: List[RunbookRef] = Field(default_factory=list, description="Runbook recommendations")
    
    status: IncidentStatus = Field(default=IncidentStatus.OPEN, description="Current status")
    narrative: Optional[str] = Field(None, description="AI-generated narrative (async)")
    confidence: Optional[Literal["low", "medium", "high"]] = Field(None, description="Narrative confidence")
    owner: Optional[str] = Field(None, description="Assigned owner")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(None)


class EnrichmentRequest(BaseMessage):
    """Request for LLM enrichment - enrichment.requested.{tracking_id}"""
    incident_id: str = Field(..., description="Incident to enrich")
    incident_type: str = Field(..., description="Incident type")
    severity: Severity = Field(..., description="Incident severity")
    scope: List[ScopeEntry] = Field(..., description="Affected scope")
    evidence_refs: List[str] = Field(..., description="Evidence reference IDs")
    priority: int = Field(default=5, ge=1, le=10, description="Enrichment priority 1-10")


class EnrichmentCompleted(BaseMessage):
    """Completed LLM enrichment - enrichment.completed.{tracking_id}"""
    incident_id: str = Field(..., description="Enriched incident ID")
    narrative: str = Field(..., description="Generated narrative")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence level")
    evidence_refs: List[str] = Field(..., description="Evidence used")
    runbooks: List[RunbookRef] = Field(default_factory=list, description="Recommended runbooks")
    cache_hit: bool = Field(default=False, description="Was cached response")
    llm_latency_ms: int = Field(..., description="LLM processing time")
    token_count: int = Field(..., description="Tokens used")


class AuditEvent(BaseModel):
    """Audit log event - ops.audit"""
    model_config = ConfigDict(extra="forbid")
    
    ts: datetime = Field(default_factory=datetime.utcnow)
    tracking_id: str = Field(..., description="Request tracking ID")
    ship_id: str = Field(..., description="Ship identifier")
    user: str = Field(..., description="User performing action")
    action: str = Field(..., description="Action performed (approve/reject/execute/etc)")
    resource: str = Field(..., description="Resource affected (incident_id/action_id)")
    status: str = Field(..., description="Action status (success/failure)")
    details: Dict[str, Any] = Field(..., description="Action details")
    error: Optional[str] = Field(None, description="Error message if failed")


class StatsSnapshot(BaseModel):
    """Statistics snapshot for monitoring"""
    model_config = ConfigDict(extra="forbid")
    
    ts: datetime = Field(default_factory=datetime.utcnow)
    ship_id: str = Field(..., description="Ship identifier")
    period: str = Field(..., description="Period (1h/24h/7d)")
    
    # Volume counts
    logs_count: int = Field(default=0, description="Total logs ingested")
    anomalies_count: int = Field(default=0, description="Total anomalies detected")
    incidents_count: int = Field(default=0, description="Total incidents created")
    duplicates_count: int = Field(default=0, description="Duplicates suppressed")
    suppressions_count: int = Field(default=0, description="Active suppressions")
    
    # Breakdown by severity
    severity_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts by severity (critical/high/medium/low)"
    )
    
    # Breakdown by type
    type_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts by incident type"
    )
    
    # Breakdown by status
    status_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Incidents by status (open/ack/resolved/suppressed)"
    )
    
    # Performance metrics
    fast_path_p95_ms: Optional[float] = Field(None, description="Fast path P95 latency")
    insight_path_p95_ms: Optional[float] = Field(None, description="Insight path P95 latency")
    llm_cache_hit_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="LLM cache hit rate")
