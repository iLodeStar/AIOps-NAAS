"""
Incident Analyzer for Post-Incident Review

Provides automated incident timeline reconstruction and root cause analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class EventType(Enum):
    """Types of events in incident timeline"""
    ALERT = "alert"
    SYMPTOM = "symptom"
    REMEDIATION_STARTED = "remediation_started"
    REMEDIATION_COMPLETED = "remediation_completed"
    RESOLUTION = "resolution"
    ESCALATION = "escalation"


class RootCauseCategory(Enum):
    """Categories of root causes"""
    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_BUG = "software_bug"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ISSUE = "network_issue"
    CAPACITY_LIMIT = "capacity_limit"
    EXTERNAL_DEPENDENCY = "external_dependency"
    ENVIRONMENTAL_FACTOR = "environmental_factor"
    HUMAN_ERROR = "human_error"


@dataclass
class TimelineEvent:
    """Single event in incident timeline"""
    timestamp: datetime
    event_type: EventType
    source_system: str
    description: str
    severity: str = "info"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RootCauseAnalysis:
    """Root cause analysis results"""
    primary_cause: RootCauseCategory
    contributing_factors: List[RootCauseCategory]
    confidence_score: float
    evidence: List[str]
    timeline_correlation: List[TimelineEvent]
    recommendations: List[str]


@dataclass
class IncidentTimeline:
    """Complete incident timeline with analysis"""
    incident_id: str
    start_time: datetime
    end_time: Optional[datetime]
    events: List[TimelineEvent] = field(default_factory=list)
    total_duration_minutes: Optional[float] = None
    detection_delay_minutes: Optional[float] = None
    resolution_time_minutes: Optional[float] = None
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.end_time:
            self.total_duration_minutes = (self.end_time - self.start_time).total_seconds() / 60
        
        # Calculate detection delay (time from first symptom to first alert)
        first_symptom = next((e for e in self.events if e.event_type == EventType.SYMPTOM), None)
        first_alert = next((e for e in self.events if e.event_type == EventType.ALERT), None)
        
        if first_symptom and first_alert:
            self.detection_delay_minutes = (first_alert.timestamp - first_symptom.timestamp).total_seconds() / 60
        
        # Calculate resolution time (from first alert to resolution)
        resolution = next((e for e in self.events if e.event_type == EventType.RESOLUTION), None)
        if first_alert and resolution:
            self.resolution_time_minutes = (resolution.timestamp - first_alert.timestamp).total_seconds() / 60


class IncidentAnalyzer:
    """Analyzes incidents to extract timeline and root cause"""
    
    def __init__(self):
        self.root_cause_patterns = self._load_root_cause_patterns()
    
    def _load_root_cause_patterns(self) -> Dict[RootCauseCategory, Dict[str, Any]]:
        """Load patterns for root cause detection"""
        return {
            RootCauseCategory.HARDWARE_FAILURE: {
                "keywords": ["disk", "memory", "cpu", "power", "temperature", "fan"],
                "error_codes": ["ECC", "SMART", "thermal"],
                "typical_duration_minutes": (60, 480)  # 1-8 hours
            },
            RootCauseCategory.SOFTWARE_BUG: {
                "keywords": ["exception", "segfault", "crash", "memory leak", "deadlock"],
                "error_codes": ["SIGSEGV", "OutOfMemoryError", "NullPointerException"],
                "typical_duration_minutes": (5, 120)  # 5 minutes to 2 hours
            },
            RootCauseCategory.CONFIGURATION_ERROR: {
                "keywords": ["config", "parameter", "setting", "timeout", "limit"],
                "error_codes": ["CONFIG_ERROR", "INVALID_PARAM"],
                "typical_duration_minutes": (10, 60)  # 10 minutes to 1 hour
            },
            RootCauseCategory.NETWORK_ISSUE: {
                "keywords": ["network", "connection", "timeout", "packet loss", "latency"],
                "error_codes": ["NETWORK_UNREACHABLE", "CONNECTION_TIMEOUT"],
                "typical_duration_minutes": (5, 240)  # 5 minutes to 4 hours
            },
            RootCauseCategory.CAPACITY_LIMIT: {
                "keywords": ["capacity", "limit", "quota", "full", "overload"],
                "error_codes": ["QUOTA_EXCEEDED", "CAPACITY_LIMIT"],
                "typical_duration_minutes": (30, 180)  # 30 minutes to 3 hours
            },
            RootCauseCategory.EXTERNAL_DEPENDENCY: {
                "keywords": ["external", "api", "service", "dependency", "third party"],
                "error_codes": ["SERVICE_UNAVAILABLE", "API_ERROR"],
                "typical_duration_minutes": (15, 720)  # 15 minutes to 12 hours
            },
            RootCauseCategory.ENVIRONMENTAL_FACTOR: {
                "keywords": ["weather", "temperature", "humidity", "vibration", "shock"],
                "error_codes": ["ENVIRONMENTAL_ALARM"],
                "typical_duration_minutes": (60, 1440)  # 1-24 hours
            },
            RootCauseCategory.HUMAN_ERROR: {
                "keywords": ["manual", "operator", "mistake", "incorrect", "wrong"],
                "error_codes": ["USER_ERROR", "MANUAL_OVERRIDE"],
                "typical_duration_minutes": (5, 60)  # 5 minutes to 1 hour
            }
        }
    
    def reconstruct_timeline(self, incident_data: Dict[str, Any]) -> IncidentTimeline:
        """Reconstruct incident timeline from various data sources"""
        
        incident_id = incident_data.get("incident_id", "unknown")
        
        # Parse events from different sources
        events = []
        
        # Add alerts
        for alert in incident_data.get("alerts", []):
            events.append(TimelineEvent(
                timestamp=datetime.fromisoformat(alert["timestamp"]),
                event_type=EventType.ALERT,
                source_system=alert.get("source", "unknown"),
                description=alert["message"],
                severity=alert.get("severity", "info"),
                metadata=alert
            ))
        
        # Add symptoms
        for symptom in incident_data.get("symptoms", []):
            events.append(TimelineEvent(
                timestamp=datetime.fromisoformat(symptom["timestamp"]),
                event_type=EventType.SYMPTOM,
                source_system=symptom.get("system", "unknown"),
                description=symptom["description"],
                metadata=symptom
            ))
        
        # Add remediation actions
        for action in incident_data.get("remediation_actions", []):
            # Start event
            events.append(TimelineEvent(
                timestamp=datetime.fromisoformat(action["start_time"]),
                event_type=EventType.REMEDIATION_STARTED,
                source_system="remediation_engine",
                description=f"Started: {action['action_name']}",
                metadata=action
            ))
            
            # Completion event (if available)
            if action.get("end_time"):
                events.append(TimelineEvent(
                    timestamp=datetime.fromisoformat(action["end_time"]),
                    event_type=EventType.REMEDIATION_COMPLETED,
                    source_system="remediation_engine",
                    description=f"Completed: {action['action_name']} - {action.get('result', 'unknown')}",
                    metadata=action
                ))
        
        # Add resolution event if available
        if incident_data.get("resolution_time"):
            events.append(TimelineEvent(
                timestamp=datetime.fromisoformat(incident_data["resolution_time"]),
                event_type=EventType.RESOLUTION,
                source_system="incident_management",
                description="Incident resolved",
                metadata=incident_data
            ))
        
        # Sort events by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        # Determine start and end times
        start_time = events[0].timestamp if events else datetime.now()
        end_time = None
        
        resolution_event = next((e for e in events if e.event_type == EventType.RESOLUTION), None)
        if resolution_event:
            end_time = resolution_event.timestamp
        elif incident_data.get("status") == "resolved" and incident_data.get("resolution_time"):
            end_time = datetime.fromisoformat(incident_data["resolution_time"])
        
        return IncidentTimeline(
            incident_id=incident_id,
            start_time=start_time,
            end_time=end_time,
            events=events
        )
    
    def analyze_root_cause(self, timeline: IncidentTimeline, 
                          system_data: Optional[Dict[str, Any]] = None) -> RootCauseAnalysis:
        """Analyze root cause based on timeline and system data"""
        
        # Collect evidence from timeline events
        all_text = " ".join([e.description for e in timeline.events]).lower()
        all_metadata = {}
        for event in timeline.events:
            all_metadata.update(event.metadata)
        
        # Score each potential root cause
        cause_scores = {}
        evidence_found = {}
        
        for cause, patterns in self.root_cause_patterns.items():
            score = 0.0
            evidence = []
            
            # Keyword matching
            for keyword in patterns["keywords"]:
                if keyword in all_text:
                    score += 1.0
                    evidence.append(f"Keyword found: {keyword}")
            
            # Error code matching
            for error_code in patterns["error_codes"]:
                if error_code.lower() in all_text:
                    score += 2.0  # Error codes are more specific
                    evidence.append(f"Error code found: {error_code}")
            
            # Duration analysis
            if timeline.total_duration_minutes:
                min_duration, max_duration = patterns["typical_duration_minutes"]
                if min_duration <= timeline.total_duration_minutes <= max_duration:
                    score += 1.0
                    evidence.append(f"Duration matches pattern: {timeline.total_duration_minutes:.1f} min")
            
            # System data analysis (if available)
            if system_data:
                if cause == RootCauseCategory.HARDWARE_FAILURE:
                    if system_data.get("cpu_usage", 0) > 95:
                        score += 1.5
                        evidence.append("High CPU usage detected")
                    if system_data.get("memory_usage", 0) > 90:
                        score += 1.5
                        evidence.append("High memory usage detected")
                
                elif cause == RootCauseCategory.NETWORK_ISSUE:
                    if system_data.get("packet_loss", 0) > 1:
                        score += 2.0
                        evidence.append(f"Packet loss: {system_data['packet_loss']}%")
                    if system_data.get("latency_ms", 0) > 1000:
                        score += 1.5
                        evidence.append(f"High latency: {system_data['latency_ms']}ms")
            
            cause_scores[cause] = score
            evidence_found[cause] = evidence
        
        # Find primary cause (highest score)
        primary_cause = max(cause_scores, key=cause_scores.get)
        primary_score = cause_scores[primary_cause]
        
        # Find contributing factors (scores > 50% of primary)
        contributing_factors = [
            cause for cause, score in cause_scores.items()
            if cause != primary_cause and score > primary_score * 0.5
        ]
        
        # Calculate confidence based on evidence strength
        confidence = min(primary_score / 5.0, 1.0)  # Normalize to 0-1
        
        # Generate recommendations
        recommendations = self._generate_recommendations(primary_cause, timeline)
        
        # Find correlated timeline events
        timeline_correlation = [
            event for event in timeline.events
            if any(keyword in event.description.lower() 
                  for keyword in self.root_cause_patterns[primary_cause]["keywords"])
        ]
        
        return RootCauseAnalysis(
            primary_cause=primary_cause,
            contributing_factors=contributing_factors,
            confidence_score=confidence,
            evidence=evidence_found[primary_cause],
            timeline_correlation=timeline_correlation,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, root_cause: RootCauseCategory, 
                                timeline: IncidentTimeline) -> List[str]:
        """Generate recommendations based on root cause"""
        
        recommendations = {
            RootCauseCategory.HARDWARE_FAILURE: [
                "Schedule preventive hardware maintenance",
                "Implement hardware monitoring with predictive alerts",
                "Consider hardware redundancy improvements",
                "Review hardware warranty and replacement schedules"
            ],
            RootCauseCategory.SOFTWARE_BUG: [
                "Implement additional automated testing",
                "Review code quality and debugging practices",
                "Consider blue-green deployments for safer releases",
                "Enhance error handling and graceful degradation"
            ],
            RootCauseCategory.CONFIGURATION_ERROR: [
                "Implement configuration validation pipelines",
                "Use infrastructure as code practices",
                "Create configuration change approval processes",
                "Implement configuration drift detection"
            ],
            RootCauseCategory.NETWORK_ISSUE: [
                "Implement network redundancy and failover",
                "Enhance network monitoring and alerting",
                "Review network capacity planning",
                "Consider network performance optimization"
            ],
            RootCauseCategory.CAPACITY_LIMIT: [
                "Implement proactive capacity monitoring",
                "Create auto-scaling policies",
                "Review capacity planning processes",
                "Consider load balancing improvements"
            ],
            RootCauseCategory.EXTERNAL_DEPENDENCY: [
                "Implement circuit breaker patterns",
                "Create fallback mechanisms for external services",
                "Monitor external service SLAs",
                "Consider reducing external dependencies"
            ],
            RootCauseCategory.ENVIRONMENTAL_FACTOR: [
                "Enhance environmental monitoring systems",
                "Implement environmental redundancy",
                "Review environmental protection measures",
                "Consider climate-controlled alternatives"
            ],
            RootCauseCategory.HUMAN_ERROR: [
                "Implement additional automation to reduce manual steps",
                "Enhance training and documentation",
                "Create validation checkpoints for manual operations",
                "Consider implementing approval workflows"
            ]
        }
        
        base_recommendations = recommendations.get(root_cause, ["Review incident details for specific recommendations"])
        
        # Add timeline-specific recommendations
        if timeline.detection_delay_minutes and timeline.detection_delay_minutes > 10:
            base_recommendations.append("Improve incident detection speed")
        
        if timeline.resolution_time_minutes and timeline.resolution_time_minutes > 60:
            base_recommendations.append("Optimize incident resolution procedures")
        
        return base_recommendations[:5]  # Limit to top 5 recommendations