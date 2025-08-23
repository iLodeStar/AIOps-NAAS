"""
Threshold Manager for Drift Detection

Manages adaptive thresholds for drift detection algorithms.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ThresholdManager:
    """Manages adaptive thresholds for drift detection"""
    
    def __init__(self):
        self.thresholds: Dict[str, float] = {}
        self.adaptation_history: List[Dict[str, Any]] = []
    
    def get_threshold(self, metric_name: str) -> float:
        """Get current threshold for a metric"""
        return self.thresholds.get(metric_name, 0.5)
    
    def update_threshold(self, metric_name: str, new_threshold: float):
        """Update threshold for a metric"""
        old_threshold = self.thresholds.get(metric_name, 0.5)
        self.thresholds[metric_name] = new_threshold
        
        self.adaptation_history.append({
            "metric": metric_name,
            "old_threshold": old_threshold,
            "new_threshold": new_threshold,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Updated {metric_name} threshold: {old_threshold} -> {new_threshold}")