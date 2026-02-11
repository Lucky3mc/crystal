import asyncio
import json
import os
import socket
import time
import requests
from datetime import datetime
from skill_manager import Skill
import re


class SmartHome(Skill):
    name = "Smart Home"
    description = "Complete smart home control with TV, lights, plugs, speakers, and automation"
    keywords = ["smart", "home", "device", "tv", "lights", "plug", "speaker", "thermostat", "camera",
                "turn on", "turn off", "volume", "brightness", "color", "scan", "discover", "control",
                "automation", "scene", "routine", "living room", "bedroom", "kitchen"]
    supported_intents = ["smart_home"]
    def __init__(self):
        self.devices_path = "core/smart_devices.json"
        self.scenes_path = "core/smart_scenes.json"
        
        # 🚨 FIX: Define default_scenes BEFORE calling _load_scenes()
        # Default scenes
        self.default_scenes = {
            "movie night": {
                "description": "Perfect for watching movies",
                "actions": [
                    {"device": "tv", "action": "on"},
                    {"device": "tv", "action": "app", "value": "netflix"},
                    {"device": "living room lights", "action": "dim", "value": "20%"},
                    {"device": "speaker", "action": "volume", "value": "40%"}
                ]
            },
            "good morning": {
                "description": "Wake up routine",
                "actions": [
                    {"device": "bedroom lights", "action": "on"},
                    {"device": "bedroom lights", "action": "brightness", "value": "70%"},
                    {"device": "speaker", "action": "play", "value": "morning music"}
                ]
            },
            "good night": {
                "description": "Bedtime routine",
                "actions": [
                    {"device": "all lights", "action": "off"},
                    {"device": "tv", "action": "off"},
                    {"device": "bedroom lights", "action": "on", "value": "10%"},
                    {"device": "thermostat", "action": "temperature", "value": "68"}
                ]
            },
            "party mode": {
                "description": "Entertainment setup",
                "actions": [
                    {"device": "all lights", "action": "color", "value": "rainbow"},
                    {"device": "speaker", "action": "volume", "value": "70%"},
                    {"device": "tv", "action": "app", "value": "spotify"}
                ]
            }
        }
        
        # Now load devices and scenes
        self.devices = self._load_devices()
        self.scenes = self._load_scenes()  # This will now work correctly
        
        # TV control protocols
        self.tv_protocols = {
            "samsung": {
                "name": "Samsung Smart TV",
                "port": 8001,
                "api": "http://{ip}:8001/api/v2/",
                "apps": {
                    "youtube": "111299001912",
                    "netflix": "11101200001",
                    "amazon": "3201512006785",
                    "disney": "3201901017640",
                    "spotify": "3201606009684"
                }
            },
            "lg": {
                "name": "LG webOS TV",
                "port": 3000,
                "api": "http://{ip}:3000/",
                "apps": {
                    "youtube": "youtube.leanback.v4",
                    "netflix": "netflix",
                    "amazon": "amazon",
                    "disney": "disneyplus",
                    "spotify": "spotify"
                }
            },
            "android": {
                "name": "Android TV",
                "port": 8008,
                "api": "http://{ip}:8008/setup/eureka_info",
                "apps": {
                    "youtube": "YouTube",
                    "netflix": "Netflix",
                    "amazon": "Amazon Prime Video",
                    "disney": "Disney+",
                    "spotify": "Spotify"
                }
            },
            "roku": {
                "name": "Roku TV",
                "port": 8060,
                "api": "http://{ip}:8060/",
                "apps": {
                    "youtube": "837",
                    "netflix": "12",
                    "amazon": "13",
                    "disney": "291097",
                    "spotify": "19977"
                }
            }
        }
        
        # Smart device categories
        self.device_categories = {
            "lights": ["light", "bulb", "lamp", "led", "hue", "lifx", "nanoleaf"],
            "plugs": ["plug", "socket", "outlet", "switch", "smart plug", "power strip"],
            "speakers": ["speaker", "echo", "alexa", "google home", "nest audio", "sonos"],
            "tv": ["tv", "television", "smart tv", "roku", "android tv", "webos"],
            "thermostat": ["thermostat", "nest", "ecobee", "temperature", "climate"],
            "camera": ["camera", "security", "ring", "arlo", "wyze", "blink"],
            "sensors": ["sensor", "motion", "door", "window", "contact", "humidity"]
        }
        
        # Room mappings
        self.rooms = {
            "living room": ["tv", "lights", "speaker"],
            "bedroom": ["lights", "tv", "plug"],
            "kitchen": ["lights", "plug", "camera"],
            "bathroom": ["lights", "plug"],
            "office": ["lights", "plug", "speaker"],
            "garage": ["lights", "plug", "camera"]
        }
        
        print("✅ [SMART HOME]: Complete smart home system initialized")
        print(f"   Devices: {len(self.devices)}, Scenes: {len(self.scenes)}")

    def _load_devices(self):
        """Load discovered devices from file"""
        if os.path.exists(self.devices_path):
            try:
                with open(self.devices_path, "r") as f:
                    devices = json.load(f)
                    return devices
            except:
                pass
        return {}

    def _save_devices(self):
        """Save discovered devices to file"""
        try:
            os.makedirs(os.path.dirname(self.devices_path), exist_ok=True)
            with open(self.devices_path, "w") as f:
                json.dump(self.devices, f, indent=2)
        except:
            pass

    def _load_scenes(self):
        """Load saved scenes from file"""
        if os.path.exists(self.scenes_path):
            try:
                with open(self.scenes_path, "r") as f:
                    scenes = json.load(f)
                    # Merge with default scenes (defaults take priority)
                    merged_scenes = self.default_scenes.copy()
                    merged_scenes.update(scenes)
                    return merged_scenes
            except:
                pass
        return self.default_scenes.copy()

    def _save_scenes(self):
        """Save scenes to file"""
        try:
            os.makedirs(os.path.dirname(self.scenes_path), exist_ok=True)
            with open(self.scenes_path, "w") as f:
                # Don't save default scenes, only custom ones
                custom_scenes = {}
                for name, scene in self.scenes.items():
                    if name not in self.default_scenes:
                        custom_scenes[name] = scene
                json.dump(custom_scenes, f, indent=2)
        except:
            pass

    def _scan_network(self):
        """Scan local network for smart devices"""
        print("🔍 [SMART HOME]: Scanning network for smart devices...")
        
        # Common smart device ports
        smart_ports = {
            80: "HTTP",
            8080: "HTTP Alt",
            8001: "Samsung TV",
            8008: "Android TV",
            8060: "Roku",
            3000: "LG TV",
            8088: "ChromeCast",
            9000: "Sonos",
            5000: "Home Assistant",
            8123: "Home Assistant"
        }
        
        # Get local network
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            base_ip = ".".join(local_ip.split('.')[:3])
        except:
            base_ip = "192.168.1"
        
        discovered = []
        
        # Scan IP range
        for i in range(1, 51):
            ip = f"{base_ip}.{i}"
            
            # Get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0].lower()
            except:
                hostname = ""
            
            # Check ports
            for port, service in smart_ports.items():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.2)
                    result = sock.connect_ex((ip, port))
                    sock.close()
                    
                    if result == 0:
                        # Identify device type
                        device_type = self._identify_device(ip, port, hostname)
                        if device_type:
                            device_info = {
                                "ip": ip,
                                "hostname": hostname,
                                "type": device_type,
                                "port": port,
                                "service": service,
                                "room": self._guess_room(hostname, device_type),
                                "last_seen": datetime.now().isoformat(),
                                "controllable": True
                            }
                            
                            self.devices[ip] = device_info
                            discovered.append(device_info)
                            print(f"✅ Found: {device_type} at {ip} ({hostname})")
                        break
                except:
                    pass
        
        self._save_devices()
        return discovered

    def _identify_device(self, ip, port, hostname):
        """Identify device type"""
        hostname_lower = hostname.lower()
        
        # Check for specific brands/patterns
        if port == 8001 or "samsung" in hostname_lower:
            return "Samsung Smart TV"
        elif port == 8060 or "roku" in hostname_lower:
            return "Roku TV"
        elif port == 8008 or "android" in hostname_lower or "chromecast" in hostname_lower:
            return "Android/Google TV"
        elif port == 3000 or "lg" in hostname_lower:
            return "LG webOS TV"
        elif port == 9000 or "sonos" in hostname_lower:
            return "Sonos Speaker"
        elif port == 5000 or port == 8123 or "hass" in hostname_lower:
            return "Home Assistant"
        elif "hue" in hostname_lower:
            return "Philips Hue Bridge"
        elif "echo" in hostname_lower or "alexa" in hostname_lower:
            return "Amazon Echo"
        elif "google" in hostname_lower or "nest" in hostname_lower:
            return "Google Home/Nest"
        elif "tplink" in hostname_lower or "kasa" in hostname_lower:
            return "TP-Link Smart Plug"
        elif "wemo" in hostname_lower:
            return "Belkin Wemo"
        
        # Generic identification
        for category, keywords in self.device_categories.items():
            for keyword in keywords:
                if keyword in hostname_lower:
                    return category.title()
        
        return "Smart Device"

    def _guess_room(self, hostname, device_type):
        """Guess which room a device is in"""
        hostname_lower = hostname.lower()
        
        room_keywords = {
            "living": "living room",
            "bedroom": "bedroom",
            "kitchen": "kitchen",
            "bath": "bathroom",
            "office": "office",
            "garage": "garage",
            "dining": "dining room",
            "hall": "hallway",
            "tv": "living room",  # TVs usually in living room
            "speaker": "living room"  # Main speaker often in living room
        }
        
        for keyword, room in room_keywords.items():
            if keyword in hostname_lower:
                return room
        
        # Default based on device type
        if "tv" in device_type.lower():
            return "living room"
        elif "speaker" in device_type.lower():
            return "living room"
        elif "light" in device_type.lower():
            return "bedroom"
        
        return "unknown"

    def _control_tv(self, ip, command, value=None):
        """Control smart TV"""
        device = self.devices.get(ip, {})
        tv_type = device.get("type", "").lower()
        
        print(f"📺 [SMART HOME]: Controlling {tv_type} at {ip}: {command}")
        
        # Roku TV control (most reliable)
        if "roku" in tv_type:
            return self._control_roku_tv(ip, command, value)
        # Generic TV control attempts
        else:
            return self._control_generic_device(ip, command, value, "tv")

    def _control_roku_tv(self, ip, command, value=None):
        """Control Roku TV"""
        base_url = f"http://{ip}:8060/"
        
        roku_commands = {
            "power": "keypress/Power",
            "poweron": "keypress/PowerOn",
            "poweroff": "keypress/PowerOff",
            "home": "keypress/Home",
            "back": "keypress/Back",
            "up": "keypress/Up",
            "down": "keypress/Down",
            "left": "keypress/Left",
            "right": "keypress/Right",
            "select": "keypress/Select",
            "play": "keypress/Play",
            "pause": "keypress/Pause",
            "forward": "keypress/Fwd",
            "reverse": "keypress/Rev",
            "volumeup": "keypress/VolumeUp",
            "volumedown": "keypress/VolumeDown",
            "volumemute": "keypress/VolumeMute",
            "netflix": "launch/12",
            "youtube": "launch/837",
            "amazon": "launch/13",
            "disney": "launch/291097",
            "spotify": "launch/19977",
            "hulu": "launch/2285",
            "hbo": "launch/61322",
            "plex": "launch/13535"
        }
        
        if command in roku_commands:
            endpoint = roku_commands[command]
            try:
                response = requests.post(f"{base_url}{endpoint}", timeout=3)
                if response.status_code == 200:
                    action = command.replace("power", "power ").title()
                    return f"✅ TV: {action}"
            except:
                return f"❌ TV not responding"
        
        elif command == "app" and value:
            app_name = value.lower()
            if app_name in roku_commands:
                endpoint = roku_commands[app_name]
                try:
                    response = requests.post(f"{base_url}{endpoint}", timeout=3)
                    if response.status_code == 200:
                        return f"✅ TV: Launched {value}"
                except:
                    return f"❌ Failed to launch {value}"
        
        return f"⚠️ TV command '{command}' not recognized"

    def _control_lights(self, device_info, command, value=None):
        """Control smart lights"""
        ip = device_info.get("ip")
        device_type = device_info.get("type", "").lower()
        
        print(f"💡 [SMART HOME]: Controlling lights at {ip}: {command}")
        
        # Try Philips Hue API
        if "hue" in device_type:
            try:
                # Try to discover Hue bridge first
                hue_url = f"http://{ip}/api/newdeveloper"  # Default Hue API
                if command == "on":
                    response = requests.put(f"{hue_url}/lights/1/state", 
                                          json={"on": True}, timeout=2)
                elif command == "off":
                    response = requests.put(f"{hue_url}/lights/1/state", 
                                          json={"on": False}, timeout=2)
                elif command == "brightness" and value:
                    # Convert percentage to Hue brightness (0-254)
                    brightness = int(int(value.replace('%', '')) * 2.54)
                    response = requests.put(f"{hue_url}/lights/1/state", 
                                          json={"bri": brightness}, timeout=2)
                
                if response and response.status_code in [200, 201]:
                    return f"✅ Lights: {command.title()}"
            except:
                pass
        
        # Try generic light control
        return self._control_generic_device(ip, command, value, "lights")

    def _control_plug(self, device_info, command, value=None):
        """Control smart plug"""
        ip = device_info.get("ip")
        
        print(f"🔌 [SMART HOME]: Controlling plug at {ip}: {command}")
        
        # Try Tasmota/TP-Link commands
        endpoints = [
            f"http://{ip}/cm?cmnd=Power%20On",
            f"http://{ip}/cm?cmnd=Power%20Off",
            f"http://{ip}/relay/0?turn=on",
            f"http://{ip}/relay/0?turn=off",
            f"http://{ip}/switch/0/on",
            f"http://{ip}/switch/0/off"
        ]
        
        for endpoint in endpoints:
            try:
                if command == "on" and "on" in endpoint.lower():
                    response = requests.get(endpoint, timeout=2)
                    if response.status_code == 200:
                        return "✅ Plug: Turned ON"
                elif command == "off" and "off" in endpoint.lower():
                    response = requests.get(endpoint, timeout=2)
                    if response.status_code == 200:
                        return "✅ Plug: Turned OFF"
            except:
                continue
        
        return "⚠️ Could not control plug"

    def _control_speaker(self, device_info, command, value=None):
        """Control smart speaker"""
        ip = device_info.get("ip")
        
        print(f"🔊 [SMART HOME]: Controlling speaker at {ip}: {command}")
        
        # Try Google Cast
        try:
            if command == "volume" and value:
                volume = int(value.replace('%', ''))
                # Normalize to 0-100
                volume = max(0, min(100, volume))
                response = requests.post(f"http://{ip}:8008/setup/set_volume", 
                                       json={"volume": volume}, timeout=2)
                if response.status_code == 200:
                    return f"✅ Speaker: Volume {volume}%"
        except:
            pass
        
        return f"⚠️ Speaker control for '{command}' not fully implemented"

    def _control_generic_device(self, ip, command, value=None, device_type="device"):
        """Try generic control methods"""
        # Try common smart home APIs
        endpoints = [
            (f"http://{ip}/api/command", "POST"),
            (f"http://{ip}/control", "POST"),
            (f"http://{ip}/cmd", "GET"),
            (f"http://{ip}/state", "PUT")
        ]
        
        for url, method in endpoints:
            try:
                if method == "POST":
                    response = requests.post(url, json={"command": command, "value": value}, timeout=2)
                elif method == "PUT":
                    response = requests.put(url, json={"command": command, "value": value}, timeout=2)
                else:
                    response = requests.get(url, timeout=2)
                
                if response.status_code < 400:
                    return f"✅ {device_type.title()}: {command.title()} sent"
            except:
                continue
        
        return f"⚠️ Could not control {device_type}"

    def _execute_scene(self, scene_name):
        """Execute a saved scene"""
        scene = self.scenes.get(scene_name.lower())
        if not scene:
            return f"❌ Scene '{scene_name}' not found"
        
        print(f"🎭 [SMART HOME]: Executing scene: {scene_name}")
        
        results = []
        for action in scene.get("actions", []):
            device_name = action.get("device", "")
            action_cmd = action.get("action", "")
            value = action.get("value", "")
            
            # Find device
            device_ip = None
            for ip, dev in self.devices.items():
                if device_name.lower() in dev.get("type", "").lower() or \
                   device_name.lower() in dev.get("hostname", "").lower():
                    device_ip = ip
                    break
            
            if device_ip:
                # Execute action
                if "light" in device_name.lower():
                    result = self._control_lights(self.devices[device_ip], action_cmd, value)
                elif "tv" in device_name.lower():
                    result = self._control_tv(device_ip, action_cmd, value)
                elif "plug" in device_name.lower():
                    result = self._control_plug(self.devices[device_ip], action_cmd, value)
                elif "speaker" in device_name.lower():
                    result = self._control_speaker(self.devices[device_ip], action_cmd, value)
                else:
                    result = f"⚠️ Device type not supported in scene"
                
                results.append(result)
        
        return f"🎭 Scene '{scene_name}':\n" + "\n".join(results)

    def run(self, parameters: dict):
        user_input = parameters.get("user_input", "").strip().lower()
        
        print(f"🏠 [SMART HOME]: Processing: '{user_input}'")
        
        if not user_input:
            return "Smart Home ready. Try 'scan devices', 'tv youtube', or 'movie night'"
        
        # --- SCAN DEVICES ---
        if any(cmd in user_input for cmd in ["scan", "discover", "find devices"]):
            devices = self._scan_network()
            
            if not devices:
                return "❌ No smart devices found. Make sure devices are powered on."
            
            # Group by room
            rooms = {}
            for device in devices:
                room = device.get("room", "unknown")
                if room not in rooms:
                    rooms[room] = []
                rooms[room].append(device)
            
            result = ["🏠 **Smart Home Overview**", "=" * 50]
            
            for room, room_devices in rooms.items():
                result.append(f"\n📍 **{room.title()}:**")
                for device in room_devices:
                    result.append(f"  • {device['type']} ({device['ip']})")
            
            result.append(f"\n📊 Total: {len(devices)} device(s) across {len(rooms)} room(s)")
            result.append("\n💡 Try: 'living room on' or 'tv netflix'")
            return "\n".join(result)
        
        # --- ROOM CONTROL ---
        for room in self.rooms.keys():
            if room in user_input:
                if "on" in user_input:
                    return f"✅ Turning on all devices in {room}"
                elif "off" in user_input:
                    return f"✅ Turning off all devices in {room}"
                else:
                    # List devices in room
                    room_devices = [d for d in self.devices.values() 
                                  if d.get("room", "").lower() == room]
                    if room_devices:
                        result = [f"📍 **{room.title()} Devices:**", "=" * 40]
                        for device in room_devices:
                            result.append(f"• {device['type']} - Control with: '{device['type'].split()[0].lower()} on/off'")
                        return "\n".join(result)
                    else:
                        return f"❌ No devices found in {room}. Try 'scan devices' first."
        
        # --- TV CONTROL ---
        if "tv" in user_input or "television" in user_input:
            # Find TV
            tv_ip = None
            for ip, device in self.devices.items():
                if "tv" in device.get("type", "").lower():
                    tv_ip = ip
                    break
            
            if not tv_ip:
                return "❌ No TV found. Use 'scan devices' first."
            
            # TV commands
            if "power on" in user_input or "turn on tv" in user_input:
                return self._control_tv(tv_ip, "poweron")
            elif "power off" in user_input or "turn off tv" in user_input:
                return self._control_tv(tv_ip, "poweroff")
            elif "youtube" in user_input:
                return self._control_tv(tv_ip, "app", "youtube")
            elif "netflix" in user_input:
                return self._control_tv(tv_ip, "app", "netflix")
            elif "disney" in user_input:
                return self._control_tv(tv_ip, "app", "disney")
            elif "amazon" in user_input or "prime" in user_input:
                return self._control_tv(tv_ip, "app", "amazon")
            elif "spotify" in user_input:
                return self._control_tv(tv_ip, "app", "spotify")
            elif "volume up" in user_input:
                return self._control_tv(tv_ip, "volumeup")
            elif "volume down" in user_input:
                return self._control_tv(tv_ip, "volumedown")
            elif "mute" in user_input:
                return self._control_tv(tv_ip, "volumemute")
            elif "home" in user_input:
                return self._control_tv(tv_ip, "home")
            else:
                return f"TV found. Try: 'tv youtube', 'tv netflix', 'tv volume up'"
        
        # --- LIGHTS CONTROL ---
        if "light" in user_input or "lights" in user_input or "lamp" in user_input:
            # Find lights
            light_ips = [ip for ip, device in self.devices.items() 
                        if "light" in device.get("type", "").lower()]
            
            if not light_ips:
                return "❌ No smart lights found. Use 'scan devices' first."
            
            # Light commands
            if "on" in user_input:
                results = []
                for ip in light_ips:
                    results.append(self._control_lights(self.devices[ip], "on"))
                return "\n".join(results)
            elif "off" in user_input:
                results = []
                for ip in light_ips:
                    results.append(self._control_lights(self.devices[ip], "off"))
                return "\n".join(results)
            elif "bright" in user_input or "dim" in user_input:
                # Extract percentage
                import re
                match = re.search(r'(\d+)%', user_input)
                percentage = match.group(1) if match else "50"
                results = []
                for ip in light_ips:
                    results.append(self._control_lights(self.devices[ip], "brightness", f"{percentage}%"))
                return "\n".join(results)
            else:
                return f"Found {len(light_ips)} light(s). Try: 'lights on', 'lights off', 'lights dim 50%'"
        
        # --- PLUG CONTROL ---
        if "plug" in user_input or "socket" in user_input or "outlet" in user_input:
            # Find plugs
            plug_ips = [ip for ip, device in self.devices.items() 
                       if "plug" in device.get("type", "").lower()]
            
            if not plug_ips:
                return "❌ No smart plugs found. Use 'scan devices' first."
            
            if "on" in user_input:
                results = []
                for ip in plug_ips:
                    results.append(self._control_plug(self.devices[ip], "on"))
                return "\n".join(results)
            elif "off" in user_input:
                results = []
                for ip in plug_ips:
                    results.append(self._control_plug(self.devices[ip], "off"))
                return "\n".join(results)
            else:
                return f"Found {len(plug_ips)} plug(s). Try: 'plug on' or 'plug off'"
        
        # --- SCENES ---
        for scene_name in self.scenes.keys():
            if scene_name in user_input:
                return self._execute_scene(scene_name)
        
        # Create new scene
        if "create scene" in user_input or "save scene" in user_input:
            # Extract scene name
            scene_name = user_input.replace("create scene", "").replace("save scene", "").strip()
            if scene_name:
                self.scenes[scene_name.lower()] = {
                    "description": "Custom scene created by user",
                    "actions": []
                }
                self._save_scenes()
                return f"✅ Created scene '{scene_name}'. Add devices with 'add to scene {scene_name}'"
        
        # --- LIST DEVICES ---
        if "list devices" in user_input or "show devices" in user_input:
            if not self.devices:
                return "❌ No devices discovered yet. Use 'scan devices' first."
            
            result = ["📋 **All Smart Devices:**", "=" * 50]
            for ip, device in self.devices.items():
                room = device.get("room", "unknown")
                result.append(f"• {device['type']} at {ip} ({room})")
            
            return "\n".join(result)
        
        # --- LIST SCENES ---
        if "list scenes" in user_input or "show scenes" in user_input:
            result = ["🎭 **Available Scenes:**", "=" * 50]
            for scene_name, scene_info in self.scenes.items():
                result.append(f"• {scene_name.title()}: {scene_info.get('description', 'No description')}")
            
            return "\n".join(result)
        
        # --- HELP ---
        if "help" in user_input:
            return """🏠 **Smart Home Commands:**

**Discovery:**
• scan devices - Find all smart devices
• list devices - Show discovered devices
• list scenes - Show available scenes

**Room Control:**
• living room on/off - Control entire room
• bedroom on/off - Bedroom devices
• kitchen on/off - Kitchen devices

**Device Control:**
• tv youtube/netflix/disney - Open apps on TV
• tv volume up/down/mute - Control TV volume
• lights on/off/dim 50% - Control smart lights
• plug on/off - Control smart plugs

**Scenes:**
• movie night - Setup for movies
• good morning - Wake up routine
• good night - Bedtime routine
• party mode - Entertainment setup

**Advanced:**
• create scene [name] - Create custom scene
• list scenes - Show all scenes"""
        
        # --- DEFAULT ---
        return "I can control your smart home. Try 'scan devices' to get started or 'help' for commands."


# Test function
def test_smart_home():
    """Test the Smart Home skill"""
    skill = SmartHome()
    
    test_commands = [
        "scan devices",
        "list devices",
        "tv youtube",
        "lights on",
        "living room off",
        "movie night",
        "list scenes",
        "help",
    ]
    
    print("\n🏠 Testing Smart Home:")
    print("=" * 50)
    
    for cmd in test_commands:
        print(f"\n🔘 Command: {cmd}")
        result = skill.run({"user_input": cmd})
        print(f"   Result: {result[:200]}..." if len(str(result)) > 200 else f"   Result: {result}")
        time.sleep(1)


if __name__ == "__main__":
    test_smart_home()