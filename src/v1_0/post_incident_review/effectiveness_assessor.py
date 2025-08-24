"""
Effectiveness Assessor for Post-Incident Review

Evaluates the effectiveness of remediation actions and system responses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import statistics

from .incident_analyzer import IncidentTimeline, RootCauseAnalysis


class EffectivenessMetric(Enum):
    """Different metrics for measuring effectiveness"""
    RESOLUTION_TIME = "resolution_time"
    SUCCESS_RATE = "success_rate"
    RECURRENCE_RATE = "recurrence_rate" 
    MTTR = "mttr"  # Mean Time To Resolution
    MTBF = "mtbf"  # Mean Time Between Failures
    CUSTOMER_IMPACT = "customer_impact"
    ROLLBACK_RATE = "rollback_rate"


class EffectivenessLevel(Enum):
    """Levels of effectiveness assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class MetricResult:
    """Result of a single effectiveness metric"""
    metric: EffectivenessMetric
    value: float
    target: float
    effectiveness_level: EffectivenessLevel
    trend: str  # improving, stable, degrading
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationAssessment:
    """Assessment of remediation effectiveness"""
    remediation_id: str
    scenario_name: str
    assessment_date: datetime
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    average_resolution_time_minutes: float
    metrics: List[MetricResult] = field(default_factory=list)
    overall_effectiveness: EffectivenessLevel = EffectivenessLevel.ACCEPTABLE
    recommendations: List[str] = field(default_factory=list)
    confidence_adjustment_suggestion: Optional[float] = None
    trend_analysis: Dict[str, Any] = field(default_factory=dict)


class EffectivenessAssessor:
    """Assesses the effectiveness of remediation actions and system responses"""
    
    def __init__(self, target_mttr_minutes: float = 30, target_success_rate: float = 0.9):
        self.target_mttr_minutes = target_mttr_minutes
        self.target_success_rate = target_success_rate
        
        # Define effectiveness thresholds
        self.thresholds = {
            EffectivenessMetric.RESOLUTION_TIME: {
                EffectivenessLevel.EXCELLENT: 15,      # < 15 minutes
                EffectivenessLevel.GOOD: 30,           # < 30 minutes  
                EffectivenessLevel.ACCEPTABLE: 60,     # < 60 minutes
                EffectivenessLevel.POOR: 120,          # < 120 minutes
                # > 120 minutes is CRITICAL
            },
            EffectivenessMetric.SUCCESS_RATE: {
                EffectivenessLevel.EXCELLENT: 0.95,    # > 95%
                EffectivenessLevel.GOOD: 0.85,         # > 85%
                EffectivenessLevel.ACCEPTABLE: 0.70,   # > 70%
                EffectivenessLevel.POOR: 0.50,         # > 50%
                # < 50% is CRITICAL
            },
            EffectivenessMetric.RECURRENCE_RATE: {
                EffectivenessLevel.EXCELLENT: 0.05,    # < 5%
                EffectivenessLevel.GOOD: 0.10,         # < 10%
                EffectivenessLevel.ACCEPTABLE: 0.20,   # < 20%
                EffectivenessLevel.POOR: 0.35,         # < 35%
                # > 35% is CRITICAL
            },
            EffectivenessMetric.ROLLBACK_RATE: {
                EffectivenessLevel.EXCELLENT: 0.02,    # < 2%
                EffectivenessLevel.GOOD: 0.05,         # < 5%
                EffectivenessLevel.ACCEPTABLE: 0.10,   # < 10%
                EffectivenessLevel.POOR: 0.20,         # < 20%
                # > 20% is CRITICAL
            }
        }
    
    def assess_remediation_effectiveness(self, remediation_history: List[Dict[str, Any]], 
                                       scenario_id: str, 
                                       time_window_days: int = 30) -> RemediationAssessment:
        """Assess effectiveness of a specific remediation scenario"""
        
        # Filter history for the specific scenario and time window
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        relevant_history = [
            entry for entry in remediation_history
            if (entry.get("scenario_id") == scenario_id and 
                datetime.fromisoformat(entry["timestamp"]) >= cutoff_date)
        ]
        
        if not relevant_history:
            # No data available
            return RemediationAssessment(
                remediation_id=scenario_id,
                scenario_name=f"Scenario {scenario_id}",
                assessment_date=datetime.now(),
                total_attempts=0,
                successful_attempts=0,
                failed_attempts=0,
                average_resolution_time_minutes=0.0,
                overall_effectiveness=EffectivenessLevel.POOR,
                recommendations=["Insufficient data for assessment - need more execution history"]
            )
        
        # Calculate basic stats
        total_attempts = len(relevant_history)
        successful_attempts = sum(1 for entry in relevant_history if entry.get("success", False))
        failed_attempts = total_attempts - successful_attempts
        
        # Calculate resolution times
        resolution_times = [
            entry.get("resolution_time_minutes", 0) 
            for entry in relevant_history 
            if entry.get("resolution_time_minutes") is not None
        ]
        average_resolution_time = statistics.mean(resolution_times) if resolution_times else 0.0
        
        # Create assessment object
        assessment = RemediationAssessment(
            remediation_id=scenario_id,
            scenario_name=relevant_history[0].get("scenario_name", f"Scenario {scenario_id}"),
            assessment_date=datetime.now(),
            total_attempts=total_attempts,
            successful_attempts=successful_attempts,
            failed_attempts=failed_attempts,
            average_resolution_time_minutes=average_resolution_time
        )
        
        # Evaluate metrics
        metrics = []
        
        # Success Rate
        success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
        success_metric = self._evaluate_metric(
            EffectivenessMetric.SUCCESS_RATE, 
            success_rate, 
            self.target_success_rate,
            relevant_history
        )
        metrics.append(success_metric)
        
        # Resolution Time
        if resolution_times:
            resolution_metric = self._evaluate_metric(
                EffectivenessMetric.RESOLUTION_TIME,
                average_resolution_time,
                self.target_mttr_minutes,
                relevant_history
            )
            metrics.append(resolution_metric)
        
        # Recurrence Rate (how often the same issue comes back)
        recurrence_rate = self._calculate_recurrence_rate(relevant_history)
        if recurrence_rate is not None:
            recurrence_metric = self._evaluate_metric(
                EffectivenessMetric.RECURRENCE_RATE,
                recurrence_rate,
                0.1,  # Target < 10%
                relevant_history
            )
            metrics.append(recurrence_metric)
        
        # Rollback Rate
        rollback_rate = self._calculate_rollback_rate(relevant_history)
        if rollback_rate is not None:
            rollback_metric = self._evaluate_metric(
                EffectivenessMetric.ROLLBACK_RATE,
                rollback_rate,
                0.05,  # Target < 5%
                relevant_history
            )
            metrics.append(rollback_metric)
        
        assessment.metrics = metrics
        
        # Calculate overall effectiveness
        assessment.overall_effectiveness = self._calculate_overall_effectiveness(metrics)
        
        # Generate recommendations
        assessment.recommendations = self._generate_recommendations(assessment, metrics)
        
        # Suggest confidence adjustment
        assessment.confidence_adjustment_suggestion = self._suggest_confidence_adjustment(
            success_rate, average_resolution_time, rollback_rate or 0
        )
        
        # Trend analysis
        assessment.trend_analysis = self._analyze_trends(relevant_history)
        
        return assessment
    
    def _evaluate_metric(self, metric_type: EffectivenessMetric, value: float, 
                        target: float, history_data: List[Dict[str, Any]]) -> MetricResult:
        """Evaluate a single effectiveness metric"""
        
        # Determine effectiveness level
        effectiveness_level = self._get_effectiveness_level(metric_type, value)
        
        # Analyze trend
        trend = self._calculate_metric_trend(metric_type, history_data)
        
        # Additional details based on metric type
        details = {"sample_size": len(history_data)}
        
        if metric_type == EffectivenessMetric.RESOLUTION_TIME:
            resolution_times = [entry.get("resolution_time_minutes", 0) for entry in history_data]
            if resolution_times:
                details.update({
                    "min_resolution_time": min(resolution_times),
                    "max_resolution_time": max(resolution_times),
                    "median_resolution_time": statistics.median(resolution_times),
                    "std_dev": statistics.stdev(resolution_times) if len(resolution_times) > 1 else 0
                })
        
        elif metric_type == EffectivenessMetric.SUCCESS_RATE:
            details.update({
                "successful_count": sum(1 for entry in history_data if entry.get("success", False)),
                "failed_count": sum(1 for entry in history_data if not entry.get("success", False))
            })
        
        return MetricResult(
            metric=metric_type,
            value=value,
            target=target,
            effectiveness_level=effectiveness_level,
            trend=trend,
            details=details
        )
    
    def _get_effectiveness_level(self, metric_type: EffectivenessMetric, value: float) -> EffectivenessLevel:
        """Determine effectiveness level based on metric value and thresholds"""
        
        if metric_type not in self.thresholds:
            return EffectivenessLevel.ACCEPTABLE  # Default for unmapped metrics
        
        thresholds = self.thresholds[metric_type]
        
        # For success rate and similar metrics (higher is better)
        if metric_type in [EffectivenessMetric.SUCCESS_RATE]:
            if value >= thresholds[EffectivenessLevel.EXCELLENT]:
                return EffectivenessLevel.EXCELLENT
            elif value >= thresholds[EffectivenessLevel.GOOD]:
                return EffectivenessLevel.GOOD
            elif value >= thresholds[EffectivenessLevel.ACCEPTABLE]:
                return EffectivenessLevel.ACCEPTABLE
            elif value >= thresholds[EffectivenessLevel.POOR]:
                return EffectivenessLevel.POOR
            else:
                return EffectivenessLevel.CRITICAL
        
        # For resolution time and similar metrics (lower is better)
        else:
            if value <= thresholds[EffectivenessLevel.EXCELLENT]:
                return EffectivenessLevel.EXCELLENT
            elif value <= thresholds[EffectivenessLevel.GOOD]:
                return EffectivenessLevel.GOOD
            elif value <= thresholds[EffectivenessLevel.ACCEPTABLE]:
                return EffectivenessLevel.ACCEPTABLE
            elif value <= thresholds[EffectivenessLevel.POOR]:
                return EffectivenessLevel.POOR
            else:
                return EffectivenessLevel.CRITICAL
    
    def _calculate_recurrence_rate(self, history_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate how often the same issue recurs after successful remediation"""
        
        # Group by affected systems and incident types
        incident_groups = {}
        for entry in history_data:
            if not entry.get("success", False):
                continue  # Only consider successful remediations
            
            # Create key based on affected systems and incident type
            systems = tuple(sorted(entry.get("affected_systems", [])))
            incident_type = entry.get("incident_type", "unknown")
            key = (systems, incident_type)
            
            if key not in incident_groups:
                incident_groups[key] = []
            incident_groups[key].append(entry)
        
        if not incident_groups:
            return None
        
        # Calculate recurrence for each group
        recurrence_rates = []
        for group_entries in incident_groups.values():
            if len(group_entries) < 2:
                continue  # Need at least 2 incidents to measure recurrence
            
            # Sort by timestamp
            sorted_entries = sorted(group_entries, key=lambda x: x.get("timestamp", ""))
            
            # Look for incidents that occur within 7 days of each other (likely recurrences)
            recurrences = 0
            for i in range(1, len(sorted_entries)):
                prev_time = datetime.fromisoformat(sorted_entries[i-1]["timestamp"])
                curr_time = datetime.fromisoformat(sorted_entries[i]["timestamp"])
                
                if (curr_time - prev_time).days <= 7:
                    recurrences += 1
            
            if len(sorted_entries) > 1:
                group_recurrence_rate = recurrences / (len(sorted_entries) - 1)
                recurrence_rates.append(group_recurrence_rate)
        
        return statistics.mean(recurrence_rates) if recurrence_rates else 0.0
    
    def _calculate_rollback_rate(self, history_data: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate how often remediations need to be rolled back"""
        
        rollback_count = sum(1 for entry in history_data if entry.get("rolled_back", False))
        total_count = len(history_data)
        
        return rollback_count / total_count if total_count > 0 else None
    
    def _calculate_metric_trend(self, metric_type: EffectivenessMetric, 
                               history_data: List[Dict[str, Any]]) -> str:
        """Calculate trend for a specific metric over time"""
        
        if len(history_data) < 3:
            return "stable"  # Not enough data to determine trend
        
        # Sort by timestamp
        sorted_data = sorted(history_data, key=lambda x: x.get("timestamp", ""))
        
        # Split into two halves
        mid_point = len(sorted_data) // 2
        first_half = sorted_data[:mid_point]
        second_half = sorted_data[mid_point:]
        
        if metric_type == EffectivenessMetric.SUCCESS_RATE:
            first_success_rate = sum(1 for entry in first_half if entry.get("success", False)) / len(first_half)
            second_success_rate = sum(1 for entry in second_half if entry.get("success", False)) / len(second_half)
            
            if second_success_rate > first_success_rate + 0.05:  # 5% improvement
                return "improving"
            elif second_success_rate < first_success_rate - 0.05:  # 5% degradation
                return "degrading"
            else:
                return "stable"
        
        elif metric_type == EffectivenessMetric.RESOLUTION_TIME:
            first_avg_time = statistics.mean([entry.get("resolution_time_minutes", 0) for entry in first_half])
            second_avg_time = statistics.mean([entry.get("resolution_time_minutes", 0) for entry in second_half])
            
            if second_avg_time < first_avg_time - 5:  # 5 minute improvement
                return "improving"
            elif second_avg_time > first_avg_time + 5:  # 5 minute degradation
                return "degrading"
            else:
                return "stable"
        
        return "stable"  # Default
    
    def _calculate_overall_effectiveness(self, metrics: List[MetricResult]) -> EffectivenessLevel:
        """Calculate overall effectiveness based on individual metrics"""
        
        if not metrics:
            return EffectivenessLevel.POOR
        
        # Convert levels to numeric scores
        level_scores = {
            EffectivenessLevel.EXCELLENT: 5,
            EffectivenessLevel.GOOD: 4,
            EffectivenessLevel.ACCEPTABLE: 3,
            EffectivenessLevel.POOR: 2,
            EffectivenessLevel.CRITICAL: 1
        }
        
        # Calculate weighted average (success rate has higher weight)
        total_score = 0
        total_weight = 0
        
        for metric in metrics:
            weight = 2.0 if metric.metric == EffectivenessMetric.SUCCESS_RATE else 1.0
            score = level_scores[metric.effectiveness_level]
            total_score += score * weight
            total_weight += weight
        
        average_score = total_score / total_weight
        
        # Convert back to effectiveness level
        if average_score >= 4.5:
            return EffectivenessLevel.EXCELLENT
        elif average_score >= 3.5:
            return EffectivenessLevel.GOOD
        elif average_score >= 2.5:
            return EffectivenessLevel.ACCEPTABLE
        elif average_score >= 1.5:
            return EffectivenessLevel.POOR
        else:
            return EffectivenessLevel.CRITICAL
    
    def _generate_recommendations(self, assessment: RemediationAssessment, 
                                 metrics: List[MetricResult]) -> List[str]:
        """Generate recommendations based on assessment results"""
        
        recommendations = []
        
        # Check each metric for issues
        for metric in metrics:
            if metric.effectiveness_level in [EffectivenessLevel.POOR, EffectivenessLevel.CRITICAL]:
                
                if metric.metric == EffectivenessMetric.SUCCESS_RATE:
                    recommendations.append(
                        f"Low success rate ({metric.value:.1%}) - Review and improve remediation procedures"
                    )
                    if metric.value < 0.5:
                        recommendations.append("Consider requiring manual approval for this scenario")
                
                elif metric.metric == EffectivenessMetric.RESOLUTION_TIME:
                    recommendations.append(
                        f"High resolution time ({metric.value:.1f} min) - Optimize remediation steps"
                    )
                    recommendations.append("Consider parallel execution or pre-positioning resources")
                
                elif metric.metric == EffectivenessMetric.RECURRENCE_RATE:
                    recommendations.append(
                        f"High recurrence rate ({metric.value:.1%}) - Remediation may not address root cause"
                    )
                    recommendations.append("Implement more comprehensive remediation or prevention measures")
                
                elif metric.metric == EffectivenessMetric.ROLLBACK_RATE:
                    recommendations.append(
                        f"High rollback rate ({metric.value:.1%}) - Improve remediation safety checks"
                    )
                    recommendations.append("Add more validation steps before executing remediation")
            
            # Check trends
            if metric.trend == "degrading":
                recommendations.append(f"{metric.metric.value} is degrading - investigate underlying causes")
        
        # Overall recommendations based on effectiveness level
        if assessment.overall_effectiveness == EffectivenessLevel.EXCELLENT:
            recommendations.append("Excellent performance - consider increasing automation confidence")
        
        elif assessment.overall_effectiveness == EffectivenessLevel.CRITICAL:
            recommendations.append("Critical issues detected - consider disabling automatic remediation")
            recommendations.append("Require manual review for all incidents of this type")
        
        # Remove duplicates and limit count
        unique_recommendations = list(set(recommendations))
        return unique_recommendations[:6]  # Limit to top 6 recommendations
    
    def _suggest_confidence_adjustment(self, success_rate: float, avg_resolution_time: float, 
                                     rollback_rate: float) -> Optional[float]:
        """Suggest confidence score adjustment based on performance metrics"""
        
        # Base confidence adjustment on success rate
        if success_rate >= 0.95 and avg_resolution_time <= 30 and rollback_rate <= 0.02:
            return 0.1  # Increase confidence by 10%
        
        elif success_rate >= 0.85 and avg_resolution_time <= 60 and rollback_rate <= 0.05:
            return 0.05  # Increase confidence by 5%
        
        elif success_rate < 0.70 or rollback_rate > 0.15:
            return -0.15  # Decrease confidence by 15%
        
        elif success_rate < 0.80 or avg_resolution_time > 90 or rollback_rate > 0.10:
            return -0.05  # Decrease confidence by 5%
        
        return None  # No adjustment needed
    
    def _analyze_trends(self, history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in the historical data"""
        
        if len(history_data) < 5:
            return {"trend_analysis": "Insufficient data for trend analysis"}
        
        # Sort by timestamp
        sorted_data = sorted(history_data, key=lambda x: x.get("timestamp", ""))
        
        # Calculate weekly aggregations
        weekly_stats = {}
        for entry in sorted_data:
            timestamp = datetime.fromisoformat(entry["timestamp"])
            week_key = timestamp.strftime("%Y-W%U")  # Year-Week format
            
            if week_key not in weekly_stats:
                weekly_stats[week_key] = {"total": 0, "successful": 0, "resolution_times": []}
            
            weekly_stats[week_key]["total"] += 1
            if entry.get("success", False):
                weekly_stats[week_key]["successful"] += 1
            
            if entry.get("resolution_time_minutes"):
                weekly_stats[week_key]["resolution_times"].append(entry["resolution_time_minutes"])
        
        # Calculate trends
        weeks = sorted(weekly_stats.keys())
        if len(weeks) < 3:
            return {"trend_analysis": "Need at least 3 weeks of data for trend analysis"}
        
        # Success rate trend
        success_rates = []
        resolution_times = []
        
        for week in weeks:
            stats = weekly_stats[week]
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            success_rates.append(success_rate)
            
            if stats["resolution_times"]:
                avg_resolution = statistics.mean(stats["resolution_times"])
                resolution_times.append(avg_resolution)
        
        # Simple trend calculation (comparing first and last third)
        first_third = len(success_rates) // 3
        last_third = len(success_rates) - first_third
        
        early_success_rate = statistics.mean(success_rates[:first_third]) if first_third > 0 else 0
        recent_success_rate = statistics.mean(success_rates[last_third:]) if last_third < len(success_rates) else 0
        
        success_trend = "stable"
        if recent_success_rate > early_success_rate + 0.1:
            success_trend = "improving"
        elif recent_success_rate < early_success_rate - 0.1:
            success_trend = "degrading"
        
        result = {
            "data_points": len(history_data),
            "weeks_analyzed": len(weeks),
            "success_rate_trend": success_trend,
            "early_success_rate": early_success_rate,
            "recent_success_rate": recent_success_rate
        }
        
        if resolution_times:
            early_resolution_time = statistics.mean(resolution_times[:first_third]) if first_third > 0 else 0
            recent_resolution_time = statistics.mean(resolution_times[last_third:]) if last_third < len(resolution_times) else 0
            
            resolution_trend = "stable"
            if recent_resolution_time < early_resolution_time - 5:  # 5 minute improvement
                resolution_trend = "improving"
            elif recent_resolution_time > early_resolution_time + 5:  # 5 minute degradation
                resolution_trend = "degrading"
            
            result.update({
                "resolution_time_trend": resolution_trend,
                "early_avg_resolution_time": early_resolution_time,
                "recent_avg_resolution_time": recent_resolution_time
            })
        
        return result
    
    def generate_effectiveness_report(self, assessments: List[RemediationAssessment]) -> Dict[str, Any]:
        """Generate a comprehensive effectiveness report"""
        
        if not assessments:
            return {"error": "No assessments provided"}
        
        # Overall statistics
        total_attempts = sum(a.total_attempts for a in assessments)
        total_successful = sum(a.successful_attempts for a in assessments)
        overall_success_rate = total_successful / total_attempts if total_attempts > 0 else 0
        
        # Effectiveness distribution
        effectiveness_distribution = {level.value: 0 for level in EffectivenessLevel}
        for assessment in assessments:
            effectiveness_distribution[assessment.overall_effectiveness.value] += 1
        
        # Top performers and underperformers
        assessments_by_success = sorted(assessments, key=lambda x: x.successful_attempts / max(x.total_attempts, 1), reverse=True)
        top_performers = assessments_by_success[:3]
        underperformers = [a for a in assessments if a.overall_effectiveness in [EffectivenessLevel.POOR, EffectivenessLevel.CRITICAL]]
        
        # Common recommendations
        all_recommendations = []
        for assessment in assessments:
            all_recommendations.extend(assessment.recommendations)
        
        recommendation_frequency = {}
        for rec in all_recommendations:
            recommendation_frequency[rec] = recommendation_frequency.get(rec, 0) + 1
        
        common_recommendations = sorted(recommendation_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Generate report
        report = {
            "report_date": datetime.now().isoformat(),
            "total_scenarios_assessed": len(assessments),
            "total_remediation_attempts": total_attempts,
            "overall_success_rate": overall_success_rate,
            "effectiveness_distribution": effectiveness_distribution,
            "average_resolution_time_minutes": statistics.mean([a.average_resolution_time_minutes for a in assessments if a.average_resolution_time_minutes > 0]),
            "top_performers": [
                {
                    "scenario": a.scenario_name,
                    "success_rate": a.successful_attempts / max(a.total_attempts, 1),
                    "avg_resolution_time": a.average_resolution_time_minutes
                } for a in top_performers
            ],
            "underperformers": [
                {
                    "scenario": a.scenario_name,
                    "success_rate": a.successful_attempts / max(a.total_attempts, 1),
                    "effectiveness": a.overall_effectiveness.value,
                    "issues": a.recommendations[:2]  # Top 2 issues
                } for a in underperformers
            ],
            "common_recommendations": [{"recommendation": rec, "frequency": freq} for rec, freq in common_recommendations],
            "confidence_adjustments_suggested": len([a for a in assessments if a.confidence_adjustment_suggestion is not None])
        }
        
        return report