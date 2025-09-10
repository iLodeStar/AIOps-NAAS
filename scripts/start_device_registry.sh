#!/bin/bash
# Quick start script for Device Registry & Mapping Service

echo "🏗️  AIOps Device Registry & Mapping Service - Quick Start"
echo "=========================================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker and docker-compose are available"

# Start the device registry service
echo "🚀 Starting Device Registry service..."
docker-compose up -d device-registry

# Wait for service to be ready
echo "⏳ Waiting for Device Registry to be ready..."
sleep 10

# Check health
for i in {1..30}; do
    if curl -f http://localhost:8081/health &> /dev/null; then
        echo "✅ Device Registry is healthy and ready!"
        break
    else
        echo "⏳ Waiting for service to start... ($i/30)"
        sleep 2
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to start within 60 seconds"
        echo "📋 Checking logs:"
        docker-compose logs device-registry
        exit 1
    fi
done

# Show service information
echo ""
echo "📊 Device Registry Service Information:"
echo "  Service URL: http://localhost:8081"
echo "  Health Check: http://localhost:8081/health"
echo "  API Documentation: http://localhost:8081/docs"
echo "  Statistics: http://localhost:8081/stats"

echo ""
echo "🖥️  Interactive Registration Script:"
echo "  Run: python scripts/register_device.py"
echo "  Or with custom URL: python scripts/register_device.py --registry-url http://localhost:8081"

echo ""
echo "📋 Quick API Tests:"
echo "  # Check health"
echo "  curl http://localhost:8081/health"
echo ""
echo "  # Get statistics"
echo "  curl http://localhost:8081/stats"
echo ""
echo "  # List ships"
echo "  curl http://localhost:8081/ships"

echo ""
echo "🔧 Example Usage:"
echo "  # Create a ship"
echo "  curl -X POST http://localhost:8081/ships \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"ship_id\":\"ship-aurora\",\"name\":\"MSC Aurora\"}'"
echo ""
echo "  # Register a device"  
echo "  curl -X POST http://localhost:8081/devices/register \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"hostname\":\"ubuntu-vm-01\",\"ship_id\":\"ship-aurora\",\"device_type\":\"server\"}'"
echo ""
echo "  # Lookup hostname"
echo "  curl http://localhost:8081/lookup/ubuntu-vm-01"

echo ""
echo "✅ Device Registry is now running!"
echo "🎯 Use the interactive script for easy device registration: python scripts/register_device.py"