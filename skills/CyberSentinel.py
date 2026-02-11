import subprocess
import threading
import pyautogui
import os
import socket
import re
from datetime import datetime
from skill_manager import Skill

# Use a more efficient screenshot save path
BASE_DIR = "cyber_logs"
SCREENSHOT_DIR = os.path.join(BASE_DIR, "captures")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class CyberSentinel(Skill):
    name = "CyberSentinel"
    description = "Network auditing and system monitoring toolkit."
    keywords = ["scan", "nmap", "capture", "payload", "port", "monitor", "audit", "network", "security", "surveillance"]
    supported_intents = ["CyberSentinel"]
    def __init__(self):
        self._stop_event = threading.Event()
        self.capture_thread = None
        self.known_targets = {
            "localhost": "127.0.0.1",
            "local": "127.0.0.1",
            "home": "192.168.1.1",
            "router": "192.168.1.1",
            "gateway": "192.168.1.1",
            "google": "8.8.8.8",
            "dns": "8.8.8.8",
        }

    def _extract_ip(self, user_input: str) -> str:
        """Extract IP address or hostname from user input without LLM"""
        # Common IP patterns
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        hostname_pattern = r'\b(?:scan|check|audit|target)\s+([a-zA-Z0-9.-]+)\b'
        
        # Try to find IP address
        ip_match = re.search(ip_pattern, user_input)
        if ip_match:
            return ip_match.group(0)
        
        # Try to find hostname
        host_match = re.search(hostname_pattern, user_input)
        if host_match:
            hostname = host_match.group(1).lower()
            
            # Check if it's a known target
            if hostname in self.known_targets:
                return self.known_targets[hostname]
            
            # Check if it's a common format
            if hostname.endswith('.com') or hostname.endswith('.org') or hostname.endswith('.net'):
                try:
                    # Try to resolve hostname
                    return socket.gethostbyname(hostname)
                except:
                    return hostname
            
            return hostname
        
        # Check for common phrases
        if any(phrase in user_input for phrase in ["my network", "this network", "local network"]):
            return "192.168.1.0/24"
        
        if "my computer" in user_input or "this pc" in user_input:
            return "127.0.0.1"
        
        # Default to localhost
        return "127.0.0.1"

    def run_scan(self, target):
        """Runs Nmap or falls back to basic socket check."""
        if not target:
            return "Error: No target specified. Try 'scan 192.168.1.1' or 'scan google.com'"
        
        print(f"📡 [SENTINEL]: Auditing target {target}...")
        
        try:
            # Determine scan type based on target
            if "/" in target:  # Network range
                args = ["nmap", "-sn", "-T4", target]  # Ping sweep only
            elif "localhost" in target or target == "127.0.0.1":
                args = ["nmap", "-p", "1-1000", "-T4", target]
            else:
                args = ["nmap", "-T4", "-F", target]  # Fast scan
            
            result = subprocess.run(args, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=45)
            
            if result.returncode == 0:
                # Format the output nicely
                output = result.stdout
                lines = output.split('\n')
                summary = []
                
                for line in lines:
                    if "Nmap scan report" in line:
                        summary.append(f"📡 {line}")
                    elif "open" in line.lower() and "port" in line.lower():
                        summary.append(f"✅ {line.strip()}")
                    elif "closed" in line.lower():
                        summary.append(f"❌ {line.strip()}")
                
                if summary:
                    return f"Scan completed for {target}:\n" + "\n".join(summary[:10]) + \
                           f"\n\n📊 Total results: {len(summary)} lines"
                else:
                    return f"Scan completed for {target}:\n{output[:500]}..."
            else:
                return f"Scan failed: {result.stderr}"
                
        except FileNotFoundError:
            # Nmap not installed, fallback to basic socket checks
            return self._basic_scan_fallback(target)
        except subprocess.TimeoutExpired:
            return f"Scan timed out for {target}. Target might be blocking scans."
        except Exception as e:
            return f"Scan error: {str(e)}"

    def _basic_scan_fallback(self, target):
        """Basic port scanner when Nmap is not available"""
        try:
            # Resolve hostname to IP
            if not re.match(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', target):
                target = socket.gethostbyname(target)
            
            results = []
            
            # Scan common ports
            common_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 3389]
            
            for port in common_ports[:10]:  # Limit to 10 ports for speed
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex((target, port))
                s.close()
                
                if result == 0:
                    results.append(f"✅ Port {port}: OPEN")
                else:
                    results.append(f"❌ Port {port}: CLOSED")
            
            return f"Basic scan for {target}:\n" + "\n".join(results)
        except socket.gaierror:
            return f"Could not resolve hostname: {target}"
        except Exception as e:
            return f"Basic scan failed: {str(e)}"

    def toggle_capture(self, active=True):
        """Start/stop screen capture"""
        if active:
            if self.capture_thread and self.capture_thread.is_alive():
                return "📹 Surveillance is already active."
            
            self._stop_event.clear()
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            return "📹 Surveillance mode activated. Capturing screenshots every 30 seconds."
        else:
            self._stop_event.set()
            if self.capture_thread:
                self.capture_thread.join(timeout=2)
            return "📹 Surveillance mode deactivated."

    def _capture_loop(self):
        """Background screenshot capture loop"""
        while not self._stop_event.is_set():
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(SCREENSHOT_DIR, f"capture_{ts}.png")
                pyautogui.screenshot().save(path)
                print(f"📸 [SENTINEL]: Saved capture to {path}")
            except Exception as e:
                print(f"⚠️ [SENTINEL]: Capture failed: {e}")
            
            # Wait 30 seconds between captures
            self._stop_event.wait(30)

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").lower().strip()
        
        print(f"🛡️ [SENTINEL]: Processing: '{user_input}'")
        
        if not user_input:
            return "Sentinel standing by. Use 'scan [IP/hostname]', 'start capture', or 'stop capture'."
        
        # 🎯 DIRECT COMMAND PARSING - No LLM needed
        
        # Capture commands
        if any(cmd in user_input for cmd in ["stop capture", "stop surveillance", "stop monitoring"]):
            return self.toggle_capture(active=False)
        
        if any(cmd in user_input for cmd in ["start capture", "begin capture", "start surveillance", 
                                            "begin surveillance", "monitor screen", "capture screen"]):
            return self.toggle_capture(active=True)
        
        # Scan commands
        if any(cmd in user_input for cmd in ["scan ", "check ", "audit ", "nmap ", "port scan", "network scan"]):
            target = self._extract_ip(user_input)
            return self.run_scan(target)
        
        # Quick scans
        if user_input in ["scan", "scan network", "scan local"]:
            return self.run_scan("192.168.1.0/24")
        
        if user_input in ["scan me", "scan my pc", "scan this computer"]:
            return self.run_scan("127.0.0.1")
        
        if user_input in ["scan google", "scan dns"]:
            return self.run_scan("8.8.8.8")
        
        if user_input in ["scan router", "scan gateway"]:
            return self.run_scan("192.168.1.1")
        
        # Status/help
        if any(word in user_input for word in ["help", "what can", "capabilities", "commands"]):
            return """🛡️ CyberSentinel Commands:
• scan [IP/hostname] - Scan target (e.g., 'scan 192.168.1.1', 'scan google.com')
• scan network - Scan local network
• scan me - Scan this computer
• start capture - Begin screenshot surveillance
• stop capture - Stop surveillance
• scan router - Scan network gateway
• scan google - Scan Google DNS (8.8.8.8)"""
        
        # Default response
        return "I didn't understand that command. Try 'scan 192.168.1.1' or 'start capture'."

# Test function
def test_cyber_sentinel():
    """Test the CyberSentinel skill"""
    skill = CyberSentinel()
    
    test_commands = [
        "scan 192.168.1.1",
        "scan google.com",
        "scan me",
        "scan network",
        "start capture",
        "stop capture",
        "scan router",
        "help",
    ]
    
    print("\n🛡️ Testing CyberSentinel:")
    print("=" * 50)
    
    for cmd in test_commands:
        print(f"\n🔘 Command: {cmd}")
        result = skill.run({"user_input": cmd})
        print(f"   Result: {result[:200]}..." if len(str(result)) > 200 else f"   Result: {result}")
    
    # Cleanup
    skill.toggle_capture(active=False)

if __name__ == "__main__":
    test_cyber_sentinel()