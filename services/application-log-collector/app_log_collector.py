#!/usr/bin/env python3
"""
AIOps NAAS - Application Log Collector Service

This service provides multiple ingestion methods for application logs from
Java, Node.js, Python, and other microservices with standardized processing.

Features:
- HTTP log endpoint for direct application integration
- TCP log receiver for traditional log shipping
- JSON log parsing and normalization
- Structured log forwarding to Vector/NATS
- Application health monitoring
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import nats
import aiohttp
from socketserver import ThreadingTCPServer, StreamRequestHandler
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for HTTP log ingestion
class LogEntry(BaseModel):
    timestamp: Optional[str] = None
    level: str = "INFO"
    message: str
    logger_name: Optional[str] = None
    service_name: str
    application: str
    host: Optional[str] = None
    thread: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LogBatch(BaseModel):
    logs: List[LogEntry]
    source_type: str = "http"  # http, tcp, file
    batch_id: Optional[str] = None

@dataclass
class StandardizedLogEntry:
    """Standardized log entry for internal processing"""
    timestamp: datetime
    level: str
    message: str
    source: str
    host: str
    service: str
    application: str
    logger_name: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    thread: Optional[str] = None
    metadata: Dict[str, Any] = None
    raw_log: str = ""

class TCPLogHandler(StreamRequestHandler):
    """TCP log handler for traditional log shipping"""
    
    def handle(self):
        """Handle incoming TCP log connections"""
        try:
            while True:
                data = self.rfile.readline()
                if not data:
                    break
                
                log_line = data.decode('utf-8').strip()
                if log_line:
                    # Process the log line
                    asyncio.create_task(self.server.log_collector.process_tcp_log(log_line, self.client_address[0]))
                    
        except Exception as e:
            logger.error(f"Error handling TCP log connection: {e}")

class ApplicationLogCollector:
    """Main application log collector service"""
    
    def __init__(self):
        self.nats_client = None
        self.tcp_server = None
        self.processed_logs = 0
        self.error_count = 0
        
        # Log level mapping
        self.level_mapping = {
            'trace': 'TRACE',
            'debug': 'DEBUG', 
            'info': 'INFO',
            'warn': 'WARN',
            'warning': 'WARN',
            'error': 'ERROR',
            'fatal': 'FATAL',
            'critical': 'FATAL'
        }
    
    async def connect_nats(self):
        """Connect to NATS for log forwarding"""
        try:
            self.nats_client = nats.NATS()
            await self.nats_client.connect("nats://nats:4222")
            logger.info("Connected to NATS for log forwarding")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
    
    def start_tcp_server(self, port: int = 5140):
        """Start TCP log server in background thread"""
        try:
            self.tcp_server = ThreadingTCPServer(('0.0.0.0', port), TCPLogHandler)
            self.tcp_server.log_collector = self  # Attach self reference
            
            # Start in background thread
            tcp_thread = threading.Thread(target=self.tcp_server.serve_forever, daemon=True)
            tcp_thread.start()
            
            logger.info(f"TCP log server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
    
    def normalize_log_level(self, level: str) -> str:
        """Normalize log level to standard format"""
        return self.level_mapping.get(level.lower(), level.upper())
    
    def parse_structured_log(self, log_line: str) -> Optional[Dict[str, Any]]:
        """Parse structured JSON log line"""
        try:
            return json.loads(log_line)
        except:
            # Try to parse common patterns
            patterns = [
                # Java Logback/Log4j pattern
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[.,]\d{3})\s+(\w+)\s+\[([^\]]+)\]\s+([^:]+):\s*(.*)',
                # Python logging pattern
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[.,]\d{3})\s*-\s*([^-]+)\s*-\s*(\w+)\s*-\s*(.*)',
                # Node.js winston pattern
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.,]\d{3}Z?)\s+(\w+):\s*(.*)'
            ]
            
            import re
            for pattern in patterns:
                match = re.match(pattern, log_line)
                if match:
                    groups = match.groups()
                    return {
                        'timestamp': groups[0],
                        'level': groups[1] if len(groups) > 1 else 'INFO',
                        'message': groups[-1],
                        'raw': log_line
                    }
            
            # Fallback: treat as plain message
            return {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': log_line,
                'raw': log_line
            }
    
    async def process_tcp_log(self, log_line: str, client_ip: str):
        """Process TCP log entry"""
        try:
            parsed = self.parse_structured_log(log_line)
            if not parsed:
                return
            
            # Create standardized log entry
            standardized = StandardizedLogEntry(
                timestamp=datetime.now(),
                level=self.normalize_log_level(parsed.get('level', 'INFO')),
                message=parsed.get('message', log_line),
                source='tcp_application',
                host=client_ip,
                service=parsed.get('service', 'unknown'),
                application=parsed.get('application', 'tcp-app'),
                logger_name=parsed.get('logger', None),
                trace_id=parsed.get('traceId', None),
                span_id=parsed.get('spanId', None),
                thread=parsed.get('thread', None),
                metadata={
                    'source_ip': client_ip,
                    'ingestion_method': 'tcp'
                },
                raw_log=log_line
            )
            
            await self.forward_log_to_pipeline(standardized)
            self.processed_logs += 1
            
        except Exception as e:
            logger.error(f"Error processing TCP log: {e}")
            self.error_count += 1
    
    async def process_http_log_batch(self, log_batch: LogBatch) -> Dict[str, Any]:
        """Process HTTP log batch"""
        processed_count = 0
        error_count = 0
        
        for log_entry in log_batch.logs:
            try:
                # Parse timestamp
                timestamp = datetime.now()
                if log_entry.timestamp:
                    try:
                        timestamp = datetime.fromisoformat(log_entry.timestamp.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Create standardized log entry
                standardized = StandardizedLogEntry(
                    timestamp=timestamp,
                    level=self.normalize_log_level(log_entry.level),
                    message=log_entry.message,
                    source='http_application',
                    host=log_entry.host or 'unknown',
                    service=log_entry.service_name,
                    application=log_entry.application,
                    logger_name=log_entry.logger_name,
                    trace_id=log_entry.trace_id,
                    span_id=log_entry.span_id,
                    thread=log_entry.thread,
                    metadata={
                        'ingestion_method': 'http',
                        'batch_id': log_batch.batch_id,
                        **(log_entry.metadata or {})
                    },
                    raw_log=json.dumps(log_entry.dict())
                )
                
                await self.forward_log_to_pipeline(standardized)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing log entry: {e}")
                error_count += 1
        
        self.processed_logs += processed_count
        self.error_count += error_count
        
        return {
            'processed': processed_count,
            'errors': error_count,
            'batch_id': log_batch.batch_id or str(uuid.uuid4())
        }
    
    async def forward_log_to_pipeline(self, log_entry: StandardizedLogEntry):
        """Forward standardized log to the data pipeline"""
        try:
            # Convert to Vector-compatible format
            vector_log = {
                'timestamp': log_entry.timestamp.isoformat(),
                'level': log_entry.level,
                'message': log_entry.message,
                'source': log_entry.source,
                'host': log_entry.host,
                'service': log_entry.service,
                'application': log_entry.application,
                'logger_name': log_entry.logger_name,
                'trace_id': log_entry.trace_id,
                'span_id': log_entry.span_id,
                'thread': log_entry.thread,
                'metadata': log_entry.metadata or {},
                'raw_log': log_entry.raw_log
            }
            
            # Send to NATS for Vector ingestion
            if self.nats_client and not self.nats_client.is_closed:
                await self.nats_client.publish(
                    "logs.applications",
                    json.dumps(vector_log).encode()
                )
            
            # Also send to data flow tracking
            flow_event = {
                'tracking_id': log_entry.trace_id or f"app-{uuid.uuid4().hex[:8]}",
                'stage': 'Application Log Collection',
                'component': 'application-log-collector',
                'status': 'completed',
                'data_size': len(log_entry.raw_log),
                'metadata': {
                    'application': log_entry.application,
                    'service': log_entry.service,
                    'level': log_entry.level
                }
            }
            
            if self.nats_client:
                await self.nats_client.publish(
                    "data.flow.application_logs",
                    json.dumps(flow_event).encode()
                )
            
        except Exception as e:
            logger.error(f"Error forwarding log to pipeline: {e}")
    
    async def get_application_configurations(self) -> Dict[str, Any]:
        """Get application configuration examples"""
        return {
            'java': {
                'logback_appender': {
                    'class': 'ch.qos.logback.core.net.SocketAppender',
                    'host': 'application-log-collector',
                    'port': 5140,
                    'includeCallerData': True
                },
                'http_example': '''
                // Java HTTP logging example
                RestTemplate restTemplate = new RestTemplate();
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                
                Map<String, Object> logEntry = Map.of(
                    "timestamp", Instant.now().toString(),
                    "level", "INFO",
                    "message", "User login successful",
                    "service_name", "auth-service",
                    "application", "cruise-management",
                    "host", InetAddress.getLocalHost().getHostName(),
                    "metadata", Map.of("userId", userId, "sessionId", sessionId)
                );
                
                HttpEntity<Map<String, Object>> request = new HttpEntity<>(logEntry, headers);
                restTemplate.postForObject("http://application-log-collector:8090/api/logs", request, String.class);
                '''
            },
            'nodejs': {
                'winston_transport': '''
                // Node.js Winston HTTP transport
                const winston = require('winston');
                
                const logger = winston.createLogger({
                    transports: [
                        new winston.transports.Http({
                            host: 'application-log-collector',
                            port: 8090,
                            path: '/api/logs/single',
                            format: winston.format.combine(
                                winston.format.timestamp(),
                                winston.format.json()
                            )
                        })
                    ]
                });
                
                logger.info('User action completed', {
                    service_name: 'navigation-service',
                    application: 'ship-control',
                    userId: 'user123',
                    action: 'course_change'
                });
                ''',
                'tcp_example': '''
                // Node.js TCP logging
                const net = require('net');
                
                const tcpLogger = net.createConnection(5140, 'application-log-collector');
                
                function log(level, message, metadata = {}) {
                    const logEntry = {
                        timestamp: new Date().toISOString(),
                        level,
                        message,
                        service_name: 'navigation-service',
                        application: 'ship-control',
                        host: require('os').hostname(),
                        metadata
                    };
                    
                    tcpLogger.write(JSON.stringify(logEntry) + '\\n');
                }
                '''
            },
            'python': {
                'http_handler': '''
                # Python HTTP logging handler
                import logging
                import json
                import requests
                from datetime import datetime
                
                class HTTPLogHandler(logging.Handler):
                    def __init__(self, url, service_name, application):
                        super().__init__()
                        self.url = url
                        self.service_name = service_name
                        self.application = application
                    
                    def emit(self, record):
                        log_entry = {
                            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                            'level': record.levelname,
                            'message': record.getMessage(),
                            'service_name': self.service_name,
                            'application': self.application,
                            'logger_name': record.name,
                            'host': 'localhost',
                            'metadata': {
                                'module': record.module,
                                'function': record.funcName,
                                'line': record.lineno
                            }
                        }
                        
                        try:
                            requests.post(self.url, json=log_entry, timeout=5)
                        except:
                            pass  # Don't fail the application if logging fails
                
                # Usage
                logger = logging.getLogger('my_service')
                handler = HTTPLogHandler(
                    'http://application-log-collector:8090/api/logs/single',
                    'data-processor',
                    'analytics-platform'
                )
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                ''',
                'sockethandler': '''
                # Python TCP SocketHandler
                import logging
                import logging.handlers
                
                # TCP Socket handler
                handler = logging.handlers.SocketHandler('application-log-collector', 5140)
                handler.setFormatter(logging.Formatter(
                    '{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s",'
                    '"service_name":"data-processor","application":"analytics-platform",'
                    '"logger_name":"%(name)s","thread":"%(thread)d"}'
                ))
                
                logger = logging.getLogger('my_service')
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                '''
            }
        }

# FastAPI app
app = FastAPI(title="AIOps Application Log Collector", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
service = ApplicationLogCollector()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await service.connect_nats()
    service.start_tcp_server()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "nats_connected": service.nats_client and not service.nats_client.is_closed,
        "tcp_server_running": service.tcp_server is not None,
        "processed_logs": service.processed_logs,
        "error_count": service.error_count
    }

@app.post("/api/logs")
async def ingest_log_batch(log_batch: LogBatch, background_tasks: BackgroundTasks):
    """Ingest a batch of log entries"""
    result = await service.process_http_log_batch(log_batch)
    return {
        "status": "accepted",
        "batch_result": result,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/logs/single")
async def ingest_single_log(log_entry: LogEntry, background_tasks: BackgroundTasks):
    """Ingest a single log entry"""
    batch = LogBatch(logs=[log_entry], source_type="http_single")
    result = await service.process_http_log_batch(batch)
    return {
        "status": "accepted",
        "log_id": result["batch_id"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/configurations")
async def get_configurations():
    """Get application integration configurations"""
    return await service.get_application_configurations()

@app.get("/api/stats")
async def get_stats():
    """Get collection statistics"""
    return {
        "processed_logs": service.processed_logs,
        "error_count": service.error_count,
        "error_rate": service.error_count / max(service.processed_logs, 1),
        "uptime_seconds": datetime.now().timestamp(),
        "nats_connected": service.nats_client and not service.nats_client.is_closed,
        "tcp_server_running": service.tcp_server is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)