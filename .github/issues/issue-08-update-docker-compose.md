## Task
Add all V3 services to `docker-compose.yml`.

## Services to Add

```yaml
enrichment-service:
  build: ./services/enrichment-service
  depends_on: [nats, clickhouse]
  environment:
    NATS_URL: nats://nats:4222
    CLICKHOUSE_HOST: clickhouse

correlation-service:
  build: ./services/correlation-service
  depends_on: [nats, enrichment-service]
  
llm-enricher:
  build: ./services/llm-enricher
  depends_on: [nats, ollama, qdrant, clickhouse]
```

Merge Ollama and Qdrant from docker-compose.v3.yml.

## Acceptance Criteria
- [ ] All V3 services in docker-compose.yml
- [ ] Dependencies correct
- [ ] `docker-compose up` works
- [ ] Service order correct

**Effort**: 2h | **Priority**: Medium | **Dependencies**: #1-7
