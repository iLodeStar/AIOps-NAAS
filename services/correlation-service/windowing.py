#!/usr/bin/env python3
"""
Time-Windowing Module for Correlation Service
Implements configurable time-window clustering for anomaly correlation
"""

import time
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from aiops_core.models import AnomalyEnriched, Domain
from aiops_core.utils import StructuredLogger

logger = StructuredLogger(__name__)


# Default time windows by domain (in seconds)
DEFAULT_TIME_WINDOWS = {
    Domain.COMMS: 300,      # 5 minutes for communication issues
    Domain.NET: 300,        # 5 minutes for network issues  
    Domain.SYSTEM: 600,     # 10 minutes for system issues
    Domain.APP: 1200,       # 20 minutes for application issues
    Domain.SECURITY: 600,   # 10 minutes for security issues
}

DEFAULT_WINDOW_SECONDS = 900  # 15 minutes default


class AnomalyWindow:
    """
    Represents a time window of correlated anomalies
    Groups anomalies by ship_id and domain for incident formation
    """
    
    def __init__(self, window_key: str, window_seconds: int):
        """
        Initialize anomaly window
        
        Args:
            window_key: Window identifier (ship_id:domain)
            window_seconds: Window duration in seconds
        """
        self.window_key = window_key
        self.window_seconds = window_seconds
        self.anomalies: List[Dict] = []
        self.created_at = time.time()
        self.last_updated = time.time()
        
    def add_anomaly(self, anomaly: AnomalyEnriched):
        """Add anomaly to window"""
        ts_unix = anomaly.ts.timestamp() if isinstance(anomaly.ts, datetime) else time.time()
        
        self.anomalies.append({
            "tracking_id": anomaly.tracking_id,
            "ts": anomaly.ts,
            "ts_unix": ts_unix,
            "severity": anomaly.severity,
            "anomaly_type": anomaly.anomaly_type,
            "detector": anomaly.detector,
            "score": anomaly.score,
            "service": anomaly.service,
            "device_id": anomaly.device_id,
            "metric_name": anomaly.metric_name,
            "metric_value": anomaly.metric_value,
            "raw_msg": anomaly.raw_msg,
            "context": anomaly.context,
            "tags": anomaly.tags,
            "meta": anomaly.meta
        })
        self.last_updated = time.time()
    
    def get_anomalies(self) -> List[Dict]:
        """Get all anomalies in window (returns a copy)"""
        return self.anomalies.copy()
    
    def get_count(self) -> int:
        """Get number of anomalies in window"""
        return len(self.anomalies)
    
    def clear(self):
        """Clear all anomalies from window"""
        self.anomalies.clear()
        self.last_updated = time.time()
    
    def is_expired(self, current_time: float) -> bool:
        """Check if window has expired"""
        age_seconds = current_time - self.created_at
        return age_seconds > self.window_seconds
    
    def get_age_seconds(self) -> float:
        """Get window age in seconds"""
        return time.time() - self.created_at


class TimeWindowManager:
    """
    Manages time-based windowing for anomaly correlation
    Configurable windows by domain (1-30 minutes)
    """
    
    def __init__(
        self,
        time_windows: Optional[Dict[Domain, int]] = None,
        default_window: int = DEFAULT_WINDOW_SECONDS,
        correlation_threshold: int = 3
    ):
        """
        Initialize time window manager
        
        Args:
            time_windows: Custom time windows by domain (seconds)
            default_window: Default window size if domain not specified
            correlation_threshold: Minimum anomalies to trigger incident
        """
        self.time_windows = time_windows or DEFAULT_TIME_WINDOWS
        self.default_window = default_window
        self.correlation_threshold = correlation_threshold
        
        self.windows: Dict[str, AnomalyWindow] = {}  # window_key -> AnomalyWindow
        
        self.stats = {
            "total_anomalies": 0,
            "windows_created": 0,
            "windows_triggered": 0,
            "windows_expired": 0,
            "cleanups_performed": 0
        }
    
    def _get_window_key(self, anomaly: AnomalyEnriched) -> str:
        """
        Generate window key for anomaly grouping
        
        Format: {ship_id}:{domain}
        This ensures anomalies are grouped by ship and domain
        """
        domain_str = anomaly.domain.value if hasattr(anomaly.domain, 'value') else str(anomaly.domain)
        return f"{anomaly.ship_id}:{domain_str}"
    
    def _get_window_duration(self, domain: Domain) -> int:
        """Get window duration for domain"""
        return self.time_windows.get(domain, self.default_window)
    
    def add_anomaly(self, anomaly: AnomalyEnriched) -> Optional[List[Dict]]:
        """
        Add anomaly to appropriate time window
        
        Args:
            anomaly: Enriched anomaly to add
            
        Returns:
            List of anomalies if window threshold reached, None otherwise
        """
        self.stats["total_anomalies"] += 1
        
        window_key = self._get_window_key(anomaly)
        window_duration = self._get_window_duration(anomaly.domain)
        
        # Get or create window
        if window_key not in self.windows:
            self.windows[window_key] = AnomalyWindow(window_key, window_duration)
            self.stats["windows_created"] += 1
            logger.debug(
                "Created new window",
                window_key=window_key,
                duration_seconds=window_duration
            )
        
        window = self.windows[window_key]
        window.add_anomaly(anomaly)
        
        logger.debug(
            "Anomaly added to window",
            window_key=window_key,
            count=window.get_count(),
            threshold=self.correlation_threshold,
            tracking_id=anomaly.tracking_id
        )
        
        # Check if window has reached correlation threshold
        if window.get_count() >= self.correlation_threshold:
            self.stats["windows_triggered"] += 1
            
            # Get anomalies and clear window
            anomalies = window.get_anomalies()
            window.clear()
            
            logger.info(
                "Window threshold reached",
                window_key=window_key,
                anomaly_count=len(anomalies),
                threshold=self.correlation_threshold
            )
            
            return anomalies
        
        return None
    
    def cleanup_expired_windows(self) -> int:
        """
        Remove expired windows that haven't reached threshold
        
        Returns:
            Number of windows removed
        """
        now = time.time()
        initial_count = len(self.windows)
        
        expired_keys = []
        for window_key, window in self.windows.items():
            if window.is_expired(now):
                expired_keys.append(window_key)
                
                # Log if window had anomalies but didn't reach threshold
                if window.get_count() > 0:
                    logger.info(
                        "Window expired without reaching threshold",
                        window_key=window_key,
                        anomaly_count=window.get_count(),
                        age_seconds=f"{window.get_age_seconds():.1f}"
                    )
        
        # Remove expired windows
        for key in expired_keys:
            del self.windows[key]
        
        removed = len(expired_keys)
        if removed > 0:
            self.stats["windows_expired"] += removed
            self.stats["cleanups_performed"] += 1
            logger.info(
                "Window cleanup completed",
                removed=removed,
                remaining=len(self.windows)
            )
        
        return removed
    
    def get_stats(self) -> Dict:
        """Get windowing statistics"""
        return {
            **self.stats,
            "active_windows": len(self.windows),
            "correlation_threshold": self.correlation_threshold,
            "default_window_seconds": self.default_window
        }
    
    def get_window_info(self) -> Dict[str, Dict]:
        """Get info about all active windows"""
        return {
            window_key: {
                "anomaly_count": window.get_count(),
                "age_seconds": window.get_age_seconds(),
                "window_seconds": window.window_seconds,
                "created_at": datetime.fromtimestamp(window.created_at).isoformat()
            }
            for window_key, window in self.windows.items()
        }
