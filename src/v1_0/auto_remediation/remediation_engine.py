"""
Remediation Engine for Auto-Remediation

Orchestrates confidence-scored auto-remediation with policy enforcement.
Integrates with AWX/Nornir for execution and provides rollback capabilities.
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .confidence_engine import ConfidenceEngine, ConfidenceLevel, IncidentContext
from .policy_manager import PolicyManager

logger = logging.getLogger(__name__)


class RemediationStatus(Enum):
    """Status of a remediation execution"""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


@dataclass
class RemediationExecution:
    """Represents a remediation execution"""
    execution_id: str
    incident_id: str
    scenario_id: str
    confidence_score: float
    confidence_level: ConfidenceLevel
    status: RemediationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_details: Optional[Dict[str, Any]] = None
    rollback_available: bool = True
    rollback_executed: bool = False
    approval_required: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class RemediationEngine:
    """
    Main engine for orchestrating auto-remediation
    """
    
    def __init__(
        self,
        confidence_engine: ConfidenceEngine,
        policy_manager: PolicyManager,
        awx_endpoint: str = "http://localhost:8080",
        dry_run: bool = False
    ):
        self.confidence_engine = confidence_engine
        self.policy_manager = policy_manager
        self.awx_endpoint = awx_endpoint
        self.dry_run = dry_run
        
        self.active_executions: Dict[str, RemediationExecution] = {}
        self.execution_history: List[RemediationExecution] = []
        
        # Metrics tracking
        self.mttr_samples: List[float] = []
        self.success_rate_window: List[bool] = []
    
    async def evaluate_incident(
        self,
        incident_context: IncidentContext,
        potential_scenarios: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate an incident and determine auto-remediation approach
        
        Returns:
            Dict with evaluation results and recommended actions
        """
        
        # Calculate confidence scores for potential scenarios
        confidence_results = self.confidence_engine.calculate_confidence(
            incident_context, potential_scenarios
        )
        
        if not confidence_results:
            return {
                'decision': 'manual_required',
                'reason': 'No applicable remediation scenarios found',
                'recommendations': []
            }
        
        # Find the best scenario
        best_scenario_id = max(
            confidence_results.keys(),
            key=lambda k: confidence_results[k][0]
        )
        
        best_confidence_score, best_confidence_level = confidence_results[best_scenario_id]
        
        # Evaluate policy constraints
        policy_result = self.policy_manager.evaluate_policy(
            scenario_id=best_scenario_id,
            confidence_level=best_confidence_level,
            confidence_score=best_confidence_score,
            affected_systems=incident_context.affected_systems
        )
        
        if not policy_result['allowed']:
            return {
                'decision': 'blocked_by_policy',
                'reason': policy_result['reason'],
                'best_scenario': best_scenario_id,
                'confidence_score': best_confidence_score,
                'confidence_level': best_confidence_level.value
            }
        
        # Determine execution approach
        if policy_result['approval_required']:
            decision = 'approval_required'
            next_action = 'request_approval'
        else:
            decision = 'auto_execute'
            next_action = 'execute_remediation'
        
        return {
            'decision': decision,
            'next_action': next_action,
            'scenario_id': best_scenario_id,
            'confidence_score': best_confidence_score,
            'confidence_level': best_confidence_level.value,
            'policy_result': policy_result,
            'all_scenarios': {
                k: {'confidence': v[0], 'level': v[1].value} 
                for k, v in confidence_results.items()
            }
        }
    
    async def execute_remediation(
        self,
        incident_context: IncidentContext,
        scenario_id: str,
        confidence_score: float,
        confidence_level: ConfidenceLevel,
        approved_by: Optional[str] = None
    ) -> RemediationExecution:
        """
        Execute a remediation scenario
        """
        
        execution_id = f"rem_{incident_context.incident_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        execution = RemediationExecution(
            execution_id=execution_id,
            incident_id=incident_context.incident_id,
            scenario_id=scenario_id,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            status=RemediationStatus.PENDING,
            started_at=datetime.now(),
            approved_by=approved_by,
            approved_at=datetime.now() if approved_by else None
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            # Update status to executing
            execution.status = RemediationStatus.EXECUTING
            logger.info(f"Starting remediation execution {execution_id}")
            
            if self.dry_run:
                # Simulate execution for testing
                await asyncio.sleep(2)
                execution.status = RemediationStatus.SUCCESS
                execution.execution_details = {'dry_run': True, 'simulated_success': True}
            else:
                # Execute via AWX/Nornir
                execution.execution_details = await self._execute_via_awx(
                    scenario_id, incident_context
                )
                execution.status = RemediationStatus.SUCCESS
            
            execution.completed_at = datetime.now()
            
            # Update confidence engine with success
            self.confidence_engine.update_scenario_success(scenario_id, True)
            
            # Track metrics
            execution_time = (execution.completed_at - execution.started_at).total_seconds() / 60
            self.mttr_samples.append(execution_time)
            self.success_rate_window.append(True)
            
            logger.info(f"Remediation execution {execution_id} completed successfully")
            
        except Exception as e:
            execution.status = RemediationStatus.FAILED
            execution.completed_at = datetime.now()
            execution.execution_details = {'error': str(e)}
            
            # Update confidence engine with failure
            self.confidence_engine.update_scenario_success(scenario_id, False)
            
            # Track failure in metrics
            self.success_rate_window.append(False)
            
            logger.error(f"Remediation execution {execution_id} failed: {e}")
        
        finally:
            # Move to history
            self.execution_history.append(execution)
            del self.active_executions[execution_id]
            
            # Maintain window size for metrics
            if len(self.success_rate_window) > 100:
                self.success_rate_window = self.success_rate_window[-100:]
            if len(self.mttr_samples) > 100:
                self.mttr_samples = self.mttr_samples[-100:]
        
        return execution
    
    async def _execute_via_awx(
        self, 
        scenario_id: str, 
        incident_context: IncidentContext
    ) -> Dict[str, Any]:
        """Execute remediation via AWX/Ansible"""
        
        # This would integrate with AWX API in a real implementation
        # For now, simulate the execution
        
        execution_details = {
            'awx_job_template': f"remediation_{scenario_id}",
            'target_systems': incident_context.affected_systems,
            'incident_context': asdict(incident_context),
            'pre_check_passed': True,
            'execution_log': [
                f"Starting remediation for {scenario_id}",
                f"Target systems: {incident_context.affected_systems}",
                "Pre-checks completed successfully",
                "Executing remediation playbook",
                "Remediation completed successfully",
                "Post-checks passed"
            ]
        }
        
        # Simulate execution time
        await asyncio.sleep(1)
        
        return execution_details
    
    async def rollback_remediation(self, execution_id: str, reason: str) -> bool:
        """
        Rollback a completed remediation
        """
        
        execution = None
        
        # Find execution in active or history
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
        else:
            for hist_exec in self.execution_history:
                if hist_exec.execution_id == execution_id:
                    execution = hist_exec
                    break
        
        if not execution:
            logger.error(f"Execution {execution_id} not found for rollback")
            return False
        
        if not execution.rollback_available:
            logger.error(f"Rollback not available for execution {execution_id}")
            return False
        
        if execution.rollback_executed:
            logger.warning(f"Rollback already executed for {execution_id}")
            return True
        
        try:
            # Execute rollback
            logger.info(f"Starting rollback for execution {execution_id}")
            
            if self.dry_run:
                # Simulate rollback
                await asyncio.sleep(1)
            else:
                await self._execute_rollback_via_awx(execution, reason)
            
            execution.rollback_executed = True
            execution.status = RemediationStatus.ROLLED_BACK
            
            if not execution.execution_details:
                execution.execution_details = {}
            execution.execution_details['rollback_reason'] = reason
            execution.execution_details['rollback_completed_at'] = datetime.now().isoformat()
            
            logger.info(f"Rollback completed for execution {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for execution {execution_id}: {e}")
            return False
    
    async def _execute_rollback_via_awx(
        self, 
        execution: RemediationExecution, 
        reason: str
    ):
        """Execute rollback via AWX/Ansible"""
        
        # This would integrate with AWX rollback playbooks
        # For now, just log the rollback action
        logger.info(
            f"Executing rollback for scenario {execution.scenario_id} "
            f"on systems {execution.execution_details.get('target_systems', [])}"
        )
        
        # Simulate rollback execution
        await asyncio.sleep(1)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current auto-remediation metrics"""
        
        # Calculate MTTR (Mean Time To Recovery)
        avg_mttr = sum(self.mttr_samples) / len(self.mttr_samples) if self.mttr_samples else 0
        
        # Calculate success rate
        success_rate = (
            sum(self.success_rate_window) / len(self.success_rate_window) 
            if self.success_rate_window else 0
        )
        
        # Count recent executions
        recent_executions = len([
            exec for exec in self.execution_history[-50:] 
            if exec.started_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ])
        
        return {
            'mttr_minutes': round(avg_mttr, 2),
            'success_rate_percent': round(success_rate * 100, 1),
            'total_executions': len(self.execution_history),
            'active_executions': len(self.active_executions),
            'executions_today': recent_executions,
            'scenarios_with_coverage': len(set(
                exec.scenario_id for exec in self.execution_history
            ))
        }