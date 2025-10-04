#!/usr/bin/env python3
"""
ClickHouse Cache for LLM Responses
Provides caching layer to avoid redundant LLM calls
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from clickhouse_driver import Client as ClickHouseClient

logger = logging.getLogger(__name__)


class LLMCache:
    """ClickHouse-based cache for LLM responses"""
    
    def __init__(
        self,
        clickhouse_host: str = "clickhouse",
        clickhouse_port: int = 9000,
        clickhouse_user: str = "default",
        clickhouse_password: str = "clickhouse123",
        cache_ttl_hours: int = 24
    ):
        self.client = ClickHouseClient(
            host=clickhouse_host,
            port=clickhouse_port,
            user=clickhouse_user,
            password=clickhouse_password
        )
        self.cache_ttl_hours = cache_ttl_hours
        self.table_name = "llm_cache"
        
        # Ensure cache table exists
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create cache table if it doesn't exist"""
        try:
            create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                cache_key String,
                incident_type String,
                incident_id String,
                ship_id String,
                response_type String,
                response_text String,
                metadata String,
                created_at DateTime DEFAULT now(),
                expires_at DateTime
            ) ENGINE = MergeTree()
            ORDER BY (cache_key, created_at)
            TTL expires_at
            """
            
            self.client.execute(create_table_query)
            logger.info(f"Cache table '{self.table_name}' ready")
            
        except Exception as e:
            logger.error(f"Error creating cache table: {e}")
    
    def get_cached_response(
        self,
        incident_data: Dict[str, Any],
        response_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached LLM response
        
        Args:
            incident_data: Incident data to generate cache key from
            response_type: Type of response (root_cause, remediation, etc.)
        
        Returns:
            Cached response data or None if not found/expired
        """
        try:
            cache_key = self._generate_cache_key(incident_data, response_type)
            
            query = f"""
            SELECT 
                response_text,
                metadata,
                created_at,
                expires_at
            FROM {self.table_name}
            WHERE cache_key = %(cache_key)s
              AND expires_at > now()
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = self.client.execute(
                query,
                {'cache_key': cache_key}
            )
            
            if result:
                row = result[0]
                metadata = json.loads(row[1]) if row[1] else {}
                
                logger.info(f"Cache hit for {response_type}")
                
                return {
                    'response_text': row[0],
                    'metadata': metadata,
                    'cached_at': row[2],
                    'cache_hit': True
                }
            else:
                logger.debug(f"Cache miss for {response_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")
            return None
    
    def store_response(
        self,
        incident_data: Dict[str, Any],
        response_type: str,
        response_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store LLM response in cache
        
        Args:
            incident_data: Incident data to generate cache key from
            response_type: Type of response (root_cause, remediation, etc.)
            response_text: The LLM response to cache
            metadata: Additional metadata to store
        
        Returns:
            True if stored successfully
        """
        try:
            cache_key = self._generate_cache_key(incident_data, response_type)
            expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            
            metadata_json = json.dumps(metadata or {})
            
            insert_query = f"""
            INSERT INTO {self.table_name} 
            (cache_key, incident_type, incident_id, ship_id, response_type, 
             response_text, metadata, expires_at)
            VALUES
            """
            
            self.client.execute(
                insert_query,
                [{
                    'cache_key': cache_key,
                    'incident_type': incident_data.get('incident_type', 'unknown'),
                    'incident_id': incident_data.get('incident_id', 'unknown'),
                    'ship_id': incident_data.get('ship_id', 'unknown'),
                    'response_type': response_type,
                    'response_text': response_text,
                    'metadata': metadata_json,
                    'expires_at': expires_at
                }]
            )
            
            logger.info(f"Stored {response_type} response in cache (TTL: {self.cache_ttl_hours}h)")
            return True
            
        except Exception as e:
            logger.error(f"Error storing response in cache: {e}")
            return False
    
    def _generate_cache_key(
        self,
        incident_data: Dict[str, Any],
        response_type: str
    ) -> str:
        """
        Generate deterministic cache key from incident data
        
        Key includes incident type, severity, service to catch similar incidents
        """
        key_parts = [
            response_type,
            incident_data.get('incident_type', ''),
            incident_data.get('severity', ''),
            incident_data.get('service', ''),
            # Include metric name for more specificity
            str(incident_data.get('metric_name', '')),
        ]
        
        key_string = "|".join(str(part) for part in key_parts)
        
        # Generate hash for consistent key length
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"{response_type}_{key_hash[:16]}"
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            stats_query = f"""
            SELECT 
                response_type,
                count() as total_entries,
                countIf(expires_at > now()) as valid_entries,
                countIf(expires_at <= now()) as expired_entries
            FROM {self.table_name}
            GROUP BY response_type
            """
            
            results = self.client.execute(stats_query)
            
            stats = {
                'by_type': {}
            }
            
            total = 0
            valid = 0
            
            for row in results:
                response_type, total_entries, valid_entries, expired_entries = row
                stats['by_type'][response_type] = {
                    'total': total_entries,
                    'valid': valid_entries,
                    'expired': expired_entries
                }
                total += total_entries
                valid += valid_entries
            
            stats['total_entries'] = total
            stats['valid_entries'] = valid
            stats['hit_rate'] = round(valid / total * 100, 2) if total > 0 else 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def health_check(self) -> bool:
        """Check ClickHouse connectivity"""
        try:
            self.client.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False
