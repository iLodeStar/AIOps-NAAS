#!/usr/bin/env python3
"""
Initialize Qdrant vector database with required collections.

This script creates the "incidents" collection in Qdrant for storing
incident embeddings used in RAG/LLM functionality.

Usage:
    python3 scripts/init_qdrant.py
    python3 scripts/init_qdrant.py --host qdrant.example.com --port 6333
    QDRANT_HOST=qdrant.example.com python3 scripts/init_qdrant.py
"""

import argparse
import os
import sys
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

def wait_for_qdrant(client: QdrantClient, max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for Qdrant to be ready."""
    for attempt in range(max_retries):
        try:
            client.get_collections()
            print(f"✓ Qdrant is ready (attempt {attempt + 1})")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Waiting for Qdrant... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"✗ Failed to connect to Qdrant after {max_retries} attempts: {e}")
                return False
    return False

def init_qdrant(host: str = "localhost", port: int = 6333):
    """Initialize Qdrant with required collections."""
    print(f"Connecting to Qdrant at {host}:{port}...")
    client = QdrantClient(host=host, port=port)
    
    # Wait for Qdrant to be ready
    if not wait_for_qdrant(client):
        print("✗ Qdrant is not available")
        sys.exit(1)
    
    # Check if "incidents" collection already exists
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if "incidents" in collection_names:
            print("✓ Collection 'incidents' already exists")
            # Get collection info
            collection_info = client.get_collection("incidents")
            print(f"  - Vector size: {collection_info.config.params.vectors.size}")
            print(f"  - Distance: {collection_info.config.params.vectors.distance}")
            
            # Validate configuration
            if collection_info.config.params.vectors.size != 384:
                print(f"  ⚠ Warning: Expected vector size 384, found {collection_info.config.params.vectors.size}")
            return
    except Exception as e:
        print(f"Warning: Could not check existing collections: {e}")
    
    # Create "incidents" collection with 384-dimensional vectors
    # Using 384 dimensions which is standard for sentence-transformers models
    # like 'all-MiniLM-L6-v2' commonly used for embeddings
    try:
        print("Creating 'incidents' collection...")
        client.create_collection(
            collection_name="incidents",
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )
        print("✓ Collection 'incidents' created successfully")
        print("  - Vector size: 384")
        print("  - Distance metric: COSINE")
        
        # Validate the created collection
        collection_info = client.get_collection("incidents")
        actual_size = collection_info.config.params.vectors.size
        if actual_size == 384:
            print("✓ Collection validated successfully")
        else:
            print(f"✗ Validation failed: Expected size 384, got {actual_size}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed to create collection 'incidents': {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Initialize Qdrant vector database with incidents collection"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("QDRANT_HOST", "localhost"),
        help="Qdrant host (default: localhost or QDRANT_HOST env var)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("QDRANT_PORT", "6333")),
        help="Qdrant port (default: 6333 or QDRANT_PORT env var)"
    )
    
    args = parser.parse_args()
    init_qdrant(host=args.host, port=args.port)
