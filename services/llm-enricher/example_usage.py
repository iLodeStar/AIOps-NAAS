#!/usr/bin/env python3
"""
Usage example for LLM Enricher Service
Demonstrates how the service integrates into the AIOps pipeline
"""

import json
from datetime import datetime


def example_incident_flow():
    """
    Example: How an incident flows through the LLM enricher
    
    1. Incident created by correlation service
    2. Published to incidents.created NATS topic
    3. LLM enricher subscribes and processes
    4. Enriched incident published to incidents.enriched
    5. Consumed by incident API and stored in ClickHouse
    """
    
    print("=" * 70)
    print("LLM Enricher Service - Usage Example")
    print("=" * 70)
    
    # 1. Incoming incident from correlation service
    print("\n[1] Incident created by correlation service:")
    print("-" * 70)
    
    incoming_incident = {
        "incident_id": "inc-20250104-143200-a1b2c3",
        "incident_type": "link_degradation",
        "severity": "high",
        "ship_id": "cruise-explorer-01",
        "tracking_id": "req-20250104-143200-xyz789",
        "created_at": "2025-01-04T14:32:00.000Z",
        "scope": [
            {
                "device_id": "sat-antenna-01",
                "service": "satellite_comms"
            }
        ],
        "corr_keys": [
            "link_degradation:cruise-explorer-01",
            "comms:cruise-explorer-01"
        ],
        "suppress_key": "link_degradation:cruise-explorer-01:sat-antenna-01:satellite_comms",
        "timeline": [
            {
                "ts": "2025-01-04T14:31:45.000Z",
                "event": "anomaly_detected",
                "description": "High latency detected",
                "source": "anomaly-detection"
            },
            {
                "ts": "2025-01-04T14:32:00.000Z",
                "event": "incident_created",
                "description": "Correlation threshold exceeded",
                "source": "benthos-correlation"
            }
        ],
        "evidence": [
            {
                "ref": "clickhouse://logs.raw/id=1234567",
                "summary": "Packet loss 15% on sat-antenna-01",
                "weight": 0.9
            }
        ],
        "status": "open"
    }
    
    print(json.dumps(incoming_incident, indent=2))
    
    # 2. NATS topic: incidents.created
    print("\n[2] Published to NATS topic: incidents.created")
    print("-" * 70)
    print(f"Topic: incidents.created")
    print(f"Message size: {len(json.dumps(incoming_incident))} bytes")
    
    # 3. LLM Enricher processing
    print("\n[3] LLM Enricher Service processes incident:")
    print("-" * 70)
    print("Step 1: Check cache for similar incident...")
    print("  → Cache miss (first time seeing this pattern)")
    print("\nStep 2: Search Qdrant for similar incidents...")
    print("  → Found 2 similar incidents from past 30 days")
    print("\nStep 3: Generate root cause via Ollama (phi3:mini)...")
    print("  → Prompt: 'Analyze maritime incident: link_degradation...'")
    print("  → Response time: 245ms")
    print("\nStep 4: Generate remediation via Ollama...")
    print("  → Prompt: 'Suggest remediation for link_degradation...'")
    print("  → Response time: 198ms")
    print("\nStep 5: Cache responses in ClickHouse...")
    print("  → Cached with TTL: 24 hours")
    print("\nStep 6: Store incident vector in Qdrant...")
    print("  → Stored for future similarity searches")
    
    # 4. Enriched output
    print("\n[4] Enriched incident published to: incidents.enriched")
    print("-" * 70)
    
    enriched_incident = {
        "incident_id": "inc-20250104-143200-a1b2c3",
        "enrichment_timestamp": "2025-01-04T14:32:01.443Z",
        "original_incident": incoming_incident,
        "ai_insights": {
            "root_cause": (
                "The satellite link degradation is likely caused by a combination of "
                "high traffic load and atmospheric interference. The 15% packet loss "
                "on sat-antenna-01 indicates signal quality issues, possibly due to "
                "weather conditions or antenna alignment drift. The system's latency "
                "exceeding normal thresholds suggests the link is operating at capacity."
            ),
            "remediation_suggestions": (
                "1. Reduce non-critical traffic to free up satellite bandwidth\n"
                "2. Check antenna alignment and adjust if necessary\n"
                "3. Monitor weather conditions and consider switching to backup link if available\n"
                "4. Review traffic patterns to identify potential optimization opportunities"
            )
        },
        "similar_incidents": [
            {
                "incident_id": "inc-20241215-091500-x7y8z9",
                "incident_type": "link_degradation",
                "severity": "high",
                "timestamp": "2024-12-15T09:15:00.000Z",
                "similarity_score": 0.87,
                "resolution": "Switched to backup satellite link, resolved in 15 minutes"
            },
            {
                "incident_id": "inc-20241220-163000-m1n2o3",
                "incident_type": "link_degradation", 
                "severity": "medium",
                "timestamp": "2024-12-20T16:30:00.000Z",
                "similarity_score": 0.74,
                "resolution": "Antenna realignment performed, quality restored"
            }
        ],
        "cache_hit": False,
        "processing_time_ms": 443.21
    }
    
    print(json.dumps(enriched_incident, indent=2))
    
    # 5. Downstream consumption
    print("\n[5] Downstream services consume enriched incident:")
    print("-" * 70)
    print("✓ Incident API: Stores in ClickHouse with AI insights")
    print("✓ Ops Console: Displays root cause and remediation to operators")
    print("✓ Remediation Service: Uses suggestions for auto-remediation consideration")
    print("✓ Notification Service: Includes AI context in alerts")
    
    # Performance summary
    print("\n[6] Performance Summary:")
    print("-" * 70)
    print(f"Total enrichment time: 443ms")
    print(f"  - Cache lookup: 12ms")
    print(f"  - Qdrant RAG search: 35ms")
    print(f"  - Ollama root cause: 245ms")
    print(f"  - Ollama remediation: 198ms")
    print(f"  - Cache storage: 8ms")
    print(f"  - Qdrant vector store: 15ms")
    print(f"\n✓ Target met: <300ms for cached responses")
    print(f"✓ Fallback available if timeout (10s)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_incident_flow()
