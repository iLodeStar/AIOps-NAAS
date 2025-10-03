#!/usr/bin/env python3
"""
ClickHouse queries for Fast Path L1 enrichment
Optimized for <500ms p99 latency
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from clickhouse_driver import Client as ClickHouseClient


class EnrichmentQueries:
    """ClickHouse query functions for anomaly enrichment"""
    
    def __init__(self, client: ClickHouseClient):
        self.client = client
    
    def get_device_metadata(self, ship_id: str, device_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Query device metadata from ClickHouse
        
        Args:
            ship_id: Ship identifier
            device_id: Device identifier (optional)
            
        Returns:
            Device metadata dict or None if not found
        """
        if not device_id:
            return None
            
        try:
            query = """
                SELECT 
                    device_type,
                    vendor,
                    model,
                    location,
                    criticality
                FROM devices 
                WHERE ship_id = %(ship_id)s 
                  AND device_id = %(device_id)s 
                LIMIT 1
            """
            
            result = self.client.execute(
                query,
                {"ship_id": ship_id, "device_id": device_id}
            )
            
            if result:
                return {
                    "device_type": result[0][0],
                    "vendor": result[0][1],
                    "model": result[0][2],
                    "location": result[0][3] if len(result[0]) > 3 else None,
                    "criticality": result[0][4] if len(result[0]) > 4 else None
                }
            
            return None
            
        except Exception as e:
            # Fail gracefully - enrichment should not block the pipeline
            return None
    
    def get_historical_failure_rates(self, ship_id: str, domain: str) -> Dict[str, Any]:
        """
        Query historical failure/anomaly rates for the last 24 hours
        
        Args:
            ship_id: Ship identifier
            domain: Domain (comms, app, net, security, system)
            
        Returns:
            Dict with failure rate statistics
        """
        try:
            query = """
                SELECT 
                    count() as total_anomalies,
                    countIf(severity = 'critical') as critical_count,
                    countIf(severity = 'high') as high_count,
                    countIf(severity = 'medium') as medium_count,
                    countIf(severity = 'low') as low_count,
                    avg(score) as avg_score
                FROM anomalies
                WHERE ship_id = %(ship_id)s
                  AND domain = %(domain)s
                  AND ts >= now() - INTERVAL 24 HOUR
            """
            
            result = self.client.execute(
                query,
                {"ship_id": ship_id, "domain": domain}
            )
            
            if result:
                row = result[0]
                return {
                    "total_anomalies_24h": row[0],
                    "critical_count_24h": row[1],
                    "high_count_24h": row[2],
                    "medium_count_24h": row[3],
                    "low_count_24h": row[4],
                    "avg_score_24h": float(row[5]) if row[5] else 0.0,
                    "failure_rate_per_hour": row[0] / 24.0 if row[0] else 0.0
                }
            
            return {
                "total_anomalies_24h": 0,
                "critical_count_24h": 0,
                "high_count_24h": 0,
                "medium_count_24h": 0,
                "low_count_24h": 0,
                "avg_score_24h": 0.0,
                "failure_rate_per_hour": 0.0
            }
            
        except Exception as e:
            # Return empty stats on error
            return {
                "total_anomalies_24h": 0,
                "failure_rate_per_hour": 0.0,
                "error": str(e)
            }
    
    def get_similar_anomalies(
        self, 
        ship_id: str, 
        domain: str,
        anomaly_type: str,
        metric_name: Optional[str] = None,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query similar anomalies from the last 7 days
        
        Args:
            ship_id: Ship identifier
            domain: Domain (comms, app, net, security, system)
            anomaly_type: Type of anomaly
            metric_name: Metric name (optional, for more specific matching)
            service: Service name (optional, for more specific matching)
            
        Returns:
            List of similar anomaly records
        """
        try:
            # Build query with optional filters
            conditions = [
                "ship_id = %(ship_id)s",
                "domain = %(domain)s",
                "anomaly_type = %(anomaly_type)s",
                "ts >= now() - INTERVAL 7 DAY"
            ]
            
            params = {
                "ship_id": ship_id,
                "domain": domain,
                "anomaly_type": anomaly_type
            }
            
            if metric_name:
                conditions.append("metric_name = %(metric_name)s")
                params["metric_name"] = metric_name
                
            if service:
                conditions.append("service = %(service)s")
                params["service"] = service
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT 
                    ts,
                    severity,
                    score,
                    detector,
                    service,
                    metric_name,
                    metric_value
                FROM anomalies
                WHERE {where_clause}
                ORDER BY ts DESC
                LIMIT 10
            """
            
            result = self.client.execute(query, params)
            
            similar_anomalies = []
            for row in result:
                similar_anomalies.append({
                    "timestamp": row[0].isoformat() if isinstance(row[0], datetime) else str(row[0]),
                    "severity": row[1],
                    "score": float(row[2]),
                    "detector": row[3],
                    "service": row[4],
                    "metric_name": row[5],
                    "metric_value": float(row[6]) if row[6] else None
                })
            
            return similar_anomalies
            
        except Exception as e:
            # Return empty list on error
            return []
    
    def get_recent_incidents(self, ship_id: str, domain: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query recent incidents related to this domain (last 24h)
        
        Args:
            ship_id: Ship identifier
            domain: Domain to filter by
            limit: Maximum number of incidents to return
            
        Returns:
            List of recent incident records
        """
        try:
            query = """
                SELECT 
                    incident_id,
                    incident_type,
                    severity,
                    status,
                    created_at
                FROM incidents
                WHERE ship_id = %(ship_id)s
                  AND incident_type = %(domain)s
                  AND created_at >= now() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
                LIMIT %(limit)s
            """
            
            result = self.client.execute(
                query,
                {"ship_id": ship_id, "domain": domain, "limit": limit}
            )
            
            incidents = []
            for row in result:
                incidents.append({
                    "incident_id": row[0],
                    "incident_type": row[1],
                    "severity": row[2],
                    "status": row[3],
                    "created_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4])
                })
            
            return incidents
            
        except Exception as e:
            return []
