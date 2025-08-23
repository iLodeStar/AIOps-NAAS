#!/bin/bash

# Log Generator Script for AIOps NAAS
# Generates rotating JSON logs for testing Vector -> ClickHouse ingestion

LOG_DIR="/var/log/sample"
LOG_FILE="$LOG_DIR/app.log"
MAX_SIZE=10485760  # 10MB
MAX_FILES=5
INTERVAL=5

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Sample log levels and messages
declare -a LEVELS=("INFO" "WARN" "ERROR" "DEBUG")
declare -a SERVICES=("api-server" "database" "auth-service" "monitoring" "backup-service")
declare -a MESSAGES=(
    "Request processed successfully"
    "User authentication completed" 
    "Database query executed"
    "Cache hit for key"
    "Configuration reloaded"
    "Health check passed"
    "Backup job started"
    "Memory usage threshold exceeded"
    "Connection timeout to external service"
    "Rate limit exceeded for user"
    "Invalid request format received"
    "Database connection pool exhausted"
)

# Function to rotate logs
rotate_logs() {
    if [[ -f "$LOG_FILE" && $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_SIZE ]]; then
        for ((i=$MAX_FILES; i>1; i--)); do
            if [[ -f "$LOG_FILE.$((i-1))" ]]; then
                mv "$LOG_FILE.$((i-1))" "$LOG_FILE.$i"
            fi
        done
        mv "$LOG_FILE" "$LOG_FILE.1"
    fi
}

# Function to generate a log entry
generate_log() {
    local level=${LEVELS[$RANDOM % ${#LEVELS[@]}]}
    local service=${SERVICES[$RANDOM % ${#SERVICES[@]}]}
    local message=${MESSAGES[$RANDOM % ${#MESSAGES[@]}]}
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local request_id=$(openssl rand -hex 8)
    
    # Create JSON log entry
    cat <<EOF
{"timestamp":"$timestamp","level":"$level","message":"$message","service":"$service","host":"ship-01","component":"$service","request_id":"$request_id","environment":"local","version":"1.0.0"}
EOF
}

echo "Starting log generator..."
echo "Log file: $LOG_FILE"
echo "Interval: ${INTERVAL}s"
echo "Press Ctrl+C to stop"

while true; do
    # Rotate logs if needed
    rotate_logs
    
    # Generate and append log entry
    generate_log >> "$LOG_FILE"
    
    # Add some variety with burst logging occasionally
    if [[ $((RANDOM % 10)) -eq 0 ]]; then
        for i in {1..5}; do
            generate_log >> "$LOG_FILE"
        done
    fi
    
    sleep "$INTERVAL"
done