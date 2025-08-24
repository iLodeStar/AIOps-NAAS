"""
Policy Manager for Auto-Remediation

Manages gradual expansion of policy coverage for auto-remediation scenarios.
Integrates with Open Policy Agent (OPA) for policy enforcement.
"""

import logging
import json
import requests
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .confidence_engine import ConfidenceLevel, RemediationScenario

logger = logging.getLogger(__name__)


@dataclass
class PolicyRule:
    """Represents a policy rule for auto-remediation"""
    rule_id: str
    scenario_id: str
    min_confidence: float
    max_blast_radius: int
    allowed_systems: List[str]
    forbidden_systems: List[str]
    time_windows: List[str]  # List of allowed time windows
    approval_required: bool
    enabled: bool = True
    created_at: str = None
    last_modified: str = None


@dataclass
class PolicyCoverageMetrics:
    """Metrics for policy coverage expansion"""
    total_scenarios: int
    covered_scenarios: int
    coverage_percentage: float
    new_scenarios_last_week: int
    auto_approved_last_week: int
    manual_interventions_last_week: int


class PolicyManager:
    """
    Manages auto-remediation policies with gradual coverage expansion
    """
    
    def __init__(self, opa_endpoint: str = "http://localhost:8181", config_path: Optional[str] = None):
        self.opa_endpoint = opa_endpoint
        self.policies: Dict[str, PolicyRule] = {}
        self.policy_history: List[Dict] = []
        self.coverage_metrics = PolicyCoverageMetrics(0, 0, 0.0, 0, 0, 0)
        
        if config_path:
            self.load_policies(config_path)
    
    def load_policies(self, config_path: str):
        """Load policies from configuration file"""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            for policy_data in data.get('policies', []):
                policy = PolicyRule(**policy_data)
                self.policies[policy.rule_id] = policy
                
            logger.info(f"Loaded {len(self.policies)} policy rules")
            
        except Exception as e:
            logger.error(f"Failed to load policies from {config_path}: {e}")
    
    def evaluate_policy(
        self,
        scenario_id: str,
        confidence_level: ConfidenceLevel,
        confidence_score: float,
        affected_systems: List[str],
        current_time: datetime = None
    ) -> Dict[str, bool]:
        """
        Evaluate if a remediation scenario meets policy requirements
        
        Returns:
            Dict with evaluation results:
            - 'allowed': bool - Whether remediation is allowed
            - 'approval_required': bool - Whether manual approval is needed  
            - 'reason': str - Reason for decision
        """
        
        if current_time is None:
            current_time = datetime.now()
            
        # Find applicable policies for this scenario
        applicable_policies = [
            policy for policy in self.policies.values()
            if policy.scenario_id == scenario_id and policy.enabled
        ]
        
        if not applicable_policies:
            # No policy exists - conservative approach
            return {
                'allowed': False,
                'approval_required': True,
                'reason': f'No policy defined for scenario {scenario_id}'
            }
        
        # Evaluate all applicable policies
        for policy in applicable_policies:
            result = self._evaluate_single_policy(
                policy, confidence_score, affected_systems, current_time
            )
            
            if not result['allowed']:
                return result
                
        # If we get here, at least one policy allows the action
        best_policy = max(applicable_policies, key=lambda p: p.min_confidence)
        
        return {
            'allowed': True,
            'approval_required': best_policy.approval_required,
            'reason': f'Approved by policy {best_policy.rule_id}'
        }
    
    def _evaluate_single_policy(
        self,
        policy: PolicyRule,
        confidence_score: float,
        affected_systems: List[str],
        current_time: datetime
    ) -> Dict[str, bool]:
        """Evaluate a single policy rule"""
        
        # Check confidence threshold
        if confidence_score < policy.min_confidence:
            return {
                'allowed': False,
                'approval_required': True,
                'reason': f'Confidence {confidence_score:.3f} below threshold {policy.min_confidence}'
            }
        
        # Check blast radius
        if len(affected_systems) > policy.max_blast_radius:
            return {
                'allowed': False,
                'approval_required': True,
                'reason': f'Blast radius {len(affected_systems)} exceeds limit {policy.max_blast_radius}'
            }
        
        # Check system restrictions
        forbidden_systems_affected = set(affected_systems) & set(policy.forbidden_systems)
        if forbidden_systems_affected:
            return {
                'allowed': False,
                'approval_required': True,
                'reason': f'Affects forbidden systems: {list(forbidden_systems_affected)}'
            }
        
        if policy.allowed_systems:
            allowed_systems_set = set(policy.allowed_systems)
            if not set(affected_systems).issubset(allowed_systems_set):
                return {
                    'allowed': False,
                    'approval_required': True,
                    'reason': 'Affects systems outside allowed list'
                }
        
        # Check time windows
        if not self._is_in_allowed_time_window(current_time, policy.time_windows):
            return {
                'allowed': False,
                'approval_required': True,
                'reason': 'Outside allowed time window'
            }
        
        # Query OPA for additional policy checks
        if not self._check_opa_policy(policy, confidence_score, affected_systems):
            return {
                'allowed': False,
                'approval_required': True,
                'reason': 'Blocked by OPA policy'
            }
        
        return {
            'allowed': True,
            'approval_required': policy.approval_required,
            'reason': f'Approved by policy {policy.rule_id}'
        }
    
    def _is_in_allowed_time_window(
        self, 
        current_time: datetime, 
        time_windows: List[str]
    ) -> bool:
        """Check if current time falls within allowed time windows"""
        
        if not time_windows:
            return True  # No restrictions
            
        current_hour = current_time.hour
        current_day = current_time.strftime('%A').lower()
        
        for window in time_windows:
            if self._time_matches_window(current_hour, current_day, window):
                return True
                
        return False
    
    def _time_matches_window(self, hour: int, day: str, window: str) -> bool:
        """Check if time matches a specific window pattern"""
        # Simple implementation - supports formats like:
        # "02:00-06:00" (daily)
        # "monday:02:00-06:00" (specific day)
        # "weekdays:02:00-06:00" (Monday-Friday)
        
        parts = window.lower().split(':')
        
        if len(parts) == 2:  # Daily window: "02:00-06:00"
            time_range = parts[1] if parts[1] else parts[0]
            start_hour, end_hour = self._parse_hour_range(time_range)
            return start_hour <= hour <= end_hour
            
        elif len(parts) == 3:  # Day-specific: "monday:02:00-06:00"
            day_spec = parts[0]
            time_range = f"{parts[1]}:{parts[2]}"
            
            if day_spec == "weekdays" and day not in ['saturday', 'sunday']:
                start_hour, end_hour = self._parse_hour_range(time_range)
                return start_hour <= hour <= end_hour
            elif day_spec == day:
                start_hour, end_hour = self._parse_hour_range(time_range)
                return start_hour <= hour <= end_hour
                
        return False
    
    def _parse_hour_range(self, time_range: str) -> tuple:
        """Parse hour range like '02:00-06:00' into (start_hour, end_hour)"""
        try:
            start_str, end_str = time_range.split('-')
            start_hour = int(start_str.split(':')[0])
            end_hour = int(end_str.split(':')[0])
            return start_hour, end_hour
        except:
            return 0, 23  # Default to full day if parsing fails
    
    def _check_opa_policy(
        self, 
        policy: PolicyRule, 
        confidence_score: float, 
        affected_systems: List[str]
    ) -> bool:
        """Check additional constraints with Open Policy Agent"""
        
        try:
            opa_data = {
                "input": {
                    "scenario_id": policy.scenario_id,
                    "confidence_score": confidence_score,
                    "affected_systems": affected_systems,
                    "policy_id": policy.rule_id
                }
            }
            
            response = requests.post(
                f"{self.opa_endpoint}/v1/data/aiops/remediation/allow",
                json=opa_data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("result", False)
            else:
                logger.warning(f"OPA query failed with status {response.status_code}")
                return False  # Conservative approach
                
        except Exception as e:
            logger.error(f"Failed to query OPA: {e}")
            return False  # Conservative approach
    
    def expand_coverage(
        self, 
        new_scenarios: List[RemediationScenario],
        success_metrics: Dict[str, float]
    ):
        """
        Gradually expand policy coverage based on new scenarios and success metrics
        """
        
        for scenario in new_scenarios:
            if self._should_add_scenario_policy(scenario, success_metrics):
                new_policy = self._create_initial_policy(scenario)
                self.policies[new_policy.rule_id] = new_policy
                
                # Record policy addition
                self.policy_history.append({
                    'action': 'policy_added',
                    'policy_id': new_policy.rule_id,
                    'scenario_id': scenario.scenario_id,
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'Automatic coverage expansion'
                })
                
                logger.info(f"Added new policy {new_policy.rule_id} for scenario {scenario.scenario_id}")
    
    def _should_add_scenario_policy(
        self,
        scenario: RemediationScenario,
        success_metrics: Dict[str, float]
    ) -> bool:
        """Determine if a new scenario should get an auto-remediation policy"""
        
        # Check if policy already exists
        existing_policies = [
            p for p in self.policies.values() 
            if p.scenario_id == scenario.scenario_id
        ]
        
        if existing_policies:
            return False
            
        # Criteria for adding new policy:
        # 1. High success rate (>80%)
        # 2. Sufficient execution history (>10 executions)
        # 3. Low risk level
        
        if (scenario.success_rate > 0.8 and 
            scenario.execution_count > 10 and
            scenario.risk_level in ['low', 'medium']):
            return True
            
        return False
    
    def _create_initial_policy(self, scenario: RemediationScenario) -> PolicyRule:
        """Create initial conservative policy for a new scenario"""
        
        return PolicyRule(
            rule_id=f"auto_{scenario.scenario_id}_{datetime.now().strftime('%Y%m%d')}",
            scenario_id=scenario.scenario_id,
            min_confidence=0.85,  # Conservative threshold initially
            max_blast_radius=3,   # Small blast radius initially
            allowed_systems=[],   # Will be learned over time
            forbidden_systems=["critical_navigation", "safety_systems"],
            time_windows=["02:00-06:00"],  # Maintenance window only
            approval_required=True,  # Require approval initially
            enabled=True,
            created_at=datetime.now().isoformat(),
            last_modified=datetime.now().isoformat()
        )
    
    def get_coverage_metrics(self, scenarios: List[RemediationScenario]) -> PolicyCoverageMetrics:
        """Calculate current policy coverage metrics"""
        
        total_scenarios = len(scenarios)
        covered_scenarios = len(set(p.scenario_id for p in self.policies.values() if p.enabled))
        coverage_percentage = (covered_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        
        # Calculate recent activity metrics
        one_week_ago = datetime.now() - timedelta(days=7)
        
        new_scenarios_last_week = sum(
            1 for entry in self.policy_history
            if (entry['action'] == 'policy_added' and 
                datetime.fromisoformat(entry['timestamp']) >= one_week_ago)
        )
        
        self.coverage_metrics = PolicyCoverageMetrics(
            total_scenarios=total_scenarios,
            covered_scenarios=covered_scenarios,
            coverage_percentage=coverage_percentage,
            new_scenarios_last_week=new_scenarios_last_week,
            auto_approved_last_week=0,  # Would be populated from execution logs
            manual_interventions_last_week=0  # Would be populated from execution logs
        )
        
        return self.coverage_metrics