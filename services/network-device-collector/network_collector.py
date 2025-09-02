#!/usr/bin/env python3
"""
Network Device Collector Service for Maritime AIOps

This service discovers and monitors maritime network infrastructure including:
- Switches (Cisco, Juniper, HP/Aruba, etc.)
- Bridges and network adapters
- Firewalls (Fortinet, Palo Alto, SonicWall)
- WiFi controllers and access points
- Routers and gateways
- Network attached storage and appliances

Features:
- SNMP-based discovery and monitoring
- Vendor-specific MIB support
- Network topology mapping
- Real-time health and performance metrics
- Integration with NATS for data streaming
- Prometheus metrics exposure
"""

import asyncio
import json
import logging
import time
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import nats
from pysnmp.hlapi.asyncio import *
from pysnmp.proto.rfc1902 import Counter64, Gauge32, Integer32
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import aiohttp
import networkx as nx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Network device types for maritime operations"""
    SWITCH = "switch"
    ROUTER = "router"
    FIREWALL = "firewall"
    WIFI_CONTROLLER = "wifi_controller"
    ACCESS_POINT = "access_point"
    BRIDGE = "bridge"
    LOAD_BALANCER = "load_balancer"
    NAS = "network_attached_storage"
    UPS = "uninterruptible_power_supply"
    UNKNOWN = "unknown"


@dataclass
class NetworkDevice:
    """Network device information"""
    ip_address: str
    hostname: str
    device_type: DeviceType
    vendor: str
    model: str
    version: str
    location: str
    snmp_community: str
    ports: int
    uptime_seconds: int
    last_seen: str


@dataclass
class InterfaceMetrics:
    """Network interface performance metrics"""
    interface_name: str
    interface_index: int
    admin_status: str
    oper_status: str
    in_octets: int
    out_octets: int
    in_packets: int
    out_packets: int
    in_errors: int
    out_errors: int
    in_discards: int
    out_discards: int
    speed_bps: int
    utilization_percent: float
    timestamp: str


@dataclass
class DeviceHealthMetrics:
    """Device health and environmental metrics"""
    device_ip: str
    cpu_utilization_percent: float
    memory_utilization_percent: float
    temperature_celsius: float
    power_supply_status: str
    fan_status: str
    disk_utilization_percent: float
    active_sessions: int
    error_count: int
    timestamp: str


class MIBRegistry:
    """Registry of SNMP OIDs for different device types and vendors"""
    
    # Standard RFC MIBs
    SYSTEM_OID = "1.3.6.1.2.1.1"
    INTERFACES_OID = "1.3.6.1.2.1.2"
    IP_OID = "1.3.6.1.2.1.4"
    ICMP_OID = "1.3.6.1.2.1.5"
    TCP_OID = "1.3.6.1.2.1.6"
    UDP_OID = "1.3.6.1.2.1.7"
    
    # Common OIDs
    OID_SYSTEM_DESCR = "1.3.6.1.2.1.1.1.0"
    OID_SYSTEM_NAME = "1.3.6.1.2.1.1.5.0"
    OID_SYSTEM_UPTIME = "1.3.6.1.2.1.1.3.0"
    OID_IF_TABLE = "1.3.6.1.2.1.2.2.1"
    
    # Vendor-specific OIDs
    CISCO_OID_BASE = "1.3.6.1.4.1.9"
    JUNIPER_OID_BASE = "1.3.6.1.4.1.2636"
    HP_OID_BASE = "1.3.6.1.4.1.11"
    FORTINET_OID_BASE = "1.3.6.1.4.1.12356"
    
    # Cisco specific
    CISCO_CPU_UTIL = "1.3.6.1.4.1.9.9.109.1.1.1.1.7"
    CISCO_MEMORY_UTIL = "1.3.6.1.4.1.9.9.48.1.1.1.5"
    CISCO_TEMPERATURE = "1.3.6.1.4.1.9.9.13.1.3.1.3"
    
    # Interface status OIDs
    IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
    IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
    IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
    IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"
    IF_IN_PACKETS = "1.3.6.1.2.1.2.2.1.11"
    IF_OUT_PACKETS = "1.3.6.1.2.1.2.2.1.17"
    IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
    IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
    IF_SPEED = "1.3.6.1.2.1.2.2.1.5"


class NetworkDeviceCollector:
    """Main collector service for network devices"""
    
    def __init__(self, config_path: str = "/app/config.yaml"):
        self.config = self._load_config(config_path)
        self.devices: Dict[str, NetworkDevice] = {}
        self.network_topology = nx.Graph()
        self.nats_client = None
        
        # Prometheus metrics
        self.device_count = Gauge('network_devices_total', 'Total number of network devices', ['type', 'vendor'])
        self.interface_utilization = Gauge('network_interface_utilization_percent', 
                                         'Interface utilization percentage', 
                                         ['device', 'interface'])
        self.device_cpu = Gauge('network_device_cpu_percent', 'Device CPU utilization', ['device', 'type'])
        self.device_memory = Gauge('network_device_memory_percent', 'Device memory utilization', ['device', 'type'])
        self.collection_duration = Histogram('network_collection_duration_seconds', 'Collection duration')
        self.collection_errors = Counter('network_collection_errors_total', 'Collection errors', ['error_type'])
        
    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for maritime network discovery"""
        return {
            'discovery': {
                'ip_ranges': ['192.168.1.0/24', '10.0.0.0/24'],
                'snmp_communities': ['public', 'private'],
                'scan_interval': 300,
                'timeout': 5,
                'retries': 3
            },
            'monitoring': {
                'polling_interval': 30,
                'interface_monitoring': True,
                'health_monitoring': True,
                'topology_discovery': True
            },
            'nats': {
                'servers': ['nats://nats:4222'],
                'subjects': {
                    'device_discovery': 'telemetry.network.discovery',
                    'interface_metrics': 'telemetry.network.interfaces',
                    'device_health': 'telemetry.network.health',
                    'topology_changes': 'telemetry.network.topology'
                }
            },
            'maritime_context': {
                'location_integration': True,
                'weather_correlation': True,
                'satellite_link_awareness': True
            }
        }
    
    async def start(self):
        """Start the network device collector service"""
        logger.info("Starting Network Device Collector Service")
        
        # Start Prometheus metrics server
        start_http_server(8080)
        logger.info("Prometheus metrics server started on port 8080")
        
        # Connect to NATS
        await self._connect_nats()
        
        # Start background tasks
        discovery_task = asyncio.create_task(self._discovery_loop())
        monitoring_task = asyncio.create_task(self._monitoring_loop())
        topology_task = asyncio.create_task(self._topology_discovery_loop())
        
        # Wait for tasks
        await asyncio.gather(discovery_task, monitoring_task, topology_task)
    
    async def _connect_nats(self):
        """Connect to NATS message broker"""
        try:
            self.nats_client = await nats.connect(servers=self.config['nats']['servers'])
            logger.info("Connected to NATS")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.collection_errors.labels(error_type='nats_connection').inc()
    
    async def _discovery_loop(self):
        """Main device discovery loop"""
        logger.info("Starting device discovery loop")
        
        while True:
            try:
                with self.collection_duration.time():
                    await self._discover_devices()
                
                await asyncio.sleep(self.config['discovery']['scan_interval'])
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                self.collection_errors.labels(error_type='discovery').inc()
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _discover_devices(self):
        """Discover network devices via SNMP"""
        logger.info("Starting device discovery")
        
        for ip_range in self.config['discovery']['ip_ranges']:
            await self._scan_ip_range(ip_range)
        
        # Update device counts
        self._update_device_metrics()
        
        # Publish discovery results
        await self._publish_discovery_results()
    
    async def _scan_ip_range(self, ip_range: str):
        """Scan IP range for SNMP-enabled devices"""
        import ipaddress
        
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            
            for ip in network.hosts():
                ip_str = str(ip)
                await self._probe_device(ip_str)
                
        except Exception as e:
            logger.error(f"Error scanning IP range {ip_range}: {e}")
            self.collection_errors.labels(error_type='ip_scan').inc()
    
    async def _probe_device(self, ip_address: str):
        """Probe a single device for SNMP availability"""
        for community in self.config['discovery']['snmp_communities']:
            try:
                # Try to get system description
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(community),
                    UdpTransportTarget((ip_address, 161)),
                    ContextData(),
                    ObjectType(ObjectIdentity(MIBRegistry.OID_SYSTEM_DESCR))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = await iterator
                
                if errorIndication or errorStatus:
                    continue
                    
                # Device responded to SNMP
                await self._identify_device(ip_address, community, varBinds[0][1])
                break
                
            except Exception as e:
                continue  # Try next community
    
    async def _identify_device(self, ip_address: str, community: str, system_descr):
        """Identify device type and vendor from system description"""
        system_descr_str = str(system_descr).lower()
        
        # Vendor identification
        vendor = "unknown"
        device_type = DeviceType.UNKNOWN
        
        if "cisco" in system_descr_str:
            vendor = "cisco"
            if "switch" in system_descr_str or "catalyst" in system_descr_str:
                device_type = DeviceType.SWITCH
            elif "router" in system_descr_str or "asr" in system_descr_str:
                device_type = DeviceType.ROUTER
            elif "asa" in system_descr_str or "firewall" in system_descr_str:
                device_type = DeviceType.FIREWALL
        elif "juniper" in system_descr_str:
            vendor = "juniper"
            if "ex" in system_descr_str or "switch" in system_descr_str:
                device_type = DeviceType.SWITCH
            elif "mx" in system_descr_str or "router" in system_descr_str:
                device_type = DeviceType.ROUTER
        elif "fortinet" in system_descr_str or "fortigate" in system_descr_str:
            vendor = "fortinet"
            device_type = DeviceType.FIREWALL
        elif "hp" in system_descr_str or "hewlett" in system_descr_str or "aruba" in system_descr_str:
            vendor = "hp"
            if "switch" in system_descr_str or "procurve" in system_descr_str:
                device_type = DeviceType.SWITCH
            elif "wireless" in system_descr_str or "controller" in system_descr_str:
                device_type = DeviceType.WIFI_CONTROLLER
        
        # Get additional device info
        device_info = await self._get_device_info(ip_address, community)
        
        device = NetworkDevice(
            ip_address=ip_address,
            hostname=device_info.get('hostname', ip_address),
            device_type=device_type,
            vendor=vendor,
            model=device_info.get('model', 'unknown'),
            version=device_info.get('version', 'unknown'),
            location=device_info.get('location', 'ship_network'),
            snmp_community=community,
            ports=device_info.get('ports', 0),
            uptime_seconds=device_info.get('uptime', 0),
            last_seen=datetime.now().isoformat()
        )
        
        self.devices[ip_address] = device
        logger.info(f"Discovered {vendor} {device_type.value} at {ip_address}")
    
    async def _get_device_info(self, ip_address: str, community: str) -> Dict[str, Any]:
        """Get additional device information via SNMP"""
        info = {}
        
        try:
            # Get system name and uptime
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((ip_address, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(MIBRegistry.OID_SYSTEM_NAME)),
                ObjectType(ObjectIdentity(MIBRegistry.OID_SYSTEM_UPTIME))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = await iterator
            
            if not errorIndication and not errorStatus:
                info['hostname'] = str(varBinds[0][1])
                info['uptime'] = int(varBinds[1][1])
            
        except Exception as e:
            logger.debug(f"Error getting device info for {ip_address}: {e}")
            
        return info
    
    async def _monitoring_loop(self):
        """Main monitoring loop for discovered devices"""
        logger.info("Starting device monitoring loop")
        
        while True:
            try:
                if self.devices:
                    await self._collect_metrics()
                
                await asyncio.sleep(self.config['monitoring']['polling_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.collection_errors.labels(error_type='monitoring').inc()
                await asyncio.sleep(30)
    
    async def _collect_metrics(self):
        """Collect metrics from all discovered devices"""
        tasks = []
        
        for ip_address, device in self.devices.items():
            if self.config['monitoring']['interface_monitoring']:
                tasks.append(self._collect_interface_metrics(device))
            
            if self.config['monitoring']['health_monitoring']:
                tasks.append(self._collect_health_metrics(device))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _collect_interface_metrics(self, device: NetworkDevice):
        """Collect interface metrics from a device"""
        try:
            # Walk interface table
            iterator = nextCmd(
                SnmpEngine(),
                CommunityData(device.snmp_community),
                UdpTransportTarget((device.ip_address, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(MIBRegistry.OID_IF_TABLE)),
                lexicographicMode=False
            )
            
            interfaces = []
            
            async for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication or errorStatus:
                    break
                
                for varBind in varBinds:
                    oid, value = varBind
                    # Process interface metrics
                    # This would need more detailed implementation for full interface metrics
            
            # Publish interface metrics
            if interfaces:
                await self._publish_interface_metrics(device, interfaces)
                
        except Exception as e:
            logger.error(f"Error collecting interface metrics from {device.ip_address}: {e}")
            self.collection_errors.labels(error_type='interface_metrics').inc()
    
    async def _collect_health_metrics(self, device: NetworkDevice):
        """Collect health metrics from a device"""
        try:
            health_metrics = DeviceHealthMetrics(
                device_ip=device.ip_address,
                cpu_utilization_percent=0.0,
                memory_utilization_percent=0.0,
                temperature_celsius=0.0,
                power_supply_status="unknown",
                fan_status="unknown",
                disk_utilization_percent=0.0,
                active_sessions=0,
                error_count=0,
                timestamp=datetime.now().isoformat()
            )
            
            # Vendor-specific health metric collection
            if device.vendor == "cisco":
                await self._collect_cisco_health(device, health_metrics)
            elif device.vendor == "juniper":
                await self._collect_juniper_health(device, health_metrics)
            
            # Update Prometheus metrics
            self.device_cpu.labels(device=device.ip_address, type=device.device_type.value).set(
                health_metrics.cpu_utilization_percent)
            self.device_memory.labels(device=device.ip_address, type=device.device_type.value).set(
                health_metrics.memory_utilization_percent)
            
            # Publish health metrics
            await self._publish_health_metrics(health_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting health metrics from {device.ip_address}: {e}")
            self.collection_errors.labels(error_type='health_metrics').inc()
    
    async def _collect_cisco_health(self, device: NetworkDevice, health_metrics: DeviceHealthMetrics):
        """Collect Cisco-specific health metrics"""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(device.snmp_community),
                UdpTransportTarget((device.ip_address, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(MIBRegistry.CISCO_CPU_UTIL)),
                ObjectType(ObjectIdentity(MIBRegistry.CISCO_MEMORY_UTIL))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = await iterator
            
            if not errorIndication and not errorStatus:
                health_metrics.cpu_utilization_percent = float(varBinds[0][1])
                health_metrics.memory_utilization_percent = float(varBinds[1][1])
                
        except Exception as e:
            logger.debug(f"Error collecting Cisco health metrics: {e}")
    
    async def _collect_juniper_health(self, device: NetworkDevice, health_metrics: DeviceHealthMetrics):
        """Collect Juniper-specific health metrics"""
        # Placeholder for Juniper-specific health collection
        pass
    
    async def _topology_discovery_loop(self):
        """Discover network topology using LLDP/CDP"""
        logger.info("Starting topology discovery loop")
        
        while True:
            try:
                if self.config['monitoring']['topology_discovery']:
                    await self._discover_topology()
                
                await asyncio.sleep(600)  # Run every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in topology discovery: {e}")
                self.collection_errors.labels(error_type='topology').inc()
                await asyncio.sleep(300)
    
    async def _discover_topology(self):
        """Discover network topology relationships"""
        logger.info("Discovering network topology")
        
        # This would implement CDP/LLDP neighbor discovery
        # For now, create basic topology based on device discovery
        
        self.network_topology.clear()
        
        for device in self.devices.values():
            self.network_topology.add_node(
                device.ip_address,
                type=device.device_type.value,
                vendor=device.vendor,
                hostname=device.hostname
            )
        
        # Publish topology changes
        await self._publish_topology_changes()
    
    def _update_device_metrics(self):
        """Update Prometheus device count metrics"""
        device_counts = {}
        
        for device in self.devices.values():
            key = (device.device_type.value, device.vendor)
            device_counts[key] = device_counts.get(key, 0) + 1
        
        # Clear previous metrics
        self.device_count.clear()
        
        # Set new metrics
        for (device_type, vendor), count in device_counts.items():
            self.device_count.labels(type=device_type, vendor=vendor).set(count)
    
    async def _publish_discovery_results(self):
        """Publish device discovery results to NATS"""
        if not self.nats_client:
            return
        
        try:
            discovery_data = {
                "timestamp": datetime.now().isoformat(),
                "total_devices": len(self.devices),
                "devices": [asdict(device) for device in self.devices.values()],
                "maritime_context": {
                    "location": "ship_network",
                    "collection_method": "snmp_discovery"
                }
            }
            
            await self.nats_client.publish(
                self.config['nats']['subjects']['device_discovery'],
                json.dumps(discovery_data).encode()
            )
            
            logger.info(f"Published discovery results for {len(self.devices)} devices")
            
        except Exception as e:
            logger.error(f"Error publishing discovery results: {e}")
            self.collection_errors.labels(error_type='nats_publish').inc()
    
    async def _publish_interface_metrics(self, device: NetworkDevice, interfaces: List[InterfaceMetrics]):
        """Publish interface metrics to NATS"""
        if not self.nats_client or not interfaces:
            return
        
        try:
            metrics_data = {
                "device_ip": device.ip_address,
                "device_type": device.device_type.value,
                "vendor": device.vendor,
                "timestamp": datetime.now().isoformat(),
                "interfaces": [asdict(interface) for interface in interfaces],
                "maritime_context": {
                    "location": "ship_network",
                    "critical_communications": True
                }
            }
            
            await self.nats_client.publish(
                self.config['nats']['subjects']['interface_metrics'],
                json.dumps(metrics_data).encode()
            )
            
        except Exception as e:
            logger.error(f"Error publishing interface metrics: {e}")
            self.collection_errors.labels(error_type='nats_publish').inc()
    
    async def _publish_health_metrics(self, health_metrics: DeviceHealthMetrics):
        """Publish device health metrics to NATS"""
        if not self.nats_client:
            return
        
        try:
            health_data = asdict(health_metrics)
            health_data["maritime_context"] = {
                "location": "ship_network",
                "environmental_monitoring": True,
                "critical_infrastructure": True
            }
            
            await self.nats_client.publish(
                self.config['nats']['subjects']['device_health'],
                json.dumps(health_data).encode()
            )
            
        except Exception as e:
            logger.error(f"Error publishing health metrics: {e}")
            self.collection_errors.labels(error_type='nats_publish').inc()
    
    async def _publish_topology_changes(self):
        """Publish network topology changes to NATS"""
        if not self.nats_client:
            return
        
        try:
            topology_data = {
                "timestamp": datetime.now().isoformat(),
                "nodes": list(self.network_topology.nodes(data=True)),
                "edges": list(self.network_topology.edges(data=True)),
                "maritime_context": {
                    "location": "ship_network",
                    "topology_type": "layer2_discovery"
                }
            }
            
            await self.nats_client.publish(
                self.config['nats']['subjects']['topology_changes'],
                json.dumps(topology_data).encode()
            )
            
            logger.info(f"Published topology with {len(self.network_topology.nodes())} nodes")
            
        except Exception as e:
            logger.error(f"Error publishing topology changes: {e}")
            self.collection_errors.labels(error_type='nats_publish').inc()


async def main():
    """Main entry point"""
    logger.info("Starting Network Device Collector Service")
    
    collector = NetworkDeviceCollector()
    
    try:
        await collector.start()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())