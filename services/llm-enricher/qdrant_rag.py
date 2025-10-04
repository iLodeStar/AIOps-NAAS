#!/usr/bin/env python3
"""
Qdrant RAG Client for Similar Incident Retrieval
Provides vector similarity search for finding related incidents
"""

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class QdrantRAGClient:
    """Client for Qdrant vector database RAG search"""
    
    def __init__(
        self,
        qdrant_url: str = "http://qdrant:6333",
        collection_name: str = "incidents",
        timeout: int = 5
    ):
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.timeout = timeout
        self.api_base = f"{qdrant_url}/collections"
        
    def health_check(self) -> bool:
        """Check if Qdrant service is available"""
        try:
            response = requests.get(
                f"{self.qdrant_url}/collections",
                timeout=3
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False
    
    def ensure_collection_exists(self) -> bool:
        """Ensure the incidents collection exists"""
        try:
            # Check if collection exists
            response = requests.get(
                f"{self.api_base}/{self.collection_name}",
                timeout=3
            )
            
            if response.status_code == 200:
                logger.info(f"Collection '{self.collection_name}' exists")
                return True
            
            # Create collection if it doesn't exist
            logger.info(f"Creating collection '{self.collection_name}'")
            create_response = requests.put(
                f"{self.api_base}/{self.collection_name}",
                json={
                    "vectors": {
                        "size": 384,  # Default embedding size for simple models
                        "distance": "Cosine"
                    }
                },
                timeout=5
            )
            
            if create_response.status_code in [200, 201]:
                logger.info(f"Collection '{self.collection_name}' created successfully")
                return True
            else:
                logger.error(f"Failed to create collection: {create_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            return False
    
    def search_similar_incidents(
        self,
        incident_data: Dict[str, Any],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar incidents using vector similarity
        
        For now, uses a simple text-based embedding approach.
        In production, would use a proper embedding model.
        """
        try:
            # Generate simple embedding from incident data
            embedding = self._generate_simple_embedding(incident_data)
            
            # Search for similar vectors
            search_response = requests.post(
                f"{self.api_base}/{self.collection_name}/points/search",
                json={
                    "vector": embedding,
                    "limit": limit,
                    "with_payload": True
                },
                timeout=self.timeout
            )
            
            if search_response.status_code == 200:
                results = search_response.json().get('result', [])
                
                # Format results
                similar_incidents = []
                for result in results:
                    payload = result.get('payload', {})
                    similar_incidents.append({
                        'incident_id': payload.get('incident_id', 'unknown'),
                        'incident_type': payload.get('incident_type', 'unknown'),
                        'severity': payload.get('severity', 'unknown'),
                        'timestamp': payload.get('timestamp', ''),
                        'similarity_score': result.get('score', 0.0),
                        'resolution': payload.get('resolution', 'N/A')
                    })
                
                logger.info(f"Found {len(similar_incidents)} similar incidents")
                return similar_incidents
            else:
                logger.warning(f"Qdrant search returned status {search_response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching similar incidents: {e}")
            return []
    
    def store_incident_vector(
        self,
        incident_id: str,
        incident_data: Dict[str, Any]
    ) -> bool:
        """Store incident vector in Qdrant for future similarity searches"""
        try:
            embedding = self._generate_simple_embedding(incident_data)
            
            # Use incident_id hash as point ID
            point_id = self._hash_to_int(incident_id)
            
            # Store the point
            response = requests.put(
                f"{self.api_base}/{self.collection_name}/points",
                json={
                    "points": [
                        {
                            "id": point_id,
                            "vector": embedding,
                            "payload": {
                                "incident_id": incident_id,
                                "incident_type": incident_data.get('incident_type', 'unknown'),
                                "severity": incident_data.get('severity', 'unknown'),
                                "service": incident_data.get('service', 'unknown'),
                                "timestamp": incident_data.get('created_at', datetime.utcnow().isoformat()),
                                "ship_id": incident_data.get('ship_id', 'unknown')
                            }
                        }
                    ]
                },
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Stored incident vector for {incident_id}")
                return True
            else:
                logger.warning(f"Failed to store vector: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing incident vector: {e}")
            return False
    
    def _generate_simple_embedding(self, incident_data: Dict[str, Any]) -> List[float]:
        """
        Generate a simple embedding from incident data
        
        This is a placeholder implementation. In production, would use:
        - sentence-transformers
        - OpenAI embeddings
        - Custom maritime domain embedding model
        """
        # Create a text representation
        text_parts = [
            incident_data.get('incident_type', ''),
            incident_data.get('severity', ''),
            incident_data.get('service', ''),
            str(incident_data.get('metric_name', '')),
        ]
        
        text = " ".join(str(part) for part in text_parts if part)
        
        # Generate pseudo-random but deterministic embedding
        # In production, replace with actual embedding model
        embedding = []
        for i in range(384):
            seed = hashlib.md5(f"{text}_{i}".encode()).hexdigest()
            value = int(seed[:8], 16) / (16**8) * 2 - 1  # Scale to [-1, 1]
            embedding.append(value)
        
        return embedding
    
    def _hash_to_int(self, text: str) -> int:
        """Convert text to deterministic integer ID"""
        hash_obj = hashlib.md5(text.encode())
        # Use first 8 bytes and convert to int
        return int(hash_obj.hexdigest()[:16], 16) % (2**63)
