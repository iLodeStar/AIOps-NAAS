#!/usr/bin/env python3
"""
AIOps NAAS v0.3 - Guarded Auto-Remediation Service

This service implements guarded auto-remediation with approval gates:
- Approval-gated playbooks for failover, QoS shaping, config changes
- Dry-run and auto-rollback capabilities
- AWX/Nornir integration patterns for network automation
- OPA (Open Policy Agent) integration for policy enforcement
- Safe semi-automatic remediation workflows

The service:
1. Listens for link degradation alerts
2. Evaluates remediation policies with OPA
3. Executes approved playbooks with dry-run/rollback
4. Provides approval workflows for high-risk actions
"""

import asyncio
import logging
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import FastAPI, HTTPException
import uvicorn

import requests
from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemediationActionType(Enum):
    FAILOVER_BACKUP_SAT = "failover_backup_satellite"
    QOS_TRAFFIC_SHAPING = "qos_traffic_shaping"
    BANDWIDTH_REDUCTION = "bandwidth_reduction"
    ANTENNA_REALIGNMENT = "antenna_realignment"
    POWER_ADJUSTMENT = "power_adjustment"
    ERROR_CORRECTION = "error_correction_increase"
    CONFIG_ROLLBACK = "configuration_rollback"

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ExecutionStatus(Enum):
    QUEUED = "queued"
    DRY_RUN = "dry_run"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class RemediationAction:
    """Individual remediation action definition"""
    action_id: str
    action_type: RemediationActionType
    name: str
    description: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    requires_approval: bool
    supports_dry_run: bool
    supports_rollback: bool
    max_execution_time_minutes: int
    parameters: Dict[str, Any]
    preconditions: List[str]
    postconditions: List[str]

@dataclass
class ApprovalRequest:
    """Approval request for remediation action"""
    request_id: str
    timestamp: datetime
    action: RemediationAction
    trigger_alert_id: str
    requesting_system: str
    risk_assessment: Dict[str, Any]
    impact_analysis: Dict[str, Any]
    approval_status: ApprovalStatus
    approver: Optional[str]
    approval_timestamp: Optional[datetime]
    expiry_time: datetime
    justification: str

@dataclass
class RemediationExecution:
    """Remediation action execution tracking"""
    execution_id: str
    action_id: str
    timestamp: datetime
    status: ExecutionStatus
    dry_run: bool
    parameters: Dict[str, Any]
    results: Dict[str, Any]
    logs: List[str]
    rollback_data: Optional[Dict[str, Any]]
    execution_time_seconds: float
    error_message: Optional[str]

@dataclass
class PolicyDecision:
    """OPA policy decision"""
    allowed: bool
    reason: str
    policy_name: str
    requires_approval: bool
    risk_assessment: Dict[str, Any]
    constraints: Dict[str, Any]

class OPAPolicyEngine:
    """Open Policy Agent integration for policy enforcement"""
    
    def __init__(self, opa_url: str = "http://opa:8181"):
        self.opa_url = opa_url
        self.policies = self._initialize_policies()
    
    def _initialize_policies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize built-in policies (fallback when OPA unavailable)"""
        return {
            "satellite_failover": {
                "max_per_hour": 2,
                "requires_approval": True,
                "allowed_risk_levels": ["HIGH", "CRITICAL"],
                "business_hours_only": False
            },
            "qos_shaping": {
                "max_per_hour": 5,
                "requires_approval": False,
                "allowed_risk_levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "max_reduction_percent": 50
            },
            "bandwidth_reduction": {
                "max_per_hour": 10,
                "requires_approval": False,
                "allowed_risk_levels": ["MEDIUM", "HIGH", "CRITICAL"],
                "max_reduction_percent": 30
            },
            "antenna_operations": {
                "max_per_hour": 3,
                "requires_approval": True,
                "allowed_risk_levels": ["HIGH", "CRITICAL"],
                "weather_conditions_check": True
            }
        }
    
    async def evaluate_action(
        self, 
        action: RemediationAction,
        context: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate remediation action against policies"""
        try:
            # Try OPA first
            return await self._evaluate_with_opa(action, context)
        except Exception as e:
            logger.warning(f"OPA unavailable, using fallback policies: {e}")
            return await self._evaluate_with_fallback(action, context)
    
    async def _evaluate_with_opa(
        self, 
        action: RemediationAction, 
        context: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate action using OPA REST API"""
        policy_input = {
            "action": asdict(action),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{self.opa_url}/v1/data/remediation/allow",
            json={"input": policy_input},
            timeout=5
        )
        response.raise_for_status()
        
        result = response.json()
        decision_data = result.get("result", {})
        
        return PolicyDecision(
            allowed=decision_data.get("allowed", False),
            reason=decision_data.get("reason", "Policy evaluation failed"),
            policy_name=decision_data.get("policy", "unknown"),
            requires_approval=decision_data.get("requires_approval", True),
            risk_assessment=decision_data.get("risk_assessment", {}),
            constraints=decision_data.get("constraints", {})
        )
    
    async def _evaluate_with_fallback(
        self, 
        action: RemediationAction, 
        context: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate action using fallback policies"""
        action_key = action.action_type.value.split("_")[0]  # Get base action type
        policy = self.policies.get(action_key, self.policies.get("qos_shaping"))
        
        # Check risk level
        allowed = action.risk_level in policy.get("allowed_risk_levels", ["LOW"])
        
        # Check rate limiting (simplified)
        max_per_hour = policy.get("max_per_hour", 1)
        recent_actions = context.get("recent_actions_count", 0)
        if recent_actions >= max_per_hour:
            allowed = False
            reason = f"Rate limit exceeded: {recent_actions}/{max_per_hour} per hour"
        else:
            reason = "Policy evaluation passed" if allowed else f"Risk level {action.risk_level} not allowed"
        
        return PolicyDecision(
            allowed=allowed,
            reason=reason,
            policy_name=f"fallback_{action_key}",
            requires_approval=policy.get("requires_approval", True),
            risk_assessment={"risk_level": action.risk_level},
            constraints={"max_per_hour": max_per_hour}
        )

class PlaybookExecutor:
    """Executes remediation playbooks with dry-run and rollback support"""
    
    def __init__(self):
        self.executing_actions: Dict[str, RemediationExecution] = {}
        
        # Define available actions
        self.available_actions = {
            RemediationActionType.FAILOVER_BACKUP_SAT: self._execute_satellite_failover,
            RemediationActionType.QOS_TRAFFIC_SHAPING: self._execute_qos_shaping,
            RemediationActionType.BANDWIDTH_REDUCTION: self._execute_bandwidth_reduction,
            RemediationActionType.ANTENNA_REALIGNMENT: self._execute_antenna_realignment,
            RemediationActionType.POWER_ADJUSTMENT: self._execute_power_adjustment,
            RemediationActionType.ERROR_CORRECTION: self._execute_error_correction,
            RemediationActionType.CONFIG_ROLLBACK: self._execute_config_rollback
        }
    
    async def execute_action(
        self, 
        action: RemediationAction, 
        dry_run: bool = False,
        execution_id: Optional[str] = None
    ) -> RemediationExecution:
        """Execute a remediation action"""
        
        if not execution_id:
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        execution = RemediationExecution(
            execution_id=execution_id,
            action_id=action.action_id,
            timestamp=datetime.now(),
            status=ExecutionStatus.DRY_RUN if dry_run else ExecutionStatus.EXECUTING,
            dry_run=dry_run,
            parameters=action.parameters,
            results={},
            logs=[],
            rollback_data=None,
            execution_time_seconds=0.0,
            error_message=None
        )
        
        self.executing_actions[execution_id] = execution
        
        try:
            start_time = time.time()
            execution.logs.append(f"Starting {'dry-run' if dry_run else 'execution'} at {datetime.now()}")
            
            # Get executor function
            executor_func = self.available_actions.get(action.action_type)
            if not executor_func:
                raise ValueError(f"No executor available for action type: {action.action_type}")
            
            # Execute the action
            result = await executor_func(action, dry_run)
            
            execution.results = result
            execution.execution_time_seconds = time.time() - start_time
            execution.status = ExecutionStatus.COMPLETED
            execution.logs.append(f"{'Dry-run' if dry_run else 'Execution'} completed successfully")
            
        except Exception as e:
            execution.error_message = str(e)
            execution.execution_time_seconds = time.time() - start_time
            execution.status = ExecutionStatus.FAILED
            execution.logs.append(f"Execution failed: {e}")
            logger.error(f"Action execution failed: {e}")
        
        return execution
    
    async def rollback_action(self, execution_id: str) -> bool:
        """Rollback a previously executed action"""
        execution = self.executing_actions.get(execution_id)
        if not execution:
            logger.error(f"No execution found for rollback: {execution_id}")
            return False
        
        if not execution.rollback_data:
            logger.error(f"No rollback data available for execution: {execution_id}")
            return False
        
        try:
            execution.logs.append(f"Starting rollback at {datetime.now()}")
            
            # Simulate rollback execution
            await asyncio.sleep(2)  # Simulate rollback time
            
            execution.status = ExecutionStatus.ROLLED_BACK
            execution.logs.append("Rollback completed successfully")
            logger.info(f"Action {execution_id} rolled back successfully")
            return True
            
        except Exception as e:
            execution.logs.append(f"Rollback failed: {e}")
            logger.error(f"Rollback failed for {execution_id}: {e}")
            return False
    
    async def _execute_satellite_failover(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute satellite failover to backup"""
        backup_satellite = action.parameters.get("backup_satellite", "SAT-BACKUP-1")
        
        if dry_run:
            return {
                "action": "satellite_failover",
                "dry_run": True,
                "target_satellite": backup_satellite,
                "estimated_downtime_seconds": 30,
                "rollback_possible": True
            }
        
        # Simulate failover execution
        await asyncio.sleep(3)  # Simulate failover time
        
        return {
            "action": "satellite_failover",
            "executed": True,
            "previous_satellite": "SAT-PRIMARY-1",
            "current_satellite": backup_satellite,
            "failover_time_seconds": 3,
            "rollback_data": {"previous_config": "sat_primary_config"}
        }
    
    async def _execute_qos_shaping(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute QoS traffic shaping"""
        priority_classes = action.parameters.get("priority_classes", ["critical", "high"])
        bandwidth_limit = action.parameters.get("bandwidth_limit_mbps", 10)
        
        if dry_run:
            return {
                "action": "qos_traffic_shaping",
                "dry_run": True,
                "priority_classes": priority_classes,
                "bandwidth_limit_mbps": bandwidth_limit,
                "affected_flows": 25
            }
        
        # Simulate QoS configuration
        await asyncio.sleep(1)
        
        return {
            "action": "qos_traffic_shaping",
            "executed": True,
            "configured_classes": priority_classes,
            "bandwidth_limit_mbps": bandwidth_limit,
            "flows_shaped": 25,
            "rollback_data": {"previous_qos_config": "default_qos"}
        }
    
    async def _execute_bandwidth_reduction(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute bandwidth reduction"""
        reduction_percent = action.parameters.get("reduction_percent", 25)
        
        if dry_run:
            return {
                "action": "bandwidth_reduction", 
                "dry_run": True,
                "reduction_percent": reduction_percent,
                "estimated_savings_mbps": 5
            }
        
        await asyncio.sleep(1)
        
        return {
            "action": "bandwidth_reduction",
            "executed": True,
            "reduction_percent": reduction_percent,
            "previous_limit_mbps": 20,
            "new_limit_mbps": 15,
            "rollback_data": {"previous_bandwidth": 20}
        }
    
    async def _execute_antenna_realignment(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute antenna realignment"""
        target_elevation = action.parameters.get("elevation_deg", 45)
        target_azimuth = action.parameters.get("azimuth_deg", 180)
        
        if dry_run:
            return {
                "action": "antenna_realignment",
                "dry_run": True,
                "target_elevation": target_elevation,
                "target_azimuth": target_azimuth,
                "estimated_time_seconds": 60
            }
        
        await asyncio.sleep(4)  # Simulate antenna movement
        
        return {
            "action": "antenna_realignment",
            "executed": True,
            "previous_elevation": 40,
            "previous_azimuth": 175,
            "new_elevation": target_elevation,
            "new_azimuth": target_azimuth,
            "alignment_time_seconds": 4,
            "rollback_data": {"previous_position": {"elevation": 40, "azimuth": 175}}
        }
    
    async def _execute_power_adjustment(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute transmit power adjustment"""
        power_adjustment_db = action.parameters.get("power_adjustment_db", 2)
        
        if dry_run:
            return {
                "action": "power_adjustment",
                "dry_run": True,
                "adjustment_db": power_adjustment_db
            }
        
        await asyncio.sleep(1)
        
        return {
            "action": "power_adjustment", 
            "executed": True,
            "adjustment_db": power_adjustment_db,
            "previous_power_dbm": 20,
            "new_power_dbm": 22,
            "rollback_data": {"previous_power": 20}
        }
    
    async def _execute_error_correction(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute error correction increase"""
        fec_level = action.parameters.get("fec_level", "strong")
        
        if dry_run:
            return {
                "action": "error_correction_increase",
                "dry_run": True,
                "fec_level": fec_level
            }
        
        await asyncio.sleep(1)
        
        return {
            "action": "error_correction_increase",
            "executed": True,
            "previous_fec": "normal",
            "new_fec": fec_level,
            "rollback_data": {"previous_fec": "normal"}
        }
    
    async def _execute_config_rollback(self, action: RemediationAction, dry_run: bool) -> Dict[str, Any]:
        """Execute configuration rollback"""
        config_version = action.parameters.get("config_version", "previous")
        
        if dry_run:
            return {
                "action": "config_rollback",
                "dry_run": True,
                "target_version": config_version
            }
        
        await asyncio.sleep(2)
        
        return {
            "action": "config_rollback",
            "executed": True,
            "rolled_back_to": config_version,
            "rollback_data": None  # Config rollbacks don't need further rollback
        }

class RemediationService:
    """Main guarded auto-remediation service"""
    
    def __init__(self):
        self.nats_client: Optional[NATS] = None
        self.policy_engine = OPAPolicyEngine()
        self.executor = PlaybookExecutor()
        self.app = FastAPI(title="Remediation Service", version="0.3.0")
        
        self.health_status = {
            "service_running": False,
            "nats_connected": False,
            "opa_available": False,
            "pending_approvals": 0,
            "actions_executed": 0,
            "actions_rolled_back": 0
        }
        
        # In-memory stores (use database in production)
        self.approval_requests: Dict[str, ApprovalRequest] = {}
        self.executions: Dict[str, RemediationExecution] = {}
        
        self.setup_routes()
        self._initialize_actions()
    
    def _initialize_actions(self):
        """Initialize available remediation actions"""
        self.remediation_actions = {
            "satellite_failover": RemediationAction(
                action_id="satellite_failover",
                action_type=RemediationActionType.FAILOVER_BACKUP_SAT,
                name="Satellite Failover",
                description="Failover to backup satellite link",
                risk_level="HIGH",
                requires_approval=True,
                supports_dry_run=True,
                supports_rollback=True,
                max_execution_time_minutes=5,
                parameters={"backup_satellite": "SAT-BACKUP-1"},
                preconditions=["backup_satellite_available", "primary_satellite_degraded"],
                postconditions=["primary_link_disabled", "backup_link_active"]
            ),
            "qos_shaping": RemediationAction(
                action_id="qos_shaping",
                action_type=RemediationActionType.QOS_TRAFFIC_SHAPING,
                name="QoS Traffic Shaping",
                description="Apply traffic shaping to prioritize critical traffic",
                risk_level="MEDIUM",
                requires_approval=False,
                supports_dry_run=True,
                supports_rollback=True,
                max_execution_time_minutes=2,
                parameters={"priority_classes": ["critical", "high"], "bandwidth_limit_mbps": 10},
                preconditions=["qos_capable_equipment"],
                postconditions=["traffic_shaped", "critical_traffic_prioritized"]
            ),
            "bandwidth_reduction": RemediationAction(
                action_id="bandwidth_reduction",
                action_type=RemediationActionType.BANDWIDTH_REDUCTION,
                name="Bandwidth Reduction",
                description="Reduce bandwidth allocation to maintain service",
                risk_level="MEDIUM",
                requires_approval=False,
                supports_dry_run=True,
                supports_rollback=True,
                max_execution_time_minutes=1,
                parameters={"reduction_percent": 25},
                preconditions=["link_degraded"],
                postconditions=["bandwidth_reduced", "service_maintained"]
            )
        }
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            return self.health_status
        
        @self.app.get("/actions")
        async def list_actions():
            """List available remediation actions"""
            return {k: asdict(v) for k, v in self.remediation_actions.items()}
        
        @self.app.post("/execute/{action_id}")
        async def execute_action(action_id: str, dry_run: bool = True):
            """Execute a remediation action"""
            if action_id not in self.remediation_actions:
                raise HTTPException(status_code=404, detail="Action not found")
            
            action = self.remediation_actions[action_id]
            execution = await self.executor.execute_action(action, dry_run)
            self.executions[execution.execution_id] = execution
            
            return asdict(execution)
        
        @self.app.get("/executions/{execution_id}")
        async def get_execution(execution_id: str):
            """Get execution details"""
            execution = self.executions.get(execution_id)
            if not execution:
                raise HTTPException(status_code=404, detail="Execution not found")
            return asdict(execution)
        
        @self.app.post("/rollback/{execution_id}")
        async def rollback_execution(execution_id: str):
            """Rollback an execution"""
            success = await self.executor.rollback_action(execution_id)
            return {"rollback_success": success, "execution_id": execution_id}
        
        @self.app.get("/approvals")
        async def list_pending_approvals():
            """List pending approval requests"""
            pending = [
                asdict(req) for req in self.approval_requests.values()
                if req.approval_status == ApprovalStatus.PENDING
            ]
            return {"pending_approvals": pending, "count": len(pending)}
        
        @self.app.post("/approve/{request_id}")
        async def approve_request(request_id: str, approver: str):
            """Approve a remediation request"""
            if request_id not in self.approval_requests:
                raise HTTPException(status_code=404, detail="Approval request not found")
            
            request = self.approval_requests[request_id]
            request.approval_status = ApprovalStatus.APPROVED
            request.approver = approver
            request.approval_timestamp = datetime.now()
            
            # Execute the approved action
            execution = await self.executor.execute_action(request.action, dry_run=False)
            self.executions[execution.execution_id] = execution
            self.health_status["actions_executed"] += 1
            
            return {
                "approval_status": "approved",
                "execution_id": execution.execution_id,
                "execution": asdict(execution)
            }
    
    async def connect_nats(self):
        """Connect to NATS message bus"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect("nats://nats:4222")
            logger.info("Connected to NATS")
            self.health_status["nats_connected"] = True
            
            # Subscribe to link health alerts
            await self.nats_client.subscribe("link.health.alert", cb=self.handle_link_alert)
            logger.info("Subscribed to link health alerts")
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
    
    async def handle_link_alert(self, msg):
        """Handle incoming link health alert"""
        try:
            alert_data = json.loads(msg.data.decode())
            logger.info(f"Received link alert: {alert_data.get('severity')} - Lead time: {alert_data.get('lead_time_minutes')}min")
            
            # Determine appropriate remediation action
            action_id = self.select_remediation_action(alert_data)
            if not action_id:
                logger.info("No suitable remediation action for alert")
                return
            
            action = self.remediation_actions[action_id]
            
            # Evaluate policy
            context = {
                "alert": alert_data,
                "timestamp": datetime.now().isoformat(),
                "recent_actions_count": len([
                    e for e in self.executions.values()
                    if (datetime.now() - e.timestamp).total_seconds() < 3600
                ])
            }
            
            decision = await self.policy_engine.evaluate_action(action, context)
            
            if not decision.allowed:
                logger.warning(f"Action {action_id} not allowed by policy: {decision.reason}")
                return
            
            if decision.requires_approval:
                # Create approval request
                await self.create_approval_request(action, alert_data, decision)
            else:
                # Execute immediately
                execution = await self.executor.execute_action(action, dry_run=False)
                self.executions[execution.execution_id] = execution
                self.health_status["actions_executed"] += 1
                logger.info(f"Auto-executed action {action_id}: {execution.execution_id}")
            
        except Exception as e:
            logger.error(f"Error handling link alert: {e}")
    
    def select_remediation_action(self, alert_data: Dict[str, Any]) -> Optional[str]:
        """Select appropriate remediation action based on alert"""
        severity = alert_data.get("severity", "WARNING")
        risk_factors = alert_data.get("risk_factors", [])
        
        # Simple action selection logic
        if "Low SNR" in risk_factors or "High BER" in risk_factors:
            if severity == "CRITICAL":
                return "satellite_failover"
            else:
                return "qos_shaping"
        
        if "Heavy precipitation" in risk_factors:
            return "bandwidth_reduction"
        
        if severity in ["HIGH", "CRITICAL"]:
            return "qos_shaping"
        
        return "bandwidth_reduction"  # Default conservative action
    
    async def create_approval_request(
        self, 
        action: RemediationAction, 
        alert_data: Dict[str, Any],
        policy_decision: PolicyDecision
    ):
        """Create approval request for high-risk actions"""
        request_id = f"approval_{uuid.uuid4().hex[:8]}"
        
        approval_request = ApprovalRequest(
            request_id=request_id,
            timestamp=datetime.now(),
            action=action,
            trigger_alert_id=alert_data.get("alert_id", "unknown"),
            requesting_system="remediation_service",
            risk_assessment=policy_decision.risk_assessment,
            impact_analysis={"estimated_downtime": "30 seconds", "affected_systems": ["satellite_link"]},
            approval_status=ApprovalStatus.PENDING,
            approver=None,
            approval_timestamp=None,
            expiry_time=datetime.now() + timedelta(minutes=30),  # 30 min approval window
            justification=f"Automatic remediation for {alert_data.get('severity')} link alert"
        )
        
        self.approval_requests[request_id] = approval_request
        self.health_status["pending_approvals"] += 1
        
        # Publish approval request to NATS
        try:
            if self.nats_client and not self.nats_client.is_closed:
                approval_json = json.dumps(asdict(approval_request), default=str)
                await self.nats_client.publish("remediation.approval.request", approval_json.encode())
                logger.info(f"Published approval request: {request_id}")
        except Exception as e:
            logger.error(f"Error publishing approval request: {e}")
    
    async def cleanup_expired_approvals(self):
        """Clean up expired approval requests"""
        now = datetime.now()
        expired = []
        
        for request_id, request in self.approval_requests.items():
            if (request.approval_status == ApprovalStatus.PENDING and 
                now > request.expiry_time):
                request.approval_status = ApprovalStatus.EXPIRED
                expired.append(request_id)
        
        if expired:
            logger.info(f"Expired {len(expired)} approval requests")
            self.health_status["pending_approvals"] -= len(expired)
    
    async def health_check_loop(self):
        """Periodic health check and cleanup loop"""
        while True:
            try:
                self.health_status["service_running"] = True
                
                # Check OPA availability
                try:
                    response = requests.get(f"{self.policy_engine.opa_url}/health", timeout=2)
                    self.health_status["opa_available"] = response.status_code == 200
                except:
                    self.health_status["opa_available"] = False
                
                # Cleanup expired approvals
                await self.cleanup_expired_approvals()
                
                await asyncio.sleep(30)  # Health check every 30 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def run_background_tasks(self):
        """Run background tasks"""
        await self.connect_nats()
        
        tasks = [
            asyncio.create_task(self.health_check_loop())
        ]
        
        await asyncio.gather(*tasks)

# Global service instance
service = RemediationService()

# FastAPI app instance
app = service.app

async def startup():
    """Application startup"""
    logger.info("Starting Remediation Service v0.3")
    # Start background tasks
    asyncio.create_task(service.run_background_tasks())

async def shutdown():
    """Application shutdown"""
    logger.info("Shutting down Remediation Service")
    if service.nats_client:
        await service.nats_client.close()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

if __name__ == "__main__":
    uvicorn.run(
        "remediation_service:app",
        host="0.0.0.0",
        port=8083,
        reload=False
    )