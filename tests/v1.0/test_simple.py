"""
Simple test runner for v1.0 components
"""

import sys
import os
import asyncio

# Add src to path and create module alias
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src/v1.0'))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from auto_remediation.confidence_engine import ConfidenceEngine, IncidentContext
        from auto_remediation.policy_manager import PolicyManager
        from compliance_audit.compliance_checker import ComplianceChecker
        from drift_monitoring.drift_detector import DriftDetector
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_confidence_engine():
    """Test confidence engine basic functionality"""
    print("Testing Confidence Engine...")
    
    try:
        from auto_remediation.confidence_engine import ConfidenceEngine, IncidentContext, RemediationScenario
        
        engine = ConfidenceEngine()
        
        # Add a mock scenario
        engine.scenarios = {
            "test_scenario": RemediationScenario(
                scenario_id="test_scenario",
                name="Test",
                description="Test",
                success_rate=0.8,
                execution_count=10
            )
        }
        
        # Create incident context
        incident = IncidentContext(
            incident_id="test_001",
            incident_type="connectivity", 
            severity="high",
            affected_systems=["satellite"],
            symptoms={"connectivity": "degraded"},
            environmental_factors={"weather": "clear"},
            ship_status={}
        )
        
        # Test confidence calculation
        results = engine.calculate_confidence(incident, ["test_scenario"])
        
        assert "test_scenario" in results
        confidence_score, confidence_level = results["test_scenario"]
        assert 0.0 <= confidence_score <= 1.0
        
        print("✓ Confidence Engine test passed")
        return True
        
    except Exception as e:
        print(f"✗ Confidence Engine test failed: {e}")
        return False

def test_compliance_checker():
    """Test compliance checker functionality"""
    print("Testing Compliance Checker...")
    
    try:
        from compliance_audit.compliance_checker import ComplianceChecker
        
        checker = ComplianceChecker()
        
        # Test system assessment
        system_config = {
            "availability": 0.999,
            "redundancy_level": 2,
            "handles_personal_data": False
        }
        
        assessment = checker.assess_system_compliance(
            "test_system",
            system_config
        )
        
        assert assessment.target_system == "test_system"
        assert assessment.overall_status.value in ["compliant", "warning", "non_compliant", "unknown"]
        
        print("✓ Compliance Checker test passed")
        return True
        
    except Exception as e:
        print(f"✗ Compliance Checker test failed: {e}")
        return False

def test_drift_detector():
    """Test drift detector functionality"""
    print("Testing Drift Detector...")
    
    try:
        from drift_monitoring.drift_detector import DriftDetector
        
        detector = DriftDetector()
        
        # Register a model
        detector.register_model("test_model", ["adwin"])
        
        assert "test_model" in detector.detectors
        
        # Add some samples
        alerts = detector.add_prediction_sample(
            "test_model",
            prediction=1.0,
            actual=1.0,
            features={"feature1": 1.0}
        )
        
        assert isinstance(alerts, list)
        
        print("✓ Drift Detector test passed")
        return True
        
    except Exception as e:
        print(f"✗ Drift Detector test failed: {e}")
        return False

async def test_integration():
    """Test basic integration"""
    print("Testing Integration...")
    
    try:
        from auto_remediation.confidence_engine import ConfidenceEngine, IncidentContext, RemediationScenario
        from auto_remediation.policy_manager import PolicyManager, PolicyRule
        from auto_remediation.remediation_engine import RemediationEngine
        
        # Create components
        confidence_engine = ConfidenceEngine()
        policy_manager = PolicyManager()
        
        # Mock data
        confidence_engine.scenarios = {
            "test_scenario": RemediationScenario(
                scenario_id="test_scenario",
                name="Test",
                description="Test",
                success_rate=0.8,
                execution_count=10
            )
        }
        
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
        
        remediation_engine = RemediationEngine(
            confidence_engine=confidence_engine,
            policy_manager=policy_manager,
            dry_run=True
        )
        
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
        
        # Test evaluation
        result = await remediation_engine.evaluate_incident(
            incident, ["test_scenario"]
        )
        
        assert "decision" in result
        
        print("✓ Integration test passed")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running v1.0 Self-Learning Closed-Loop Automation tests...\n")
    
    tests = [
        test_imports(),
        test_confidence_engine(),
        test_compliance_checker(),
        test_drift_detector(),
    ]
    
    # Run async integration test
    try:
        integration_result = asyncio.run(test_integration())
        tests.append(integration_result)
    except Exception as e:
        print(f"✗ Integration test error: {e}")
        tests.append(False)
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)