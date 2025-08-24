"""
Drift Detector for Model and System Behavior Monitoring

Implements multiple drift detection algorithms including:
- ADWIN (Adaptive Windowing)
- Page-Hinkley Test
- Kolmogorov-Smirnov Test
- Statistical drift detection
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json

# Handle numpy dependency
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Simple numpy fallbacks
    class np:
        @staticmethod
        def mean(data):
            return sum(data) / len(data) if data else 0
        
        @staticmethod
        def var(data):
            if not data:
                return 0
            mean_val = sum(data) / len(data)
            return sum((x - mean_val) ** 2 for x in data) / len(data)
        
        @staticmethod
        def std(data):
            return np.var(data) ** 0.5
        
        @staticmethod
        def sqrt(x):
            return x ** 0.5
        
        @staticmethod
        def log(x):
            import math
            return math.log(x)
        
        @staticmethod
        def max(a, b):
            return max(a, b)
        
        @staticmethod
        def abs(x):
            return abs(x)

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift that can be detected"""
    CONCEPT_DRIFT = "concept_drift"      # Changes in target relationships
    DATA_DRIFT = "data_drift"            # Changes in input data distribution
    PERFORMANCE_DRIFT = "performance_drift"  # Changes in model performance
    BEHAVIORAL_DRIFT = "behavioral_drift"    # Changes in system behavior patterns


@dataclass
class DriftAlert:
    """Represents a drift detection alert"""
    alert_id: str
    model_id: str
    drift_type: DriftType
    severity: str  # low, medium, high, critical
    confidence: float
    detected_at: datetime
    description: str
    affected_features: List[str]
    metrics: Dict[str, float]
    recommendations: List[str]


class ADWINDetector:
    """Adaptive Windowing (ADWIN) drift detector"""
    
    def __init__(self, delta: float = 0.002):
        self.delta = delta  # Confidence parameter
        self.window = []
        self.total_sum = 0
        self.variance_sum = 0
        
    def add_element(self, value: float) -> bool:
        """Add new element and check for drift"""
        self.window.append(value)
        self.total_sum += value
        
        if len(self.window) < 2:
            return False
            
        # Check for drift using ADWIN algorithm
        return self._detect_drift()
    
    def _detect_drift(self) -> bool:
        """Internal drift detection logic"""
        n = len(self.window)
        if n < 10:  # Minimum window size
            return False
            
        # Calculate current mean
        current_mean = self.total_sum / n
        
        # Check different window cuts
        for i in range(1, n):
            w1_sum = sum(self.window[:i])
            w2_sum = sum(self.window[i:])
            
            w1_mean = w1_sum / i
            w2_mean = w2_sum / (n - i)
            
            # Calculate variance estimates
            w1_var = np.var(self.window[:i]) if i > 1 else 0
            w2_var = np.var(self.window[i:]) if (n - i) > 1 else 0
            
            # ADWIN threshold calculation
            m = 1.0 / i + 1.0 / (n - i)
            threshold = np.sqrt((2.0 * max(w1_var, w2_var) * np.log(2.0/self.delta) * m))
            
            if abs(w1_mean - w2_mean) > threshold:
                # Drift detected - keep recent window
                self.window = self.window[i:]
                self.total_sum = w2_sum
                return True
                
        return False


class PageHinkleyDetector:
    """Page-Hinkley Test drift detector"""
    
    def __init__(self, threshold: float = 50, alpha: float = 0.9999):
        self.threshold = threshold
        self.alpha = alpha
        self.sum_pos = 0
        self.sum_neg = 0
        self.sum_x = 0
        self.n = 0
        
    def add_element(self, value: float) -> bool:
        """Add new element and check for drift"""
        self.n += 1
        self.sum_x += value
        
        if self.n == 1:
            self.x_mean = value
            return False
            
        # Update mean incrementally
        self.x_mean = self.sum_x / self.n
        
        # Page-Hinkley statistics
        self.sum_pos = max(0, self.alpha * self.sum_pos + (value - self.x_mean))
        self.sum_neg = min(0, self.alpha * self.sum_neg + (value - self.x_mean))
        
        # Check for drift
        return abs(self.sum_pos) > self.threshold or abs(self.sum_neg) > self.threshold


class KSTestDetector:
    """Kolmogorov-Smirnov Test drift detector"""
    
    def __init__(self, reference_window_size: int = 1000, detection_window_size: int = 100):
        self.reference_window_size = reference_window_size
        self.detection_window_size = detection_window_size
        self.reference_window = []
        self.detection_window = []
        
    def add_element(self, value: float) -> bool:
        """Add new element and check for drift"""
        # Maintain reference window
        self.reference_window.append(value)
        if len(self.reference_window) > self.reference_window_size:
            self.reference_window.pop(0)
            
        # Maintain detection window
        self.detection_window.append(value)
        if len(self.detection_window) > self.detection_window_size:
            self.detection_window.pop(0)
            
        # Check for drift when detection window is full
        if len(self.detection_window) == self.detection_window_size and \
           len(self.reference_window) >= self.detection_window_size * 2:
            return self._ks_test()
            
        return False
    
    def _ks_test(self) -> bool:
        """Perform Kolmogorov-Smirnov test"""
        try:
            from scipy import stats
            
            # Perform KS test
            statistic, p_value = stats.ks_2samp(self.reference_window, self.detection_window)
            
            # Drift detected if p-value is low (distributions are different)
            return p_value < 0.05
            
        except ImportError:
            logger.warning("scipy not available, using simplified KS test")
            return self._simple_ks_test()
    
    def _simple_ks_test(self) -> bool:
        """Simplified KS test without scipy"""
        ref_mean = np.mean(self.reference_window)
        det_mean = np.mean(self.detection_window)
        ref_std = np.std(self.reference_window)
        
        # Simple threshold-based test
        threshold = 2.0 * ref_std / np.sqrt(len(self.detection_window))
        return abs(ref_mean - det_mean) > threshold


class DriftDetector:
    """
    Main drift detection orchestrator
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.detectors: Dict[str, Dict[str, Any]] = {}
        self.drift_history: List[DriftAlert] = []
        self.model_performance_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Default configuration
        self.config = {
            'adwin_delta': 0.002,
            'ph_threshold': 50,
            'ph_alpha': 0.9999,
            'ks_reference_size': 1000,
            'ks_detection_size': 100,
            'performance_window': 50,
            'behavioral_window': 100
        }
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config.get('drift_detection', {}))
            logger.info("Drift detection configuration loaded")
        except Exception as e:
            logger.error(f"Failed to load drift config: {e}")
    
    def register_model(self, model_id: str, drift_methods: List[str] = None):
        """Register a model for drift monitoring"""
        if drift_methods is None:
            drift_methods = ['adwin', 'page_hinkley', 'ks_test']
        
        self.detectors[model_id] = {}
        
        for method in drift_methods:
            if method == 'adwin':
                self.detectors[model_id]['adwin'] = ADWINDetector(
                    delta=self.config['adwin_delta']
                )
            elif method == 'page_hinkley':
                self.detectors[model_id]['page_hinkley'] = PageHinkleyDetector(
                    threshold=self.config['ph_threshold'],
                    alpha=self.config['ph_alpha']
                )
            elif method == 'ks_test':
                self.detectors[model_id]['ks_test'] = KSTestDetector(
                    reference_window_size=self.config['ks_reference_size'],
                    detection_window_size=self.config['ks_detection_size']
                )
        
        self.model_performance_history[model_id] = []
        logger.info(f"Registered model {model_id} for drift monitoring")
    
    def add_prediction_sample(
        self,
        model_id: str,
        prediction: float,
        actual: Optional[float] = None,
        features: Optional[Dict[str, float]] = None
    ) -> List[DriftAlert]:
        """
        Add a prediction sample and check for drift
        
        Args:
            model_id: ID of the model
            prediction: Model prediction
            actual: Actual value (if available)
            features: Feature values used for prediction
            
        Returns:
            List of drift alerts if any drift is detected
        """
        alerts = []
        
        if model_id not in self.detectors:
            logger.warning(f"Model {model_id} not registered for drift monitoring")
            return alerts
        
        # Check concept drift using prediction error
        if actual is not None:
            error = abs(prediction - actual)
            alerts.extend(self._check_concept_drift(model_id, error))
            
            # Track performance over time
            self.model_performance_history[model_id].append(
                (datetime.now(), error)
            )
            
            # Maintain window size
            if len(self.model_performance_history[model_id]) > self.config['performance_window']:
                self.model_performance_history[model_id].pop(0)
        
        # Check data drift using feature values
        if features:
            alerts.extend(self._check_data_drift(model_id, features))
        
        # Check performance drift
        alerts.extend(self._check_performance_drift(model_id))
        
        return alerts
    
    def _check_concept_drift(self, model_id: str, error: float) -> List[DriftAlert]:
        """Check for concept drift using prediction error"""
        alerts = []
        
        for detector_name, detector in self.detectors[model_id].items():
            if hasattr(detector, 'add_element') and detector.add_element(error):
                alert = DriftAlert(
                    alert_id=f"drift_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    model_id=model_id,
                    drift_type=DriftType.CONCEPT_DRIFT,
                    severity=self._calculate_drift_severity(detector_name, error),
                    confidence=0.8,  # Would be calculated based on detector specifics
                    detected_at=datetime.now(),
                    description=f"Concept drift detected in {model_id} using {detector_name}",
                    affected_features=["prediction_error"],
                    metrics={"current_error": error, "detector": detector_name},
                    recommendations=[
                        "Consider model retraining",
                        "Review recent data for quality issues",
                        "Check for environmental changes"
                    ]
                )
                
                alerts.append(alert)
                self.drift_history.append(alert)
                
                logger.warning(f"Concept drift detected in {model_id} using {detector_name}")
        
        return alerts
    
    def _check_data_drift(self, model_id: str, features: Dict[str, float]) -> List[DriftAlert]:
        """Check for data drift in feature distributions"""
        # This would be implemented with more sophisticated feature drift detection
        # For now, return empty list as placeholder
        return []
    
    def _check_performance_drift(self, model_id: str) -> List[DriftAlert]:
        """Check for performance drift over time"""
        if model_id not in self.model_performance_history:
            return []
        
        history = self.model_performance_history[model_id]
        
        if len(history) < 20:  # Need sufficient history
            return []
        
        # Split into recent and older windows
        split_point = len(history) // 2
        older_errors = [error for _, error in history[:split_point]]
        recent_errors = [error for _, error in history[split_point:]]
        
        older_mean = np.mean(older_errors)
        recent_mean = np.mean(recent_errors)
        
        # Check if recent performance is significantly worse
        if recent_mean > older_mean * 1.5:  # 50% degradation threshold
            alert = DriftAlert(
                alert_id=f"perf_drift_{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                model_id=model_id,
                drift_type=DriftType.PERFORMANCE_DRIFT,
                severity="medium",
                confidence=0.7,
                detected_at=datetime.now(),
                description=f"Performance drift detected in {model_id}",
                affected_features=["model_accuracy"],
                metrics={
                    "older_mean_error": older_mean,
                    "recent_mean_error": recent_mean,
                    "degradation_ratio": recent_mean / older_mean
                },
                recommendations=[
                    "Model retraining recommended",
                    "Review feature engineering",
                    "Check data quality"
                ]
            )
            
            self.drift_history.append(alert)
            logger.warning(f"Performance drift detected in {model_id}")
            return [alert]
        
        return []
    
    def _calculate_drift_severity(self, detector_name: str, metric_value: float) -> str:
        """Calculate severity based on detector type and metric"""
        # Simple severity calculation - would be more sophisticated in practice
        if metric_value > 0.8:
            return "critical"
        elif metric_value > 0.6:
            return "high"
        elif metric_value > 0.4:
            return "medium"
        else:
            return "low"
    
    def get_drift_summary(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of drift detection status"""
        
        if model_id:
            alerts = [alert for alert in self.drift_history if alert.model_id == model_id]
        else:
            alerts = self.drift_history
        
        # Count alerts by type and severity
        drift_counts = {}
        severity_counts = {}
        
        for alert in alerts[-100:]:  # Last 100 alerts
            drift_type = alert.drift_type.value
            drift_counts[drift_type] = drift_counts.get(drift_type, 0) + 1
            
            severity = alert.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_alerts': len(alerts),
            'recent_alerts': len([a for a in alerts if 
                (datetime.now() - a.detected_at).days <= 7]),
            'drift_type_counts': drift_counts,
            'severity_counts': severity_counts,
            'models_monitored': list(self.detectors.keys()),
            'last_alert': alerts[-1].detected_at.isoformat() if alerts else None
        }