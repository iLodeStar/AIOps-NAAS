"""
Alert Manager for Drift Detection

Manages drift detection alerts and notifications.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DriftAlert:
    """Drift detection alert"""
    alert_id: str
    model_id: str
    drift_type: str
    severity: str
    confidence: float
    detected_at: datetime
    description: str

class AlertManager:
    """Manages drift detection alerts"""
    
    def __init__(self):
        self.active_alerts: Dict[str, DriftAlert] = {}
        self.alert_history: List[DriftAlert] = []
    
    def create_alert(
        self,
        model_id: str,
        drift_type: str,
        severity: str,
        confidence: float,
        description: str
    ) -> DriftAlert:
        """Create a new drift alert"""
        
        alert = DriftAlert(
            alert_id=f"drift_alert_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            model_id=model_id,
            drift_type=drift_type,
            severity=severity,
            confidence=confidence,
            detected_at=datetime.now(),
            description=description
        )
        
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"Drift alert created: {alert.description}")
        return alert
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            logger.info(f"Drift alert {alert_id} resolved")
    
    def get_active_alerts(self, model_id: str = None) -> List[DriftAlert]:
        """Get active alerts"""
        if model_id:
            return [alert for alert in self.active_alerts.values() if alert.model_id == model_id]
        return list(self.active_alerts.values())