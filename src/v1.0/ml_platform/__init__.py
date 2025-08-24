"""
ML Platform Module for v1.0 Self-Learning Closed-Loop Automation

Provides MLflow integration for model lifecycle management including:
- Model registry and versioning
- Periodic retraining pipelines
- Shadow deployments
- Model promotion workflows
"""

from .model_registry import ModelRegistry
from .retraining_pipeline import RetrainingPipeline
from .shadow_deployment import ShadowDeployment
from .promotion_manager import PromotionManager

__all__ = ['ModelRegistry', 'RetrainingPipeline', 'ShadowDeployment', 'PromotionManager']