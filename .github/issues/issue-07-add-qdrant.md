## Objective
Add Qdrant vector database to docker-compose.yml and initialize incidents collection.

## Required Changes
Add Qdrant service to `docker-compose.yml`.
Create collection initialization script.

## Acceptance Criteria
- [ ] Qdrant service added to docker-compose.yml
- [ ] Collection "incidents" created
- [ ] Health check passing
- [ ] HTTP API accessible at http://localhost:6333
- [ ] gRPC API accessible at localhost:6334
- [ ] Initialization script created and tested

## Dependencies
- None (infrastructure component)

**Estimated Effort**: 1 hour  
**Sprint**: 2 (Week 2)  
**Priority**: High
