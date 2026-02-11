import scapy.all as scapy
import socket
import logging
import requests
import json
import time
from skill_manager import Skill

class WifiScanSkill(Skill):
    name = "WiFi Scanner"
    description = "Scans local network for connected devices with MAC vendor lookup"
    keywords = ["scan wifi", "network scan", "who is on my network", "list devices", 
                "network map", "find devices", "connected devices", "wifi devices"]
    supported_intents = ["scan_wifi"]
    def __init__(self):
        self.logger = logging.getLogger("Crystal.WifiScan")
        self.mac_vendors = {}
        self._load_mac_vendors()
    
    def _load_mac_vendors(self):
        """Load MAC vendor database for device identification"""
        try:
            # Try to load from local cache first
            import os
            cache_file = "mac_vendors.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    self.mac_vendors = json.load(f)
                    print(f"✅ [WIFI SCAN]: Loaded {len(self.mac_vendors)} MAC vendors from cache")
                    return
            
            # Try to fetch from online API
            print("📡 [WIFI SCAN]: Fetching MAC vendor database...")
            response = requests.get("https://macvendors.co/api/vendors", timeout=10)
            if response.status_code == 200:
                self.mac_vendors = response.json()
                # Save to cache
                with open(cache_file, 'w') as f:
                    json.dump(self.mac_vendors, f)
                print(f"✅ [WIFI SCAN]: Loaded {len(self.mac_vendors)} MAC vendors")
            else:
                print("⚠️ [WIFI SCAN]: Could not fetch MAC vendors, using local database")
                self._load_default_vendors()
                
        except Exception as e:
            print(f"⚠️ [WIFI SCAN]: MAC vendor load error: {e}")
            self._load_default_vendors()
    
    def _load_default_vendors(self):
        """Load a small set of common MAC vendors"""
        self.mac_vendors = {
            "00:1A:11": "Nokia",
            "00:1B:63": "Apple",
            "00:1C:B3": "Apple",
            "00:1D:4F": "Apple",
            "00:1E:52": "Apple",
            "00:1F:5B": "Apple",
            "00:23:DF": "Apple",
            "00:25:00": "Apple",
            "00:26:08": "Samsung",
            "00:26:B0": "Samsung",
            "34:23:BA": "Apple",
            "3C:07:54": "Apple",
            "3C:AB:8E": "Apple",
            "60:F8:1D": "Apple",
            "70:56:81": "Apple",
            "88:66:A5": "Apple",
            "AC:BC:32": "Apple",
            "B8:E8:56": "Apple",
            "F0:24:75": "Apple",
            "F0:98:9D": "Apple",
            "F4:F5:E8": "Google",
            "F4:F5:24": "Google",
            "28:16:2E": "Google",
            "8C:85:90": "Google",
            "A4:77:33": "Google",
            "D8:EB:97": "Google",
            "28:ED:6A": "Google",
            "84:85:06": "Amazon",
            "68:37:E9": "Amazon",
            "F0:D2:F1": "Amazon",
            "0C:47:C9": "Amazon",
            "74:75:48": "Amazon",
            "A0:02:DC": "Amazon",
            "FC:A6:67": "Amazon",
            "38:F7:3D": "Amazon",
            "40:B4:CD": "Amazon",
            "8C:85:80": "OnePlus",
            "7C:2E:BD": "OnePlus",
            "44:74:6C": "OnePlus",
            "00:08:22": "D-Link",
            "00:13:46": "D-Link",
            "00:15:E9": "D-Link",
            "00:17:9A": "D-Link",
            "00:1B:11": "D-Link",
            "00:1C:F0": "D-Link",
            "00:22:B0": "D-Link",
            "00:24:01": "D-Link",
            "00:26:5A": "D-Link",
        }
    
    def get_vendor_from_mac(self, mac_address):
        """Look up vendor from MAC address"""
        if not mac_address:
            return "Unknown"
        
        # Normalize MAC address
        mac = mac_address.upper().replace('-', ':')
        
        # Try different prefix lengths
        prefixes = [mac[:8], mac[:6]]
        
        for prefix in prefixes:
            if prefix in self.mac_vendors:
                return self.mac_vendors[prefix]
        
        return "Unknown"
    
    def get_local_ip_range(self):
        """Automatically finds your network range"""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Calculate network range
            ip_parts = local_ip.split('.')
            network_range = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
            
            print(f"🌐 [WIFI SCAN]: Local IP: {local_ip}, Network: {network_range}")
            return network_range
            
        except Exception as e:
            print(f"⚠️ [WIFI SCAN]: Could not determine network: {e}")
            return '192.168.1.0/24'
    
    def scan_network(self, ip_range):
        """Scan network for devices using ARP"""
        print(f"🔍 [WIFI SCAN]: Scanning {ip_range}...")
        
        try:
            # Create ARP request
            arp_request = scapy.ARP(pdst=ip_range)
            broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
            arp_request_broadcast = broadcast / arp_request
            
            # Send request with timeout
            answered_list = scapy.srp(arp_request_broadcast, timeout=3, verbose=False)[0]
            
            devices = []
            for sent, received in answered_list:
                device_info = {
                    "ip": received.psrc,
                    "mac": received.hwsrc,
                    "vendor": self.get_vendor_from_mac(received.hwsrc)
                }
                devices.append(device_info)
            
            # Sort devices by IP address
            devices.sort(key=lambda x: [int(i) for i in x['ip'].split('.')])
            
            return devices
            
        except PermissionError:
            print("❌ [WIFI SCAN]: Permission denied. Try running as administrator/root.")
            return None
        except Exception as e:
            print(f"❌ [WIFI SCAN]: Scan failed: {e}")
            return None
    
    def get_hostname(self, ip_address):
        """Try to get hostname for IP"""
        try:
            return socket.gethostbyaddr(ip_address)[0]
        except:
            return ""
    
    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").lower()
        
        print(f"📡 [WIFI SCAN]: Processing: '{user_input}'")
        
        # Check for help command
        if "help" in user_input or "how to" in user_input:
            return """📡 WiFi Scanner Help:
• 'scan wifi' - Scan local network for devices
• 'list devices' - Show connected devices
• 'who is on my network' - Network discovery
• 'network map' - Map all connected devices

Note: Requires admin/root privileges on some systems."""
        
        # Check for specific network scan
        if "scan" in user_input and ("wifi" in user_input or "network" in user_input):
            return self._perform_scan()
        elif any(cmd in user_input for cmd in ["who is on", "list devices", "network map", "connected devices"]):
            return self._perform_scan()
        elif "scan" in user_input:
            # Just "scan" by itself
            return self._perform_scan()
        
        return "Use 'scan wifi' to discover devices on your network."
    
    def _perform_scan(self):
        """Perform the network scan and format results"""
        ip_range = self.get_local_ip_range()
        
        print(f"🔄 [WIFI SCAN]: Starting network scan on {ip_range}...")
        
        # Perform scan
        devices = self.scan_network(ip_range)
        
        if devices is None:
            return "❌ Scan failed. You might need to run as administrator/root."
        
        if not devices:
            return "🔍 No devices found on the network. Are you connected to WiFi?"
        
        # Format results
        result = f"🌐 **Network Scan Results**\n"
        result += f"Network: `{ip_range}`\n"
        result += f"Devices Found: **{len(devices)}**\n"
        result += "=" * 60 + "\n\n"
        
        # Group devices by type/vendor
        device_groups = {}
        for device in devices:
            vendor = device['vendor']
            if vendor not in device_groups:
                device_groups[vendor] = []
            device_groups[vendor].append(device)
        
        # Sort groups by device count
        sorted_groups = sorted(device_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        for vendor, vendor_devices in sorted_groups:
            if vendor == "Unknown":
                result += f"📶 **Other Devices** ({len(vendor_devices)}):\n"
            else:
                result += f"📱 **{vendor}** ({len(vendor_devices)}):\n"
            
            for device in vendor_devices:
                # Try to get hostname
                hostname = self.get_hostname(device['ip'])
                hostname_display = f" ({hostname})" if hostname else ""
                
                result += f"  • `{device['ip']:15}` - {device['mac']}{hostname_display}\n"
            
            result += "\n"
        
        # Add summary
        result += "=" * 60 + "\n"
        result += "💡 **Tips:**\n"
        result += "- Unknown devices might be IoT devices or routers\n"
        result += "- MAC addresses starting with '00:' are usually wired devices\n"
        result += "- Apple devices typically have 'Apple' as vendor\n"
        
        return result

# Standalone testing
if __name__ == "__main__":
    scanner = WifiScanSkill()
    
    test_commands = [
        "scan wifi",
        "who is on my network",
        "list devices",
        "help",
    ]
    
    print("📡 Testing WiFi Scanner:")
    print("=" * 50)
    
    for cmd in test_commands:
        print(f"\n🔘 Command: {cmd}")
        result = scanner.run({"user_input": cmd})
        print(f"📊 Result:\n{result}")
        print("-" * 50)

# Alternative simple version if scapy is not available
class SimpleNetworkScanner(Skill):
    name = "Network Scanner"
    description = "Basic network device discovery using ping"
    keywords = ["ping scan", "simple scan", "check network"]
    
    def __init__(self):
        import platform
        self.os_type = platform.system()
    
    def ping_host(self, ip):
        """Ping a single host"""
        import subprocess
        param = '-n' if self.os_type == 'Windows' else '-c'
        command = ['ping', param, '1', '-w', '1000', ip]
        try:
            output = subprocess.run(command, capture_output=True, text=True, timeout=2)
            return output.returncode == 0
        except:
            return False
    
    def run(self, parameters: dict):
        # Simple ping scan for common local IPs
        base_ip = "192.168.1."
        devices = []
        
        print(f"🔍 [SIMPLE SCAN]: Pinging common addresses...")
        
        for i in range(1, 255):
            ip = f"{base_ip}{i}"
            if self.ping_host(ip):
                devices.append(ip)
                print(f"✅ Found: {ip}")
        
        if devices:
            return f"Found {len(devices)} active devices:\n" + "\n".join([f"• {ip}" for ip in devices])
        else:
            return "No devices found. Check your network connection."