#!/usr/bin/env python3
"""
Pipeline Stats Collection Tool

This tool collects and displays statistics from each stage of the modular
event processing pipeline to provide visibility into data flow:

- Logs received
- Anomalies detected  
- Anomalies enriched
- Anomalies enhanced
- Events deduplicated
- Incidents created
- Incidents enriched
- Incidents correlated

Usage:
    python3 scripts/collect_pipeline_stats.py
    python3 scripts/collect_pipeline_stats.py --watch
    python3 scripts/collect_pipeline_stats.py --export-json
"""

import asyncio
import json
import time
import requests
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess

class PipelineStatsCollector:
    """Collects statistics from all pipeline services"""
    
    def __init__(self):
        self.services = {
            'vector': {'port': 8686, 'endpoint': '/metrics', 'type': 'prometheus'},
            'anomaly_detection': {'port': 8080, 'endpoint': '/health', 'type': 'json'},
            'benthos_enrichment': {'port': 4196, 'endpoint': '/stats', 'type': 'json'},
            'enhanced_anomaly': {'port': 9082, 'endpoint': '/health', 'type': 'json'}, 
            'benthos_correlation': {'port': 4195, 'endpoint': '/stats', 'type': 'json'},
            'incident_api': {'port': 8081, 'endpoint': '/health', 'type': 'json'}
        }
        
    def get_service_stats(self, service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get stats from a single service"""
        try:
            url = f"http://localhost:{config['port']}{config['endpoint']}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                if config['type'] == 'prometheus':
                    return self.parse_prometheus_metrics(response.text)
                else:
                    return response.json()
            else:
                return {'error': f"HTTP {response.status_code}", 'status': 'unhealthy'}
                
        except requests.exceptions.RequestException as e:
            return {'error': str(e), 'status': 'unreachable'}
    
    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics from Vector"""
        metrics = {}
        lines = metrics_text.split('\n')
        
        for line in lines:
            if line.startswith('vector_events_in_total'):
                # Extract events by component
                if 'syslog' in line:
                    value = line.split()[-1]
                    metrics['logs_received'] = int(float(value))
            elif line.startswith('vector_events_out_total'):
                if 'anomalous' in line:
                    value = line.split()[-1] 
                    metrics['anomalous_logs_sent'] = int(float(value))
                elif 'clickhouse' in line:
                    value = line.split()[-1]
                    metrics['logs_stored'] = int(float(value))
                    
        return metrics
    
    def get_clickhouse_stats(self) -> Dict[str, Any]:
        """Get statistics from ClickHouse"""
        stats = {}
        
        try:
            # Count total logs
            result = subprocess.run([
                'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
                '--query=SELECT count() FROM logs.raw'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                stats['total_logs_stored'] = int(result.stdout.strip())
            
            # Count incidents  
            result = subprocess.run([
                'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client', 
                '--query=SELECT count() FROM logs.incidents'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                stats['total_incidents_stored'] = int(result.stdout.strip())
                
            # Count recent activity (last hour)
            result = subprocess.run([
                'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
                '--query=SELECT count() FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                stats['recent_logs_1h'] = int(result.stdout.strip())
                
        except Exception as e:
            stats['error'] = str(e)
            
        return stats
    
    def collect_all_stats(self) -> Dict[str, Any]:
        """Collect statistics from all services"""
        timestamp = datetime.now().isoformat()
        stats = {
            'timestamp': timestamp,
            'pipeline_stats': {}
        }
        
        # Collect service stats
        for service_name, config in self.services.items():
            stats['pipeline_stats'][service_name] = self.get_service_stats(service_name, config)
        
        # Add ClickHouse stats
        stats['pipeline_stats']['clickhouse'] = self.get_clickhouse_stats()
        
        # Calculate derived metrics
        stats['derived_metrics'] = self.calculate_derived_metrics(stats['pipeline_stats'])
        
        return stats
    
    def calculate_derived_metrics(self, service_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics for pipeline health"""
        derived = {}
        
        # Pipeline throughput metrics
        vector_stats = service_stats.get('vector', {})
        logs_received = vector_stats.get('logs_received', 0)
        anomalous_sent = vector_stats.get('anomalous_logs_sent', 0)
        
        if logs_received > 0:
            derived['anomaly_detection_rate'] = (anomalous_sent / logs_received) * 100
        
        # Service health summary
        healthy_services = 0
        total_services = len(self.services)
        
        for service_name, service_data in service_stats.items():
            if service_name == 'clickhouse':
                continue
                
            if 'error' not in service_data and service_data.get('status') != 'unreachable':
                healthy_services += 1
        
        derived['pipeline_health'] = (healthy_services / total_services) * 100
        
        # Processing efficiency
        anomaly_service = service_stats.get('anomaly_detection', {})
        incident_api = service_stats.get('incident_api', {})
        
        anomalies_detected = anomaly_service.get('anomalies_detected', 0)
        incidents_created = incident_api.get('incidents_created', 0)
        
        if anomalies_detected > 0:
            derived['incident_creation_rate'] = (incidents_created / anomalies_detected) * 100
            
        return derived
    
    def format_stats_table(self, stats: Dict[str, Any]) -> str:
        """Format stats as readable table"""
        output = []
        output.append("=" * 80)
        output.append(f"AIOps Pipeline Statistics - {stats['timestamp']}")
        output.append("=" * 80)
        
        # Service Status
        output.append("\n📊 SERVICE STATUS:")
        output.append("-" * 40)
        
        for service_name, service_data in stats['pipeline_stats'].items():
            if 'error' in service_data:
                status = f"❌ {service_data['error']}"
            elif service_data.get('status') == 'unreachable':
                status = "🔴 Unreachable"
            else:
                status = "✅ Healthy"
                
            output.append(f"{service_name:20} {status}")
        
        # Pipeline Metrics
        output.append("\n📈 PIPELINE METRICS:")
        output.append("-" * 40)
        
        vector_stats = stats['pipeline_stats'].get('vector', {})
        logs_received = vector_stats.get('logs_received', 0)
        anomalous_sent = vector_stats.get('anomalous_logs_sent', 0)
        logs_stored = vector_stats.get('logs_stored', 0)
        
        output.append(f"Logs Received:       {logs_received:,}")
        output.append(f"Anomalous Detected:  {anomalous_sent:,}")
        output.append(f"Logs Stored:         {logs_stored:,}")
        
        # Service-specific metrics
        anomaly_stats = stats['pipeline_stats'].get('anomaly_detection', {})
        if 'anomalies_detected' in anomaly_stats:
            output.append(f"Anomalies Detected:  {anomaly_stats['anomalies_detected']:,}")
        
        enrichment_stats = stats['pipeline_stats'].get('benthos_enrichment', {})
        if 'processed_events' in enrichment_stats:
            output.append(f"Events Enriched:     {enrichment_stats['processed_events']:,}")
            
        enhanced_stats = stats['pipeline_stats'].get('enhanced_anomaly', {})
        if 'anomalies_enhanced' in enhanced_stats:
            output.append(f"Anomalies Enhanced:  {enhanced_stats['anomalies_enhanced']:,}")
        
        correlation_stats = stats['pipeline_stats'].get('benthos_correlation', {})
        if 'processed_events' in correlation_stats:
            output.append(f"Events Correlated:   {correlation_stats['processed_events']:,}")
            
        incident_stats = stats['pipeline_stats'].get('incident_api', {})
        if 'incidents_created' in incident_stats:
            output.append(f"Incidents Created:   {incident_stats['incidents_created']:,}")
        
        # ClickHouse metrics
        ch_stats = stats['pipeline_stats'].get('clickhouse', {})
        if 'total_logs_stored' in ch_stats:
            output.append(f"Total Logs in DB:    {ch_stats['total_logs_stored']:,}")
        if 'total_incidents_stored' in ch_stats:
            output.append(f"Total Incidents:     {ch_stats['total_incidents_stored']:,}")
        if 'recent_logs_1h' in ch_stats:
            output.append(f"Recent Logs (1h):    {ch_stats['recent_logs_1h']:,}")
        
        # Derived metrics
        derived = stats.get('derived_metrics', {})
        if derived:
            output.append("\n🔍 DERIVED METRICS:")
            output.append("-" * 40)
            
            if 'anomaly_detection_rate' in derived:
                output.append(f"Anomaly Detection Rate: {derived['anomaly_detection_rate']:.2f}%")
            if 'pipeline_health' in derived:
                output.append(f"Pipeline Health:        {derived['pipeline_health']:.1f}%")
            if 'incident_creation_rate' in derived:
                output.append(f"Incident Creation Rate: {derived['incident_creation_rate']:.2f}%")
        
        output.append("=" * 80)
        return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description='Collect AIOps Pipeline Statistics')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=30, help='Watch interval in seconds')
    parser.add_argument('--export-json', action='store_true', help='Export as JSON')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    collector = PipelineStatsCollector()
    
    if args.watch:
        print("📡 Starting continuous pipeline monitoring...")
        print(f"   Update interval: {args.interval} seconds")
        print("   Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                stats = collector.collect_all_stats()
                
                # Clear screen and show stats
                print("\033[2J\033[H")  # Clear screen and move cursor to top
                print(collector.format_stats_table(stats))
                
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped.")
    else:
        # Single collection
        stats = collector.collect_all_stats()
        
        if args.export_json:
            json_output = json.dumps(stats, indent=2)
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(json_output)
                print(f"📄 Stats exported to: {args.output}")
            else:
                print(json_output)
        else:
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(collector.format_stats_table(stats))
                print(f"📄 Stats saved to: {args.output}")
            else:
                print(collector.format_stats_table(stats))

if __name__ == "__main__":
    main()