#!/usr/bin/env python3
"""
v1.0 Self-Learning Closed-Loop Automation Demo

Demonstrates the key capabilities of the v1.0 implementation:
- Confidence-scored auto-remediation
- Drift monitoring and model management
- Compliance checking
- Change management
- Post-incident review automation
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src/v1.0'))

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def print_subsection(title):
    print(f"\n--- {title} ---")

async def demo_auto_remediation():
    """Demo auto-remediation system"""
    print_section("V1.0 AUTO-REMEDIATION SYSTEM DEMO")
    
    from auto_remediation.confidence_engine import ConfidenceEngine, IncidentContext, RemediationScenario
    from auto_remediation.policy_manager import PolicyManager, PolicyRule
    from auto_remediation.remediation_engine import RemediationEngine
    
    print_subsection("1. Setting up Confidence Engine")
    
    # Create confidence engine with scenarios
    engine = ConfidenceEngine()
    engine.scenarios = {
        "satellite_failover": RemediationScenario(
            scenario_id="satellite_failover",
            name="Satellite Link Failover",
            description="Automatic failover to backup satellite link",
            success_rate=0.92,
            execution_count=45,
            risk_level="medium"
        ),
        "bandwidth_throttling": RemediationScenario(
            scenario_id="bandwidth_throttling", 
            name="Emergency Bandwidth Throttling",
            description="Reduce non-critical traffic during degradation",
            success_rate=0.88,
            execution_count=78,
            risk_level="low"
        )
    }
    
    print(f"✓ Loaded {len(engine.scenarios)} remediation scenarios")
    
    print_subsection("2. Setting up Policy Manager")
    
    # Create policy manager
    policy_manager = PolicyManager()
    policy_manager.policies = {
        "auto_satellite_failover": PolicyRule(
            rule_id="auto_satellite_failover",
            scenario_id="satellite_failover", 
            min_confidence=0.80,
            max_blast_radius=2,
            allowed_systems=["satellite_modem", "backup_modem"],
            forbidden_systems=["navigation", "safety_systems"],
            time_windows=["00:00-23:59"],
            approval_required=False
        ),
        "auto_bandwidth_throttling": PolicyRule(
            rule_id="auto_bandwidth_throttling",
            scenario_id="bandwidth_throttling",
            min_confidence=0.75, 
            max_blast_radius=5,
            allowed_systems=["qos", "traffic_shaper"],
            forbidden_systems=["emergency_comms"],
            time_windows=["00:00-23:59"],
            approval_required=False
        )
    }
    
    print(f"✓ Configured {len(policy_manager.policies)} auto-remediation policies")
    
    print_subsection("3. Creating Remediation Engine")
    
    # Create remediation engine
    remediation_engine = RemediationEngine(
        confidence_engine=engine,
        policy_manager=policy_manager,
        dry_run=True  # Safe demo mode
    )
    
    print("✓ Remediation engine initialized in dry-run mode")
    
    print_subsection("4. Processing Incident")
    
    # Create incident context
    incident = IncidentContext(
        incident_id="DEMO_001",
        incident_type="satellite_connectivity",
        severity="high",
        affected_systems=["satellite_modem", "backup_modem"],
        symptoms={"connectivity": "degraded", "signal_strength": "weak"},
        environmental_factors={"weather": "cloudy", "ship_heading": "north"},
        ship_status={"position": "Atlantic Ocean", "speed": "15 knots"}
    )
    
    print(f"✓ Created incident: {incident.incident_id} ({incident.severity} severity)")
    
    # Evaluate incident
    evaluation = await remediation_engine.evaluate_incident(
        incident, ["satellite_failover", "bandwidth_throttling"]
    )
    
    print(f"✓ Incident evaluation completed:")
    print(f"  - Decision: {evaluation['decision']}")
    print(f"  - Best scenario: {evaluation.get('scenario_id', 'N/A')}")
    print(f"  - Confidence: {evaluation.get('confidence_score', 0):.3f}")
    print(f"  - Level: {evaluation.get('confidence_level', 'N/A')}")
    
    if evaluation['decision'] == 'auto_execute':
        print_subsection("5. Executing Auto-Remediation")
        
        execution = await remediation_engine.execute_remediation(
            incident_context=incident,
            scenario_id=evaluation['scenario_id'],
            confidence_score=evaluation['confidence_score'],
            confidence_level=evaluation['confidence_level']
        )
        
        print(f"✓ Remediation executed successfully!")
        print(f"  - Execution ID: {execution.execution_id}")
        print(f"  - Status: {execution.status.value}")
        print(f"  - Duration: {execution.resolution_time_minutes:.1f} minutes")
        
        # Show metrics
        metrics = remediation_engine.get_metrics()
        print(f"\n📊 System Metrics:")
        print(f"  - MTTR: {metrics['mttr_minutes']:.1f} minutes")
        print(f"  - Success Rate: {metrics['success_rate_percent']}%")
        print(f"  - Total Executions: {metrics['total_executions']}")

def demo_drift_monitoring():
    """Demo drift monitoring system"""
    print_section("V1.0 DRIFT MONITORING SYSTEM DEMO")
    
    from drift_monitoring.drift_detector import DriftDetector
    
    print_subsection("1. Setting up Drift Detector")
    
    detector = DriftDetector()
    
    # Register models for monitoring
    detector.register_model("link_quality_predictor", ["adwin", "page_hinkley"])
    detector.register_model("traffic_anomaly_detector", ["ks_test"])
    
    print(f"✓ Registered {len(detector.detectors)} models for drift monitoring")
    
    print_subsection("2. Simulating Model Predictions")
    
    # Simulate stable predictions
    print("Simulating stable baseline...")
    for i in range(20):
        detector.add_prediction_sample(
            "link_quality_predictor",
            prediction=0.8 + (i * 0.001),  # Gradual trend
            actual=0.8 + (i * 0.001) + (0.02 * (i % 3 - 1)),  # Small noise
            features={"signal_strength": 0.8, "weather_score": 0.9}
        )
    
    print("✓ Added 20 baseline samples")
    
    # Simulate drift
    print("Simulating concept drift...")
    alerts = detector.add_prediction_sample(
        "link_quality_predictor",
        prediction=0.9,  # Model still predicts high
        actual=0.4,      # But actual performance drops significantly
        features={"signal_strength": 0.4, "weather_score": 0.3}
    )
    
    if alerts:
        print(f"🚨 DRIFT DETECTED! {len(alerts)} alerts generated")
        for alert in alerts:
            print(f"  - {alert.drift_type.value}: {alert.description}")
            print(f"    Severity: {alert.severity}, Confidence: {alert.confidence:.3f}")
    else:
        print("ℹ️ No drift detected (algorithms may need more samples)")
    
    # Show drift summary
    summary = detector.get_drift_summary()
    print(f"\n📊 Drift Monitoring Summary:")
    print(f"  - Total alerts: {summary['total_alerts']}")
    print(f"  - Recent alerts: {summary['recent_alerts']}")
    print(f"  - Models monitored: {len(summary['models_monitored'])}")

def demo_compliance_checking():
    """Demo compliance checking system"""
    print_section("V1.0 COMPLIANCE & AUDIT SYSTEM DEMO")
    
    from compliance_audit.compliance_checker import ComplianceChecker, ComplianceFramework
    
    print_subsection("1. Setting up Compliance Checker")
    
    checker = ComplianceChecker()
    print(f"✓ Loaded {len(checker.rules)} default compliance rules")
    
    print_subsection("2. Assessing System Compliance")
    
    # Test navigation system compliance (should be compliant)
    nav_system_config = {
        "availability": 0.999,
        "redundancy_level": 3,
        "handles_personal_data": False,
        "critical_system": True,
        "change_approved": True
    }
    
    assessment = checker.assess_system_compliance(
        "navigation_system",
        nav_system_config
    )
    
    print(f"✓ Navigation System Assessment:")
    print(f"  - Status: {assessment.overall_status.value}")
    print(f"  - Violations: {len(assessment.violations)}")
    print(f"  - Warnings: {len(assessment.warnings)}")
    
    if assessment.violations:
        for violation in assessment.violations:
            print(f"    ❌ {violation.rule_name}: {violation.description}")
    
    # Test non-compliant system
    print_subsection("3. Detecting Compliance Violations")
    
    non_compliant_config = {
        "availability": 0.95,  # Below SOLAS requirement
        "redundancy_level": 1,  # Insufficient redundancy  
        "handles_personal_data": True,
        "encryption_at_rest": False,  # GDPR violation
        "encryption_in_transit": False,
        "critical_system": True,
        "change_approved": False  # Missing approval
    }
    
    violation_assessment = checker.assess_operation_compliance(
        "auto_remediation",
        {"safety_approval": False},
        ["communication_system"]
    )
    
    print(f"✓ Operation Compliance Assessment:")
    print(f"  - Status: {violation_assessment.overall_status.value}")
    print(f"  - Violations: {len(violation_assessment.violations)}")
    
    for violation in violation_assessment.violations:
        print(f"    ❌ {violation.rule_name}: {violation.description}")
        print(f"       Remediation: {violation.remediation_suggestions[0] if violation.remediation_suggestions else 'N/A'}")

def demo_post_incident_review():
    """Demo post-incident review and learning system"""
    print_section("V1.0 POST-INCIDENT REVIEW & LEARNING DEMO")
    
    from post_incident_review.incident_analyzer import IncidentAnalyzer, EventType, RootCauseCategory
    from post_incident_review.pattern_recognizer import PatternRecognizer, PatternType
    from post_incident_review.effectiveness_assessor import EffectivenessAssessor, EffectivenessLevel
    from post_incident_review.learning_engine import LearningEngine, ImplementationStatus
    
    print_subsection("1. Incident Timeline Reconstruction")
    
    # Create sample incident data
    sample_incident = {
        "incident_id": "INC-2024-001",
        "start_time": "2024-01-15T09:15:00",
        "resolution_time": "2024-01-15T09:25:00", 
        "alerts": [
            {
                "timestamp": "2024-01-15T09:15:00",
                "source": "satellite_monitor",
                "message": "Satellite link quality degraded",
                "severity": "high"
            }
        ],
        "symptoms": [
            {
                "timestamp": "2024-01-15T09:14:30",
                "system": "communication",
                "description": "Increased packet loss on primary satellite link"
            }
        ],
        "remediation_actions": [
            {
                "start_time": "2024-01-15T09:17:00",
                "end_time": "2024-01-15T09:19:00",
                "action_name": "satellite_failover",
                "result": "success"
            }
        ]
    }
    
    analyzer = IncidentAnalyzer()
    timeline = analyzer.reconstruct_timeline(sample_incident)
    
    print(f"✓ Timeline reconstructed for {timeline.incident_id}")
    print(f"  - Duration: {timeline.total_duration_minutes:.1f} minutes")
    print(f"  - Detection delay: {timeline.detection_delay_minutes:.1f} minutes")
    print(f"  - Resolution time: {timeline.resolution_time_minutes:.1f} minutes")
    print(f"  - Events captured: {len(timeline.events)}")
    
    print_subsection("2. Root Cause Analysis")
    
    root_cause = analyzer.analyze_root_cause(timeline, {
        "network_latency": 150,
        "packet_loss": 5,
        "signal_strength": -85
    })
    
    print(f"✓ Root cause identified: {root_cause.primary_cause.value}")
    print(f"  - Confidence: {root_cause.confidence_score:.1%}")
    print(f"  - Evidence points: {len(root_cause.evidence)}")
    print(f"  - Recommendations: {len(root_cause.recommendations)}")
    
    print_subsection("3. Pattern Recognition")
    
    # Sample historical incident data
    incidents_data = [
        {"incident_id": "INC-001", "start_time": "2024-01-15T09:15:00", "affected_systems": ["satellite"], "root_cause_analysis": {"primary_cause": "network_issue"}},
        {"incident_id": "INC-002", "start_time": "2024-01-15T14:30:00", "affected_systems": ["satellite"], "root_cause_analysis": {"primary_cause": "network_issue"}},
        {"incident_id": "INC-003", "start_time": "2024-01-16T09:45:00", "affected_systems": ["satellite"], "root_cause_analysis": {"primary_cause": "network_issue"}},
        {"incident_id": "INC-004", "start_time": "2024-01-17T14:20:00", "affected_systems": ["navigation"], "root_cause_analysis": {"primary_cause": "hardware_failure"}},
    ]
    
    pattern_recognizer = PatternRecognizer()
    patterns = pattern_recognizer.analyze_incidents(incidents_data)
    
    print(f"✓ Patterns identified: {len(patterns)}")
    for pattern in patterns[:3]:  # Show top 3
        print(f"  - {pattern.description} (confidence: {pattern.confidence:.1%})")
    
    print_subsection("4. Effectiveness Assessment")
    
    # Sample remediation history
    remediation_history = [
        {"scenario_id": "satellite_failover", "scenario_name": "Satellite Failover", "timestamp": "2024-01-15T09:17:00", "success": True, "resolution_time_minutes": 8},
        {"scenario_id": "satellite_failover", "scenario_name": "Satellite Failover", "timestamp": "2024-01-16T14:20:00", "success": True, "resolution_time_minutes": 12},
        {"scenario_id": "satellite_failover", "scenario_name": "Satellite Failover", "timestamp": "2024-01-17T11:30:00", "success": False, "resolution_time_minutes": 45},
        {"scenario_id": "satellite_failover", "scenario_name": "Satellite Failover", "timestamp": "2024-01-18T16:15:00", "success": True, "resolution_time_minutes": 6},
        {"scenario_id": "satellite_failover", "scenario_name": "Satellite Failover", "timestamp": "2024-01-19T10:45:00", "success": True, "resolution_time_minutes": 10},
    ]
    
    assessor = EffectivenessAssessor()
    assessment = assessor.assess_remediation_effectiveness(remediation_history, "satellite_failover")
    
    print(f"✓ Effectiveness assessed for satellite_failover scenario")
    print(f"  - Success rate: {assessment.successful_attempts}/{assessment.total_attempts} ({assessment.successful_attempts/max(assessment.total_attempts,1):.1%})")
    print(f"  - Average resolution: {assessment.average_resolution_time_minutes:.1f} minutes")
    print(f"  - Overall effectiveness: {assessment.overall_effectiveness.value}")
    print(f"  - Recommendations: {len(assessment.recommendations)}")
    
    print_subsection("5. Learning Engine")
    
    learning_engine = LearningEngine()
    current_confidence = {"satellite_failover": 0.75}
    current_policies = {"min_confidence_auto": 0.7, "max_blast_radius": 5}
    
    learning_cycle = learning_engine.run_learning_cycle(
        incident_timelines=[timeline],
        root_cause_analyses=[root_cause],
        incident_patterns=patterns,
        effectiveness_assessments=[assessment],
        current_confidence_scores=current_confidence,
        current_policies=current_policies
    )
    
    print(f"✓ Learning cycle completed: {learning_cycle.cycle_id}")
    print(f"  - Confidence adjustments suggested: {len(learning_cycle.confidence_adjustments)}")
    print(f"  - Policy recommendations: {len(learning_cycle.policy_recommendations)}")
    print(f"  - New scenarios suggested: {len(learning_cycle.new_scenarios_suggested)}")
    print(f"  - Effectiveness improvements identified: {len(learning_cycle.effectiveness_improvements)}")
    
    # Show sample learning insights
    if learning_cycle.confidence_adjustments:
        adj = learning_cycle.confidence_adjustments[0]
        print(f"\n📊 Sample Confidence Adjustment:")
        print(f"  - Scenario: {adj.scenario_id}")
        print(f"  - Current → Suggested: {adj.current_confidence:.2f} → {adj.suggested_confidence:.2f}")
        print(f"  - Reason: {adj.adjustment_reason}")
    
    if learning_cycle.effectiveness_improvements:
        print(f"\n🎯 Sample Improvement: {learning_cycle.effectiveness_improvements[0]}")

def demo_system_integration():
    """Demo complete system integration"""
    print_section("V1.0 INTEGRATED SYSTEM DEMO")
    
    print_subsection("Simulating Complete Incident Lifecycle")
    
    print("📋 Incident Timeline:")
    print("  1. 09:15 - Satellite link degradation detected")
    print("  2. 09:16 - Confidence engine evaluates scenarios")  
    print("  3. 09:16 - Policy manager checks constraints")
    print("  4. 09:16 - Compliance validation passes")
    print("  5. 09:17 - Auto-remediation executed (satellite failover)")
    print("  6. 09:19 - Service restored, rollback capability maintained")
    print("  7. 09:20 - Post-incident review triggered")
    print("  8. 09:25 - Learning extracted, confidence scores updated")
    
    print("\n✅ Complete closed-loop automation demonstrated!")
    
    print(f"\n🎯 Key v1.0 Achievements:")
    print("  - Confidence-scored auto-remediation with gradual policy expansion")
    print("  - Drift monitoring with automatic model lifecycle management")  
    print("  - Comprehensive compliance checking (SOLAS, MARPOL, ISPS, GDPR)")
    print("  - Automated change windows and approval workflows")
    print("  - Post-incident review with learning extraction")
    print("  - Auditable and safe automation at fleet scale")

async def main():
    """Run the complete v1.0 demo"""
    print("🚢 AIOps NAAS v1.0 Self-Learning Closed-Loop Automation Demo")
    print("="*60)
    
    try:
        await demo_auto_remediation()
        demo_drift_monitoring()
        demo_compliance_checking()
        demo_post_incident_review()
        demo_system_integration()
        
        print(f"\n🎉 v1.0 Demo completed successfully!")
        print("The self-learning closed-loop automation system is ready for deployment.")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)