# Custom NATS image with CLI tools for debugging
FROM nats:alpine

# Install NATS CLI for debugging
RUN apk update && \
    apk add --no-cache curl && \
    curl -sf https://binaries.nats.dev/nats-io/nats/v2@latest | sh && \
    mv nats /usr/local/bin/ && \
    chmod +x /usr/local/bin/nats && \
    apk del curl && \
    rm -rf /var/cache/apk/*

# Verify NATS CLI installation
RUN nats --version

# Use default NATS server entrypoint
ENTRYPOINT ["/nats-server"]