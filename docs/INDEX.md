# AIOps NAAS Documentation Index

Complete documentation index for the Cruise AIOps Platform.

## 🚀 Getting Started

**New to the platform?** Start here:

1. [README](../README.md) - Project overview, key capabilities, quick start
2. [Quickstart Guide](quickstart.md) - Get the Docker Compose stack running
3. [Quick Reference](quick-reference.md) - Common commands and access points
4. [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - System architecture at a glance

## 🏗️ Architecture Documentation

### Core Architecture

- **[Architecture Overview](ARCHITECTURE_OVERVIEW.md)** ⭐ **START HERE**
  - Complete system architecture with diagrams
  - Service catalog with ports
  - Data flows and integrations
  - AI/ML integration points
  - 11KB comprehensive guide

- **[Main Architecture](architecture.md)**
  - Edge+Core offline-first design
  - OSS stack components
  - Mermaid diagrams
  - Throughput and sizing
  - License considerations

### Sequential Pipeline Architecture 🔥 **NEW**

The modular event processing pipeline is the heart of the AIOps platform:

- **[Sequential Pipeline Architecture](sequential-pipeline-architecture.md)** ⭐ **DETAILED DESIGN**
  - Complete pipeline design specification
  - Service responsibilities
  - NATS topic architecture
  - AI/ML integration points
  - Configuration details
  - Production readiness checklist
  - 12KB authoritative design document

- **[Pipeline Validation Report](SEQUENTIAL_PIPELINE_VALIDATION.md)** ✅
  - Complete validation with code evidence
  - NATS topic verification
  - Service dependency validation
  - Port configuration checks
  - Design principles compliance
  - 10KB validation report

- **[Pipeline Visual Diagrams](SEQUENTIAL_PIPELINE_DIAGRAM.md)** 📊
  - Mermaid flow diagrams
  - Complete system architecture
  - Service dependency chains
  - Data enrichment flow
  - AI/ML integration diagrams
  - Health check commands
  - Troubleshooting guide
  - 12KB visual reference

### Supporting Architecture Docs

- [Modular Pipeline Architecture](modular-pipeline-architecture.md) - Dual processing architecture
- [Comprehensive Data Flow Diagram](comprehensive-data-flow-diagram.md) - Complete system flows
- [Data Flow Guide](data-flow-guide.md) - Service interaction patterns
- [Service Data Flow Map](service-data-flow-map.md) - Service-level flows
- [End-to-End Flow Guide](end-to-end-flow-guide.md) - Complete flow walkthrough
- [Incident Flow Architecture](incident-flow-architecture.md) - Incident processing flows

## 🔧 Configuration & Setup

### Deployment Guides

- **[Quickstart Guide](quickstart.md)** - Docker Compose for local/testing
- **[Local & Non-Production Deployment](deployment/local-and-nonprod.md)** - Comprehensive setup
- **[One-Click Setup](deployment/one-click.md)** - Interactive wizard for beginners

### Configuration

- **[Vendor Configuration Guide](configuration/vendor-config.md)** - VSAT and device integration
- [Benthos Input Formats](benthos-input-formats.md) - Data format specifications
- [Upstream Format Compatibility](upstream-format-compatibility.md) - Format compatibility
- [Device Registry Configuration](device-registry-hostname-and-ip-requirements.md) - Hostname/IP setup

## 📈 Features & Capabilities

### Core Features

- **[v0.3 Features](v0.3-features.md)** - Predictive Link Health + Guarded Remediation
- [Network Device Monitoring Guide](network-device-monitoring-guide.md) - SNMP and telemetry
- [Device Registry Mapping Service](device-registry-mapping-service.md) - Device tracking
- [IP Address Registry](ip-address-registry.md) - IP management
- [Two-Level Correlation Guide](two-level-correlation-guide.md) - Event correlation

### Specialized Features

- [Incident Data Debugging Guide](incident-data-debugging-guide.md) - Troubleshooting incidents
- [User-Friendly Incident Explanation](../USER_FRIENDLY_INCIDENT_EXPLANATION.md) - LLM-powered explanations
- [Onboarding Service](../services/onboarding-service/README.md) - Two-level approval workflow
- [System Syslog Support](../SYSTEM_SYSLOG_SUPPORT.md) - Syslog integration

## 🧪 Testing & Validation

### Testing Documentation

- **[Manual Testing Guide](validation/manual-testing-guide.md)** - Step-by-step validation
- **[Testing Documentation Summary](../TESTING_DOCUMENTATION_SUMMARY.md)** - All test suites
- [Testing Directory](testing/) - Test specifications and procedures

### Validation Scripts

Located in `scripts/`:
- `verify_modular_pipeline.sh` - End-to-end pipeline verification
- `validate_pipeline.sh` - Pipeline validation
- `validate_pipeline.py` - Python validation
- `collect_pipeline_stats.py` - Statistics collection

### Test Results & Reports

Located in repository root:
- [Comprehensive End-to-End Validation](../COMPREHENSIVE_END_TO_END_VALIDATION.md)
- [Comprehensive Step-by-Step Testing Guide](../COMPREHENSIVE_STEP_BY_STEP_TESTING_GUIDE.md)
- [Enhanced Comprehensive Testing Guide](../ENHANCED_COMPREHENSIVE_TESTING_GUIDE.md)

## 🔄 Operations & Maintenance

### CI/CD & Deployment

- [CI/CD Pipeline](ci-cd-pipeline.md) - Automated testing and deployment
- [Roadmap](roadmap.md) - Development milestones and features

### Administration

Located in `docs/admin/`:
- Dashboard management
- User administration
- System monitoring
- Backup and recovery

## 📝 Implementation Summaries

Complete implementation documentation:

- [Onboarding Service Complete](../ONBOARDING_SERVICE_COMPLETE.md) - Service implementation
- [V03 Implementation Summary](../V03_IMPLEMENTATION_SUMMARY.md) - v0.3 features
- [End-to-End Implementation](../END_TO_END_IMPLEMENTATION.md) - Complete system
- [Complete User-Friendly Correlation Solution](../COMPLETE_USER_FRIENDLY_CORRELATION_SOLUTION.md)
- [Comprehensive Data Flow Architecture](../COMPREHENSIVE_DATA_FLOW_ARCHITECTURE.md)

## 🐛 Troubleshooting & Fixes

### Fix Documentation

- [One-Click Debugging Implementation](../ONE_CLICK_DEBUGGING_IMPLEMENTATION_SUMMARY.md)
- [One-Click Incident Debugging](../ONE_CLICK_INCIDENT_DEBUGGING_README.md)
- [Critical Fixes Documentation](../) - Multiple fix summaries in root

### Issue Reports

- [Incident Data Debugging](incident-data-debugging-guide.md)
- [Firewall and Port Validation Report](../firewall_and_port_validation_report.md)

## 📊 Quick Reference Tables

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Grafana | 3000 | Dashboards |
| VictoriaMetrics | 8428 | Metrics |
| ClickHouse | 8123, 9000 | Logs |
| NATS | 4222, 8222 | Message bus |
| Benthos Enrichment | 4196 | L1 enrichment |
| Enhanced Anomaly | 9082 | L2 analysis |
| Benthos Correlation | 4195 | Incident formation |
| Incident API | 9081 | REST API |
| Device Registry | 8083 | Device info |
| Link Health | 8082 | Predictions |
| Ollama | 11434 | LLM |
| Qdrant | 6333 | Vector DB |

See [SEQUENTIAL_PIPELINE_DIAGRAM.md](SEQUENTIAL_PIPELINE_DIAGRAM.md#port-reference) for complete port list.

### NATS Topics

Sequential pipeline topics (in order):
1. `logs.anomalous` - ERROR/WARNING logs from Vector
2. `anomaly.detected` - Basic anomaly detection output
3. `anomaly.detected.enriched` - Level 1 enriched anomalies
4. `anomaly.detected.enriched.final` - Level 2 enhanced analysis
5. `incidents.created` - Final incidents for storage

### Health Check Commands

```bash
# Pipeline services
curl http://localhost:4196/ping   # Benthos Enrichment
curl http://localhost:9082/health # Enhanced Anomaly
curl http://localhost:4195/ping   # Benthos Correlation
curl http://localhost:9081/health # Incident API

# Infrastructure
curl http://localhost:8123/ping       # ClickHouse
curl http://localhost:8428/health     # VictoriaMetrics
curl http://localhost:8222/varz       # NATS
curl http://localhost:3000/api/health # Grafana
```

## 🔍 Finding Documentation

### By Topic

- **Getting Started**: [README](../README.md), [Quickstart](quickstart.md)
- **Architecture**: [Overview](ARCHITECTURE_OVERVIEW.md), [Main](architecture.md), [Pipeline](sequential-pipeline-architecture.md)
- **Configuration**: [Vendor Config](configuration/vendor-config.md), [Deployment](deployment/)
- **Testing**: [Manual Testing](validation/manual-testing-guide.md), [Validation](SEQUENTIAL_PIPELINE_VALIDATION.md)
- **Operations**: [CI/CD](ci-cd-pipeline.md), [Roadmap](roadmap.md)
- **Troubleshooting**: [Pipeline Diagrams](SEQUENTIAL_PIPELINE_DIAGRAM.md), [Quick Reference](quick-reference.md)

### By Role

**Developers**:
1. [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - Understand the system
2. [Sequential Pipeline Architecture](sequential-pipeline-architecture.md) - Core design
3. [Data Flow Guide](data-flow-guide.md) - Service interactions
4. [Testing](testing/) - Test specifications

**Operators**:
1. [Quickstart Guide](quickstart.md) - Deploy the stack
2. [Quick Reference](quick-reference.md) - Common commands
3. [Manual Testing Guide](validation/manual-testing-guide.md) - Validation
4. [Pipeline Diagrams](SEQUENTIAL_PIPELINE_DIAGRAM.md) - Troubleshooting

**Architects**:
1. [Main Architecture](architecture.md) - Edge+Core design
2. [Sequential Pipeline Architecture](sequential-pipeline-architecture.md) - Event processing
3. [Comprehensive Data Flow Diagram](comprehensive-data-flow-diagram.md) - System flows
4. [Roadmap](roadmap.md) - Future capabilities

## 📚 Documentation Status

### ✅ Complete & Validated

- Sequential Pipeline Architecture (design, validation, diagrams)
- Architecture Overview
- Service configurations
- Docker Compose setup
- Testing infrastructure
- Quick reference guides

### 📝 Active Development

See [Roadmap](roadmap.md) for upcoming features and documentation.

## 🤝 Contributing

When adding new documentation:
1. Update this INDEX.md
2. Add cross-references to related docs
3. Include in appropriate category
4. Update README.md if it's a major addition
5. Follow existing documentation patterns

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/iLodeStar/AIOps-NAAS/issues)
- **Documentation Issues**: Tag with `documentation` label
- **Architecture Questions**: Reference [Sequential Pipeline Architecture](sequential-pipeline-architecture.md)

---

**Last Updated**: October 2, 2025  
**Documentation Version**: 1.0  
**Total Documents**: 50+ docs across architecture, configuration, testing, and operations

**Most Important Docs for New Users**:
1. [README](../README.md) ⭐
2. [Architecture Overview](ARCHITECTURE_OVERVIEW.md) ⭐
3. [Sequential Pipeline Architecture](sequential-pipeline-architecture.md) ⭐
4. [Quickstart Guide](quickstart.md) ⭐
5. [Quick Reference](quick-reference.md) ⭐
