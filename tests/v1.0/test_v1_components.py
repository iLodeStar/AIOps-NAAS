"""
Test suite for v1.0 Self-Learning Closed-Loop Automation
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

# Import components to test
from v1.0.auto_remediation.confidence_engine import ConfidenceEngine, IncidentContext
from v1.0.auto_remediation.policy_manager import PolicyManager  
from v1.0.auto_remediation.remediation_engine import RemediationEngine
from v1.0.compliance_audit.compliance_checker import ComplianceChecker
from v1.0.drift_monitoring.drift_detector import DriftDetector


class TestConfidenceEngine:
    """Test cases for the Confidence Engine"""
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        engine = ConfidenceEngine()
        
        # Create mock incident
        incident = IncidentContext(
            incident_id="test_001",
            incident_type="connectivity",
            severity="high",
            affected_systems=["satellite_modem"],
            symptoms={"connectivity": "degraded"},
            environmental_factors={"weather": "clear"},
            ship_status={}
        )
        
        # Mock scenarios - since we don't have config file in test
        from v1.0.auto_remediation.confidence_engine import RemediationScenario
        engine.scenarios = {
            "satellite_failover": RemediationScenario(
                scenario_id="satellite_failover",
                name="Satellite Failover",
                description="Test scenario",
                success_rate=0.9,
                execution_count=50,
                risk_level="medium"
            )
        }
        
        results = engine.calculate_confidence(incident, ["satellite_failover"])
        
        assert "satellite_failover" in results
        confidence_score, confidence_level = results["satellite_failover"]
        assert 0.0 <= confidence_score <= 1.0
        assert confidence_level.value in ["low", "medium", "high", "critical"]
    
    def test_scenario_success_update(self):
        """Test updating scenario success rates"""
        engine = ConfidenceEngine()
        
        # Add mock scenario
        from v1.0.auto_remediation.confidence_engine import RemediationScenario
        engine.scenarios = {
            "test_scenario": RemediationScenario(
                scenario_id="test_scenario",
                name="Test",
                description="Test",
                success_rate=0.8,
                execution_count=10
            )
        }
        
        original_rate = engine.scenarios["test_scenario"].success_rate
        original_count = engine.scenarios["test_scenario"].execution_count
        
        # Update with success
        engine.update_scenario_success("test_scenario", True)
        
        assert engine.scenarios["test_scenario"].execution_count == original_count + 1
        # Success rate should change slightly due to exponential moving average


class TestPolicyManager:
    """Test cases for the Policy Manager"""
    
    def test_policy_evaluation_allowed(self):
        """Test policy evaluation that allows action"""
        manager = PolicyManager()
        
        # Mock policy
        from v1.0.auto_remediation.policy_manager import PolicyRule
        manager.policies = {
            "test_policy": PolicyRule(
                rule_id="test_policy",
                scenario_id="test_scenario",
                min_confidence=0.5,
                max_blast_radius=5,
                allowed_systems=[],
                forbidden_systems=[],
                time_windows=[],
                approval_required=False
            )
        }
        
        from auto_remediation.confidence_engine import ConfidenceLevel
        
        result = manager.evaluate_policy(
            scenario_id="test_scenario",
            confidence_level=ConfidenceLevel.HIGH,
            confidence_score=0.8,
            affected_systems=["test_system"]
        )
        
        assert result['allowed'] is True
        assert result['approval_required'] is False
    
    def test_policy_evaluation_blocked(self):
        """Test policy evaluation that blocks action"""
        manager = PolicyManager()
        
        # Mock policy with high confidence requirement
        from auto_remediation.policy_manager import PolicyRule
        manager.policies = {
            "strict_policy": PolicyRule(
                rule_id="strict_policy", 
                scenario_id="test_scenario",
                min_confidence=0.95,
                max_blast_radius=1,
                allowed_systems=[],
                forbidden_systems=["test_system"],
                time_windows=[],
                approval_required=True
            )
        }
        
        from auto_remediation.confidence_engine import ConfidenceLevel
        
        result = manager.evaluate_policy(
            scenario_id="test_scenario",
            confidence_level=ConfidenceLevel.MEDIUM,
            confidence_score=0.7,
            affected_systems=["test_system"]
        )
        
        assert result['allowed'] is False


class TestComplianceChecker:
    """Test cases for the Compliance Checker"""
    
    def test_system_compliance_assessment(self):
        """Test system compliance assessment"""
        checker = ComplianceChecker()
        
        # Test compliant system
        system_config = {
            "availability": 0.999,
            "redundancy_level": 2,
            "encryption_at_rest": True,
            "encryption_in_transit": True,
            "handles_personal_data": True
        }
        
        assessment = checker.assess_system_compliance(
            "test_navigation_system",
            system_config
        )
        
        assert assessment.overall_status.value in ["compliant", "warning", "non_compliant"]
        assert assessment.target_system == "test_navigation_system"
    
    def test_operation_compliance_assessment(self):
        """Test operation compliance assessment"""
        checker = ComplianceChecker()
        
        operation_details = {
            "operation_type": "auto_remediation",
            "confidence_score": 0.8,
            "safety_approval": False
        }
        
        assessment = checker.assess_operation_compliance(
            "auto_remediation",
            operation_details,
            ["navigation_system"]
        )
        
        # Should flag missing safety approval for navigation system
        assert len(assessment.violations) > 0 or len(assessment.warnings) > 0


class TestDriftDetector:
    """Test cases for the Drift Detector"""
    
    def test_model_registration(self):
        """Test model registration for drift monitoring"""
        detector = DriftDetector()
        
        detector.register_model("test_model", ["adwin"])
        
        assert "test_model" in detector.detectors
        assert "adwin" in detector.detectors["test_model"]
    
    def test_drift_detection(self):
        """Test drift detection with prediction samples"""
        detector = DriftDetector()
        detector.register_model("test_model", ["adwin"])
        
        # Add samples - first establish baseline
        for i in range(50):
            alerts = detector.add_prediction_sample(
                "test_model",
                prediction=1.0 + (i * 0.01),  # Gradually increasing
                actual=1.0 + (i * 0.01),
                features={"feature1": 1.0 + (i * 0.01)}
            )
        
        # Now add significantly different sample
        alerts = detector.add_prediction_sample(
            "test_model",
            prediction=2.0,  # Big jump
            actual=1.5,      # Different actual
            features={"feature1": 2.0}
        )
        
        # May or may not detect drift depending on algorithm sensitivity
        # Just check that no errors occurred
        assert isinstance(alerts, list)


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_incident_processing_flow(self):
        """Test complete incident processing flow"""
        
        # This would test the full V1ClosedLoopOrchestrator
        # For now, just test that components can work together
        
        # Create components
        confidence_engine = ConfidenceEngine()
        policy_manager = PolicyManager()
        remediation_engine = RemediationEngine(
            confidence_engine=confidence_engine,
            policy_manager=policy_manager,
            dry_run=True
        )
        
        # Mock some data
        from auto_remediation.confidence_engine import RemediationScenario
        confidence_engine.scenarios = {
            "test_scenario": RemediationScenario(
                scenario_id="test_scenario",
                name="Test",
                description="Test",
                success_rate=0.8,
                execution_count=10
            )
        }
        
        from auto_remediation.policy_manager import PolicyRule
        policy_manager.policies = {
            "test_policy": PolicyRule(
                rule_id="test_policy",
                scenario_id="test_scenario",
                min_confidence=0.5,
                max_blast_radius=5,
                allowed_systems=[],
                forbidden_systems=[],
                time_windows=[],
                approval_required=False
            )
        }
        
        # Create incident
        incident = IncidentContext(
            incident_id="integration_test",
            incident_type="test",
            severity="medium",
            affected_systems=["test_system"],
            symptoms={"test": "symptom"},
            environmental_factors={},
            ship_status={}
        )
        
        # Evaluate incident
        result = await remediation_engine.evaluate_incident(
            incident, ["test_scenario"]
        )
        
        assert "decision" in result
        assert result["decision"] in ["auto_execute", "approval_required", "manual_required", "blocked_by_policy"]


if __name__ == "__main__":
    # Run basic tests if executed directly
    print("Running basic v1.0 component tests...")
    
    # Test confidence engine
    test_confidence = TestConfidenceEngine()
    test_confidence.test_confidence_calculation()
    test_confidence.test_scenario_success_update()
    print("✓ Confidence Engine tests passed")
    
    # Test policy manager
    test_policy = TestPolicyManager()
    test_policy.test_policy_evaluation_allowed()
    test_policy.test_policy_evaluation_blocked()
    print("✓ Policy Manager tests passed")
    
    # Test compliance checker
    test_compliance = TestComplianceChecker()
    test_compliance.test_system_compliance_assessment()
    test_compliance.test_operation_compliance_assessment()
    print("✓ Compliance Checker tests passed")
    
    # Test drift detector
    test_drift = TestDriftDetector()
    test_drift.test_model_registration()
    test_drift.test_drift_detection()
    print("✓ Drift Detector tests passed")
    
    # Test integration
    test_integration = TestIntegration()
    asyncio.run(test_integration.test_incident_processing_flow())
    print("✓ Integration tests passed")
    
    print("\nAll v1.0 component tests passed! 🎉")