#!/usr/bin/env python3
"""
Data Field Enhancement Script

This script analyzes and enhances incident data fields by extracting
missing information from various sources in the pipeline. It can be used
to improve data quality and reduce unknown/fallback values.

Usage:
    python3 scripts/enhance_incident_data.py --analyze
    python3 scripts/enhance_incident_data.py --fix-recent --dry-run
    python3 scripts/enhance_incident_data.py --backfill-data
"""

import json
import re
import subprocess
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

class IncidentDataEnhancer:
    def __init__(self):
        self.clickhouse_creds = self._get_clickhouse_creds()
        
    def _get_clickhouse_creds(self) -> Optional[Dict[str, str]]:
        """Get working ClickHouse credentials"""
        credentials = [
            {'user': 'admin', 'password': 'admin'},
            {'user': 'default', 'password': 'clickhouse123'},
            {'user': 'default', 'password': 'changeme_clickhouse'}
        ]
        
        for creds in credentials:
            try:
                result = subprocess.run([
                    'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
                    f'--user={creds["user"]}', f'--password={creds["password"]}',
                    '--query=SELECT 1'
                ], capture_output=True, timeout=10)
                
                if result.returncode == 0:
                    return creds
            except:
                continue
        
        return None

    def query_clickhouse(self, query: str) -> List[List[str]]:
        """Execute ClickHouse query and return results as list of rows"""
        if not self.clickhouse_creds:
            return []
            
        try:
            result = subprocess.run([
                'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
                f'--user={self.clickhouse_creds["user"]}', 
                f'--password={self.clickhouse_creds["password"]}',
                '--format=TabSeparated',
                f'--query={query}'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                return [row.split('\t') for row in result.stdout.strip().split('\n')]
            return []
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return []

    def analyze_missing_data(self):
        """Analyze patterns in missing incident data"""
        print("🔍 ANALYZING MISSING DATA PATTERNS")
        print("=" * 50)
        
        # Get incidents with missing data
        query = """
        SELECT 
            incident_id,
            ship_id,
            service, 
            metric_name,
            metric_value,
            correlation_id,
            JSONExtractString(metadata, 'host') as metadata_host,
            JSONExtractString(metadata, 'event_source') as event_source,
            correlated_events,
            created_at
        FROM logs.incidents 
        WHERE created_at > now() - INTERVAL 7 DAY
        AND (ship_id = 'unknown-ship' OR service = 'unknown_service' OR metric_name = 'unknown_metric')
        ORDER BY created_at DESC
        LIMIT 20
        """
        
        incidents = self.query_clickhouse(query)
        
        if not incidents:
            print("  ✅ No incidents with missing data found in last 7 days")
            return
            
        print(f"  Found {len(incidents)} incidents with missing data:")
        print()
        
        for incident in incidents:
            if len(incident) >= 10:
                incident_id, ship_id, service, metric_name, metric_value, correlation_id, metadata_host, event_source, correlated_events, created_at = incident[:10]
                
                print(f"  📋 Incident: {incident_id[:8]}...")
                print(f"     Created: {created_at}")
                print(f"     Ship ID: {ship_id}")
                print(f"     Service: {service}")
                print(f"     Metric: {metric_name}")
                print(f"     Host (metadata): {metadata_host}")
                print(f"     Event Source: {event_source}")
                
                # Try to find matching raw logs for this incident
                if correlation_id:
                    raw_data = self._find_related_raw_data(correlation_id, created_at)
                    if raw_data:
                        print(f"     🔗 Related raw data found:")
                        for raw in raw_data[:2]:  # Show first 2 matches
                            if len(raw) >= 6:
                                print(f"        Host: {raw[4]}, Service: {raw[5]}, Message: {raw[2][:60]}...")
                
                print()

    def _find_related_raw_data(self, correlation_id: str, created_at: str) -> List[List[str]]:
        """Find raw log data related to an incident"""
        # Look for raw logs around the incident creation time
        query = f"""
        SELECT timestamp, level, message, source, host, service
        FROM logs.raw 
        WHERE timestamp >= '{created_at}' - INTERVAL 1 MINUTE
        AND timestamp <= '{created_at}' + INTERVAL 1 MINUTE
        AND (message LIKE '%{correlation_id}%' 
             OR message LIKE '%ERROR%' 
             OR message LIKE '%CRITICAL%'
             OR message LIKE '%WARNING%')
        ORDER BY timestamp DESC
        LIMIT 5
        """
        
        return self.query_clickhouse(query)

    def extract_data_from_message(self, message: str) -> Dict[str, str]:
        """Extract structured data from log messages"""
        extracted = {}
        
        # Common patterns in log messages
        patterns = {
            'metric_name': r'metric_name=([^\s]+)',
            'metric_value': r'metric_value=([\d.]+)',
            'ship_id': r'ship_id=([^\s]+)',
            'service': r'service=([^\s]+)',
            'host': r'host=([^\s]+)',
            'tracking_id': r'tracking_id=([^\s]+)',
            'anomaly_score': r'anomaly_score=([\d.]+)'
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, message)
            if match:
                extracted[field] = match.group(1)
        
        # Try to extract service from syslog format
        # Format: <priority>timestamp hostname service: message
        syslog_pattern = r'^<\d+>.*?\s+(\S+)\s+(\S+):\s+'
        match = re.search(syslog_pattern, message)
        if match and 'service' not in extracted:
            extracted['service'] = match.group(2)
            if 'host' not in extracted:
                extracted['host'] = match.group(1)
        
        return extracted

    def suggest_field_enhancements(self, dry_run: bool = True):
        """Suggest enhancements for incidents with missing data"""
        print("💡 SUGGESTING FIELD ENHANCEMENTS")
        print("=" * 50)
        
        # Get recent incidents with missing data
        query = """
        SELECT 
            incident_id,
            ship_id,
            service,
            metric_name,
            correlation_id,
            correlated_events,
            JSONExtractString(metadata, 'host') as metadata_host,
            created_at
        FROM logs.incidents 
        WHERE created_at > now() - INTERVAL 24 HOUR
        AND (ship_id = 'unknown-ship' OR service = 'unknown_service' OR metric_name = 'unknown_metric')
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        incidents = self.query_clickhouse(query)
        
        if not incidents:
            print("  ✅ No recent incidents need enhancement")
            return
            
        enhancements = []
        
        for incident in incidents:
            if len(incident) >= 8:
                incident_id, ship_id, service, metric_name, correlation_id, correlated_events, metadata_host, created_at = incident[:8]
                
                enhancement = {
                    'incident_id': incident_id,
                    'current': {
                        'ship_id': ship_id,
                        'service': service, 
                        'metric_name': metric_name
                    },
                    'suggested': {}
                }
                
                # Try to extract from correlated_events
                if correlated_events and correlated_events != '[]':
                    try:
                        events = json.loads(correlated_events)
                        for event in events:
                            if isinstance(event, dict):
                                # Extract from event metadata
                                metadata = event.get('metadata', {})
                                if isinstance(metadata, dict):
                                    if ship_id == 'unknown-ship' and 'ship_id' in metadata:
                                        enhancement['suggested']['ship_id'] = metadata['ship_id']
                                    if metric_name == 'unknown_metric' and 'metric_name' in metadata:
                                        enhancement['suggested']['metric_name'] = metadata['metric_name']
                                
                                # Extract from event description or message
                                description = event.get('description', '')
                                if description:
                                    extracted = self.extract_data_from_message(description)
                                    if ship_id == 'unknown-ship' and 'ship_id' in extracted:
                                        enhancement['suggested']['ship_id'] = extracted['ship_id']
                                    if service == 'unknown_service' and 'service' in extracted:
                                        enhancement['suggested']['service'] = extracted['service']
                                    if metric_name == 'unknown_metric' and 'metric_name' in extracted:
                                        enhancement['suggested']['metric_name'] = extracted['metric_name']
                    except:
                        pass
                
                # Try hostname-based ship_id derivation
                if ship_id == 'unknown-ship' and metadata_host and metadata_host != 'unknown':
                    if '-' in metadata_host:
                        derived_ship_id = metadata_host.split('-')[0] + '-ship'
                        enhancement['suggested']['ship_id'] = derived_ship_id
                    else:
                        enhancement['suggested']['ship_id'] = metadata_host
                
                if enhancement['suggested']:
                    enhancements.append(enhancement)
        
        # Display suggestions
        for enh in enhancements:
            print(f"  📋 Incident: {enh['incident_id'][:8]}...")
            print(f"     Current data:")
            for field, value in enh['current'].items():
                print(f"       {field}: {value}")
            print(f"     Suggested improvements:")
            for field, value in enh['suggested'].items():
                print(f"       {field}: {enh['current'][field]} → {value}")
            
            if not dry_run:
                print(f"     🔄 Applying enhancement...")
                self._apply_enhancement(enh['incident_id'], enh['suggested'])
            else:
                print(f"     🔍 (Dry run - no changes made)")
            print()

    def _apply_enhancement(self, incident_id: str, suggested: Dict[str, str]):
        """Apply field enhancements to an incident"""
        if not self.clickhouse_creds:
            print("      ❌ No ClickHouse credentials available")
            return
            
        updates = []
        for field, value in suggested.items():
            updates.append(f"{field} = '{value}'")
        
        if updates:
            update_query = f"""
            ALTER TABLE logs.incidents 
            UPDATE {', '.join(updates)}
            WHERE incident_id = '{incident_id}'
            """
            
            try:
                result = subprocess.run([
                    'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
                    f'--user={self.clickhouse_creds["user"]}', 
                    f'--password={self.clickhouse_creds["password"]}',
                    f'--query={update_query}'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print(f"      ✅ Enhanced {len(updates)} field(s)")
                else:
                    print(f"      ❌ Update failed: {result.stderr}")
            except Exception as e:
                print(f"      ❌ Enhancement failed: {e}")

    def generate_data_source_mapping(self):
        """Generate a mapping of data sources for missing fields"""
        print("📊 DATA SOURCE MAPPING FOR MISSING FIELDS")
        print("=" * 50)
        
        mapping = {
            'ship_id': {
                'primary_source': 'Device Registry (hostname lookup)',
                'fallback_sources': [
                    'Hostname parsing (e.g., ship-01 -> ship-01)',
                    'Extract from log message ship_id= field',
                    'Instance label from metric data',
                    'Host field from raw logs'
                ],
                'current_issues': [
                    'Device registry service may not be running',
                    'Hostname mappings not configured',
                    'Raw logs missing hostname field'
                ]
            },
            'service': {
                'primary_source': 'Syslog appname field or application logs',
                'fallback_sources': [
                    'Extract from log message service= field',
                    'Parse from Vector source configuration',
                    'Derive from container/application name',
                    'Use filename for file-based logs'
                ],
                'current_issues': [
                    'Applications not setting syslog appname',
                    'Unstructured log messages',
                    'Vector not extracting service field'
                ]
            },
            'metric_name': {
                'primary_source': 'Anomaly detection service NATS events',
                'fallback_sources': [
                    'Extract from log message metric_name= field',
                    'Parse from VictoriaMetrics query names',
                    'Use host metrics source metric names',
                    'Extract from SNMP OID mappings'
                ],
                'current_issues': [
                    'Anomaly detection not publishing to NATS',
                    'NATS messages missing metric_name field',
                    'Benthos not extracting metric names properly'
                ]
            },
            'metric_value': {
                'primary_source': 'Real-time metric values from VictoriaMetrics',
                'fallback_sources': [
                    'Extract from log message metric_value= field',
                    'Parse numeric values from log content',
                    'Query ClickHouse for recent metric data',
                    'Use anomaly detection threshold values'
                ],
                'current_issues': [
                    'Metric values not included in anomaly events',
                    'Data type conversion issues',
                    'Numeric parsing failures in pipeline'
                ]
            },
            'host': {
                'primary_source': 'Syslog hostname field or Vector transforms',
                'fallback_sources': [
                    'Container hostname',
                    'System hostname',
                    'Instance labels from metrics',
                    'Extract from file paths'
                ],
                'current_issues': [
                    'Vector not extracting hostname from sources',
                    'Missing hostname in syslog messages',
                    'Container names used instead of ship names'
                ]
            }
        }
        
        for field, info in mapping.items():
            print(f"\n🏷️  Field: {field}")
            print(f"   Primary Source: {info['primary_source']}")
            print(f"   Fallback Sources:")
            for source in info['fallback_sources']:
                print(f"     • {source}")
            print(f"   Current Issues:")
            for issue in info['current_issues']:
                print(f"     ⚠️  {issue}")

def main():
    parser = argparse.ArgumentParser(description='Enhance incident data fields')
    parser.add_argument('--analyze', action='store_true', help='Analyze missing data patterns')
    parser.add_argument('--fix-recent', action='store_true', help='Suggest fixes for recent incidents')
    parser.add_argument('--dry-run', action='store_true', help='Show suggestions without applying them')
    parser.add_argument('--data-mapping', action='store_true', help='Show data source mapping')
    
    args = parser.parse_args()
    
    enhancer = IncidentDataEnhancer()
    
    if not enhancer.clickhouse_creds:
        print("❌ Could not connect to ClickHouse")
        print("   Ensure ClickHouse is running and accessible")
        return
    
    if args.data_mapping:
        enhancer.generate_data_source_mapping()
    elif args.analyze:
        enhancer.analyze_missing_data()
    elif args.fix_recent:
        enhancer.suggest_field_enhancements(dry_run=args.dry_run)
    else:
        print("🔧 INCIDENT DATA ENHANCEMENT TOOL")
        print("=" * 50)
        print("Available options:")
        print("  --analyze         : Analyze patterns in missing data")
        print("  --fix-recent      : Suggest fixes for recent incidents")
        print("  --dry-run         : Show suggestions without applying")
        print("  --data-mapping    : Show where missing data should come from")
        print()
        print("Example usage:")
        print("  python3 scripts/enhance_incident_data.py --analyze")
        print("  python3 scripts/enhance_incident_data.py --fix-recent --dry-run")
        print("  python3 scripts/enhance_incident_data.py --data-mapping")

if __name__ == "__main__":
    main()