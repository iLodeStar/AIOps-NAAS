FROM timberio/vector:0.49.0-debian

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Keep the same entrypoint
ENTRYPOINT ["/usr/bin/vector"]