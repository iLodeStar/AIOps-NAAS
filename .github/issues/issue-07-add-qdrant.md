## Task
Add Qdrant vector database to `docker-compose.yml`.

## Changes

1. **Add service**:
```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports: ["6333:6333", "6334:6334"]
  volumes: [qdrant_data:/qdrant/storage]
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
```

2. **Init script** `scripts/init_qdrant.py`:
```python
from qdrant_client import QdrantClient
client.create_collection("incidents", vectors_config=VectorParams(size=384))
```

## Acceptance Criteria
- [ ] Service in docker-compose.yml
- [ ] Collection "incidents" created
- [ ] Health check passes
- [ ] HTTP at http://localhost:6333

**Effort**: 1h | **Priority**: High | **Dependencies**: None
