"""
Pattern Recognizer for Post-Incident Learning

Identifies recurring patterns and extracts learning insights from incidents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from collections import defaultdict
import json
import hashlib

from .incident_analyzer import IncidentTimeline, RootCauseAnalysis, RootCauseCategory


class PatternType(Enum):
    """Types of incident patterns"""
    TEMPORAL = "temporal"  # Time-based patterns
    SYSTEM = "system"  # System/component patterns
    ROOT_CAUSE = "root_cause"  # Root cause patterns
    REMEDIATION = "remediation"  # Remediation effectiveness patterns
    ENVIRONMENTAL = "environmental"  # Environmental factor patterns


class LearningType(Enum):
    """Types of learning insights"""
    CONFIDENCE_ADJUSTMENT = "confidence_adjustment"
    POLICY_REFINEMENT = "policy_refinement"
    NEW_SCENARIO = "new_scenario"
    PREVENTION_OPPORTUNITY = "prevention_opportunity"
    PROCESS_IMPROVEMENT = "process_improvement"


@dataclass
class IncidentPattern:
    """Represents a recurring incident pattern"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    frequency: int
    confidence: float
    first_seen: datetime
    last_seen: datetime
    affected_systems: Set[str] = field(default_factory=set)
    common_root_causes: List[RootCauseCategory] = field(default_factory=list)
    typical_duration_minutes: Optional[float] = None
    success_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class LearningPattern:
    """Learning insight extracted from pattern analysis"""
    learning_id: str
    learning_type: LearningType
    source_pattern: str
    description: str
    confidence: float
    recommendation: str
    impact_assessment: str
    implementation_priority: str  # high, medium, low
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternRecognizer:
    """Recognizes patterns in incident data and extracts learning insights"""
    
    def __init__(self, min_pattern_frequency: int = 3, min_pattern_confidence: float = 0.7):
        self.min_pattern_frequency = min_pattern_frequency
        self.min_pattern_confidence = min_pattern_confidence
        self.known_patterns: Dict[str, IncidentPattern] = {}
        self.learning_history: List[LearningPattern] = []
    
    def analyze_incidents(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze multiple incidents to identify patterns"""
        
        patterns = []
        
        # Analyze temporal patterns
        patterns.extend(self._analyze_temporal_patterns(incidents_data))
        
        # Analyze system patterns  
        patterns.extend(self._analyze_system_patterns(incidents_data))
        
        # Analyze root cause patterns
        patterns.extend(self._analyze_root_cause_patterns(incidents_data))
        
        # Analyze remediation patterns
        patterns.extend(self._analyze_remediation_patterns(incidents_data))
        
        # Analyze environmental patterns
        patterns.extend(self._analyze_environmental_patterns(incidents_data))
        
        # Filter patterns by minimum frequency and confidence
        filtered_patterns = [
            p for p in patterns 
            if p.frequency >= self.min_pattern_frequency and p.confidence >= self.min_pattern_confidence
        ]
        
        # Update known patterns
        for pattern in filtered_patterns:
            self.known_patterns[pattern.pattern_id] = pattern
        
        return filtered_patterns
    
    def _analyze_temporal_patterns(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze time-based patterns"""
        patterns = []
        
        # Group incidents by hour of day
        hourly_incidents = defaultdict(list)
        for incident in incidents_data:
            if incident.get("start_time"):
                hour = datetime.fromisoformat(incident["start_time"]).hour
                hourly_incidents[hour].append(incident)
        
        # Find peak incident hours
        for hour, hour_incidents in hourly_incidents.items():
            if len(hour_incidents) >= self.min_pattern_frequency:
                pattern_id = f"temporal_peak_hour_{hour:02d}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.TEMPORAL,
                    description=f"High incident frequency during hour {hour:02d}:00-{hour+1:02d}:00",
                    frequency=len(hour_incidents),
                    confidence=min(len(hour_incidents) / 10.0, 1.0),  # Normalize to 0-1
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in hour_incidents),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in hour_incidents),
                    metadata={"peak_hour": hour, "incidents": [inc["incident_id"] for inc in hour_incidents]}
                )
                patterns.append(pattern)
        
        # Group incidents by day of week
        daily_incidents = defaultdict(list)
        for incident in incidents_data:
            if incident.get("start_time"):
                day = datetime.fromisoformat(incident["start_time"]).weekday()
                daily_incidents[day].append(incident)
        
        # Find problematic days
        for day, day_incidents in daily_incidents.items():
            if len(day_incidents) >= self.min_pattern_frequency:
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                pattern_id = f"temporal_peak_day_{day}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.TEMPORAL,
                    description=f"High incident frequency on {day_names[day]}s",
                    frequency=len(day_incidents),
                    confidence=min(len(day_incidents) / 15.0, 1.0),
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in day_incidents),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in day_incidents),
                    metadata={"peak_day": day, "day_name": day_names[day]}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_system_patterns(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze system/component-based patterns"""
        patterns = []
        
        # Group incidents by affected system
        system_incidents = defaultdict(list)
        for incident in incidents_data:
            for system in incident.get("affected_systems", []):
                system_incidents[system].append(incident)
        
        # Find problematic systems
        for system, sys_incidents in system_incidents.items():
            if len(sys_incidents) >= self.min_pattern_frequency:
                # Calculate average duration
                durations = []
                for incident in sys_incidents:
                    if incident.get("duration_minutes"):
                        durations.append(incident["duration_minutes"])
                
                avg_duration = sum(durations) / len(durations) if durations else None
                
                pattern_id = f"system_frequent_{hashlib.md5(system.encode()).hexdigest()[:8]}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.SYSTEM,
                    description=f"Frequent incidents affecting {system}",
                    frequency=len(sys_incidents),
                    confidence=min(len(sys_incidents) / 8.0, 1.0),
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in sys_incidents if inc.get("start_time")),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in sys_incidents if inc.get("start_time")),
                    affected_systems={system},
                    typical_duration_minutes=avg_duration,
                    metadata={"primary_system": system, "incident_count": len(sys_incidents)}
                )
                patterns.append(pattern)
        
        # Look for system correlation patterns
        system_pairs = defaultdict(list)
        for incident in incidents_data:
            affected = incident.get("affected_systems", [])
            if len(affected) >= 2:
                for i, sys1 in enumerate(affected):
                    for sys2 in affected[i+1:]:
                        pair_key = tuple(sorted([sys1, sys2]))
                        system_pairs[pair_key].append(incident)
        
        # Find correlated system failures
        for (sys1, sys2), pair_incidents in system_pairs.items():
            if len(pair_incidents) >= self.min_pattern_frequency:
                pattern_id = f"system_correlation_{hashlib.md5(f'{sys1}_{sys2}'.encode()).hexdigest()[:8]}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.SYSTEM,
                    description=f"Correlated failures: {sys1} and {sys2}",
                    frequency=len(pair_incidents),
                    confidence=min(len(pair_incidents) / 5.0, 1.0),
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in pair_incidents if inc.get("start_time")),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in pair_incidents if inc.get("start_time")),
                    affected_systems={sys1, sys2},
                    metadata={"correlated_systems": [sys1, sys2], "correlation_strength": len(pair_incidents)}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_root_cause_patterns(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze root cause patterns"""
        patterns = []
        
        # Group incidents by root cause
        root_cause_incidents = defaultdict(list)
        for incident in incidents_data:
            root_cause = incident.get("root_cause_analysis", {}).get("primary_cause")
            if root_cause:
                root_cause_incidents[root_cause].append(incident)
        
        # Find frequent root causes
        for root_cause, rc_incidents in root_cause_incidents.items():
            if len(rc_incidents) >= self.min_pattern_frequency:
                # Calculate success rates for remediation
                successful_remediations = sum(1 for inc in rc_incidents if inc.get("remediation_success", False))
                success_rate = successful_remediations / len(rc_incidents) if rc_incidents else 0.0
                
                pattern_id = f"root_cause_{root_cause}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.ROOT_CAUSE,
                    description=f"Recurring incidents with root cause: {root_cause}",
                    frequency=len(rc_incidents),
                    confidence=min(len(rc_incidents) / 6.0, 1.0),
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in rc_incidents if inc.get("start_time")),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in rc_incidents if inc.get("start_time")),
                    common_root_causes=[RootCauseCategory(root_cause)] if root_cause else [],
                    success_rate=success_rate,
                    metadata={"primary_root_cause": root_cause, "remediation_success_rate": success_rate}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_remediation_patterns(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze remediation effectiveness patterns"""
        patterns = []
        
        # Group incidents by remediation action
        remediation_effectiveness = defaultdict(list)
        for incident in incidents_data:
            for action in incident.get("remediation_actions", []):
                action_name = action.get("action_name", "unknown")
                success = action.get("result") == "success"
                remediation_effectiveness[action_name].append({
                    "incident": incident,
                    "action": action,
                    "success": success
                })
        
        # Find patterns in remediation effectiveness
        for action_name, action_data in remediation_effectiveness.items():
            if len(action_data) >= self.min_pattern_frequency:
                success_count = sum(1 for data in action_data if data["success"])
                success_rate = success_count / len(action_data)
                
                # Create pattern for low success rate remediations
                if success_rate < 0.7:  # Low success threshold
                    pattern_id = f"remediation_low_success_{hashlib.md5(action_name.encode()).hexdigest()[:8]}"
                    pattern = IncidentPattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.REMEDIATION,
                        description=f"Low success rate for remediation: {action_name}",
                        frequency=len(action_data),
                        confidence=min((1.0 - success_rate) * 2, 1.0),  # Higher confidence for lower success rates
                        first_seen=min(datetime.fromisoformat(data["incident"]["start_time"]) for data in action_data if data["incident"].get("start_time")),
                        last_seen=max(datetime.fromisoformat(data["incident"]["start_time"]) for data in action_data if data["incident"].get("start_time")),
                        success_rate=success_rate,
                        metadata={
                            "remediation_action": action_name,
                            "total_attempts": len(action_data),
                            "success_count": success_count,
                            "failure_count": len(action_data) - success_count
                        }
                    )
                    patterns.append(pattern)
                
                # Create pattern for highly effective remediations
                elif success_rate > 0.9 and len(action_data) >= 5:
                    pattern_id = f"remediation_high_success_{hashlib.md5(action_name.encode()).hexdigest()[:8]}"
                    pattern = IncidentPattern(
                        pattern_id=pattern_id,
                        pattern_type=PatternType.REMEDIATION,
                        description=f"Highly effective remediation: {action_name}",
                        frequency=len(action_data),
                        confidence=success_rate,
                        first_seen=min(datetime.fromisoformat(data["incident"]["start_time"]) for data in action_data if data["incident"].get("start_time")),
                        last_seen=max(datetime.fromisoformat(data["incident"]["start_time"]) for data in action_data if data["incident"].get("start_time")),
                        success_rate=success_rate,
                        metadata={
                            "remediation_action": action_name,
                            "total_attempts": len(action_data),
                            "success_count": success_count
                        }
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_environmental_patterns(self, incidents_data: List[Dict[str, Any]]) -> List[IncidentPattern]:
        """Analyze environmental factor patterns"""
        patterns = []
        
        # Group incidents by environmental conditions
        env_incidents = defaultdict(list)
        for incident in incidents_data:
            env_factors = incident.get("environmental_factors", {})
            for factor, value in env_factors.items():
                if value and str(value).lower() not in ["none", "null", "normal"]:
                    env_key = f"{factor}:{value}"
                    env_incidents[env_key].append(incident)
        
        # Find environmental correlation patterns
        for env_condition, env_incident_list in env_incidents.items():
            if len(env_incident_list) >= self.min_pattern_frequency:
                factor, value = env_condition.split(":", 1)
                
                pattern_id = f"environmental_{hashlib.md5(env_condition.encode()).hexdigest()[:8]}"
                pattern = IncidentPattern(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.ENVIRONMENTAL,
                    description=f"Incidents correlated with {factor}: {value}",
                    frequency=len(env_incident_list),
                    confidence=min(len(env_incident_list) / 4.0, 1.0),
                    first_seen=min(datetime.fromisoformat(inc["start_time"]) for inc in env_incident_list if inc.get("start_time")),
                    last_seen=max(datetime.fromisoformat(inc["start_time"]) for inc in env_incident_list if inc.get("start_time")),
                    metadata={
                        "environmental_factor": factor,
                        "environmental_value": value,
                        "incident_correlation": len(env_incident_list)
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def extract_learning_insights(self, patterns: List[IncidentPattern], 
                                 remediation_history: Optional[Dict[str, Any]] = None) -> List[LearningPattern]:
        """Extract learning insights from identified patterns"""
        
        learning_insights = []
        
        for pattern in patterns:
            insights = self._extract_pattern_learnings(pattern, remediation_history)
            learning_insights.extend(insights)
        
        # Remove duplicates and sort by priority
        unique_insights = []
        seen_recommendations = set()
        
        for insight in learning_insights:
            if insight.recommendation not in seen_recommendations:
                unique_insights.append(insight)
                seen_recommendations.add(insight.recommendation)
        
        # Sort by implementation priority and confidence
        priority_order = {"high": 3, "medium": 2, "low": 1}
        unique_insights.sort(
            key=lambda x: (priority_order.get(x.implementation_priority, 0), x.confidence),
            reverse=True
        )
        
        # Update learning history
        self.learning_history.extend(unique_insights)
        
        return unique_insights
    
    def _extract_pattern_learnings(self, pattern: IncidentPattern, 
                                  remediation_history: Optional[Dict[str, Any]] = None) -> List[LearningPattern]:
        """Extract learning insights from a specific pattern"""
        
        learnings = []
        
        if pattern.pattern_type == PatternType.TEMPORAL:
            # Temporal patterns suggest prevention opportunities
            if "peak_hour" in pattern.metadata:
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}",
                    learning_type=LearningType.PREVENTION_OPPORTUNITY,
                    source_pattern=pattern.pattern_id,
                    description=f"High incident frequency during specific hours suggests preventive action opportunities",
                    confidence=pattern.confidence,
                    recommendation=f"Schedule preventive maintenance before peak incident hour {pattern.metadata['peak_hour']}:00",
                    impact_assessment="Could reduce incident frequency by 20-40%",
                    implementation_priority="medium",
                    metadata={"peak_hour": pattern.metadata["peak_hour"]}
                )
                learnings.append(learning)
        
        elif pattern.pattern_type == PatternType.SYSTEM:
            if "primary_system" in pattern.metadata:
                # System reliability issues
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}",
                    learning_type=LearningType.PREVENTION_OPPORTUNITY,
                    source_pattern=pattern.pattern_id,
                    description=f"System {pattern.metadata['primary_system']} shows high incident frequency",
                    confidence=pattern.confidence,
                    recommendation=f"Implement enhanced monitoring and redundancy for {pattern.metadata['primary_system']}",
                    impact_assessment="Could reduce system-specific incidents by 30-50%",
                    implementation_priority="high" if pattern.frequency > 10 else "medium"
                )
                learnings.append(learning)
            
            elif "correlated_systems" in pattern.metadata:
                # System correlation suggests dependency issues
                systems = pattern.metadata["correlated_systems"]
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}",
                    learning_type=LearningType.POLICY_REFINEMENT,
                    source_pattern=pattern.pattern_id,
                    description=f"Strong correlation between failures of {systems[0]} and {systems[1]}",
                    confidence=pattern.confidence,
                    recommendation=f"Create dependency-aware policies for {' and '.join(systems)}",
                    impact_assessment="Could prevent cascading failures",
                    implementation_priority="high"
                )
                learnings.append(learning)
        
        elif pattern.pattern_type == PatternType.ROOT_CAUSE:
            # Root cause patterns suggest process improvements
            root_cause = pattern.metadata.get("primary_root_cause")
            success_rate = pattern.metadata.get("remediation_success_rate", 0)
            
            if success_rate < 0.7:
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}",
                    learning_type=LearningType.PROCESS_IMPROVEMENT,
                    source_pattern=pattern.pattern_id,
                    description=f"Low remediation success rate for {root_cause} incidents",
                    confidence=pattern.confidence,
                    recommendation=f"Develop more effective remediation procedures for {root_cause}",
                    impact_assessment="Could improve resolution success by 15-30%",
                    implementation_priority="high"
                )
                learnings.append(learning)
        
        elif pattern.pattern_type == PatternType.REMEDIATION:
            # Remediation patterns suggest confidence adjustments
            action_name = pattern.metadata.get("remediation_action")
            success_rate = pattern.success_rate or 0
            
            if success_rate < 0.5:
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}",
                    learning_type=LearningType.CONFIDENCE_ADJUSTMENT,
                    source_pattern=pattern.pattern_id,
                    description=f"Remediation action '{action_name}' has low success rate ({success_rate:.1%})",
                    confidence=pattern.confidence,
                    recommendation=f"Lower confidence threshold for '{action_name}' or require manual approval",
                    impact_assessment="Could prevent ineffective automatic remediations",
                    implementation_priority="high"
                )
                learnings.append(learning)
            
            elif success_rate > 0.9 and pattern.frequency >= 5:
                learning = LearningPattern(
                    learning_id=f"learning_{pattern.pattern_id}_promote",
                    learning_type=LearningType.CONFIDENCE_ADJUSTMENT,
                    source_pattern=pattern.pattern_id,
                    description=f"Remediation action '{action_name}' has high success rate ({success_rate:.1%})",
                    confidence=pattern.confidence,
                    recommendation=f"Increase confidence threshold for '{action_name}' to enable more automation",
                    impact_assessment="Could reduce manual intervention requirements by 10-20%",
                    implementation_priority="medium"
                )
                learnings.append(learning)
        
        elif pattern.pattern_type == PatternType.ENVIRONMENTAL:
            # Environmental patterns suggest monitoring improvements
            factor = pattern.metadata.get("environmental_factor")
            value = pattern.metadata.get("environmental_value")
            
            learning = LearningPattern(
                learning_id=f"learning_{pattern.pattern_id}",
                learning_type=LearningType.PREVENTION_OPPORTUNITY,
                source_pattern=pattern.pattern_id,
                description=f"Incidents strongly correlated with {factor}: {value}",
                confidence=pattern.confidence,
                recommendation=f"Implement proactive monitoring and alerts for {factor} conditions",
                impact_assessment="Could enable preventive actions before incidents occur",
                implementation_priority="medium"
            )
            learnings.append(learning)
        
        return learnings