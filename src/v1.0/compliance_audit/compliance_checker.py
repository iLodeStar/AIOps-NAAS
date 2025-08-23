"""
Automated Compliance Checker

Validates system changes and operations against compliance policies
including maritime regulations, safety requirements, and operational procedures.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    """Compliance check status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    SOLAS = "solas"              # Safety of Life at Sea
    MARPOL = "marpol"            # Marine Pollution Prevention
    ISM = "ism"                  # International Safety Management
    ISPS = "isps"                # International Ship and Port Security
    MLC = "mlc"                  # Maritime Labour Convention
    GDPR = "gdpr"                # General Data Protection Regulation
    INTERNAL = "internal"        # Internal company policies


@dataclass
class ComplianceRule:
    """Represents a compliance rule"""
    rule_id: str
    name: str
    framework: ComplianceFramework
    description: str
    severity: str  # critical, high, medium, low
    automated_check: bool
    check_function: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    enabled: bool = True


@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    violation_id: str
    rule_id: str
    rule_name: str
    framework: ComplianceFramework
    severity: str
    status: ComplianceStatus
    detected_at: datetime
    description: str
    affected_systems: List[str]
    evidence: Dict[str, Any]
    remediation_required: bool
    remediation_suggestions: List[str]


@dataclass
class ComplianceAssessment:
    """Results of a compliance assessment"""
    assessment_id: str
    target_system: str
    target_operation: str
    assessed_at: datetime
    overall_status: ComplianceStatus
    frameworks_checked: List[ComplianceFramework]
    violations: List[ComplianceViolation]
    warnings: List[ComplianceViolation]
    summary: Dict[str, Any]


class ComplianceChecker:
    """
    Automated compliance checking engine
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.rules: Dict[str, ComplianceRule] = {}
        self.violation_history: List[ComplianceViolation] = []
        self.assessment_history: List[ComplianceAssessment] = []
        
        if config_path:
            self.load_rules(config_path)
        else:
            self._load_default_rules()
    
    def load_rules(self, config_path: str):
        """Load compliance rules from configuration file"""
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            for rule_data in data.get('compliance_rules', []):
                rule = ComplianceRule(**rule_data)
                self.rules[rule.rule_id] = rule
            
            logger.info(f"Loaded {len(self.rules)} compliance rules")
            
        except Exception as e:
            logger.error(f"Failed to load compliance rules: {e}")
    
    def _load_default_rules(self):
        """Load default compliance rules"""
        default_rules = [
            # Safety-critical system rules (SOLAS)
            ComplianceRule(
                rule_id="solas_001",
                name="Navigation System Availability",
                framework=ComplianceFramework.SOLAS,
                description="Navigation systems must maintain 99.9% availability",
                severity="critical",
                automated_check=True,
                check_function="check_navigation_availability",
                parameters={"min_availability": 0.999}
            ),
            
            # Communication system rules (SOLAS)
            ComplianceRule(
                rule_id="solas_002", 
                name="Emergency Communication Backup",
                framework=ComplianceFramework.SOLAS,
                description="Emergency communication systems must have redundancy",
                severity="critical",
                automated_check=True,
                check_function="check_communication_redundancy"
            ),
            
            # Environmental monitoring (MARPOL)
            ComplianceRule(
                rule_id="marpol_001",
                name="Emission Monitoring",
                framework=ComplianceFramework.MARPOL,
                description="Emission levels must be continuously monitored and logged",
                severity="high",
                automated_check=True,
                check_function="check_emission_monitoring"
            ),
            
            # Security systems (ISPS)
            ComplianceRule(
                rule_id="isps_001",
                name="Access Control Logs",
                framework=ComplianceFramework.ISPS,
                description="All access to restricted areas must be logged",
                severity="high",
                automated_check=True,
                check_function="check_access_control_logging"
            ),
            
            # Data protection (GDPR)
            ComplianceRule(
                rule_id="gdpr_001",
                name="Personal Data Encryption",
                framework=ComplianceFramework.GDPR,
                description="Personal data must be encrypted at rest and in transit",
                severity="high",
                automated_check=True,
                check_function="check_data_encryption"
            ),
            
            # Change management (Internal)
            ComplianceRule(
                rule_id="internal_001",
                name="Change Approval Required",
                framework=ComplianceFramework.INTERNAL,
                description="Critical system changes require approval",
                severity="medium",
                automated_check=True,
                check_function="check_change_approval"
            ),
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default compliance rules")
    
    def assess_system_compliance(
        self,
        system_name: str,
        system_config: Dict[str, Any],
        frameworks: Optional[List[ComplianceFramework]] = None
    ) -> ComplianceAssessment:
        """
        Assess compliance of a system configuration
        
        Args:
            system_name: Name of the system being assessed
            system_config: Configuration details of the system
            frameworks: Specific frameworks to check (all if None)
            
        Returns:
            ComplianceAssessment with results
        """
        
        assessment_id = f"assess_{system_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine which rules to check
        rules_to_check = []
        if frameworks:
            rules_to_check = [
                rule for rule in self.rules.values()
                if rule.framework in frameworks and rule.enabled
            ]
        else:
            rules_to_check = [rule for rule in self.rules.values() if rule.enabled]
        
        violations = []
        warnings = []
        
        # Run compliance checks
        for rule in rules_to_check:
            if rule.automated_check and rule.check_function:
                try:
                    violation = self._run_compliance_check(
                        rule, system_name, system_config
                    )
                    if violation:
                        if violation.status == ComplianceStatus.NON_COMPLIANT:
                            violations.append(violation)
                        elif violation.status == ComplianceStatus.WARNING:
                            warnings.append(violation)
                        
                        self.violation_history.append(violation)
                        
                except Exception as e:
                    logger.error(f"Failed to run compliance check {rule.rule_id}: {e}")
        
        # Determine overall status
        if violations:
            critical_violations = [v for v in violations if v.severity == "critical"]
            if critical_violations:
                overall_status = ComplianceStatus.NON_COMPLIANT
            else:
                overall_status = ComplianceStatus.WARNING
        elif warnings:
            overall_status = ComplianceStatus.WARNING
        else:
            overall_status = ComplianceStatus.COMPLIANT
        
        # Create assessment
        assessment = ComplianceAssessment(
            assessment_id=assessment_id,
            target_system=system_name,
            target_operation="system_configuration",
            assessed_at=datetime.now(),
            overall_status=overall_status,
            frameworks_checked=frameworks or list(ComplianceFramework),
            violations=violations,
            warnings=warnings,
            summary={
                "total_rules_checked": len(rules_to_check),
                "violations_count": len(violations),
                "warnings_count": len(warnings),
                "critical_violations": len([v for v in violations if v.severity == "critical"]),
                "high_violations": len([v for v in violations if v.severity == "high"])
            }
        )
        
        self.assessment_history.append(assessment)
        
        logger.info(
            f"Compliance assessment {assessment_id} completed: "
            f"{overall_status.value} ({len(violations)} violations, {len(warnings)} warnings)"
        )
        
        return assessment
    
    def assess_operation_compliance(
        self,
        operation_type: str,
        operation_details: Dict[str, Any],
        target_systems: List[str]
    ) -> ComplianceAssessment:
        """
        Assess compliance of a planned operation
        
        Args:
            operation_type: Type of operation (e.g., 'auto_remediation', 'maintenance')
            operation_details: Details of the planned operation
            target_systems: Systems that will be affected
            
        Returns:
            ComplianceAssessment with results
        """
        
        assessment_id = f"assess_op_{operation_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        violations = []
        warnings = []
        
        # Check operation-specific compliance rules
        for rule in self.rules.values():
            if not rule.enabled or not rule.automated_check:
                continue
            
            try:
                violation = self._run_operation_compliance_check(
                    rule, operation_type, operation_details, target_systems
                )
                if violation:
                    if violation.status == ComplianceStatus.NON_COMPLIANT:
                        violations.append(violation)
                    elif violation.status == ComplianceStatus.WARNING:
                        warnings.append(violation)
                    
                    self.violation_history.append(violation)
                    
            except Exception as e:
                logger.error(f"Failed to run operation compliance check {rule.rule_id}: {e}")
        
        # Determine overall status
        if violations:
            critical_violations = [v for v in violations if v.severity == "critical"]
            overall_status = ComplianceStatus.NON_COMPLIANT if critical_violations else ComplianceStatus.WARNING
        elif warnings:
            overall_status = ComplianceStatus.WARNING
        else:
            overall_status = ComplianceStatus.COMPLIANT
        
        assessment = ComplianceAssessment(
            assessment_id=assessment_id,
            target_system=", ".join(target_systems),
            target_operation=operation_type,
            assessed_at=datetime.now(),
            overall_status=overall_status,
            frameworks_checked=list(ComplianceFramework),
            violations=violations,
            warnings=warnings,
            summary={
                "operation_type": operation_type,
                "affected_systems_count": len(target_systems),
                "violations_count": len(violations),
                "warnings_count": len(warnings)
            }
        )
        
        self.assessment_history.append(assessment)
        
        return assessment
    
    def _run_compliance_check(
        self,
        rule: ComplianceRule,
        system_name: str,
        system_config: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Run a specific compliance check"""
        
        # This is where specific compliance check functions would be implemented
        # For now, we'll implement some basic checks
        
        if rule.check_function == "check_navigation_availability":
            return self._check_navigation_availability(rule, system_name, system_config)
        elif rule.check_function == "check_communication_redundancy":
            return self._check_communication_redundancy(rule, system_name, system_config)
        elif rule.check_function == "check_data_encryption":
            return self._check_data_encryption(rule, system_name, system_config)
        elif rule.check_function == "check_change_approval":
            return self._check_change_approval(rule, system_name, system_config)
        
        return None
    
    def _run_operation_compliance_check(
        self,
        rule: ComplianceRule,
        operation_type: str,
        operation_details: Dict[str, Any],
        target_systems: List[str]
    ) -> Optional[ComplianceViolation]:
        """Run compliance check for a planned operation"""
        
        # Check if operation affects safety-critical systems
        if rule.framework == ComplianceFramework.SOLAS:
            safety_critical_systems = ["navigation", "communication", "propulsion", "steering"]
            if any(system in " ".join(target_systems).lower() for system in safety_critical_systems):
                if not operation_details.get("safety_approval", False):
                    return ComplianceViolation(
                        violation_id=f"viol_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        framework=rule.framework,
                        severity=rule.severity,
                        status=ComplianceStatus.NON_COMPLIANT,
                        detected_at=datetime.now(),
                        description=f"Operation {operation_type} affects safety-critical systems without approval",
                        affected_systems=target_systems,
                        evidence={"operation_details": operation_details},
                        remediation_required=True,
                        remediation_suggestions=["Obtain safety approval before proceeding"]
                    )
        
        return None
    
    def _check_navigation_availability(
        self,
        rule: ComplianceRule,
        system_name: str,
        system_config: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check navigation system availability"""
        
        if "navigation" not in system_name.lower():
            return None
        
        availability = system_config.get("availability", 0.0)
        min_availability = rule.parameters.get("min_availability", 0.999)
        
        if availability < min_availability:
            return ComplianceViolation(
                violation_id=f"viol_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                framework=rule.framework,
                severity=rule.severity,
                status=ComplianceStatus.NON_COMPLIANT,
                detected_at=datetime.now(),
                description=f"Navigation availability {availability:.3f} below required {min_availability}",
                affected_systems=[system_name],
                evidence={"current_availability": availability, "required_availability": min_availability},
                remediation_required=True,
                remediation_suggestions=[
                    "Implement redundant navigation systems",
                    "Review maintenance procedures",
                    "Check for hardware failures"
                ]
            )
        
        return None
    
    def _check_communication_redundancy(
        self,
        rule: ComplianceRule,
        system_name: str,
        system_config: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check communication system redundancy"""
        
        if "communication" not in system_name.lower() and "radio" not in system_name.lower():
            return None
        
        redundancy_level = system_config.get("redundancy_level", 0)
        
        if redundancy_level < 2:  # Require at least N+1 redundancy
            return ComplianceViolation(
                violation_id=f"viol_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                framework=rule.framework,
                severity=rule.severity,
                status=ComplianceStatus.NON_COMPLIANT,
                detected_at=datetime.now(),
                description=f"Communication system lacks sufficient redundancy (level: {redundancy_level})",
                affected_systems=[system_name],
                evidence={"current_redundancy": redundancy_level, "required_redundancy": 2},
                remediation_required=True,
                remediation_suggestions=[
                    "Install backup communication equipment",
                    "Configure automatic failover",
                    "Test backup systems regularly"
                ]
            )
        
        return None
    
    def _check_data_encryption(
        self,
        rule: ComplianceRule,
        system_name: str,
        system_config: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check data encryption compliance"""
        
        if not system_config.get("handles_personal_data", False):
            return None
        
        encryption_at_rest = system_config.get("encryption_at_rest", False)
        encryption_in_transit = system_config.get("encryption_in_transit", False)
        
        if not (encryption_at_rest and encryption_in_transit):
            return ComplianceViolation(
                violation_id=f"viol_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                framework=rule.framework,
                severity=rule.severity,
                status=ComplianceStatus.NON_COMPLIANT,
                detected_at=datetime.now(),
                description="Personal data not properly encrypted",
                affected_systems=[system_name],
                evidence={
                    "encryption_at_rest": encryption_at_rest,
                    "encryption_in_transit": encryption_in_transit
                },
                remediation_required=True,
                remediation_suggestions=[
                    "Enable encryption at rest",
                    "Enable encryption in transit",
                    "Review encryption key management"
                ]
            )
        
        return None
    
    def _check_change_approval(
        self,
        rule: ComplianceRule,
        system_name: str,
        system_config: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check change approval requirements"""
        
        is_critical = system_config.get("critical_system", False)
        has_approval = system_config.get("change_approved", False)
        
        if is_critical and not has_approval:
            return ComplianceViolation(
                violation_id=f"viol_{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                rule_id=rule.rule_id,
                rule_name=rule.name,
                framework=rule.framework,
                severity=rule.severity,
                status=ComplianceStatus.NON_COMPLIANT,
                detected_at=datetime.now(),
                description="Critical system change lacks required approval",
                affected_systems=[system_name],
                evidence={"is_critical": is_critical, "has_approval": has_approval},
                remediation_required=True,
                remediation_suggestions=[
                    "Obtain proper change approval",
                    "Follow change management procedures",
                    "Document approval in change log"
                ]
            )
        
        return None
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get summary of compliance status"""
        
        if not self.assessment_history:
            return {"message": "No compliance assessments performed yet"}
        
        recent_assessments = self.assessment_history[-50:]  # Last 50 assessments
        
        status_counts = {}
        framework_violations = {}
        
        for assessment in recent_assessments:
            status = assessment.overall_status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            for violation in assessment.violations:
                framework = violation.framework.value
                framework_violations[framework] = framework_violations.get(framework, 0) + 1
        
        return {
            "total_assessments": len(self.assessment_history),
            "recent_assessments": len(recent_assessments),
            "status_distribution": status_counts,
            "violations_by_framework": framework_violations,
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "last_assessment": self.assessment_history[-1].assessed_at.isoformat() if self.assessment_history else None
        }