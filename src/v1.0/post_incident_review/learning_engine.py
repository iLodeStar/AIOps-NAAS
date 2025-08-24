"""
Learning Engine for Post-Incident Review

Implements continuous learning and improvement based on incident analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json

from .incident_analyzer import IncidentTimeline, RootCauseAnalysis
from .pattern_recognizer import IncidentPattern, LearningPattern, LearningType
from .effectiveness_assessor import RemediationAssessment, EffectivenessLevel


class AdjustmentType(Enum):
    """Types of adjustments the learning engine can make"""
    CONFIDENCE_INCREASE = "confidence_increase"
    CONFIDENCE_DECREASE = "confidence_decrease"
    POLICY_TIGHTENING = "policy_tightening"
    POLICY_RELAXATION = "policy_relaxation"
    NEW_SCENARIO = "new_scenario"
    SCENARIO_REFINEMENT = "scenario_refinement"


class ImplementationStatus(Enum):
    """Status of learning implementation"""
    PENDING = "pending"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ConfidenceAdjustment:
    """Specific confidence score adjustment recommendation"""
    adjustment_id: str
    scenario_id: str
    current_confidence: float
    suggested_confidence: float
    adjustment_reason: str
    evidence_strength: float
    impact_assessment: str
    implementation_status: ImplementationStatus = ImplementationStatus.PENDING
    created_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyRecommendation:
    """Policy change recommendation"""
    recommendation_id: str
    policy_type: str  # approval_threshold, time_window, blast_radius, etc.
    current_value: Any
    suggested_value: Any
    rationale: str
    expected_impact: str
    risk_level: str  # low, medium, high
    affected_scenarios: List[str] = field(default_factory=list)
    implementation_status: ImplementationStatus = ImplementationStatus.PENDING
    created_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningCycle:
    """Complete learning cycle results"""
    cycle_id: str
    analysis_date: datetime
    incidents_analyzed: int
    patterns_identified: int
    confidence_adjustments: List[ConfidenceAdjustment] = field(default_factory=list)
    policy_recommendations: List[PolicyRecommendation] = field(default_factory=list)
    new_scenarios_suggested: List[Dict[str, Any]] = field(default_factory=list)
    effectiveness_improvements: List[str] = field(default_factory=list)
    implementation_plan: Dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """Main learning engine that coordinates post-incident learning"""
    
    def __init__(self, confidence_adjustment_threshold: float = 0.1,
                 min_evidence_strength: float = 0.7):
        self.confidence_adjustment_threshold = confidence_adjustment_threshold
        self.min_evidence_strength = min_evidence_strength
        self.learning_history: List[LearningCycle] = []
        self.implemented_adjustments: Dict[str, ConfidenceAdjustment] = {}
        self.implemented_policies: Dict[str, PolicyRecommendation] = {}
        
        # Learning configuration
        self.learning_config = {
            "max_confidence_adjustment": 0.2,  # Maximum single adjustment
            "min_incidents_for_adjustment": 5,  # Minimum incidents before adjustment
            "confidence_decay_rate": 0.95,     # Decay old adjustments over time
            "policy_change_threshold": 0.8,    # Threshold for policy changes
            "review_period_days": 7            # How often to run learning cycles
        }
    
    def run_learning_cycle(self, 
                          incident_timelines: List[IncidentTimeline],
                          root_cause_analyses: List[RootCauseAnalysis],
                          incident_patterns: List[IncidentPattern],
                          effectiveness_assessments: List[RemediationAssessment],
                          current_confidence_scores: Dict[str, float],
                          current_policies: Dict[str, Any]) -> LearningCycle:
        """Run a complete learning cycle"""
        
        cycle_id = f"learning_cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cycle = LearningCycle(
            cycle_id=cycle_id,
            analysis_date=datetime.now(),
            incidents_analyzed=len(incident_timelines),
            patterns_identified=len(incident_patterns)
        )
        
        # Generate confidence adjustments
        cycle.confidence_adjustments = self._generate_confidence_adjustments(
            effectiveness_assessments,
            incident_patterns,
            current_confidence_scores
        )
        
        # Generate policy recommendations
        cycle.policy_recommendations = self._generate_policy_recommendations(
            incident_patterns,
            effectiveness_assessments,
            current_policies
        )
        
        # Suggest new scenarios
        cycle.new_scenarios_suggested = self._suggest_new_scenarios(
            root_cause_analyses,
            incident_patterns
        )
        
        # Identify effectiveness improvement opportunities
        cycle.effectiveness_improvements = self._identify_effectiveness_improvements(
            effectiveness_assessments,
            incident_patterns
        )
        
        # Create implementation plan
        cycle.implementation_plan = self._create_implementation_plan(cycle)
        
        # Store in learning history
        self.learning_history.append(cycle)
        
        return cycle
    
    def _generate_confidence_adjustments(self,
                                       assessments: List[RemediationAssessment],
                                       patterns: List[IncidentPattern],
                                       current_scores: Dict[str, float]) -> List[ConfidenceAdjustment]:
        """Generate confidence score adjustment recommendations"""
        
        adjustments = []
        
        for assessment in assessments:
            scenario_id = assessment.remediation_id
            current_confidence = current_scores.get(scenario_id, 0.5)
            
            # Skip if insufficient data
            if assessment.total_attempts < self.learning_config["min_incidents_for_adjustment"]:
                continue
            
            # Calculate suggested adjustment based on performance
            suggested_adjustment = 0.0
            evidence_strength = 0.0
            reason_parts = []
            
            # Based on success rate
            success_rate = assessment.successful_attempts / max(assessment.total_attempts, 1)
            if success_rate >= 0.95:
                suggested_adjustment += 0.1
                evidence_strength += 0.3
                reason_parts.append(f"excellent success rate ({success_rate:.1%})")
            elif success_rate >= 0.85:
                suggested_adjustment += 0.05
                evidence_strength += 0.2
                reason_parts.append(f"good success rate ({success_rate:.1%})")
            elif success_rate < 0.60:
                suggested_adjustment -= 0.15
                evidence_strength += 0.4
                reason_parts.append(f"poor success rate ({success_rate:.1%})")
            elif success_rate < 0.75:
                suggested_adjustment -= 0.05
                evidence_strength += 0.2
                reason_parts.append(f"below target success rate ({success_rate:.1%})")
            
            # Based on resolution time
            if assessment.average_resolution_time_minutes > 0:
                if assessment.average_resolution_time_minutes <= 15:
                    suggested_adjustment += 0.05
                    evidence_strength += 0.1
                    reason_parts.append("fast resolution time")
                elif assessment.average_resolution_time_minutes >= 90:
                    suggested_adjustment -= 0.1
                    evidence_strength += 0.2
                    reason_parts.append("slow resolution time")
            
            # Based on trends
            if assessment.trend_analysis.get("success_rate_trend") == "improving":
                suggested_adjustment += 0.03
                evidence_strength += 0.1
                reason_parts.append("improving trend")
            elif assessment.trend_analysis.get("success_rate_trend") == "degrading":
                suggested_adjustment -= 0.05
                evidence_strength += 0.15
                reason_parts.append("degrading trend")
            
            # Based on rollback rate (if available)
            rollback_metrics = [m for m in assessment.metrics if m.metric.value == "rollback_rate"]
            if rollback_metrics:
                rollback_rate = rollback_metrics[0].value
                if rollback_rate > 0.1:  # > 10% rollback rate
                    suggested_adjustment -= 0.1
                    evidence_strength += 0.2
                    reason_parts.append(f"high rollback rate ({rollback_rate:.1%})")
            
            # Apply limits
            max_adjustment = self.learning_config["max_confidence_adjustment"]
            suggested_adjustment = max(-max_adjustment, min(max_adjustment, suggested_adjustment))
            
            # Only recommend if adjustment is significant and evidence is strong
            if (abs(suggested_adjustment) >= self.confidence_adjustment_threshold and 
                evidence_strength >= self.min_evidence_strength):
                
                new_confidence = max(0.0, min(1.0, current_confidence + suggested_adjustment))
                
                # Determine impact assessment
                if suggested_adjustment > 0:
                    impact = f"Will increase automation by allowing more confident decisions"
                else:
                    impact = f"Will reduce risk by requiring more manual oversight"
                
                adjustment = ConfidenceAdjustment(
                    adjustment_id=f"conf_adj_{scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    scenario_id=scenario_id,
                    current_confidence=current_confidence,
                    suggested_confidence=new_confidence,
                    adjustment_reason="; ".join(reason_parts),
                    evidence_strength=evidence_strength,
                    impact_assessment=impact,
                    metadata={
                        "assessment_data": {
                            "success_rate": success_rate,
                            "total_attempts": assessment.total_attempts,
                            "avg_resolution_time": assessment.average_resolution_time_minutes,
                            "effectiveness_level": assessment.overall_effectiveness.value
                        }
                    }
                )
                adjustments.append(adjustment)
        
        return adjustments
    
    def _generate_policy_recommendations(self,
                                       patterns: List[IncidentPattern],
                                       assessments: List[RemediationAssessment],
                                       current_policies: Dict[str, Any]) -> List[PolicyRecommendation]:
        """Generate policy change recommendations"""
        
        recommendations = []
        
        # Analyze patterns for policy implications
        for pattern in patterns:
            
            # Temporal patterns suggest time window adjustments
            if pattern.pattern_type.value == "temporal" and pattern.frequency >= 5:
                if "peak_hour" in pattern.metadata:
                    peak_hour = pattern.metadata["peak_hour"]
                    rec = PolicyRecommendation(
                        recommendation_id=f"policy_time_{pattern.pattern_id}",
                        policy_type="maintenance_window",
                        current_value=current_policies.get("maintenance_windows", "any time"),
                        suggested_value=f"avoid {peak_hour:02d}:00-{peak_hour+1:02d}:00",
                        rationale=f"High incident frequency during hour {peak_hour} suggests avoiding automated changes",
                        expected_impact="Could reduce incident overlap and system stress",
                        risk_level="low",
                        affected_scenarios=[],
                        metadata={"peak_hour": peak_hour, "incident_frequency": pattern.frequency}
                    )
                    recommendations.append(rec)
            
            # System correlation patterns suggest blast radius adjustments
            elif pattern.pattern_type.value == "system" and "correlated_systems" in pattern.metadata:
                systems = pattern.metadata["correlated_systems"]
                rec = PolicyRecommendation(
                    recommendation_id=f"policy_blast_{pattern.pattern_id}",
                    policy_type="blast_radius_limit",
                    current_value=current_policies.get("max_blast_radius", 10),
                    suggested_value=1,  # Limit to single system when correlation exists
                    rationale=f"Systems {' and '.join(systems)} show failure correlation",
                    expected_impact="Could prevent cascading failures",
                    risk_level="medium",
                    affected_scenarios=[],
                    metadata={"correlated_systems": systems, "correlation_strength": pattern.frequency}
                )
                recommendations.append(rec)
        
        # Analyze assessments for policy implications
        critical_assessments = [a for a in assessments if a.overall_effectiveness == EffectivenessLevel.CRITICAL]
        poor_assessments = [a for a in assessments if a.overall_effectiveness == EffectivenessLevel.POOR]
        
        # If multiple scenarios are performing poorly, tighten approval requirements
        if len(critical_assessments) >= 2 or len(poor_assessments) >= 3:
            rec = PolicyRecommendation(
                recommendation_id=f"policy_approval_tighten_{datetime.now().strftime('%Y%m%d')}",
                policy_type="approval_requirement",
                current_value=current_policies.get("min_confidence_auto", 0.7),
                suggested_value=0.85,
                rationale=f"Multiple scenarios ({len(critical_assessments + poor_assessments)}) showing poor performance",
                expected_impact="Will require more manual oversight but reduce failed automations",
                risk_level="medium",
                affected_scenarios=[a.scenario_name for a in critical_assessments + poor_assessments],
                metadata={"critical_count": len(critical_assessments), "poor_count": len(poor_assessments)}
            )
            recommendations.append(rec)
        
        # If many scenarios are performing excellently, consider relaxing policies
        excellent_assessments = [a for a in assessments if a.overall_effectiveness == EffectivenessLevel.EXCELLENT]
        if len(excellent_assessments) >= len(assessments) * 0.7:  # 70% performing excellently
            rec = PolicyRecommendation(
                recommendation_id=f"policy_approval_relax_{datetime.now().strftime('%Y%m%d')}",
                policy_type="approval_requirement", 
                current_value=current_policies.get("min_confidence_auto", 0.7),
                suggested_value=0.6,
                rationale=f"Most scenarios ({len(excellent_assessments)}/{len(assessments)}) performing excellently",
                expected_impact="Will increase automation and reduce operator workload",
                risk_level="low",
                affected_scenarios=[a.scenario_name for a in excellent_assessments],
                metadata={"excellent_count": len(excellent_assessments), "total_count": len(assessments)}
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _suggest_new_scenarios(self,
                             root_cause_analyses: List[RootCauseAnalysis],
                             patterns: List[IncidentPattern]) -> List[Dict[str, Any]]:
        """Suggest new remediation scenarios based on analysis"""
        
        new_scenarios = []
        
        # Group root causes to identify gaps
        root_cause_frequency = {}
        for analysis in root_cause_analyses:
            cause = analysis.primary_cause.value
            if cause not in root_cause_frequency:
                root_cause_frequency[cause] = {
                    "count": 0,
                    "recommendations": [],
                    "evidence": []
                }
            root_cause_frequency[cause]["count"] += 1
            root_cause_frequency[cause]["recommendations"].extend(analysis.recommendations)
            root_cause_frequency[cause]["evidence"].extend(analysis.evidence)
        
        # Identify frequent root causes that might benefit from automation
        for root_cause, data in root_cause_frequency.items():
            if data["count"] >= 3:  # Frequent enough to consider automation
                
                # Check if there are common recommendations that could be automated
                recommendation_counts = {}
                for rec in data["recommendations"]:
                    recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
                
                common_recommendations = [rec for rec, count in recommendation_counts.items() if count >= 2]
                
                if common_recommendations:
                    scenario_suggestion = {
                        "scenario_name": f"Auto-remediation for {root_cause}",
                        "root_cause_addressed": root_cause,
                        "frequency_justification": data["count"],
                        "suggested_actions": common_recommendations[:3],  # Top 3
                        "evidence_summary": list(set(data["evidence"]))[:5],  # Top 5 unique evidence items
                        "estimated_success_rate": 0.6,  # Conservative estimate
                        "risk_level": "medium",
                        "implementation_priority": "high" if data["count"] >= 5 else "medium"
                    }
                    new_scenarios.append(scenario_suggestion)
        
        # Look for patterns that suggest new scenarios
        for pattern in patterns:
            if pattern.pattern_type.value == "system" and pattern.frequency >= 4:
                if "primary_system" in pattern.metadata:
                    system = pattern.metadata["primary_system"]
                    scenario_suggestion = {
                        "scenario_name": f"Proactive maintenance for {system}",
                        "system_focused": system,
                        "frequency_justification": pattern.frequency,
                        "suggested_actions": [
                            f"Schedule preventive maintenance for {system}",
                            f"Implement enhanced monitoring for {system}",
                            f"Create system health checks for {system}"
                        ],
                        "estimated_success_rate": 0.8,  # Preventive actions typically more successful
                        "risk_level": "low",
                        "implementation_priority": "medium"
                    }
                    new_scenarios.append(scenario_suggestion)
        
        return new_scenarios[:5]  # Limit to top 5 suggestions
    
    def _identify_effectiveness_improvements(self,
                                           assessments: List[RemediationAssessment],
                                           patterns: List[IncidentPattern]) -> List[str]:
        """Identify specific effectiveness improvement opportunities"""
        
        improvements = []
        
        # Analyze assessments for common issues
        slow_scenarios = [a for a in assessments if a.average_resolution_time_minutes > 60]
        if slow_scenarios:
            improvements.append(
                f"Optimize resolution procedures for {len(slow_scenarios)} slow scenarios "
                f"(avg {sum(a.average_resolution_time_minutes for a in slow_scenarios)/len(slow_scenarios):.1f} min)"
            )
        
        high_failure_scenarios = [a for a in assessments if a.successful_attempts / max(a.total_attempts, 1) < 0.7]
        if high_failure_scenarios:
            improvements.append(
                f"Improve success rates for {len(high_failure_scenarios)} underperforming scenarios"
            )
        
        # Look for recurrence patterns
        recurrence_issues = []
        for assessment in assessments:
            recurrence_metrics = [m for m in assessment.metrics if m.metric.value == "recurrence_rate"]
            if recurrence_metrics and recurrence_metrics[0].value > 0.15:
                recurrence_issues.append(assessment.scenario_name)
        
        if recurrence_issues:
            improvements.append(
                f"Address root causes for {len(recurrence_issues)} scenarios with high recurrence rates"
            )
        
        # Analyze patterns for improvement opportunities
        temporal_patterns = [p for p in patterns if p.pattern_type.value == "temporal"]
        if temporal_patterns:
            improvements.append(
                "Implement time-based preventive measures to reduce peak-hour incidents"
            )
        
        correlation_patterns = [p for p in patterns if p.pattern_type.value == "system" and "correlated_systems" in p.metadata]
        if correlation_patterns:
            improvements.append(
                "Implement dependency-aware remediation to prevent cascading failures"
            )
        
        return improvements[:6]  # Limit to top 6 improvements
    
    def _create_implementation_plan(self, cycle: LearningCycle) -> Dict[str, Any]:
        """Create an implementation plan for learning recommendations"""
        
        plan = {
            "immediate_actions": [],  # Can be implemented immediately
            "short_term_actions": [], # Require 1-2 weeks
            "long_term_actions": [],  # Require 1+ months
            "requires_approval": [],  # Need management approval
            "estimated_impact": {
                "automation_increase": 0,
                "risk_reduction": 0,
                "efficiency_gain": 0
            }
        }
        
        # Categorize confidence adjustments
        for adjustment in cycle.confidence_adjustments:
            if abs(adjustment.suggested_confidence - adjustment.current_confidence) <= 0.1:
                plan["immediate_actions"].append({
                    "type": "confidence_adjustment",
                    "action": f"Adjust confidence for {adjustment.scenario_id} from {adjustment.current_confidence:.2f} to {adjustment.suggested_confidence:.2f}",
                    "reason": adjustment.adjustment_reason
                })
            else:
                plan["requires_approval"].append({
                    "type": "confidence_adjustment",
                    "action": f"Major confidence change for {adjustment.scenario_id}",
                    "current": adjustment.current_confidence,
                    "suggested": adjustment.suggested_confidence,
                    "reason": adjustment.adjustment_reason
                })
        
        # Categorize policy recommendations
        for policy_rec in cycle.policy_recommendations:
            if policy_rec.risk_level == "low":
                plan["short_term_actions"].append({
                    "type": "policy_change",
                    "action": f"Update {policy_rec.policy_type}",
                    "details": f"Change from {policy_rec.current_value} to {policy_rec.suggested_value}",
                    "rationale": policy_rec.rationale
                })
            else:
                plan["requires_approval"].append({
                    "type": "policy_change",
                    "action": f"Policy change: {policy_rec.policy_type}",
                    "risk_level": policy_rec.risk_level,
                    "rationale": policy_rec.rationale
                })
        
        # New scenarios are typically long-term
        for scenario in cycle.new_scenarios_suggested:
            plan["long_term_actions"].append({
                "type": "new_scenario",
                "action": f"Develop {scenario['scenario_name']}",
                "priority": scenario.get("implementation_priority", "medium")
            })
        
        # Estimate impact
        confidence_increases = len([a for a in cycle.confidence_adjustments if a.suggested_confidence > a.current_confidence])
        confidence_decreases = len([a for a in cycle.confidence_adjustments if a.suggested_confidence < a.current_confidence])
        
        plan["estimated_impact"]["automation_increase"] = confidence_increases * 5  # 5% per adjustment
        plan["estimated_impact"]["risk_reduction"] = confidence_decreases * 3  # 3% per adjustment
        plan["estimated_impact"]["efficiency_gain"] = len(cycle.effectiveness_improvements) * 2  # 2% per improvement
        
        return plan
    
    def implement_adjustments(self, cycle: LearningCycle, 
                            approved_adjustments: List[str],
                            approved_policies: List[str]) -> Dict[str, Any]:
        """Implement approved learning recommendations"""
        
        implementation_results = {
            "implemented_confidence_adjustments": 0,
            "implemented_policy_changes": 0,
            "implementation_errors": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Implement confidence adjustments
        for adjustment in cycle.confidence_adjustments:
            if adjustment.adjustment_id in approved_adjustments:
                try:
                    # In a real implementation, this would update the confidence engine
                    adjustment.implementation_status = ImplementationStatus.IMPLEMENTED
                    self.implemented_adjustments[adjustment.adjustment_id] = adjustment
                    implementation_results["implemented_confidence_adjustments"] += 1
                except Exception as e:
                    implementation_results["implementation_errors"].append(
                        f"Failed to implement confidence adjustment {adjustment.adjustment_id}: {str(e)}"
                    )
        
        # Implement policy recommendations
        for policy_rec in cycle.policy_recommendations:
            if policy_rec.recommendation_id in approved_policies:
                try:
                    # In a real implementation, this would update the policy manager
                    policy_rec.implementation_status = ImplementationStatus.IMPLEMENTED
                    self.implemented_policies[policy_rec.recommendation_id] = policy_rec
                    implementation_results["implemented_policy_changes"] += 1
                except Exception as e:
                    implementation_results["implementation_errors"].append(
                        f"Failed to implement policy recommendation {policy_rec.recommendation_id}: {str(e)}"
                    )
        
        return implementation_results
    
    def get_learning_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """Get summary of learning activities over specified period"""
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_cycles = [cycle for cycle in self.learning_history if cycle.analysis_date >= cutoff_date]
        
        if not recent_cycles:
            return {"message": f"No learning cycles found in the last {days_back} days"}
        
        # Aggregate statistics
        total_incidents = sum(cycle.incidents_analyzed for cycle in recent_cycles)
        total_patterns = sum(cycle.patterns_identified for cycle in recent_cycles)
        total_adjustments = sum(len(cycle.confidence_adjustments) for cycle in recent_cycles)
        total_policies = sum(len(cycle.policy_recommendations) for cycle in recent_cycles)
        
        # Implementation statistics
        implemented_adjustments = len([adj for adj in self.implemented_adjustments.values() 
                                     if adj.created_date >= cutoff_date])
        implemented_policies = len([pol for pol in self.implemented_policies.values() 
                                  if pol.created_date >= cutoff_date])
        
        return {
            "period_days": days_back,
            "learning_cycles_run": len(recent_cycles),
            "total_incidents_analyzed": total_incidents,
            "total_patterns_identified": total_patterns,
            "confidence_adjustments_suggested": total_adjustments,
            "policy_recommendations_made": total_policies,
            "adjustments_implemented": implemented_adjustments,
            "policies_implemented": implemented_policies,
            "implementation_rate": {
                "adjustments": implemented_adjustments / max(total_adjustments, 1),
                "policies": implemented_policies / max(total_policies, 1)
            },
            "most_recent_cycle": recent_cycles[-1].cycle_id if recent_cycles else None,
            "effectiveness_trend": self._calculate_learning_effectiveness_trend(recent_cycles)
        }
    
    def _calculate_learning_effectiveness_trend(self, cycles: List[LearningCycle]) -> str:
        """Calculate whether learning effectiveness is improving over time"""
        
        if len(cycles) < 2:
            return "insufficient_data"
        
        # Look at the number of recommendations per incident over time
        recent_efficiency = []
        for cycle in cycles:
            if cycle.incidents_analyzed > 0:
                recommendations_per_incident = (len(cycle.confidence_adjustments) + 
                                              len(cycle.policy_recommendations)) / cycle.incidents_analyzed
                recent_efficiency.append(recommendations_per_incident)
        
        if len(recent_efficiency) < 2:
            return "stable"
        
        # Simple trend calculation
        first_half = recent_efficiency[:len(recent_efficiency)//2]
        second_half = recent_efficiency[len(recent_efficiency)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_second > avg_first * 1.1:  # 10% improvement
            return "improving"
        elif avg_second < avg_first * 0.9:  # 10% degradation
            return "degrading"
        else:
            return "stable"