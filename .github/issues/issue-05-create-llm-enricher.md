## Task
Create `services/llm-enricher/` for AI-based incident insights.

## Implementation

```python
from aiops_core.models import Incident, EnrichedIncident
from aiops_core.utils import StructuredLogger

# Subscribe: incidents.created
# Generate AI insights:
#   - Root cause (Ollama phi3:mini)
#   - Similar incidents (Qdrant RAG)
#   - Remediation suggestions
# Cache responses in ClickHouse
# Publish: incidents.enriched
# Target: <300ms with timeout fallback
```

## Structure
```
services/llm-enricher/
├── llm_service.py      # Main service
├── ollama_client.py    # LLM integration
├── qdrant_rag.py       # RAG search
├── llm_cache.py        # ClickHouse cache
└── Dockerfile
```

## Acceptance Criteria
- [ ] Subscribes to `incidents.created`
- [ ] Ollama integration works (phi3:mini)
- [ ] Qdrant RAG retrieves similar incidents
- [ ] Responses cached in ClickHouse
- [ ] Publishes to `incidents.enriched`
- [ ] Timeout fallback functional
- [ ] Latency <300ms (p99)

**Effort**: 4-5h | **Priority**: High | **Dependencies**: #6, #7, #1-4
