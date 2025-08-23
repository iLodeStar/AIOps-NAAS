# Cruise AIOps Platform - GitHub Copilot Instructions

**ALWAYS** follow these instructions first and only fall back to additional search and context gathering if the information in these instructions is incomplete or found to be in error.

## Current Repository State (CRITICAL)

**This is currently a design-stage repository with no buildable code.** The repository contains only documentation and architectural designs for a future Cruise AIOps Platform.

## Repository Structure

```
/home/runner/work/AIOps-NAAS/AIOps-NAAS/
├── README.md                    # 46 lines - Main project overview
├── .gitignore                   # 95 lines - Comprehensive ignore rules  
├── .github/
│   └── copilot-instructions.md  # This file
└── docs/
    ├── architecture.md          # 123 lines - Detailed system architecture
    └── roadmap.md               # 38 lines - Development milestones
```

## Working Effectively

### Essential Commands (All Validated)
- Navigate to repository root: `cd /home/runner/work/AIOps-NAAS/AIOps-NAAS`
- Check repository status: `git --no-pager status`
- View all files: `ls -la`
- Read documentation: `cat README.md`, `cat docs/architecture.md`, `cat docs/roadmap.md`
- Search documentation: `grep -r "search_term" docs/`

### Current Limitations (No Build/Test Available)
- **NO BUILD SYSTEM**: No package.json, Makefile, Dockerfile, or build scripts exist
- **NO CODE**: No source code files (.py, .js, .ts, .go, .java) exist
- **NO TESTS**: No test frameworks or test files exist
- **NO DEPENDENCIES**: No dependency management files exist
- **NO CI/CD**: No GitHub Actions workflows exist

## Key Architecture Understanding (From docs/architecture.md)

### Planned Technology Stack
- **Logs**: Fluent Bit/Vector → ClickHouse
- **Metrics**: Prometheus → VictoriaMetrics  
- **Traces**: OpenTelemetry → Tempo/Jaeger (optional)
- **Message Bus**: NATS JetStream
- **Stream Processing**: Benthos/Bytewax
- **LLM + RAG**: Ollama + Qdrant + LangChain/LlamaIndex
- **Automation**: AWX + Nornir/Netmiko + OPA
- **UI**: Grafana OSS + React Ops Console + Keycloak
- **Deployment**: k3s + Argo CD + Harbor (optional)

### System Components
- **Edge (Ship)**: Autonomous operations with offline capability
- **Core (Shore)**: Fleet management and control plane
- **High-throughput**: Target >=100K events/sec ingestion

## Development Roadmap (From docs/roadmap.md)

### Current Phase: Pre-v0.1
The repository is in planning/design phase. According to README.md: "Coming soon: docker-compose and Helm charts for v0.1 bootstrap on a test node."

### Planned Milestones
- **v0.1 MVP**: Single ship with basic observability
- **v0.2**: Anomaly detection + correlation  
- **v0.3**: Predictive models + guarded remediation
- **v0.4**: Fleet management + forecasting
- **v1.0**: Self-learning closed-loop automation

## Validation Steps

### Documentation Validation (Always Run These)
```bash
# Verify all docs are accessible
cd /home/runner/work/AIOps-NAAS/AIOps-NAAS
cat README.md | head -10
ls -la docs/
cat docs/architecture.md | wc -l  # Should show 123 lines
cat docs/roadmap.md | wc -l       # Should show 38 lines

# Check for any new files
find . -type f -name "*.md" -o -name "*.txt" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml"
```

### Git Operations (Always Work)
```bash
git --no-pager status
git --no-pager log --oneline -5
git --no-pager diff
```

## Common Tasks

### Research and Documentation Review
- **ALWAYS** read `docs/architecture.md` first to understand the planned system
- **ALWAYS** check `docs/roadmap.md` to understand development phases
- Search documentation: `grep -r "keyword" docs/`
- Understand the offline-first, OSS-first design philosophy

### When Code is Added (Future)
Based on the planned architecture, expect these patterns:
- **Python** for ML/analytics components (River, scikit-learn, PyTorch)
- **Go** for high-performance data ingestion
- **JavaScript/TypeScript** for React Ops Console
- **YAML** for Kubernetes/Argo CD configurations
- **Docker** containers for all components

### File Location Patterns (When Implemented)
- Configuration: Look for `/configs/`, `/helm/`, `/k8s/`
- Source code: Likely `/src/`, `/pkg/`, `/services/`
- Documentation: Always in `/docs/`
- Deployment: Look for `/deploy/`, `/infra/`, `/charts/`

## Critical Guidelines

### Do NOT Attempt These (Will Fail)
- `npm install` or `npm run *` - No Node.js project exists
- `pip install` or `python *` - No Python project exists  
- `make *` - No Makefile exists
- `docker build` - No Dockerfiles exist
- Any build or test commands - No build system exists

### Always Do These Instead
1. **Start with documentation**: Read all `.md` files in `/docs/`
2. **Understand the architecture**: Study the Mermaid diagram in `docs/architecture.md`
3. **Check roadmap**: See current milestone in `docs/roadmap.md`
4. **Search existing docs**: Use `grep -r` to find relevant information
5. **Focus on design**: This is a planning repository, contribute to architecture/design

## Future Development Guidance

When actual code is added to this repository:
- **Follow OSS-first principle**: All components should be open source
- **Maintain offline-first design**: Components must work without internet
- **Target high throughput**: Design for >=100K events/sec
- **Use recommended stack**: Stick to technologies listed in architecture.md
- **Follow roadmap phases**: Implement features according to planned milestones

## Quick Reference Commands

```bash
# Repository overview
ls -la /home/runner/work/AIOps-NAAS/AIOps-NAAS/

# Read all documentation  
cat README.md && echo -e "\n--- ARCHITECTURE ---\n" && cat docs/architecture.md && echo -e "\n--- ROADMAP ---\n" && cat docs/roadmap.md

# Search for specific topics
grep -r "ClickHouse\|VictoriaMetrics\|Grafana" docs/

# Check for any changes
git --no-pager status && git --no-pager diff
```

## Summary

This repository is in the architectural design phase for a sophisticated maritime AIOps platform. Focus on understanding the planned system architecture, contributing to documentation, and preparing for future implementation phases. Do not attempt to build or run code - none exists yet.