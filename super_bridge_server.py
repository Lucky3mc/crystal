# super_bridge_server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import threading
import time
from datetime import datetime
import logging
from typing import Dict, List, Any
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SuperCrystalBridge:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        
        self.connected_devices = {}
        self.skill_responses = {}
        self.crystal_endpoint = "http://localhost:8000"  # Your Crystal AI
        
        # Skill mappings
        self.skill_categories = {
            'media': ['play', 'pause', 'stop', 'music', 'video', 'volume', 'mute'],
            'communication': ['call', 'message', 'sms', 'email', 'contact'],
            'device': ['brightness', 'volume', 'wifi', 'bluetooth', 'battery'],
            'apps': ['open', 'close', 'launch', 'install', 'app'],
            'camera': ['camera', 'photo', 'picture', 'selfie', 'record'],
            'files': ['file', 'folder', 'download', 'delete', 'move'],
            'settings': ['setting', 'configure', 'preference', 'option'],
            'automation': ['automate', 'schedule', 'timer', 'reminder'],
            'security': ['lock', 'unlock', 'password', 'secure'],
            'system': ['info', 'status', 'storage', 'memory']
        }
        
        logger.info("Super Crystal Bridge initialized")
    
    def setup_routes(self):
        @self.app.route('/ping', methods=['GET'])
        def ping():
            return jsonify({
                'status': 'online',
                'service': 'Super Crystal Bridge',
                'time': datetime.now().isoformat(),
                'devices': len(self.connected_devices),
                'version': '2.0'
            })
        
        @self.app.route('/register', methods=['POST'])
        def register_device():
            data = request.json
            device_id = data.get('device_id')
            
            if not device_id:
                return jsonify({'error': 'Device ID required'}), 400
            
            device_info = {
                'capabilities': data.get('capabilities', {}),
                'last_seen': datetime.now(),
                'name': data.get('name', 'Android Device'),
                'type': 'android',
                'ip': request.remote_addr,
                'skills': data.get('capabilities', {}).get('skills', []),
                'registered_at': datetime.now().isoformat()
            }
            
            self.connected_devices[device_id] = device_info
            logger.info(f"Device registered: {device_id} with {len(device_info['skills'])} skills")
            
            return jsonify({
                'status': 'registered',
                'device_id': device_id,
                'message': 'Welcome to Crystal Network',
                'available_skills': list(self.skill_categories.keys())
            })
        
        @self.app.route('/process', methods=['POST'])
        def process_command():
            try:
                data = request.json
                device_id = data.get('device_id')
                message = data.get('message', '').strip()
                
                if not device_id or not message:
                    return jsonify({'error': 'Missing parameters'}), 400
                
                # Update device presence
                if device_id in self.connected_devices:
                    self.connected_devices[device_id]['last_seen'] = datetime.now()
                else:
                    self.connected_devices[device_id] = {
                        'last_seen': datetime.now(),
                        'name': 'New Device',
                        'type': 'android'
                    }
                
                logger.info(f"Processing command from {device_id}: {message}")
                
                # Check if command matches any skill category
                skill_match = self.match_skill_category(message)
                if skill_match:
                    response = self.generate_skill_response(skill_match, message, device_id)
                    return jsonify({
                        'response': response,
                        'skill_used': skill_match,
                        'processed_by': 'bridge',
                        'should_speak': True
                    })
                
                # Send to Crystal AI for complex processing
                crystal_response = self.send_to_crystal(message, device_id)
                
                return jsonify({
                    'response': crystal_response,
                    'skill_used': 'ai',
                    'processed_by': 'crystal_ai',
                    'should_speak': True
                })
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/devices', methods=['GET'])
        def list_devices():
            devices = []
            for device_id, info in self.connected_devices.items():
                device_data = {
                    'id': device_id,
                    'name': info.get('name', 'Unknown'),
                    'type': info.get('type', 'unknown'),
                    'last_seen': info['last_seen'].isoformat(),
                    'ip': info.get('ip', 'unknown'),
                    'skills': info.get('capabilities', {}).get('skills', []),
                    'status': 'active' if (datetime.now() - info['last_seen']).seconds < 60 else 'inactive'
                }
                devices.append(device_data)
            
            return jsonify({
                'devices': devices,
                'total': len(devices),
                'active': sum(1 for d in devices if d['status'] == 'active')
            })
        
        @self.app.route('/skills', methods=['GET'])
        def list_skills():
            return jsonify({
                'categories': self.skill_categories,
                'total_categories': len(self.skill_categories),
                'description': 'Available skill categories for Android devices'
            })
        
        @self.app.route('/execute_skill', methods=['POST'])
        def execute_skill():
            """Direct skill execution endpoint"""
            data = request.json
            skill_name = data.get('skill')
            parameters = data.get('parameters', {})
            device_id = data.get('device_id')
            
            if not skill_name:
                return jsonify({'error': 'Skill name required'}), 400
            
            response = self.execute_direct_skill(skill_name, parameters, device_id)
            return jsonify({
                'skill': skill_name,
                'result': response,
                'device_id': device_id
            })
    
    def match_skill_category(self, message: str) -> str:
        """Match message to skill category"""
        message_lower = message.lower()
        
        for category, keywords in self.skill_categories.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return category
        
        return None
    
    def generate_skill_response(self, category: str, message: str, device_id: str) -> str:
        """Generate response based on skill category"""
        device_info = self.connected_devices.get(device_id, {})
        device_skills = device_info.get('capabilities', {}).get('skills', [])
        
        responses = {
            'media': f"I'll handle media control for: '{message}'. Your device has {len([s for s in device_skills if 'music' in s or 'media' in s])} media skills.",
            'communication': f"Communication command detected: '{message}'. I can help with calls, messages, and contacts.",
            'device': f"Device control: '{message}'. Adjusting device settings as requested.",
            'apps': f"App control: '{message}'. Launching or managing applications.",
            'camera': f"Camera command: '{message}'. Ready to capture photos or videos.",
            'files': f"File management: '{message}'. Handling file operations.",
            'settings': f"Settings adjustment: '{message}'. Configuring device preferences.",
            'automation': f"Automation: '{message}'. Setting up routines or schedules.",
            'security': f"Security command: '{message}'. Managing device security.",
            'system': f"System info: '{message}'. Getting device status and information."
        }
        
        return responses.get(category, f"Processing {category} skill: {message}")
    
    def execute_direct_skill(self, skill_name: str, parameters: Dict, device_id: str) -> str:
        """Execute a specific skill directly"""
        skill_responses = {
            'play_music': f"Playing music with parameters: {parameters}",
            'take_photo': "Taking photo with camera",
            'make_call': f"Making call to: {parameters.get('number', 'unknown')}",
            'send_message': f"Sending message: {parameters.get('text', '')}",
            'open_app': f"Opening app: {parameters.get('app_name', 'unknown')}",
            'set_brightness': f"Setting brightness to: {parameters.get('level', 50)}%",
            'toggle_wifi': "Toggling WiFi",
            'get_battery': "Getting battery status",
            'list_files': "Listing files in downloads",
            'set_alarm': f"Setting alarm for: {parameters.get('time', 'unknown')}"
        }
        
        return skill_responses.get(skill_name, f"Skill '{skill_name}' executed with parameters: {parameters}")
    
    def send_to_crystal(self, message: str, device_id: str) -> str:
        """Send to your Crystal AI"""
        try:
            device_info = self.connected_devices.get(device_id, {})
            
            ai_request = {
                'input': message,
                'device_id': device_id,
                'device_info': device_info,
                'device_skills': device_info.get('capabilities', {}).get('skills', []),
                'context': {
                    'time': datetime.now().isoformat(),
                    'has_media': 'music' in str(device_info.get('capabilities', {})).lower(),
                    'can_call': 'call' in str(device_info.get('capabilities', {})).lower(),
                    'device_type': device_info.get('type', 'android')
                }
            }
            
            # Send to your Crystal AI
            response = requests.post(
                f"{self.crystal_endpoint}/chat",
                json=ai_request,
                timeout=30
            )
            
            if response.status_code == 200:
                ai_data = response.json()
                return ai_data.get('response', f"Crystal AI: {message}")
            else:
                return self.fallback_response(message, device_info)
                
        except Exception as e:
            logger.error(f"Crystal AI connection failed: {e}")
            return self.fallback_response(message, {})
    
    def fallback_response(self, message: str, device_info: Dict) -> str:
        """Fallback when Crystal AI is unavailable"""
        message_lower = message.lower()
        
        fallbacks = [
            ("hello", "Hello! Your Android clone is connected to Crystal Bridge."),
            ("what can you do", "I can help control your Android device: play music, make calls, send messages, control settings, and much more!"),
            ("time", f"The time is {datetime.now().strftime('%I:%M %p')}"),
            ("date", f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"),
            ("battery", "You can check battery in device settings or ask me to check it for you."),
            ("weather", "I can fetch weather info through the main Crystal AI when connected."),
            ("thank", "You're welcome! I'm here to help with your Android device.")
        ]
        
        for keyword, response in fallbacks:
            if keyword in message_lower:
                return response
        
        # Check device capabilities
        skills = device_info.get('capabilities', {}).get('skills', [])
        if skills:
            skill_list = ', '.join(skills[:5])
            return f"Your device has these skills: {skill_list}. Please connect to main Crystal AI for: '{message}'"
        
        return f"Android Clone received: '{message}'. Connect to main Crystal AI for full processing."
    
    def cleanup_devices(self):
        """Remove inactive devices"""
        while True:
            time.sleep(300)  # 5 minutes
            current_time = datetime.now()
            expired = []
            
            for device_id, info in self.connected_devices.items():
                if (current_time - info['last_seen']).seconds > 900:  # 15 minutes
                    expired.append(device_id)
            
            for device_id in expired:
                del self.connected_devices[device_id]
                logger.info(f"Removed inactive device: {device_id}")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the bridge server"""
        # Start cleanup thread
        threading.Thread(target=self.cleanup_devices, daemon=True).start()
        
        # Get local IP for display
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = host
        
        logger.info("=" * 60)
        logger.info("SUPER CRYSTAL BRIDGE SERVER")
        logger.info("=" * 60)
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Local IP: {local_ip}")
        logger.info(f"Android devices connect to: http://{local_ip}:{port}")
        logger.info(f"Skill Categories: {len(self.skill_categories)}")
        logger.info("=" * 60)
        logger.info("Ready for Android clone connections...")
        
        self.app.run(host=host, port=port, debug=debug, threaded=True)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Super Crystal Bridge for Android')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    bridge = SuperCrystalBridge()
    bridge.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()