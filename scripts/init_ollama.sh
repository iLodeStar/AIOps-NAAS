#!/bin/bash
set -euo pipefail

# Simple Ollama Initialization Script
# Pulls phi3:mini model into the running Ollama container

CONTAINER_NAME="aiops-ollama"
MODEL_NAME="phi3:mini"

echo "[init_ollama] Pulling ${MODEL_NAME} model into ${CONTAINER_NAME}..."

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[init_ollama] ERROR: Container ${CONTAINER_NAME} is not running."
    echo "[init_ollama] Please start it first with: docker compose up -d ollama"
    exit 1
fi

echo "[init_ollama] Executing: docker exec ${CONTAINER_NAME} ollama pull ${MODEL_NAME}"
docker exec "${CONTAINER_NAME}" ollama pull "${MODEL_NAME}"

echo "[init_ollama] Successfully pulled ${MODEL_NAME} model"
echo "[init_ollama] You can now use the model via: http://localhost:11434/api/generate"
