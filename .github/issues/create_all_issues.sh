#!/bin/bash
# Script to create GitHub issues for V3 Implementation
# Run this script to create all 14 issues in the correct order

set -e

REPO="iLodeStar/AIOps-NAAS"
MILESTONE="v1.0"  # Update if milestone exists

echo "Creating GitHub Issues for V3 Architecture Implementation"
echo "Repository: $REPO"
echo "============================================================"

# Function to create an issue
create_issue() {
    local title="$1"
    local body_file="$2"
    local labels="$3"
    
    echo "Creating issue: $title"
    gh issue create \
        --repo "$REPO" \
        --title "$title" \
        --body-file "$body_file" \
        --label "$labels" || echo "  ⚠️ Failed to create (may already exist)"
    echo "  ✅ Done"
    echo ""
}

# Sprint 1 - Critical Path
echo "📋 Sprint 1: Critical Services (Week 1)"
echo "========================================"

create_issue \
    "[V3] Refactor anomaly-detection service to use V3 Pydantic models" \
    ".github/issues/issue-01-refactor-anomaly-detection.md" \
    "priority: critical,type: refactoring,sprint: 1,v3-architecture"

create_issue \
    "[V3] Create enrichment-service for Fast Path context enrichment" \
    ".github/issues/issue-02-create-enrichment-service.md" \
    "priority: critical,type: feature,sprint: 1,v3-architecture,new-service"

create_issue \
    "[V3] Create correlation-service for incident formation and deduplication" \
    ".github/issues/issue-03-create-correlation-service.md" \
    "priority: critical,type: feature,sprint: 1,v3-architecture,new-service"

create_issue \
    "[V3] Add V3 API endpoints to incident-api (stats, trace)" \
    ".github/issues/issue-04-add-v3-endpoints.md" \
    "priority: critical,type: feature,sprint: 1,v3-architecture,api"

# Sprint 2 - AI/ML Integration
echo "📋 Sprint 2: AI/ML Integration (Week 2)"
echo "========================================"

create_issue \
    "[V3] Add Ollama LLM service to docker-compose.yml" \
    ".github/issues/issue-06-add-ollama.md" \
    "priority: high,type: infrastructure,sprint: 2,v3-architecture,ai-ml"

create_issue \
    "[V3] Add Qdrant vector database to docker-compose.yml" \
    ".github/issues/issue-07-add-qdrant.md" \
    "priority: high,type: infrastructure,sprint: 2,v3-architecture,ai-ml"

create_issue \
    "[V3] Create llm-enricher service for LLM/RAG-based insights" \
    ".github/issues/issue-05-create-llm-enricher.md" \
    "priority: high,type: feature,sprint: 2,v3-architecture,ai-ml,new-service"

# Sprint 3 - Infrastructure
echo "📋 Sprint 3: Infrastructure & Observability (Week 3)"
echo "===================================================="

create_issue \
    "[V3] Configure Vector to generate tracking_id for all logs" \
    ".github/issues/issue-10-add-tracking-id.md" \
    "priority: medium,type: infrastructure,sprint: 3,v3-architecture,observability"

create_issue \
    "[V3] Add all V3 services to main docker-compose.yml" \
    ".github/issues/issue-08-update-docker-compose.md" \
    "priority: medium,type: infrastructure,sprint: 3,v3-architecture"

create_issue \
    "[V3] Configure VMAlert for Fast Path and Insight Path SLO monitoring" \
    ".github/issues/issue-09-add-vmalert.md" \
    "priority: medium,type: infrastructure,sprint: 3,v3-architecture,observability"

create_issue \
    "[V3] Migrate all services to use StructuredLogger from aiops_core" \
    ".github/issues/issue-11-migrate-structured-logger.md" \
    "priority: medium,type: refactoring,sprint: 3,v3-architecture,observability"

# Sprint 4 - Quality
echo "📋 Sprint 4: Quality & Polish (Week 4)"
echo "======================================="

create_issue \
    "[V3] Remove legacy test files and redundant documentation" \
    ".github/issues/issue-12-cleanup-legacy-files.md" \
    "priority: low,type: maintenance,sprint: 4,v3-architecture,cleanup"

create_issue \
    "[V3] Create comprehensive E2E test suite for Fast Path and Insight Path" \
    ".github/issues/issue-13-create-e2e-tests.md" \
    "priority: low,type: testing,sprint: 4,v3-architecture,e2e-tests"

create_issue \
    "[V3] Build Grafana plugin and create deployment package" \
    ".github/issues/issue-14-build-grafana-plugin.md" \
    "priority: low,type: frontend,sprint: 4,v3-architecture,ui"

echo "============================================================"
echo "✅ All 14 issues created successfully!"
echo ""
echo "Next steps:"
echo "1. Review issues at: https://github.com/$REPO/issues"
echo "2. Assign issues to team members"
echo "3. Link issues to Epic: ISSUE-20251003-142429-V3-COMPLETION"
echo "4. Start Sprint 1 with issues #1-4"
echo ""
echo "Execution Order:"
echo "  Sprint 1 (Week 1): #1 → #2 → #3 → #4"
echo "  Sprint 2 (Week 2): #6, #7 (parallel) → #5"
echo "  Sprint 3 (Week 3): #10, #8 → #9, #11"
echo "  Sprint 4 (Week 4): #12, #13, #14"
