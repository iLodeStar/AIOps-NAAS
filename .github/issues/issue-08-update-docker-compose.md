## Objective
Add all V3 services to main docker-compose.yml with proper dependencies and configuration.

## Services to Add
- enrichment-service
- correlation-service
- llm-enricher
- Merge Ollama and Qdrant from docker-compose.v3.yml

## Acceptance Criteria
- [ ] All V3 services added to docker-compose.yml
- [ ] Dependencies correctly configured
- [ ] Environment variables set
- [ ] Health checks defined for all services
- [ ] `docker-compose up` starts all services successfully
- [ ] Service startup order correct

## Dependencies
- Issues #1, #2, #3, #4 (services must exist)
- Issues #6, #7 (Ollama and Qdrant services)

**Estimated Effort**: 2 hours  
**Sprint**: 3 (Week 3)  
**Priority**: Medium
