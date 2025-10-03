#!/usr/bin/env python3
"""
Deduplication Module for Correlation Service
Implements fingerprint-based deduplication and suppression logic
"""

import time
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime
from aiops_core.models import AnomalyEnriched
from aiops_core.utils import StructuredLogger

logger = StructuredLogger(__name__)


class DeduplicationCache:
    """
    Fingerprint-based deduplication cache with TTL
    Tracks suppression keys to prevent duplicate incident creation
    """
    
    def __init__(self, ttl_seconds: int = 900):
        """
        Initialize deduplication cache
        
        Args:
            ttl_seconds: Time-to-live for suppression entries (default 15 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, float] = {}  # suppress_key -> last_seen_timestamp
        self.stats = {
            "total_checks": 0,
            "duplicates_found": 0,
            "unique_incidents": 0,
            "cache_cleanups": 0
        }
    
    def compute_fingerprint(self, anomaly: AnomalyEnriched) -> str:
        """
        Compute fingerprint for anomaly based on key attributes
        
        Uses MD5 hash for fingerprinting (not cryptographic security).
        MD5 is acceptable here as we're using it for deduplication,
        not security. Collision resistance is sufficient for this use case.
        
        Args:
            anomaly: Enriched anomaly event
            
        Returns:
            Fingerprint hash string (16 chars)
        """
        # Create fingerprint from: ship_id, domain, service, anomaly_type
        # This ensures similar anomalies are grouped together
        fingerprint_parts = [
            anomaly.ship_id,
            anomaly.domain.value if hasattr(anomaly.domain, 'value') else str(anomaly.domain),
            anomaly.service,
            anomaly.anomaly_type
        ]
        
        # Add device_id if present (for device-specific issues)
        if anomaly.device_id:
            fingerprint_parts.append(anomaly.device_id)
        
        # Create hash from fingerprint
        fingerprint_str = ":".join(fingerprint_parts)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
    
    def compute_suppress_key(self, anomaly: AnomalyEnriched) -> str:
        """
        Compute suppression key for deduplication
        
        Format: {fingerprint}:{severity}
        This allows different severities to create separate incidents
        
        Args:
            anomaly: Enriched anomaly event
            
        Returns:
            Suppression key string
        """
        fingerprint = self.compute_fingerprint(anomaly)
        severity = anomaly.severity.value if hasattr(anomaly.severity, 'value') else str(anomaly.severity)
        return f"{fingerprint}:{severity}"
    
    def should_suppress(self, anomaly: AnomalyEnriched) -> Tuple[bool, str]:
        """
        Check if anomaly should be suppressed (duplicate)
        
        Args:
            anomaly: Enriched anomaly event
            
        Returns:
            Tuple of (should_suppress: bool, suppress_key: str)
        """
        self.stats["total_checks"] += 1
        
        suppress_key = self.compute_suppress_key(anomaly)
        now = time.time()
        
        # Check if we've seen this recently
        if suppress_key in self.cache:
            last_seen = self.cache[suppress_key]
            age_seconds = now - last_seen
            
            if age_seconds < self.ttl_seconds:
                # Still within TTL - suppress this duplicate
                self.stats["duplicates_found"] += 1
                logger.debug(
                    "Duplicate suppressed",
                    suppress_key=suppress_key,
                    age_seconds=f"{age_seconds:.1f}",
                    tracking_id=anomaly.tracking_id
                )
                return True, suppress_key
        
        # Not a duplicate - record this as seen
        self.cache[suppress_key] = now
        self.stats["unique_incidents"] += 1
        
        logger.debug(
            "Unique anomaly",
            suppress_key=suppress_key,
            tracking_id=anomaly.tracking_id
        )
        
        return False, suppress_key
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        initial_size = len(self.cache)
        
        # Remove entries older than TTL
        self.cache = {
            key: timestamp
            for key, timestamp in self.cache.items()
            if (now - timestamp) < self.ttl_seconds
        }
        
        removed = initial_size - len(self.cache)
        if removed > 0:
            self.stats["cache_cleanups"] += 1
            logger.info(
                "Cache cleanup completed",
                removed=removed,
                remaining=len(self.cache)
            )
        
        return removed
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics"""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "ttl_seconds": self.ttl_seconds
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "total_checks": 0,
            "duplicates_found": 0,
            "unique_incidents": 0,
            "cache_cleanups": 0
        }
