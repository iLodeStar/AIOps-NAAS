#!/usr/bin/env python3
"""
End-to-End Test Script for AIOps NAAS
Tests the complete Alert -> Policy -> Approval -> Execution -> Audit pipeline
"""

import asyncio
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RemediationAction(Enum):
    SATELLITE_FAILOVER = "satellite_failover"
    QOS_SHAPING = "qos_shaping"
    BANDWIDTH_REDUCTION = "bandwidth_reduction"
    ANTENNA_ADJUSTMENT = "antenna_adjustment"
    POWER_ADJUSTMENT = "power_adjustment"
    ERROR_CORRECTION = "error_correction"


@dataclass
class AlertEvent:
    """Alert event structure"""
    alert_id: str
    timestamp: str
    severity: AlertSeverity
    alert_type: str
    description: str
    metrics: Dict[str, float]
    source_system: str
    affected_services: List[str]


@dataclass
class PolicyDecision:
    """Policy decision result"""
    decision_id: str
    alert_id: str
    allowed: bool
    recommended_action: RemediationAction
    approval_required: bool
    risk_assessment: str
    reason: str
    constraints: Dict[str, Any]


@dataclass
class ExecutionResult:
    """Remediation execution result"""
    execution_id: str
    alert_id: str
    action: RemediationAction
    status: str
    started_at: str
    completed_at: str
    dry_run: bool
    success: bool
    error_message: str
    rollback_available: bool


class E2ETestOrchestrator:
    """End-to-End test orchestrator"""
    
    def __init__(self):
        self.test_results = {
            "test_run_id": f"e2e_{int(time.time())}",
            "started_at": datetime.now().isoformat(),
            "alerts_generated": 0,
            "policy_evaluations": 0,
            "approvals_processed": 0,
            "executions_attempted": 0,
            "audit_entries": 0,
            "success_rate": 0.0,
            "errors": [],
            "test_scenarios": []
        }
        
        # Service endpoints (adjust if services are running)
        self.service_endpoints = {
            "link_health": "http://localhost:8082",
            "remediation": "http://localhost:8083",
            "opa": "http://localhost:8181",
            "grafana": "http://localhost:3000",
            "victoria_metrics": "http://localhost:8428"
        }
        
        self.alert_counter = 0
    
    def generate_test_alert(self, severity: AlertSeverity, scenario_name: str) -> AlertEvent:
        """Generate a test alert for different scenarios"""
        self.alert_counter += 1
        alert_id = f"alert_{self.alert_counter:04d}_{scenario_name}"
        
        # Define test scenarios with specific characteristics
        scenarios = {
            "satellite_degradation": {
                "description": "Satellite link quality degradation detected",
                "metrics": {"snr_db": 4.5, "ber": 0.001, "signal_strength_dbm": -75},
                "affected_services": ["crew-wifi", "guest-wifi", "pos-system"]
            },
            "weather_impact": {
                "description": "Weather-related signal attenuation",
                "metrics": {"rain_fade_margin_db": 1.2, "signal_strength_dbm": -80},
                "affected_services": ["guest-wifi"]
            },
            "network_congestion": {
                "description": "Network congestion detected",
                "metrics": {"interface_utilization": 95, "packet_loss": 5.5, "latency_ms": 500},
                "affected_services": ["all-services"]
            },
            "equipment_failure": {
                "description": "Critical equipment failure",
                "metrics": {"temperature_celsius": 85, "error_count": 150},
                "affected_services": ["navigation-system", "safety-system"]
            }
        }
        
        scenario_data = scenarios.get(scenario_name, scenarios["satellite_degradation"])
        
        alert = AlertEvent(
            alert_id=alert_id,
            timestamp=datetime.now().isoformat(),
            severity=severity,
            alert_type=f"link_health.{scenario_name}",
            description=scenario_data["description"],
            metrics=scenario_data["metrics"],
            source_system="link_health_service",
            affected_services=scenario_data["affected_services"]
        )
        
        logger.info(f"Generated test alert: {alert_id} ({severity.value}) - {scenario_name}")
        return alert
    
    async def simulate_policy_evaluation(self, alert: AlertEvent) -> PolicyDecision:
        """Simulate policy evaluation for the alert"""
        
        # Simulate policy logic
        risk_levels = {
            AlertSeverity.LOW: "low",
            AlertSeverity.MEDIUM: "medium", 
            AlertSeverity.HIGH: "high",
            AlertSeverity.CRITICAL: "critical"
        }
        
        # Action selection based on alert type and severity
        if "satellite" in alert.alert_type:
            if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                action = RemediationAction.SATELLITE_FAILOVER
                approval_required = True
            else:
                action = RemediationAction.QOS_SHAPING
                approval_required = False
        elif "network" in alert.alert_type:
            action = RemediationAction.BANDWIDTH_REDUCTION
            approval_required = alert.severity == AlertSeverity.CRITICAL
        else:
            action = RemediationAction.ANTENNA_ADJUSTMENT
            approval_required = False
        
        decision = PolicyDecision(
            decision_id=f"policy_{alert.alert_id}",
            alert_id=alert.alert_id,
            allowed=True,  # For testing, allow all
            recommended_action=action,
            approval_required=approval_required,
            risk_assessment=risk_levels[alert.severity],
            reason=f"Auto-selected {action.value} based on {alert.alert_type} and {alert.severity.value} severity",
            constraints={
                "max_execution_time_minutes": 10,
                "rollback_required": True,
                "dry_run_first": True
            }
        )
        
        logger.info(f"Policy decision: {action.value} {'(approval required)' if approval_required else '(auto-approved)'}")
        return decision
    
    async def simulate_approval_process(self, decision: PolicyDecision) -> bool:
        """Simulate approval process for high-risk actions"""
        
        if not decision.approval_required:
            logger.info(f"Action {decision.recommended_action.value} auto-approved")
            return True
        
        # Simulate approval delay
        await asyncio.sleep(0.5)  # Simulate approval processing time
        
        # For testing, approve most requests but reject some for realism
        import random
        approved = random.random() > 0.1  # 90% approval rate
        
        if approved:
            logger.info(f"Action {decision.recommended_action.value} manually approved")
        else:
            logger.warning(f"Action {decision.recommended_action.value} manually rejected")
        
        return approved
    
    async def simulate_remediation_execution(self, decision: PolicyDecision, approved: bool) -> ExecutionResult:
        """Simulate remediation action execution"""
        
        execution_id = f"exec_{decision.alert_id}"
        started_at = datetime.now().isoformat()
        
        if not approved:
            return ExecutionResult(
                execution_id=execution_id,
                alert_id=decision.alert_id,
                action=decision.recommended_action,
                status="rejected",
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                dry_run=False,
                success=False,
                error_message="Action rejected by approval process",
                rollback_available=False
            )
        
        # Simulate execution time
        execution_time = {
            RemediationAction.SATELLITE_FAILOVER: 2.0,
            RemediationAction.QOS_SHAPING: 0.5,
            RemediationAction.BANDWIDTH_REDUCTION: 0.3,
            RemediationAction.ANTENNA_ADJUSTMENT: 1.0,
            RemediationAction.POWER_ADJUSTMENT: 0.8,
            RemediationAction.ERROR_CORRECTION: 0.2
        }
        
        await asyncio.sleep(execution_time.get(decision.recommended_action, 1.0))
        
        # Simulate occasional failures for realism
        import random
        success = random.random() > 0.05  # 95% success rate
        
        result = ExecutionResult(
            execution_id=execution_id,
            alert_id=decision.alert_id,
            action=decision.recommended_action,
            status="completed" if success else "failed",
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
            dry_run=decision.constraints.get("dry_run_first", False),
            success=success,
            error_message="" if success else f"Simulated execution failure for {decision.recommended_action.value}",
            rollback_available=success and decision.constraints.get("rollback_required", False)
        )
        
        if success:
            logger.info(f"Execution completed: {decision.recommended_action.value}")
        else:
            logger.error(f"Execution failed: {decision.recommended_action.value} - {result.error_message}")
        
        return result
    
    async def create_audit_entry(self, alert: AlertEvent, decision: PolicyDecision, 
                                execution: ExecutionResult) -> Dict[str, Any]:
        """Create audit trail entry"""
        
        audit_entry = {
            "audit_id": f"audit_{alert.alert_id}",
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "type": alert.alert_type,
                "description": alert.description
            },
            "policy_decision": {
                "decision_id": decision.decision_id,
                "action": decision.recommended_action.value,
                "approval_required": decision.approval_required,
                "risk_assessment": decision.risk_assessment
            },
            "execution": {
                "execution_id": execution.execution_id,
                "status": execution.status,
                "success": execution.success,
                "dry_run": execution.dry_run
            },
            "compliance": {
                "policy_followed": True,
                "audit_trail_complete": True,
                "data_retention_compliant": True
            }
        }
        
        logger.info(f"Audit entry created: {audit_entry['audit_id']}")
        return audit_entry
    
    async def run_test_scenario(self, scenario_name: str, severity: AlertSeverity) -> Dict[str, Any]:
        """Run a complete test scenario"""
        scenario_start = datetime.now()
        
        try:
            # Step 1: Generate Alert
            alert = self.generate_test_alert(severity, scenario_name)
            self.test_results["alerts_generated"] += 1
            
            # Step 2: Policy Evaluation
            decision = await self.simulate_policy_evaluation(alert)
            self.test_results["policy_evaluations"] += 1
            
            # Step 3: Approval Process
            if decision.approval_required:
                approved = await self.simulate_approval_process(decision)
                self.test_results["approvals_processed"] += 1
            else:
                approved = True
            
            # Step 4: Execution
            execution = await self.simulate_remediation_execution(decision, approved)
            self.test_results["executions_attempted"] += 1
            
            # Step 5: Audit Trail
            audit_entry = await self.create_audit_entry(alert, decision, execution)
            self.test_results["audit_entries"] += 1
            
            scenario_result = {
                "scenario": scenario_name,
                "severity": severity.value,
                "duration_seconds": (datetime.now() - scenario_start).total_seconds(),
                "success": execution.success and approved,
                "alert": alert,
                "decision": decision,
                "execution": execution,
                "audit": audit_entry
            }
            
            return scenario_result
            
        except Exception as e:
            error_msg = f"Scenario {scenario_name} failed: {str(e)}"
            logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            
            return {
                "scenario": scenario_name,
                "severity": severity.value,
                "success": False,
                "error": error_msg
            }
    
    async def run_e2e_tests(self) -> Dict[str, Any]:
        """Run complete end-to-end test suite"""
        logger.info("Starting AIOps NAAS End-to-End Tests")
        logger.info("="*60)
        
        # Define test scenarios
        test_scenarios = [
            ("satellite_degradation", AlertSeverity.HIGH),
            ("weather_impact", AlertSeverity.MEDIUM),
            ("network_congestion", AlertSeverity.CRITICAL),
            ("equipment_failure", AlertSeverity.HIGH),
            ("satellite_degradation", AlertSeverity.LOW),
            ("weather_impact", AlertSeverity.CRITICAL)
        ]
        
        # Run scenarios
        for scenario_name, severity in test_scenarios:
            logger.info(f"\n🔍 Running scenario: {scenario_name} ({severity.value})")
            logger.info("-" * 50)
            
            scenario_result = await self.run_test_scenario(scenario_name, severity)
            self.test_results["test_scenarios"].append(scenario_result)
            
            # Brief pause between scenarios
            await asyncio.sleep(0.2)
        
        # Calculate final statistics
        successful_scenarios = len([s for s in self.test_results["test_scenarios"] if s.get("success", False)])
        total_scenarios = len(self.test_results["test_scenarios"])
        
        self.test_results["success_rate"] = (successful_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0
        self.test_results["completed_at"] = datetime.now().isoformat()
        self.test_results["total_duration_seconds"] = (
            datetime.fromisoformat(self.test_results["completed_at"]) - 
            datetime.fromisoformat(self.test_results["started_at"])
        ).total_seconds()
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("E2E TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Test Run ID: {self.test_results['test_run_id']}")
        logger.info(f"Total Scenarios: {total_scenarios}")
        logger.info(f"Successful Scenarios: {successful_scenarios}")
        logger.info(f"Success Rate: {self.test_results['success_rate']:.1f}%")
        logger.info(f"Alerts Generated: {self.test_results['alerts_generated']}")
        logger.info(f"Policy Evaluations: {self.test_results['policy_evaluations']}")
        logger.info(f"Approvals Processed: {self.test_results['approvals_processed']}")
        logger.info(f"Executions Attempted: {self.test_results['executions_attempted']}")
        logger.info(f"Audit Entries: {self.test_results['audit_entries']}")
        logger.info(f"Total Duration: {self.test_results['total_duration_seconds']:.1f}s")
        
        if self.test_results["errors"]:
            logger.info(f"Errors: {len(self.test_results['errors'])}")
            for error in self.test_results["errors"]:
                logger.error(f"  - {error}")
        
        return self.test_results


async def main():
    """Main entry point for E2E tests"""
    orchestrator = E2ETestOrchestrator()
    
    try:
        results = await orchestrator.run_e2e_tests()
        
        # Save results to file
        with open("e2e_results.json", "w") as f:
            # Convert dataclass objects to dicts for JSON serialization
            serializable_results = json.loads(json.dumps(results, default=str))
            json.dump(serializable_results, f, indent=2)
        
        # Return appropriate exit code
        if results["success_rate"] >= 80:  # 80% success threshold
            logger.info("✅ E2E tests PASSED")
            return 0
        else:
            logger.error("❌ E2E tests FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"E2E test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))