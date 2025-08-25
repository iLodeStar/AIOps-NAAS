#!/usr/bin/env bash
# Push synthetic metrics to VictoriaMetrics using Influx line protocol.
set -euo pipefail

VM_URL="${VM_URL:-http://localhost:8428}"
HOSTS=("edge-1" "edge-2" "edge-3")

echo "[simulate] Sending synthetic metrics to ${VM_URL}/write ..."
for i in $(seq 1 50); do
  ts=$(date +%s%N)
  for h in "${HOSTS[@]}"; do
    cpu=$(awk -v min=10 -v max=90 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
    mem=$(awk -v min=20 -v max=95 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
    loss=$(awk -v min=0 -v max=5 'BEGIN{srand(); printf "%.2f", min+rand()*(max-min)}')
    lat=$(awk -v min=5 -v max=200 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
    body="cpu_usage,host=${h} value=${cpu} ${ts}
mem_usage,host=${h} value=${mem} ${ts}
packet_loss,host=${h} value=${loss} ${ts}
latency_ms,host=${h} value=${lat} ${ts}"
    curl -fsS -X POST "${VM_URL}/write" --data-binary "$body" >/dev/null || true
  done
  sleep 0.2
done
echo "[simulate] Done. Try building a Grafana panel from 'cpu_usage' or 'latency_ms'."