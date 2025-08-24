"""
Auto-Remediation Module for v1.0 Self-Learning Closed-Loop Automation

This module provides confidence-scored auto-remediation for known scenarios
with gradual policy coverage expansion.
"""

from .confidence_engine import ConfidenceEngine
from .policy_manager import PolicyManager
from .remediation_engine import RemediationEngine

__all__ = ['ConfidenceEngine', 'PolicyManager', 'RemediationEngine']