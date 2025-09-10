#!/usr/bin/env python3
"""
Interactive Device Registration Script
Provides a user-friendly CLI for registering devices with BOTH hostname AND IP address
requirements, with auto-generated device IDs and auto-detection of current system identifiers.

IMPORTANT: This service now requires BOTH hostname AND IP address for device registration.
The registry enforces "hostname AND ip" instead of the previous "hostname OR ip" approach.
"""

import sys
import json
import requests
import socket
import subprocess
import platform
from typing import Dict, List, Optional, Tuple
import argparse
from datetime import datetime


def get_system_identifiers() -> Tuple[str, List[str]]:
    """Auto-detect current system hostname and IP addresses"""
    try:
        # Get hostname
        hostname = socket.gethostname()
        
        # Get IP addresses
        ip_addresses = []
        
        # Method 1: Use socket to get primary IP
        try:
            # Connect to external address to get local IP (doesn't actually connect)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
            if primary_ip and primary_ip != "127.0.0.1":
                ip_addresses.append(primary_ip)
        except:
            pass
        
        # Method 2: Try to get interface IPs based on OS
        try:
            if platform.system() == "Linux":
                # Use ip command on Linux
                result = subprocess.run(['ip', 'route', 'get', '8.8.8.8'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'src' in line:
                            parts = line.split()
                            try:
                                ip_idx = parts.index('src') + 1
                                if ip_idx < len(parts):
                                    ip = parts[ip_idx]
                                    if ip not in ip_addresses and ip != "127.0.0.1":
                                        ip_addresses.append(ip)
                            except:
                                pass
            elif platform.system() == "Darwin":  # macOS
                # Use route command on macOS
                result = subprocess.run(['route', 'get', 'default'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'interface:' in line:
                            interface = line.split(':')[-1].strip()
                            # Get IP for this interface
                            try:
                                import subprocess
                                ip_result = subprocess.run(['ifconfig', interface], 
                                                         capture_output=True, text=True, timeout=5)
                                for ip_line in ip_result.stdout.split('\n'):
                                    if 'inet ' in ip_line and 'inet 127.' not in ip_line:
                                        ip = ip_line.split()[1]
                                        if ip not in ip_addresses:
                                            ip_addresses.append(ip)
                            except:
                                pass
        except:
            pass
        
        # Method 3: Fallback - get all addresses for hostname
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for info in addr_info:
                ip = info[4][0]
                if ip not in ip_addresses and ip != "127.0.0.1" and not ip.startswith("::"):
                    ip_addresses.append(ip)
        except:
            pass
        
        # Remove duplicates and sort
        ip_addresses = list(dict.fromkeys(ip_addresses))  # Remove duplicates preserving order
        
        return hostname, ip_addresses
        
    except Exception as e:
        print(f"Warning: Could not auto-detect system identifiers: {e}")
        return "unknown", []


class DeviceRegistrationCLI:
    def __init__(self, registry_url: str = "http://localhost:8081"):
        self.registry_url = registry_url.rstrip('/')
        self.session = requests.Session()
        
    def test_connection(self) -> bool:
        """Test connection to device registry service"""
        try:
            response = self.session.get(f"{self.registry_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Cannot connect to Device Registry at {self.registry_url}")
            print(f"   Error: {e}")
            print(f"   Please ensure the device-registry service is running.")
            return False
    
    def list_ships(self) -> List[Dict]:
        """List all registered ships"""
        try:
            response = self.session.get(f"{self.registry_url}/ships")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching ships: {e}")
            return []
    
    def create_ship(self, ship_id: str, name: str, fleet_id: str = None, location: str = None) -> bool:
        """Create a new ship"""
        ship_data = {
            "ship_id": ship_id,
            "name": name,
            "fleet_id": fleet_id,
            "location": location,
            "status": "active"
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/ships", json=ship_data)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"❌ Ship ID '{ship_id}' already exists")
            else:
                print(f"❌ Error creating ship: {e}")
            return False
        except Exception as e:
            print(f"❌ Error creating ship: {e}")
            return False
    
    def register_device(self, hostname: str, ip_address: str, ship_id: str, device_type: str, 
                       vendor: str = None, model: str = None, location: str = None,
                       additional_ip_addresses: List[str] = None) -> Optional[str]:
        """Register a device with hostname AND IP address and return device_id"""
        device_data = {
            "hostname": hostname,
            "ip_address": ip_address,
            "ship_id": ship_id,
            "device_type": device_type,
            "vendor": vendor,
            "model": model,
            "location": location,
            "additional_ip_addresses": additional_ip_addresses or []
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/devices/register", json=device_data)
            response.raise_for_status()
            result = response.json()
            return result.get("device_id"), result.get("identifiers_registered", [])
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                print(f"❌ Device with this hostname+IP combination already exists or ship '{ship_id}' not found")
            else:
                print(f"❌ Error registering device: {e}")
            return None, []
        except Exception as e:
            print(f"❌ Error registering device: {e}")
            return None, []
    
    def lookup_hostname(self, hostname: str) -> Optional[Dict]:
        """Lookup hostname mapping"""
        try:
            response = self.session.get(f"{self.registry_url}/lookup/{hostname}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            else:
                print(f"❌ Error looking up hostname: {e}")
                return None
        except Exception as e:
            print(f"❌ Error looking up hostname: {e}")
            return None
    
    def list_devices(self, ship_id: str = None) -> List[Dict]:
        """List devices, optionally filtered by ship_id"""
        try:
            params = {"ship_id": ship_id} if ship_id else {}
            response = self.session.get(f"{self.registry_url}/devices", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching devices: {e}")
            return []
    
    def get_stats(self) -> Optional[Dict]:
        """Get registry statistics"""
        try:
            response = self.session.get(f"{self.registry_url}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching stats: {e}")
            return None
    
    def interactive_ship_creation(self):
        """Interactive ship creation wizard"""
        print("\n🚢 Ship Registration Wizard")
        print("=" * 50)
        
        ship_id = input("Enter Ship ID (e.g., 'ship-001', 'msc-aurora'): ").strip()
        if not ship_id:
            print("❌ Ship ID is required")
            return False
        
        name = input("Enter Ship Name (e.g., 'MSC Aurora', 'Container Ship 1'): ").strip()
        if not name:
            print("❌ Ship name is required")
            return False
        
        fleet_id = input("Enter Fleet ID (optional, press Enter to skip): ").strip()
        fleet_id = fleet_id if fleet_id else None
        
        location = input("Enter Current Location (optional, press Enter to skip): ").strip()
        location = location if location else None
        
        print(f"\n📋 Ship Details:")
        print(f"   Ship ID: {ship_id}")
        print(f"   Name: {name}")
        print(f"   Fleet ID: {fleet_id or 'Not specified'}")
        print(f"   Location: {location or 'Not specified'}")
        
        confirm = input("\nCreate this ship? (y/N): ").strip().lower()
        if confirm == 'y':
            if self.create_ship(ship_id, name, fleet_id, location):
                print(f"✅ Ship '{ship_id}' created successfully!")
                return True
            else:
                return False
        else:
            print("❌ Ship creation cancelled")
            return False
    
    def auto_register_current_system(self):
        """Auto-detect current system and register it interactively"""
        print("\n🖥️  Auto-Register Current System")
        print("=" * 50)
        
        # Detect current system identifiers
        print("🔍 Detecting current system identifiers...")
        hostname, ip_addresses = get_system_identifiers()
        
        print(f"\n📋 Detected System Information:")
        print(f"   Hostname: {hostname}")
        if ip_addresses:
            print(f"   IP Addresses: {', '.join(ip_addresses)}")
        else:
            print(f"   IP Addresses: None detected")
        
        # Check if already registered
        existing_hostname = self.lookup_hostname(hostname)
        existing_ips = []
        for ip in ip_addresses:
            existing_ip = self.lookup_hostname(ip)
            if existing_ip:
                existing_ips.append((ip, existing_ip))
        
        if existing_hostname or existing_ips:
            print(f"\n⚠️  System Already Registered:")
            if existing_hostname:
                mapping = existing_hostname['mapping']
                print(f"   Hostname '{hostname}' → Ship: {mapping['ship_id']} ({mapping['ship_name']})")
                print(f"   Device: {mapping['device_id']} ({mapping['device_type']})")
            
            for ip, mapping_info in existing_ips:
                mapping = mapping_info['mapping']
                print(f"   IP '{ip}' → Ship: {mapping['ship_id']} ({mapping['ship_name']})")
                print(f"   Device: {mapping['device_id']} ({mapping['device_type']})")
            return False
        
        # Confirm detected information
        use_detected = input(f"\nUse detected hostname '{hostname}'? (Y/n): ").strip().lower()
        if use_detected == 'n':
            hostname = input("Enter hostname manually: ").strip()
            if not hostname:
                print("❌ Hostname is required")
                return False
        
        # Handle IP addresses - now REQUIRED
        primary_ip = None
        additional_ip_addresses = []
        
        if not ip_addresses:
            print("❌ Error: No IP addresses detected. Both hostname AND IP address are required.")
            manual_ip = input("Please enter the primary IP address manually: ").strip()
            if not manual_ip:
                print("❌ IP address is required for device registration")
                return False
            primary_ip = manual_ip
        else:
            print(f"\n📡 Detected IP Addresses:")
            for i, ip in enumerate(ip_addresses, 1):
                print(f"   {i}. {ip}")
            
            if len(ip_addresses) == 1:
                # Only one IP detected, use as primary
                primary_ip = ip_addresses[0]
                print(f"\n✅ Using {primary_ip} as primary IP address")
            else:
                # Multiple IPs detected, ask user to select primary
                while True:
                    try:
                        choice = input(f"\nSelect primary IP address (1-{len(ip_addresses)}): ").strip()
                        ip_idx = int(choice) - 1
                        if 0 <= ip_idx < len(ip_addresses):
                            primary_ip = ip_addresses[ip_idx]
                            # Remaining IPs become additional
                            additional_ip_addresses = [ip for i, ip in enumerate(ip_addresses) if i != ip_idx]
                            break
                        else:
                            print(f"❌ Invalid selection. Please choose 1-{len(ip_addresses)}")
                    except ValueError:
                        print(f"❌ Invalid selection. Please choose 1-{len(ip_addresses)}")
                    except KeyboardInterrupt:
                        print("\n❌ Registration cancelled")
                        return False
        
        # Get ship and device information
        ships = self.list_ships()
        if not ships:
            print("❌ No ships found. Please create a ship first.")
            create_ship = input("Would you like to create a ship now? (y/N): ").strip().lower()
            if create_ship == 'y':
                if self.interactive_ship_creation():
                    ships = self.list_ships()
                else:
                    return False
            else:
                return False
        
        print(f"\n📋 Available Ships:")
        for i, ship in enumerate(ships, 1):
            print(f"   {i}. {ship['ship_id']} - {ship['name']}")
        
        # Ship selection
        while True:
            try:
                ship_choice = input(f"\nSelect ship (1-{len(ships)}) or enter ship_id directly: ").strip()
                
                # Try to parse as number first
                try:
                    ship_idx = int(ship_choice) - 1
                    if 0 <= ship_idx < len(ships):
                        selected_ship = ships[ship_idx]['ship_id']
                        break
                except ValueError:
                    pass
                
                # Try as direct ship_id
                if any(ship['ship_id'] == ship_choice for ship in ships):
                    selected_ship = ship_choice
                    break
                else:
                    print(f"❌ Invalid selection. Please choose 1-{len(ships)} or valid ship_id")
            except KeyboardInterrupt:
                print("\n❌ Registration cancelled")
                return False
        
        # Device type selection
        print(f"\n📱 Device Type Categories:")
        device_types = [
            "workstation",    # User workstations, terminals, laptops
            "server",         # Application servers, databases, file servers  
            "network",        # Switches, routers, wireless access points
            "navigation",     # GPS, radar, AIS, chart plotters
            "communication",  # VHF, satellite communication, intercom
            "engine",         # Engine monitoring, propulsion systems
            "safety",         # Fire detection, emergency systems, life safety
            "iot_sensor",     # Temperature, humidity, pressure sensors
            "security",       # CCTV, access control, alarm systems
            "other"           # Miscellaneous devices
        ]
        
        for i, dtype in enumerate(device_types, 1):
            print(f"   {i:2d}. {dtype}")
        
        # Auto-suggest device type based on hostname
        suggested_type = "workstation"  # Default suggestion
        hostname_lower = hostname.lower()
        if any(term in hostname_lower for term in ["server", "srv", "db", "database"]):
            suggested_type = "server"
        elif any(term in hostname_lower for term in ["switch", "router", "ap", "wifi"]):
            suggested_type = "network"
        elif any(term in hostname_lower for term in ["vm", "desktop", "laptop", "pc"]):
            suggested_type = "workstation"
        
        print(f"\n💡 Suggested device type based on hostname: {suggested_type}")
        
        while True:
            try:
                type_choice = input(f"\nSelect device type (1-{len(device_types)}) or enter type directly [suggested: {suggested_type}]: ").strip()
                
                if not type_choice:  # Use suggestion
                    device_type = suggested_type
                    break
                
                # Try to parse as number first
                try:
                    type_idx = int(type_choice) - 1
                    if 0 <= type_idx < len(device_types):
                        device_type = device_types[type_idx]
                        break
                except ValueError:
                    pass
                
                # Use direct input
                device_type = type_choice
                break
            except KeyboardInterrupt:
                print("\n❌ Registration cancelled")
                return False
        
        # Optional details
        vendor = input("Enter Vendor/Manufacturer (optional, press Enter to skip): ").strip()
        vendor = vendor if vendor else None
        
        model = input("Enter Model (optional, press Enter to skip): ").strip()
        model = model if model else None
        
        location = input("Enter Location on Ship (optional, e.g., 'Bridge', 'Engine Room'): ").strip()
        location = location if location else None
        
        # Summary
        print(f"\n📋 Auto-Registration Summary:")
        print(f"   Hostname: {hostname}")
        print(f"   Primary IP: {primary_ip}")
        if additional_ip_addresses:
            print(f"   Additional IPs: {', '.join(additional_ip_addresses)}")
        print(f"   Ship: {selected_ship}")
        print(f"   Device Type: {device_type}")
        print(f"   Vendor: {vendor or 'Not specified'}")
        print(f"   Model: {model or 'Not specified'}")
        print(f"   Location: {location or 'Not specified'}")
        
        confirm = input("\nRegister this system? (y/N): ").strip().lower()
        if confirm == 'y':
            device_id, registered_identifiers = self.register_device(
                hostname, primary_ip, selected_ship, device_type, vendor, model, location, additional_ip_addresses)
            if device_id:
                print(f"✅ System registered successfully!")
                print(f"   Device ID: {device_id}")
                print(f"   Registered Identifiers: {', '.join(registered_identifiers)}")
                print(f"   Ship: {selected_ship}")
                return True
            else:
                return False
        else:
            print("❌ Auto-registration cancelled")
            return False
    def interactive_device_registration(self):
        """Interactive device registration wizard"""
        print("\n🖥️  Device Registration Wizard")
        print("=" * 50)
        
        # First, list available ships
        ships = self.list_ships()
        if not ships:
            print("❌ No ships found. Please create a ship first.")
            create_ship = input("Would you like to create a ship now? (y/N): ").strip().lower()
            if create_ship == 'y':
                if self.interactive_ship_creation():
                    ships = self.list_ships()
                else:
                    return False
            else:
                return False
        
        print(f"\n📋 Available Ships:")
        for i, ship in enumerate(ships, 1):
            print(f"   {i}. {ship['ship_id']} - {ship['name']}")
        
        # Ship selection
        while True:
            try:
                ship_choice = input(f"\nSelect ship (1-{len(ships)}) or enter ship_id directly: ").strip()
                
                # Try to parse as number first
                try:
                    ship_idx = int(ship_choice) - 1
                    if 0 <= ship_idx < len(ships):
                        selected_ship = ships[ship_idx]['ship_id']
                        break
                except ValueError:
                    pass
                
                # Try as direct ship_id
                if any(ship['ship_id'] == ship_choice for ship in ships):
                    selected_ship = ship_choice
                    break
                else:
                    print(f"❌ Invalid selection. Please choose 1-{len(ships)} or valid ship_id")
            except KeyboardInterrupt:
                print("\n❌ Registration cancelled")
                return False
        
        # Device details
        # Device details - Now require BOTH hostname AND IP
        hostname = input("\nEnter Hostname (e.g., 'ubuntu-vm-01', 'nav-computer'): ").strip()
        if not hostname:
            print("❌ Hostname is required")
            return False
        
        # Check if hostname already exists
        existing = self.lookup_hostname(hostname)
        if existing:
            print(f"❌ Hostname '{hostname}' is already registered:")
            print(f"   Ship: {existing['mapping']['ship_id']} ({existing['mapping']['ship_name']})")
            print(f"   Device: {existing['mapping']['device_id']}")
            print(f"   Type: {existing['mapping']['device_type']}")
            return False
        
        # Require primary IP address
        primary_ip = input("Enter Primary IP Address (e.g., '192.168.1.100'): ").strip()
        if not primary_ip:
            print("❌ Primary IP address is required")
            return False
        
        # Validate IP format
        try:
            import ipaddress
            ipaddress.ip_address(primary_ip)
        except ValueError:
            print(f"❌ Invalid IP address format: {primary_ip}")
            return False
        
        # Check if IP already exists
        existing_ip = self.lookup_hostname(primary_ip)
        if existing_ip:
            print(f"❌ IP address '{primary_ip}' is already registered:")
            print(f"   Ship: {existing_ip['mapping']['ship_id']} ({existing_ip['mapping']['ship_name']})")
            print(f"   Device: {existing_ip['mapping']['device_id']}")
            print(f"   Type: {existing_ip['mapping']['device_type']}")
            return False
        
        # Additional IP addresses (not hostnames anymore)
        additional_ip_addresses = []
        add_more = input("\nDo you want to add additional IP addresses? (y/N): ").strip().lower()
        if add_more == 'y':
            while True:
                additional = input("Enter additional IP address (or press Enter to finish): ").strip()
                if not additional:
                    break
                
                # Validate IP format
                try:
                    ipaddress.ip_address(additional)
                except ValueError:
                    print(f"❌ Invalid IP address format: {additional}")
                    continue
                    
                if additional not in additional_ip_addresses and additional not in [hostname, primary_ip]:
                    # Check if this IP is already registered
                    existing_additional = self.lookup_hostname(additional)
                    if existing_additional:
                        print(f"   ⚠️  '{additional}' is already registered to ship {existing_additional['mapping']['ship_id']}")
                        use_anyway = input("   Continue anyway? (y/N): ").strip().lower()
                        if use_anyway != 'y':
                            continue
                    additional_ip_addresses.append(additional)
                    print(f"   ✅ Added: {additional}")
                else:
                    print(f"   ⚠️  Skipping duplicate: {additional}")
        
        print(f"\n📱 Device Type Categories:")
        device_types = [
            "navigation",     # GPS, radar, AIS, chart plotters
            "communication",  # VHF, satellite communication, intercom
            "engine",         # Engine monitoring, propulsion systems
            "safety",         # Fire detection, emergency systems, life safety
            "network",        # Switches, routers, wireless access points
            "server",         # Application servers, databases, file servers
            "workstation",    # User workstations, terminals, laptops
            "iot_sensor",     # Temperature, humidity, pressure sensors
            "security",       # CCTV, access control, alarm systems
            "other"           # Miscellaneous devices
        ]
        
        for i, dtype in enumerate(device_types, 1):
            print(f"   {i:2d}. {dtype}")
        
        while True:
            try:
                type_choice = input(f"\nSelect device type (1-{len(device_types)}) or enter type directly: ").strip()
                
                # Try to parse as number first
                try:
                    type_idx = int(type_choice) - 1
                    if 0 <= type_idx < len(device_types):
                        device_type = device_types[type_idx]
                        break
                except ValueError:
                    pass
                
                # Use direct input
                device_type = type_choice
                break
            except KeyboardInterrupt:
                print("\n❌ Registration cancelled")
                return False
        
        # Optional details
        vendor = input("Enter Vendor/Manufacturer (optional, press Enter to skip): ").strip()
        vendor = vendor if vendor else None
        
        model = input("Enter Model (optional, press Enter to skip): ").strip()
        model = model if model else None
        
        location = input("Enter Location on Ship (optional, e.g., 'Bridge', 'Engine Room'): ").strip()
        location = location if location else None
        
        # Summary
        print(f"\n📋 Device Registration Summary:")
        print(f"   Hostname: {hostname}")
        print(f"   Primary IP: {primary_ip}")
        if additional_ip_addresses:
            print(f"   Additional IPs: {', '.join(additional_ip_addresses)}")
        print(f"   Ship: {selected_ship}")
        print(f"   Device Type: {device_type}")
        print(f"   Vendor: {vendor or 'Not specified'}")
        print(f"   Model: {model or 'Not specified'}")
        print(f"   Location: {location or 'Not specified'}")
        
        confirm = input("\nRegister this device? (y/N): ").strip().lower()
        if confirm == 'y':
            device_id, registered_identifiers = self.register_device(
                hostname, primary_ip, selected_ship, device_type, vendor, model, location, additional_ip_addresses)
            if device_id:
                print(f"✅ Device registered successfully!")
                print(f"   Device ID: {device_id}")
                print(f"   Registered Identifiers: {', '.join(registered_identifiers)}")
                print(f"   Ship: {selected_ship}")
                return True
            else:
                return False
        else:
            print("❌ Device registration cancelled")
            return False
    
    def display_stats(self):
        """Display registry statistics"""
        stats = self.get_stats()
        if not stats:
            return
        
        print(f"\n📊 Device Registry Statistics")
        print("=" * 50)
        print(f"Total Ships: {stats['total_ships']}")
        print(f"Total Devices: {stats['total_devices']}")
        
        if stats['device_types']:
            print(f"\n🔧 Device Types:")
            for device_type, count in sorted(stats['device_types'].items()):
                print(f"   {device_type}: {count}")
        
        if stats['ship_device_counts']:
            print(f"\n🚢 Devices per Ship:")
            for ship_id, count in sorted(stats['ship_device_counts'].items()):
                print(f"   {ship_id}: {count} devices")
        
        print(f"\nLast Updated: {stats['timestamp']}")
    
    def display_ships(self):
        """Display all ships"""
        ships = self.list_ships()
        if not ships:
            print("❌ No ships found")
            return
        
        print(f"\n🚢 Registered Ships ({len(ships)} total)")
        print("=" * 70)
        for ship in ships:
            print(f"Ship ID: {ship['ship_id']}")
            print(f"  Name: {ship['name']}")
            print(f"  Fleet: {ship['fleet_id'] or 'Not specified'}")
            print(f"  Location: {ship['location'] or 'Not specified'}")
            print(f"  Status: {ship['status']}")
            print()
    
    def display_devices(self, ship_id: str = None):
        """Display all devices or devices for specific ship"""
        devices = self.list_devices(ship_id)
        if not devices:
            if ship_id:
                print(f"❌ No devices found for ship '{ship_id}'")
            else:
                print("❌ No devices found")
            return
        
        title = f"Devices for Ship '{ship_id}'" if ship_id else "All Registered Devices"
        print(f"\n🖥️  {title} ({len(devices)} total)")
        print("=" * 80)
        
        current_ship = None
        for device in devices:
            if current_ship != device['ship_id']:
                current_ship = device['ship_id']
                print(f"\n🚢 Ship: {device['ship_id']} ({device['ship_name']})")
                print("-" * 60)
            
            print(f"  Device ID: {device['device_id']}")
            print(f"  Primary Hostname: {device['hostname']}")
            
            # Show all identifiers if available
            if 'all_identifiers' in device and len(device['all_identifiers']) > 1:
                other_identifiers = [id for id in device['all_identifiers'] if id != device['hostname']]
                if other_identifiers:
                    print(f"  Additional Identifiers: {', '.join(other_identifiers)}")
            
            print(f"  Type: {device['device_type']}")
            if device['vendor']:
                print(f"  Vendor: {device['vendor']}")
            if device['model']:
                print(f"  Model: {device['model']}")
            if device['location']:
                print(f"  Location: {device['location']}")
            print(f"  Created: {device['created_at']}")
            print()
    
    def lookup_and_display(self, hostname: str):
        """Lookup and display hostname mapping"""
        result = self.lookup_hostname(hostname)
        if not result:
            print(f"❌ Hostname '{hostname}' not found in registry")
            return
        
        mapping = result['mapping']
        print(f"\n🔍 Hostname Lookup: {hostname}")
        print("=" * 50)
        print(f"Ship ID: {mapping['ship_id']}")
        print(f"Ship Name: {mapping['ship_name']}")
        print(f"Device ID: {mapping['device_id']}")
        print(f"Device Type: {mapping['device_type']}")
        if mapping['vendor']:
            print(f"Vendor: {mapping['vendor']}")
        if mapping['model']:
            print(f"Model: {mapping['model']}")
        if mapping['location']:
            print(f"Location: {mapping['location']}")
    
    def main_menu(self):
        """Display main menu and handle user choice"""
        while True:
            print(f"\n🏗️  AIOps Device Registry - Interactive Registration")
            print("=" * 60)
            print("1. Register New Ship")
            print("2. Register New Device/Hostname") 
            print("3. Auto-Register Current System")
            print("4. Lookup Hostname/IP")
            print("5. List All Ships")
            print("6. List All Devices")
            print("7. List Devices for Specific Ship")
            print("8. Show Registry Statistics")
            print("9. Exit")
            
            try:
                choice = input("\nSelect option (1-9): ").strip()
                
                if choice == '1':
                    self.interactive_ship_creation()
                elif choice == '2':
                    self.interactive_device_registration()
                elif choice == '3':
                    self.auto_register_current_system()
                elif choice == '4':
                    identifier = input("Enter hostname or IP to lookup: ").strip()
                    if identifier:
                        self.lookup_and_display(identifier)
                elif choice == '5':
                    self.display_ships()
                elif choice == '6':
                    self.display_devices()
                elif choice == '7':
                    ship_id = input("Enter ship ID: ").strip()
                    if ship_id:
                        self.display_devices(ship_id)
                elif choice == '8':
                    self.display_stats()
                elif choice == '9':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-9.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Device Registration Script - Enforces hostname AND IP address registration"
    )
    parser.add_argument(
        '--registry-url', 
        default='http://localhost:8081',
        help='Device Registry service URL (default: http://localhost:8081)'
    )
    parser.add_argument(
        '--ship-id',
        help='Create a ship with specified ID (requires --ship-name)'
    )
    parser.add_argument(
        '--ship-name',
        help='Ship name when creating a ship (requires --ship-id)'
    )
    parser.add_argument(
        '--hostname',
        help='Device hostname (requires --ip-address, --ship-id and --device-type)'
    )
    parser.add_argument(
        '--ip-address',
        help='Primary IP address (requires --hostname, --ship-id and --device-type)'
    )
    parser.add_argument(
        '--device-type',
        help='Device type when registering device'
    )
    parser.add_argument(
        '--lookup',
        help='Lookup hostname or IP address mapping'
    )
    parser.add_argument(
        '--list-ships',
        action='store_true',
        help='List all ships and exit'
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List all devices and exit'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show registry statistics and exit'
    )
    parser.add_argument(
        '--auto-register',
        action='store_true',
        help='Auto-detect current system and register interactively'
    )
    parser.add_argument(
        '--additional-ip-addresses',
        nargs='*',
        help='Additional IP addresses when registering device'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = DeviceRegistrationCLI(args.registry_url)
    
    # Test connection
    if not cli.test_connection():
        sys.exit(1)
    
    print(f"✅ Connected to Device Registry at {args.registry_url}")
    
    # Handle non-interactive commands
    if args.list_ships:
        cli.display_ships()
        return
    
    if args.list_devices:
        cli.display_devices()
        return
    
    if args.stats:
        cli.display_stats()
        return
    
    if args.auto_register:
        cli.auto_register_current_system()
        return
    
    if args.lookup:
        cli.lookup_and_display(args.lookup)
        return
    
    if args.ship_id and args.ship_name:
        if cli.create_ship(args.ship_id, args.ship_name):
            print(f"✅ Ship '{args.ship_id}' created successfully!")
        return
    
    if args.hostname and args.ip_address and args.ship_id and args.device_type:
        device_id, registered_identifiers = cli.register_device(
            args.hostname, args.ip_address, args.ship_id, args.device_type, 
            additional_ip_addresses=args.additional_ip_addresses
        )
        if device_id:
            print(f"✅ Device registered successfully! Device ID: {device_id}")
            print(f"✅ Registered identifiers: {', '.join(registered_identifiers)}")
        return
    
    # Start interactive mode
    cli.main_menu()


if __name__ == "__main__":
    main()