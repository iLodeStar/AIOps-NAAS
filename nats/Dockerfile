# Custom NATS image with CLI tools for debugging
FROM nats:alpine

# Install NATS CLI (stable release v0.1.5)
RUN apk add --no-cache curl unzip && \
    VERSION=0.1.5 && \
    ARCH=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/') && \
    curl -L "https://github.com/nats-io/natscli/releases/download/v${VERSION}/nats-${VERSION}-linux-${ARCH}.zip" -o nats.zip && \
    unzip nats.zip && \
    mv nats-${VERSION}-linux-${ARCH}/nats /usr/local/bin/ && \
    chmod +x /usr/local/bin/nats && \
    rm -rf nats.zip nats-${VERSION}-linux-${ARCH} && \
    apk del curl unzip

# Verify CLI installed
RUN nats --version

# DO NOT override ENTRYPOINT, keep base image entrypoint:
# ENTRYPOINT ["/usr/local/bin/nats-server"]

