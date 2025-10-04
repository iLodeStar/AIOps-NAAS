#!/usr/bin/env python3
"""
Ollama LLM Client for Incident Enrichment
Provides integration with Ollama API for generating AI insights
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama LLM integration"""
    
    def __init__(
        self,
        ollama_url: str = "http://ollama:11434",
        model: str = "phi3:mini",
        timeout: int = 10
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self.api_endpoint = f"{ollama_url}/api/generate"
        
    def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def generate_root_cause_analysis(
        self,
        incident_data: Dict[str, Any]
    ) -> Optional[str]:
        """Generate root cause analysis using LLM"""
        try:
            prompt = self._build_root_cause_prompt(incident_data)
            
            start_time = datetime.utcnow()
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('response', '').strip()
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(f"Root cause analysis generated in {duration_ms:.2f}ms")
                
                return analysis
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except requests.Timeout:
            logger.warning("Ollama request timeout")
            return None
        except Exception as e:
            logger.error(f"Error generating root cause: {e}")
            return None
    
    def generate_remediation_suggestions(
        self,
        incident_data: Dict[str, Any],
        root_cause: Optional[str] = None
    ) -> Optional[str]:
        """Generate remediation suggestions using LLM"""
        try:
            prompt = self._build_remediation_prompt(incident_data, root_cause)
            
            start_time = datetime.utcnow()
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                suggestions = result.get('response', '').strip()
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(f"Remediation suggestions generated in {duration_ms:.2f}ms")
                
                return suggestions
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except requests.Timeout:
            logger.warning("Ollama request timeout")
            return None
        except Exception as e:
            logger.error(f"Error generating remediation: {e}")
            return None
    
    def _build_root_cause_prompt(self, incident_data: Dict[str, Any]) -> str:
        """Build prompt for root cause analysis"""
        incident_type = incident_data.get('incident_type', 'unknown')
        severity = incident_data.get('severity', 'unknown')
        service = incident_data.get('service', 'unknown')
        metric_name = incident_data.get('metric_name', 'N/A')
        metric_value = incident_data.get('metric_value', 'N/A')
        scope = incident_data.get('scope', [])
        
        scope_str = ", ".join([f"{s.get('device_id', 'N/A')}/{s.get('service', 'N/A')}" for s in scope])
        
        prompt = f"""Analyze this maritime AIOps incident and provide a concise root cause analysis.

Incident Details:
- Type: {incident_type}
- Severity: {severity}
- Affected Service: {service}
- Metric: {metric_name} = {metric_value}
- Affected Scope: {scope_str}

Provide a brief root cause analysis (2-3 sentences) focusing on:
1. What is the most likely root cause
2. Why this issue occurred
3. What system component is affected

Keep the response concise and actionable."""
        
        return prompt
    
    def _build_remediation_prompt(
        self,
        incident_data: Dict[str, Any],
        root_cause: Optional[str]
    ) -> str:
        """Build prompt for remediation suggestions"""
        incident_type = incident_data.get('incident_type', 'unknown')
        severity = incident_data.get('severity', 'unknown')
        service = incident_data.get('service', 'unknown')
        
        root_cause_str = f"\n\nRoot Cause: {root_cause}" if root_cause else ""
        
        prompt = f"""Based on this maritime AIOps incident, suggest remediation actions.

Incident Details:
- Type: {incident_type}
- Severity: {severity}
- Affected Service: {service}{root_cause_str}

Provide 2-3 specific remediation steps that operators should take.
Focus on maritime-specific actions (satellite links, network equipment, ship operations).
Keep each step brief and actionable."""
        
        return prompt
