## Task
Add Ollama service to `docker-compose.yml`.

## Changes

1. **Add service**:
```yaml
ollama:
  image: ollama/ollama:latest
  ports: ["11434:11434"]
  volumes: [ollama_data:/root/.ollama]
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
```

2. **Init script** `scripts/init_ollama.sh`:
```bash
docker exec aiops-ollama ollama pull phi3:mini
```

## Acceptance Criteria
- [ ] Service in docker-compose.yml
- [ ] phi3:mini model ready
- [ ] Health check passes
- [ ] API at http://localhost:11434

**Effort**: 1h | **Priority**: High | **Dependencies**: None
