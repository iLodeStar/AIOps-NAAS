"""
Model Registry Integration with MLflow

Manages model versions, metadata, and lifecycle stages.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    logger.warning("MLflow not available, using mock implementation")
    MLFLOW_AVAILABLE = False


class ModelStage(Enum):
    """MLflow model stages"""
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"
    NONE = "None"


@dataclass
class ModelVersion:
    """Represents a model version"""
    name: str
    version: str
    stage: ModelStage
    creation_timestamp: datetime
    last_updated_timestamp: datetime
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    run_id: Optional[str] = None
    source: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None


@dataclass
class ModelMetadata:
    """Metadata for registered models"""
    name: str
    description: Optional[str]
    creation_timestamp: datetime
    last_updated_timestamp: datetime
    latest_versions: List[ModelVersion]
    tags: Optional[Dict[str, str]] = None


class ModelRegistry:
    """
    MLflow Model Registry integration for model lifecycle management
    """
    
    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5000"):
        self.tracking_uri = mlflow_tracking_uri
        
        if MLFLOW_AVAILABLE:
            mlflow.set_tracking_uri(self.tracking_uri)
            self.client = MlflowClient()
        else:
            self.client = None
            # Mock storage for when MLflow is not available
            self.mock_models: Dict[str, ModelMetadata] = {}
            self.mock_versions: Dict[str, List[ModelVersion]] = {}
    
    def register_model(
        self,
        model_name: str,
        model_uri: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ModelVersion:
        """
        Register a new model or create a new version of existing model
        
        Args:
            model_name: Name of the model
            model_uri: URI of the model artifacts
            description: Model description
            tags: Model tags
            
        Returns:
            ModelVersion object
        """
        
        if MLFLOW_AVAILABLE and self.client:
            return self._register_model_mlflow(model_name, model_uri, description, tags)
        else:
            return self._register_model_mock(model_name, model_uri, description, tags)
    
    def _register_model_mlflow(
        self,
        model_name: str,
        model_uri: str,
        description: Optional[str],
        tags: Optional[Dict[str, str]]
    ) -> ModelVersion:
        """Register model using MLflow"""
        
        try:
            # Register the model
            registered_model = mlflow.register_model(
                model_uri=model_uri,
                name=model_name,
                tags=tags
            )
            
            # Update description if provided
            if description:
                self.client.update_registered_model(
                    name=model_name,
                    description=description
                )
            
            # Get the latest version
            latest_version = self.client.get_latest_versions(
                name=model_name, 
                stages=["None"]
            )[0]
            
            return ModelVersion(
                name=model_name,
                version=latest_version.version,
                stage=ModelStage.NONE,
                creation_timestamp=datetime.fromtimestamp(
                    int(latest_version.creation_timestamp) / 1000
                ),
                last_updated_timestamp=datetime.fromtimestamp(
                    int(latest_version.last_updated_timestamp) / 1000
                ),
                description=description,
                tags=tags,
                run_id=latest_version.run_id,
                source=latest_version.source
            )
            
        except Exception as e:
            logger.error(f"Failed to register model {model_name}: {e}")
            raise
    
    def _register_model_mock(
        self,
        model_name: str,
        model_uri: str,
        description: Optional[str],
        tags: Optional[Dict[str, str]]
    ) -> ModelVersion:
        """Mock model registration for testing"""
        
        now = datetime.now()
        
        # Get next version number
        if model_name in self.mock_versions:
            version = str(len(self.mock_versions[model_name]) + 1)
        else:
            version = "1"
            self.mock_versions[model_name] = []
        
        model_version = ModelVersion(
            name=model_name,
            version=version,
            stage=ModelStage.NONE,
            creation_timestamp=now,
            last_updated_timestamp=now,
            description=description,
            tags=tags,
            run_id=f"mock_run_{model_name}_{version}",
            source=model_uri
        )
        
        # Store mock version
        self.mock_versions[model_name].append(model_version)
        
        # Update or create mock model metadata
        if model_name not in self.mock_models:
            self.mock_models[model_name] = ModelMetadata(
                name=model_name,
                description=description,
                creation_timestamp=now,
                last_updated_timestamp=now,
                latest_versions=[model_version],
                tags=tags
            )
        else:
            self.mock_models[model_name].latest_versions.append(model_version)
            self.mock_models[model_name].last_updated_timestamp = now
        
        logger.info(f"Mock registered model {model_name} version {version}")
        return model_version
    
    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: ModelStage,
        archive_existing_versions: bool = True
    ) -> bool:
        """
        Transition model to a different stage
        
        Args:
            model_name: Name of the model
            version: Version to transition
            stage: Target stage
            archive_existing_versions: Whether to archive existing versions in target stage
            
        Returns:
            Success status
        """
        
        if MLFLOW_AVAILABLE and self.client:
            return self._transition_model_stage_mlflow(
                model_name, version, stage, archive_existing_versions
            )
        else:
            return self._transition_model_stage_mock(
                model_name, version, stage, archive_existing_versions
            )
    
    def _transition_model_stage_mlflow(
        self,
        model_name: str,
        version: str,
        stage: ModelStage,
        archive_existing_versions: bool
    ) -> bool:
        """Transition model stage using MLflow"""
        
        try:
            # Archive existing versions in target stage if requested
            if archive_existing_versions and stage != ModelStage.NONE:
                existing_versions = self.client.get_latest_versions(
                    name=model_name,
                    stages=[stage.value]
                )
                
                for existing_version in existing_versions:
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=existing_version.version,
                        stage=ModelStage.ARCHIVED.value
                    )
                    logger.info(
                        f"Archived {model_name} v{existing_version.version}"
                    )
            
            # Transition the target version
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage.value
            )
            
            logger.info(f"Transitioned {model_name} v{version} to {stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition model stage: {e}")
            return False
    
    def _transition_model_stage_mock(
        self,
        model_name: str,
        version: str,
        stage: ModelStage,
        archive_existing_versions: bool
    ) -> bool:
        """Mock model stage transition"""
        
        if model_name not in self.mock_versions:
            logger.error(f"Model {model_name} not found")
            return False
        
        # Find the version to transition
        target_version = None
        for model_version in self.mock_versions[model_name]:
            if model_version.version == version:
                target_version = model_version
                break
        
        if not target_version:
            logger.error(f"Version {version} of model {model_name} not found")
            return False
        
        # Archive existing versions if requested
        if archive_existing_versions and stage != ModelStage.NONE:
            for model_version in self.mock_versions[model_name]:
                if model_version.stage == stage and model_version.version != version:
                    model_version.stage = ModelStage.ARCHIVED
                    logger.info(f"Archived {model_name} v{model_version.version}")
        
        # Transition the target version
        target_version.stage = stage
        target_version.last_updated_timestamp = datetime.now()
        
        logger.info(f"Mock transitioned {model_name} v{version} to {stage.value}")
        return True
    
    def get_model_versions(
        self,
        model_name: str,
        stages: Optional[List[ModelStage]] = None
    ) -> List[ModelVersion]:
        """
        Get model versions, optionally filtered by stage
        
        Args:
            model_name: Name of the model
            stages: List of stages to filter by
            
        Returns:
            List of ModelVersion objects
        """
        
        if MLFLOW_AVAILABLE and self.client:
            return self._get_model_versions_mlflow(model_name, stages)
        else:
            return self._get_model_versions_mock(model_name, stages)
    
    def _get_model_versions_mlflow(
        self,
        model_name: str,
        stages: Optional[List[ModelStage]]
    ) -> List[ModelVersion]:
        """Get model versions using MLflow"""
        
        try:
            if stages:
                stage_names = [stage.value for stage in stages]
                mlflow_versions = self.client.get_latest_versions(
                    name=model_name,
                    stages=stage_names
                )
            else:
                # Get all versions
                registered_model = self.client.get_registered_model(model_name)
                mlflow_versions = registered_model.latest_versions
            
            versions = []
            for mlflow_version in mlflow_versions:
                version = ModelVersion(
                    name=model_name,
                    version=mlflow_version.version,
                    stage=ModelStage(mlflow_version.current_stage),
                    creation_timestamp=datetime.fromtimestamp(
                        int(mlflow_version.creation_timestamp) / 1000
                    ),
                    last_updated_timestamp=datetime.fromtimestamp(
                        int(mlflow_version.last_updated_timestamp) / 1000
                    ),
                    description=mlflow_version.description,
                    tags=mlflow_version.tags,
                    run_id=mlflow_version.run_id,
                    source=mlflow_version.source
                )
                versions.append(version)
            
            return versions
            
        except Exception as e:
            logger.error(f"Failed to get model versions for {model_name}: {e}")
            return []
    
    def _get_model_versions_mock(
        self,
        model_name: str,
        stages: Optional[List[ModelStage]]
    ) -> List[ModelVersion]:
        """Get model versions from mock storage"""
        
        if model_name not in self.mock_versions:
            return []
        
        versions = self.mock_versions[model_name]
        
        if stages:
            versions = [v for v in versions if v.stage in stages]
        
        return versions
    
    def add_model_tags(
        self,
        model_name: str,
        version: str,
        tags: Dict[str, str]
    ) -> bool:
        """Add tags to a model version"""
        
        if MLFLOW_AVAILABLE and self.client:
            try:
                for key, value in tags.items():
                    self.client.set_model_version_tag(
                        name=model_name,
                        version=version,
                        key=key,
                        value=value
                    )
                return True
            except Exception as e:
                logger.error(f"Failed to add tags to {model_name} v{version}: {e}")
                return False
        else:
            # Mock implementation
            if model_name in self.mock_versions:
                for model_version in self.mock_versions[model_name]:
                    if model_version.version == version:
                        if model_version.tags is None:
                            model_version.tags = {}
                        model_version.tags.update(tags)
                        return True
            return False
    
    def get_model_metadata(self, model_name: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        
        if MLFLOW_AVAILABLE and self.client:
            try:
                registered_model = self.client.get_registered_model(model_name)
                
                # Get latest versions
                latest_versions = []
                for stage in ModelStage:
                    try:
                        versions = self.client.get_latest_versions(
                            name=model_name,
                            stages=[stage.value]
                        )
                        for version in versions:
                            latest_versions.append(ModelVersion(
                                name=model_name,
                                version=version.version,
                                stage=ModelStage(version.current_stage),
                                creation_timestamp=datetime.fromtimestamp(
                                    int(version.creation_timestamp) / 1000
                                ),
                                last_updated_timestamp=datetime.fromtimestamp(
                                    int(version.last_updated_timestamp) / 1000
                                ),
                                description=version.description,
                                tags=version.tags,
                                run_id=version.run_id,
                                source=version.source
                            ))
                    except:
                        pass  # No versions in this stage
                
                return ModelMetadata(
                    name=model_name,
                    description=registered_model.description,
                    creation_timestamp=datetime.fromtimestamp(
                        int(registered_model.creation_timestamp) / 1000
                    ),
                    last_updated_timestamp=datetime.fromtimestamp(
                        int(registered_model.last_updated_timestamp) / 1000
                    ),
                    latest_versions=latest_versions,
                    tags=registered_model.tags
                )
                
            except Exception as e:
                logger.error(f"Failed to get metadata for model {model_name}: {e}")
                return None
        else:
            return self.mock_models.get(model_name)