## Objective
Add Ollama LLM service to docker-compose.yml and initialize with phi3:mini model.

## Required Changes
Add Ollama service to `docker-compose.yml` with health checks and volume mounts.
Create initialization script to pull phi3:mini model.

## Acceptance Criteria
- [ ] Ollama service added to docker-compose.yml
- [ ] phi3:mini model pulled and ready
- [ ] Health check passing
- [ ] API accessible at http://localhost:11434
- [ ] Initialization script created and tested

## Dependencies
- None (infrastructure component)

**Estimated Effort**: 1 hour  
**Sprint**: 2 (Week 2)  
**Priority**: High
