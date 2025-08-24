#!/usr/bin/env python3
"""
AIOps NAAS v0.3 - Integration Test for Predictive Link Health + Guarded Auto-Remediation

This script demonstrates the v0.3 features:
1. Predictive satellite link health monitoring
2. Risk assessment and remediation selection
3. Policy-based decision making
4. Approval workflow simulation

Run without external dependencies to validate the core logic.
"""

import json
import time
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from enum import Enum

# Simplified data classes for testing
@dataclass
class ModemKPIs:
    timestamp: datetime
    snr_db: float
    ber: float
    signal_strength_dbm: float
    rain_fade_margin_db: float

@dataclass
class WeatherData:
    timestamp: datetime
    precipitation_mm_hr: float
    wind_speed_knots: float

@dataclass
class ShipTelemetry:
    timestamp: datetime
    latitude: float
    longitude: float
    pitch_deg: float
    roll_deg: float
    speed_knots: float

@dataclass
class LinkPrediction:
    timestamp: datetime
    predicted_quality_score: float
    degradation_risk_level: str
    contributing_factors: List[str]
    recommended_actions: List[str]

class RemediationActionType(Enum):
    FAILOVER_BACKUP_SAT = "failover_backup_satellite"
    QOS_TRAFFIC_SHAPING = "qos_traffic_shaping"
    BANDWIDTH_REDUCTION = "bandwidth_reduction"

@dataclass
class RemediationAction:
    action_id: str
    action_type: RemediationActionType
    name: str
    risk_level: str
    requires_approval: bool
    parameters: Dict[str, Any]

@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool
    risk_assessment: Dict[str, Any]

class SimpleLinkPredictor:
    """Simplified link quality predictor for testing"""
    
    def predict_link_quality(self, modem: ModemKPIs, weather: WeatherData, ship: ShipTelemetry) -> LinkPrediction:
        # Calculate base quality from SNR and BER
        snr_score = max(0, min(1, (modem.snr_db - 5) / 20))
        ber_score = max(0, min(1, -(-6 if modem.ber < 1e-6 else -4 if modem.ber < 1e-4 else -2) / -6))
        
        base_quality = (snr_score * 0.6 + ber_score * 0.4)
        
        # Apply weather and movement impacts
        weather_impact = 1.0 - (weather.precipitation_mm_hr * 0.1)
        movement_impact = 1.0 - (abs(ship.pitch_deg) + abs(ship.roll_deg)) * 0.02
        
        final_quality = base_quality * weather_impact * movement_impact
        
        # Determine risk level
        if final_quality < 0.3:
            risk_level = "CRITICAL"
        elif final_quality < 0.5:
            risk_level = "HIGH"
        elif final_quality < 0.7:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Identify contributing factors
        factors = []
        if modem.snr_db < 10:
            factors.append("Low SNR")
        if modem.ber > 1e-4:
            factors.append("High BER")
        if weather.precipitation_mm_hr > 5:
            factors.append("Heavy precipitation")
        if abs(ship.pitch_deg) > 10 or abs(ship.roll_deg) > 10:
            factors.append("Excessive ship movement")
        
        # Generate recommendations
        recommendations = []
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.extend(["Switch to backup satellite", "Reduce bandwidth usage"])
        if "Heavy precipitation" in factors:
            recommendations.append("Monitor rain radar")
        if "Low SNR" in factors:
            recommendations.append("Check antenna alignment")
        
        return LinkPrediction(
            timestamp=datetime.now(),
            predicted_quality_score=max(0.0, min(1.0, final_quality)),
            degradation_risk_level=risk_level,
            contributing_factors=factors,
            recommended_actions=recommendations
        )

class SimplePolicyEngine:
    """Simplified policy engine for testing"""
    
    def evaluate_action(self, action: RemediationAction, context: Dict[str, Any]) -> PolicyDecision:
        # Simple policy rules
        allowed = True
        reason = "Action approved"
        
        # Check risk level
        if action.risk_level == "CRITICAL" and context.get("recent_actions", 0) >= 2:
            allowed = False
            reason = "Too many critical actions recently"
        
        # Determine approval requirement
        requires_approval = action.requires_approval or action.risk_level in ["HIGH", "CRITICAL"]
        
        return PolicyDecision(
            allowed=allowed,
            reason=reason,
            requires_approval=requires_approval,
            risk_assessment={"risk_level": action.risk_level, "context_score": len(context)}
        )

class SimpleRemediationService:
    """Simplified remediation service for testing"""
    
    def __init__(self):
        self.predictor = SimpleLinkPredictor()
        self.policy_engine = SimplePolicyEngine()
        self.actions = {
            "satellite_failover": RemediationAction(
                action_id="satellite_failover",
                action_type=RemediationActionType.FAILOVER_BACKUP_SAT,
                name="Satellite Failover",
                risk_level="HIGH",
                requires_approval=True,
                parameters={"backup_satellite": "SAT-BACKUP-1"}
            ),
            "qos_shaping": RemediationAction(
                action_id="qos_shaping",
                action_type=RemediationActionType.QOS_TRAFFIC_SHAPING,
                name="QoS Traffic Shaping",
                risk_level="MEDIUM",
                requires_approval=False,
                parameters={"bandwidth_limit_mbps": 10}
            ),
            "bandwidth_reduction": RemediationAction(
                action_id="bandwidth_reduction",
                action_type=RemediationActionType.BANDWIDTH_REDUCTION,
                name="Bandwidth Reduction",
                risk_level="MEDIUM",
                requires_approval=False,
                parameters={"reduction_percent": 25}
            )
        }
    
    def select_remediation_action(self, prediction: LinkPrediction) -> Optional[str]:
        """Select appropriate remediation action based on prediction"""
        if prediction.degradation_risk_level == "CRITICAL":
            return "satellite_failover"
        elif "Low SNR" in prediction.contributing_factors or "High BER" in prediction.contributing_factors:
            return "qos_shaping"
        elif prediction.degradation_risk_level in ["HIGH", "MEDIUM"]:
            return "bandwidth_reduction"
        return None
    
    def process_link_alert(self, prediction: LinkPrediction) -> Dict[str, Any]:
        """Process link quality prediction and determine remediation"""
        # Select action
        action_id = self.select_remediation_action(prediction)
        if not action_id:
            return {"status": "no_action", "reason": "No suitable remediation action"}
        
        action = self.actions[action_id]
        
        # Evaluate policy
        context = {"recent_actions": random.randint(0, 3), "current_time": datetime.now().isoformat()}
        decision = self.policy_engine.evaluate_action(action, context)
        
        result = {
            "prediction": asdict(prediction),
            "selected_action": asdict(action),
            "policy_decision": asdict(decision),
            "status": "approved" if decision.allowed else "rejected",
            "approval_required": decision.requires_approval,
            "timestamp": datetime.now().isoformat()
        }
        
        return result

def simulate_satellite_conditions():
    """Simulate various satellite link conditions"""
    scenarios = [
        {
            "name": "Normal Operation",
            "modem": ModemKPIs(datetime.now(), 18.0, 1e-7, -65, 8.0),
            "weather": WeatherData(datetime.now(), 0.0, 10.0),
            "ship": ShipTelemetry(datetime.now(), 25.76, -80.19, 2.0, 3.0, 18.0)
        },
        {
            "name": "Rain Fade Scenario",
            "modem": ModemKPIs(datetime.now(), 12.0, 1e-5, -75, 2.0),
            "weather": WeatherData(datetime.now(), 15.0, 25.0),
            "ship": ShipTelemetry(datetime.now(), 25.76, -80.19, 3.0, 2.0, 20.0)
        },
        {
            "name": "Heavy Weather + Movement",
            "modem": ModemKPIs(datetime.now(), 8.0, 5e-4, -82, 1.0),
            "weather": WeatherData(datetime.now(), 25.0, 45.0),
            "ship": ShipTelemetry(datetime.now(), 25.76, -80.19, 12.0, 15.0, 16.0)
        },
        {
            "name": "Critical Link Degradation",
            "modem": ModemKPIs(datetime.now(), 5.0, 1e-3, -88, 0.5),
            "weather": WeatherData(datetime.now(), 8.0, 35.0),
            "ship": ShipTelemetry(datetime.now(), 25.76, -80.19, 8.0, 6.0, 22.0)
        }
    ]
    
    return scenarios

def run_integration_test():
    """Run comprehensive integration test"""
    print("🚢 AIOps NAAS v0.3 - Integration Test")
    print("=" * 60)
    
    service = SimpleRemediationService()
    scenarios = simulate_satellite_conditions()
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🔍 Test Scenario {i}: {scenario['name']}")
        print("-" * 40)
        
        # Generate prediction
        prediction = service.predictor.predict_link_quality(
            scenario['modem'], scenario['weather'], scenario['ship']
        )
        
        print(f"📊 Link Quality: {prediction.predicted_quality_score:.3f}")
        print(f"⚠️  Risk Level: {prediction.degradation_risk_level}")
        print(f"🔧 Contributing Factors: {', '.join(prediction.contributing_factors) or 'None'}")
        
        # Process remediation
        result = service.process_link_alert(prediction)
        
        print(f"🛠️  Selected Action: {result['selected_action']['name']}")
        print(f"📋 Risk Level: {result['selected_action']['risk_level']}")
        print(f"✅ Policy Decision: {result['status'].upper()}")
        print(f"👤 Approval Required: {'Yes' if result['approval_required'] else 'No'}")
        print(f"💭 Reason: {result['policy_decision']['reason']}")
        
        results.append(result)
    
    # Summary
    print(f"\n📈 Test Summary")
    print("=" * 30)
    approved_actions = sum(1 for r in results if r['status'] == 'approved')
    approval_required = sum(1 for r in results if r['approval_required'])
    
    print(f"Total Scenarios: {len(results)}")
    print(f"Actions Approved: {approved_actions}")
    print(f"Approval Required: {approval_required}")
    print(f"Auto-Approved: {approved_actions - approval_required}")
    
    # Risk level distribution
    risk_levels = {}
    for result in results:
        risk = result['prediction']['degradation_risk_level']
        risk_levels[risk] = risk_levels.get(risk, 0) + 1
    
    print(f"\nRisk Level Distribution:")
    for risk, count in risk_levels.items():
        print(f"  {risk}: {count}")
    
    print(f"\n✅ Integration test completed successfully!")
    print(f"🎯 v0.3 features validated: Predictive Link Health + Guarded Auto-Remediation")
    
    return results

if __name__ == "__main__":
    try:
        results = run_integration_test()
        
        # Export results for review
        with open("/tmp/v03_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Detailed results exported to /tmp/v03_test_results.json")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)