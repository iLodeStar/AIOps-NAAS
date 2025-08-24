#!/usr/bin/env python3
"""
AIOps NAAS NATS Consumer

Subscribes to NATS subjects and logs messages for testing and debugging.
Can be used to capture data during soak testing.

Usage:
    python3 consumer.py --subjects "telemetry.*" "link.health.*" --duration 600
    python3 consumer.py --subjects "link.health.prediction" "link.health.alert" --output consumer_log.json
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from nats.aio.client import Client as NATS
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    print("Error: NATS not available. Install with: pip install nats-py")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NATSConsumer:
    """NATS message consumer and logger"""
    
    def __init__(self, subjects: List[str], output_file: Optional[str] = None):
        self.subjects = subjects
        self.output_file = output_file
        self.nats_client = None
        self.running = False
        self.message_count = 0
        self.messages = []
        self.subject_stats = {}
        
    async def connect_nats(self, nats_url: str = "nats://localhost:4222"):
        """Connect to NATS server"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect(nats_url)
            logger.info(f"Connected to NATS at {nats_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    async def message_handler(self, msg):
        """Handle incoming NATS messages"""
        try:
            subject = msg.subject
            data = json.loads(msg.data.decode())
            timestamp = datetime.now()
            
            # Store message with metadata
            message_record = {
                'timestamp': timestamp.isoformat(),
                'subject': subject,
                'data': data,
                'size_bytes': len(msg.data)
            }
            
            self.messages.append(message_record)
            self.message_count += 1
            
            # Update subject statistics
            if subject not in self.subject_stats:
                self.subject_stats[subject] = {
                    'count': 0,
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'total_bytes': 0
                }
            
            self.subject_stats[subject]['count'] += 1
            self.subject_stats[subject]['last_seen'] = timestamp
            self.subject_stats[subject]['total_bytes'] += len(msg.data)
            
            # Log message (compact format)
            logger.info(f"[{subject}] {json.dumps(data, default=str)}")
            
            # Periodic stats
            if self.message_count % 50 == 0:
                self._log_stats()
                
        except Exception as e:
            logger.error(f"Error processing message from {msg.subject}: {e}")
    
    def _log_stats(self):
        """Log consumer statistics"""
        logger.info(f"Messages received: {self.message_count}")
        for subject, stats in self.subject_stats.items():
            logger.info(f"  {subject}: {stats['count']} messages, {stats['total_bytes']} bytes")
    
    async def subscribe_to_subjects(self):
        """Subscribe to configured NATS subjects"""
        subscriptions = []
        
        for subject in self.subjects:
            try:
                sub = await self.nats_client.subscribe(subject, cb=self.message_handler)
                subscriptions.append(sub)
                logger.info(f"Subscribed to {subject}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {subject}: {e}")
        
        return subscriptions
    
    async def run_consumer(self, duration_seconds: Optional[int] = None):
        """Run the consumer for specified duration or indefinitely"""
        if not await self.connect_nats():
            return False
        
        logger.info(f"Starting consumer for subjects: {self.subjects}")
        if duration_seconds:
            logger.info(f"Duration: {duration_seconds} seconds")
        else:
            logger.info("Duration: indefinite (Ctrl+C to stop)")
        
        # Subscribe to subjects
        subscriptions = await self.subscribe_to_subjects()
        if not subscriptions:
            logger.error("No successful subscriptions - exiting")
            return False
        
        self.running = True
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds) if duration_seconds else None
        
        try:
            # Main consumer loop
            while self.running:
                # Check if duration exceeded
                if end_time and datetime.now() >= end_time:
                    logger.info("Duration completed")
                    break
                
                # Sleep briefly to allow message processing
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.running = False
            
            # Unsubscribe
            for sub in subscriptions:
                try:
                    await sub.unsubscribe()
                except:
                    pass
            
            # Close NATS connection
            if self.nats_client:
                await self.nats_client.close()
                logger.info("NATS connection closed")
        
        # Final statistics
        elapsed = datetime.now() - start_time
        logger.info(f"Consumer finished after {elapsed.total_seconds():.1f} seconds")
        logger.info(f"Total messages received: {self.message_count}")
        
        # Detailed stats per subject
        for subject, stats in self.subject_stats.items():
            duration = (stats['last_seen'] - stats['first_seen']).total_seconds()
            rate = stats['count'] / max(duration, 1)
            logger.info(f"  {subject}: {stats['count']} messages, "
                       f"{stats['total_bytes']} bytes, {rate:.2f} msg/sec")
        
        # Save to file if specified
        if self.output_file:
            await self.save_to_file()
        
        return True
    
    async def save_to_file(self):
        """Save consumed messages to JSON file"""
        try:
            output_data = {
                'consumer_info': {
                    'subjects': self.subjects,
                    'total_messages': self.message_count,
                    'start_time': min(msg['timestamp'] for msg in self.messages) if self.messages else None,
                    'end_time': max(msg['timestamp'] for msg in self.messages) if self.messages else None,
                    'subject_stats': {
                        subject: {
                            'count': stats['count'],
                            'total_bytes': stats['total_bytes'],
                            'first_seen': stats['first_seen'].isoformat(),
                            'last_seen': stats['last_seen'].isoformat()
                        }
                        for subject, stats in self.subject_stats.items()
                    }
                },
                'messages': self.messages
            }
            
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            logger.info(f"Saved {self.message_count} messages to {self.output_file}")
            logger.info(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
            
        except Exception as e:
            logger.error(f"Failed to save to file {self.output_file}: {e}")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AIOps NAAS NATS Consumer")
    parser.add_argument("--subjects", nargs="+", required=True,
                       help="NATS subjects to subscribe to (supports wildcards)")
    parser.add_argument("--duration", type=int,
                       help="Consumer duration in seconds (default: run indefinitely)")
    parser.add_argument("--nats-url", default="nats://localhost:4222",
                       help="NATS server URL (default: nats://localhost:4222)")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--log-level", default="INFO", 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help="Log level")
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and run consumer
    consumer = NATSConsumer(args.subjects, args.output)
    success = await consumer.run_consumer(args.duration)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())