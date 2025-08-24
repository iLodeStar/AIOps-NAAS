"""
Confidence Engine for Auto-Remediation

Provides confidence scoring for known remediation scenarios based on:
- Historical success rates
- Incident similarity matching
- Environmental context
- Risk assessment
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for auto-remediation decisions"""
    LOW = "low"          # 0-40%: Manual intervention required
    MEDIUM = "medium"    # 40-75%: Approval required
    HIGH = "high"        # 75-90%: Auto-execute with monitoring
    CRITICAL = "critical"  # 90-100%: Auto-execute immediately


@dataclass
class RemediationScenario:
    """Represents a known remediation scenario"""
    scenario_id: str
    name: str
    description: str
    success_rate: float
    execution_count: int
    last_execution: Optional[str] = None
    risk_level: str = "medium"
    prerequisites: List[str] = None
    rollback_available: bool = True


@dataclass
class IncidentContext:
    """Context information for an incident"""
    incident_id: str
    incident_type: str
    severity: str
    affected_systems: List[str]
    symptoms: Dict[str, str]
    environmental_factors: Dict[str, str]
    ship_status: Dict[str, str]


class ConfidenceEngine:
    """
    Engine for calculating confidence scores for auto-remediation decisions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.scenarios: Dict[str, RemediationScenario] = {}
        self.confidence_thresholds = {
            ConfidenceLevel.LOW: 0.4,
            ConfidenceLevel.MEDIUM: 0.75,
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.CRITICAL: 1.0
        }
        
        if config_path:
            self.load_scenarios(config_path)
    
    def load_scenarios(self, config_path: str):
        """Load remediation scenarios from configuration"""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                
            for scenario_data in data.get('scenarios', []):
                scenario = RemediationScenario(**scenario_data)
                self.scenarios[scenario.scenario_id] = scenario
                
            logger.info(f"Loaded {len(self.scenarios)} remediation scenarios")
            
        except Exception as e:
            logger.error(f"Failed to load scenarios from {config_path}: {e}")
    
    def calculate_confidence(
        self, 
        incident_context: IncidentContext,
        potential_scenarios: List[str]
    ) -> Dict[str, Tuple[float, ConfidenceLevel]]:
        """
        Calculate confidence scores for potential remediation scenarios
        
        Args:
            incident_context: Current incident information
            potential_scenarios: List of scenario IDs to evaluate
            
        Returns:
            Dict mapping scenario_id to (confidence_score, confidence_level)
        """
        results = {}
        
        for scenario_id in potential_scenarios:
            if scenario_id not in self.scenarios:
                logger.warning(f"Unknown scenario: {scenario_id}")
                continue
                
            scenario = self.scenarios[scenario_id]
            confidence_score = self._compute_scenario_confidence(
                incident_context, scenario
            )
            confidence_level = self._get_confidence_level(confidence_score)
            
            results[scenario_id] = (confidence_score, confidence_level)
            
        return results
    
    def _compute_scenario_confidence(
        self,
        incident_context: IncidentContext,
        scenario: RemediationScenario
    ) -> float:
        """Compute confidence score for a specific scenario"""
        
        # Base confidence from historical success rate
        base_confidence = scenario.success_rate
        
        # Adjust for execution frequency (more executions = higher confidence)
        frequency_factor = min(1.0, scenario.execution_count / 100.0)
        
        # Adjust for incident severity match
        severity_factor = self._calculate_severity_match(
            incident_context.severity, scenario.risk_level
        )
        
        # Adjust for system compatibility
        system_factor = self._calculate_system_compatibility(
            incident_context.affected_systems, scenario
        )
        
        # Adjust for environmental factors
        env_factor = self._calculate_environmental_compatibility(
            incident_context.environmental_factors, scenario
        )
        
        # Rollback availability boosts confidence
        rollback_factor = 1.1 if scenario.rollback_available else 0.9
        
        # Combine factors
        final_confidence = (
            base_confidence * 
            (0.3 + 0.7 * frequency_factor) * 
            severity_factor * 
            system_factor * 
            env_factor * 
            rollback_factor
        )
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, final_confidence))
    
    def _calculate_severity_match(self, incident_severity: str, scenario_risk: str) -> float:
        """Calculate how well incident severity matches scenario risk level"""
        severity_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        
        incident_level = severity_map.get(incident_severity.lower(), 2)
        scenario_level = severity_map.get(scenario_risk.lower(), 2)
        
        # Perfect match = 1.0, one level off = 0.8, etc.
        diff = abs(incident_level - scenario_level)
        return max(0.5, 1.0 - (diff * 0.2))
    
    def _calculate_system_compatibility(
        self, 
        affected_systems: List[str], 
        scenario: RemediationScenario
    ) -> float:
        """Calculate system compatibility factor"""
        # For now, return a neutral factor
        # In a real implementation, this would check system prerequisites
        return 1.0
    
    def _calculate_environmental_compatibility(
        self, 
        env_factors: Dict[str, str], 
        scenario: RemediationScenario
    ) -> float:
        """Calculate environmental compatibility factor"""
        # Basic implementation - check for critical environmental constraints
        ship_connectivity = env_factors.get("connectivity", "unknown")
        weather_conditions = env_factors.get("weather", "unknown")
        
        # Reduce confidence for poor connectivity or bad weather
        if ship_connectivity == "offline":
            return 0.8
        elif weather_conditions in ["storm", "severe"]:
            return 0.9
        
        return 1.0
    
    def _get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Convert numerical confidence score to confidence level"""
        if confidence_score >= self.confidence_thresholds[ConfidenceLevel.CRITICAL]:
            return ConfidenceLevel.CRITICAL
        elif confidence_score >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif confidence_score >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def update_scenario_success(self, scenario_id: str, success: bool):
        """Update scenario success rate based on execution results"""
        if scenario_id not in self.scenarios:
            logger.warning(f"Cannot update unknown scenario: {scenario_id}")
            return
            
        scenario = self.scenarios[scenario_id]
        
        # Update success rate using exponential moving average
        alpha = 0.1  # Learning rate
        new_success_rate = (
            (1 - alpha) * scenario.success_rate + 
            alpha * (1.0 if success else 0.0)
        )
        
        scenario.success_rate = new_success_rate
        scenario.execution_count += 1
        
        logger.info(
            f"Updated scenario {scenario_id}: "
            f"success_rate={new_success_rate:.3f}, "
            f"executions={scenario.execution_count}"
        )