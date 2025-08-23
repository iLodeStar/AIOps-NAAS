"""
Change Management Module for v1.0 Self-Learning Closed-Loop Automation

Provides change window management, approval workflows, and automated scheduling.
"""

from .change_window import ChangeWindowManager
from .approval_workflow import ApprovalWorkflowEngine

__all__ = ['ChangeWindowManager', 'ApprovalWorkflowEngine']