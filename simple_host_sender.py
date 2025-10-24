"""
Simplified Pillbox Communication Module
Supports direct transmission of instructions to pillbox
"""
import socket
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from queue import Queue

@dataclass
class SimpleAlert:
    """Simplified Medication Alert"""
    medication_id: str  # M0-M9
    scheduled_time: str
    dosage_count: int
    notes: str  # Instructions, will be displayed on pillbox

@dataclass
class PillboxStatus:
    """Pillbox Status"""
    compartment_id: str
    is_open: bool
    last_opened: str
    medication_count: int = 0

@dataclass
class WelcomeInfo:
    """ESP32 Welcome Message Info"""
    device: str          # Device name
    ip: str             # ESP32 IP address
    time: str           # Current time
    boxes: int          # Number of boxes

@dataclass
class BoxEvent:
    """Box Open/Close Event"""
    box: int            # Box number
    state: str          # "open" or "closed"
    time: str           # Event time

class SimplePillboxCommunicator:
    """Simplified Pillbox Communicator"""

    def __init__(self, ip=None, port=8080, auto_discover=True):
        """
        Initialize Pillbox Communicator

        Args:
            ip: ESP32 IP address (None = auto-discover)
            port: ESP32 TCP port (default 8080)
            auto_discover: Automatically discover ESP32 if ip is None
        """
        self.ip = ip
        self.port = port
        self.auto_discover = auto_discover
        self.socket = None
        self.is_connected = False
        self.is_listening = False
        self.status_callbacks: List[Callable] = []
        self.listen_thread: Optional[threading.Thread] = None
        self.last_status: Dict[str, PillboxStatus] = {}
        self.recv_buffer = ""                           # TCP receive buffer
        self.welcome_info: Optional[WelcomeInfo] = None # Welcome message info
        self.device_boxes = 0                           # Number of device boxes
        self.message_queue = Queue()                    # Thread-safe message queue for Qt GUI

        # Auto-discover ESP32 if no IP provided
        if self.ip is None and self.auto_discover:
            print("No IP provided, attempting auto-discovery...")
            self._auto_discover_esp32()
        
    def _auto_discover_esp32(self):
        """Auto-discover ESP32 using UDP broadcast"""
        try:
            from esp32_discovery import discover_esp32, save_to_config

            discovered_ip, discovered_port = discover_esp32(timeout=3, max_retries=2)

            if discovered_ip:
                self.ip = discovered_ip
                self.port = discovered_port
                print(f"[Success] Auto-discovered ESP32 at {self.ip}:{self.port}")

                # Save to config for future use
                save_to_config(self.ip, self.port)
            else:
                print("[Failed] Auto-discovery failed, trying config file...")
                self._load_from_config()

        except ImportError:
            print("[Warning] esp32_discovery module not found, trying config file...")
            self._load_from_config()
        except Exception as e:
            print(f"[Warning] Auto-discovery error: {e}")
            self._load_from_config()

    def _load_from_config(self):
        """Load IP from config file as fallback"""
        try:
            with open("system_config.json", 'r') as f:
                config = json.load(f)
                self.ip = config.get('pillbox_ip', '192.168.4.2')
                self.port = config.get('pillbox_port', 8080)
                print(f"[Info] Loaded from config: {self.ip}:{self.port}")
        except Exception as e:
            print(f"[Warning] Failed to load config: {e}")
            print("  Using default IP: 192.168.4.2:8080")
            self.ip = "192.168.4.2"
            self.port = 8080

    def add_status_callback(self, callback: Callable):
        """Add Status Callback Function"""
        self.status_callbacks.append(callback)

    def connect(self) -> bool:
        """Connect to Pillbox"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
            self.is_connected = True
            print(f"Connected to pillbox at {self.ip}:{self.port}")
            
            # Start listening for status
            self.start_listening()
            return True
            
        except socket.error as e:
            print(f"Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect"""
        self.is_connected = False
        self.stop_listening()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def start_listening(self):
        """Start Listening for Pillbox Status"""
        if self.is_listening:
            return
            
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
    
    def stop_listening(self):
        """Stop Listening"""
        self.is_listening = False
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2)

    def _listen_loop(self):
        """Listen Loop with message buffering"""
        while self.is_listening and self.is_connected:
            try:
                if self.socket:
                    self.socket.settimeout(1)
                    data = self.socket.recv(1024).decode('utf-8')

                    if data:
                        # Accumulate to receive buffer
                        self.recv_buffer += data

                        # Split by newline to get complete messages
                        while '\n' in self.recv_buffer:
                            line, self.recv_buffer = self.recv_buffer.split('\n', 1)
                            line = line.strip()

                            if line:  # Ignore empty lines
                                self._process_received_data(line)

            except socket.timeout:
                continue
            except socket.error as e:
                print(f"Listen error: {e}")
                self.is_connected = False
                break
            except Exception as e:
                print(f"Unexpected error in listen loop: {e}")
                continue
    
    def _process_received_data(self, data: str):
        """Process Received Data"""
        try:
            status_data = json.loads(data.strip())

            if 'type' not in status_data:
                return  # Silently ignore messages without type field

            msg_type = status_data['type']

            # Dispatch based on message type
            if msg_type == 'welcome':
                self._handle_welcome(status_data)
            elif msg_type == 'status':
                self._handle_status_report(status_data)
            elif msg_type == 'box_event':
                self._handle_box_event(status_data)
            elif msg_type == 'compartment_status':
                self._handle_compartment_status(status_data)
            # Unknown types are silently ignored

        except json.JSONDecodeError:
            pass  # Silently ignore JSON decode errors
        except Exception:
            pass  # Silently ignore all other errors
    
    def _handle_welcome(self, data: Dict):
        """Handle Welcome Message from ESP32"""
        self.welcome_info = WelcomeInfo(
            device=data.get('device', 'Unknown'),
            ip=data.get('ip', self.ip),
            time=data.get('time', ''),
            boxes=data.get('boxes', 0)
        )
        self.device_boxes = self.welcome_info.boxes

        # Put message in queue for GUI thread to process (thread-safe)
        self.message_queue.put(('welcome', self.welcome_info))

    def _handle_status_report(self, data: Dict):
        """Handle Status Report from ESP32"""
        # Put message in queue for GUI thread to process (thread-safe)
        self.message_queue.put(('status', data))

    def _handle_box_event(self, data: Dict):
        """Handle Box Open/Close Event"""
        event = BoxEvent(
            box=data.get('box', 0),
            state=data.get('state', 'unknown'),
            time=data.get('time', '')
        )

        # Put message in queue for GUI thread to process (thread-safe)
        self.message_queue.put(('box_event', event))

    def _handle_compartment_status(self, data: Dict):
        """Handle Pillbox Compartment Status"""
        compartment_id = data.get('compartment_id')
        if compartment_id:
            status = PillboxStatus(
                compartment_id=compartment_id,
                is_open=data.get('is_open', False),
                last_opened=data.get('last_opened', ''),
                medication_count=data.get('medication_count', 0)
            )

            self.last_status[compartment_id] = status

            # Put message in queue for GUI thread to process (thread-safe)
            self.message_queue.put(('compartment_status', status))
    


    def send_medication_config(self, config: Dict[str, str]) -> bool:
        """Send Medication Configuration to Pillbox
        config: {"0": "M0", "1": "M1", ...} compartment to medication mapping
        """
        config_data = {
            'type': 'medication_config',
            'compartments': config,
            'timestamp': datetime.now().isoformat()
        }
        return self._send_json(config_data)

    def send_schedule_config(self, schedules: List[Dict]) -> Dict:
        """
        Send complete medication schedule configuration to ESP32

        Args:
            schedules: List of schedule dictionaries from database

        Returns:
            dict: Response from ESP32 with assignment info or error

        Format sent to ESP32:
        {
            "cmd": "SET_SCHEDULE",
            "medications": [
                {
                    "medication_id": "M0",
                    "medication_name": "Aspirin",
                    "times_per_day": 3,
                    "pills_per_dose": 2,
                    "schedule_times": ["08:00", "14:00", "20:00"],
                    "start_date": "2025-10-15",
                    "end_date": "2025-11-15",
                    "notes": "Take with food",
                    "duration": 60,
                    "is_active": true
                }
            ]
        }
        """
        if not self.is_connected or not self.socket:
            return {"status": "ERROR", "message": "Not connected to pillbox"}

        try:
            from simple_models import get_medication_name

            # Build medications list
            medications = []
            for schedule in schedules:
                if not schedule.get('is_active', True):
                    continue

                med_id = schedule.get('medication_id', 'M0')
                med_name = get_medication_name(med_id)

                med_config = {
                    "medication_id": med_id,
                    "medication_name": med_name,
                    "times_per_day": schedule.get('times_per_day', 1),
                    "pills_per_dose": schedule.get('dosage_count', 1),
                    "schedule_times": schedule.get('schedule_times', []),
                    "start_date": schedule.get('start_date', ''),
                    "end_date": schedule.get('end_date', ''),
                    "notes": schedule.get('notes', '')[:100],  # Limit to 100 chars
                    "duration": 60,  # Default duration in minutes
                    "is_active": True
                }

                medications.append(med_config)

            if not medications:
                return {"status": "ERROR", "message": "No active medications to send"}

            # Build command with header
            config_data = {
                "cmd": "SET_SCHEDULE",
                "timestamp": datetime.now().isoformat(),
                "medications": medications
            }

            # Send as JSON
            json_str = json.dumps(config_data, ensure_ascii=False)
            message = json_str + '\n'
            self.socket.send(message.encode('utf-8'))

            # Wait for response (with timeout)
            old_timeout = self.socket.gettimeout()
            self.socket.settimeout(5)
            try:
                response_data = self.socket.recv(2048).decode('utf-8')
                response = json.loads(response_data.strip())
                return response
            except socket.timeout:
                return {"status": "TIMEOUT", "message": "No response from ESP32"}
            except json.JSONDecodeError:
                return {"status": "ERROR", "message": "Invalid response format"}
            finally:
                self.socket.settimeout(old_timeout)

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def send_display_message(self, medication_id: str, dosage_count: int, 
                           scheduled_time: str, notes: str, duration: int = 30) -> bool:
        """Send Complete Medication Reminder to Pillbox Screen"""
        from simple_models import get_medication_name
        
        med_name = get_medication_name(medication_id)
        
        # Compose complete message
        message = f"Medication Reminder\n\n"
        message += f"Medication: {medication_id} ({med_name})\n"
        message += f"Time: {scheduled_time}\n"
        message += f"Dosage: {dosage_count} pills\n"
        
        if notes:
            message += f"\nInstructions:\n{notes}\n"
        
        message += "\nPlease take medication on time!"
        
        display_data = {
            'type': 'display_message',
            'medication_id': medication_id,
            'message': message,
            'notes': notes,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        return self._send_json(display_data)
    
    def request_status(self) -> bool:
        """Request Pillbox Status"""
        request_data = {
            'type': 'status_request',
            'timestamp': datetime.now().isoformat()
        }
        return self._send_json(request_data)
    
    def _send_json(self, data: Dict) -> bool:
        """Send JSON Format Data"""
        if not self.is_connected or not self.socket:
            print("Not connected to pillbox")
            return False
        
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            message = json_str + '\n'
            self.socket.send(message.encode('utf-8'))
            print(f"Sent: {json_str}")
            return True
            
        except socket.error as e:
            print(f"Send error: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"JSON send error: {e}")
            return False

# Maintain backward compatibility
class ESP32Sender:
    """Simplified ESP32 Communication Class (Legacy)"""

    def __init__(self, ip=None, port=8080, auto_discover=True):
        """
        Initialize ESP32 Sender

        Args:
            ip: ESP32 IP address (None = auto-discover)
            port: ESP32 TCP port (default 8080)
            auto_discover: Automatically discover ESP32 if ip is None
        """
        self.ip = ip
        self.port = port
        self.socket = None

        # Auto-discover if no IP provided
        if self.ip is None and auto_discover:
            try:
                from esp32_discovery import discover_esp32
                discovered_ip, discovered_port = discover_esp32(timeout=3, max_retries=2)
                if discovered_ip:
                    self.ip = discovered_ip
                    self.port = discovered_port
                else:
                    self.ip = "192.168.4.2"  # Default fallback
            except:
                self.ip = "192.168.4.2"  # Default fallback

    def connect(self):
        """Connect to ESP32"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
            return True
        except socket.error as e:
            print(f"Connection failed: {e}")
            return False

    def send(self, message):
        """Send Message to ESP32"""
        if not self.socket:
            return False
        try:
            self.socket.send((message + '\n').encode('utf-8'))
            return True
        except socket.error:
            return False

    def close(self):
        """Close Connection"""
        if self.socket:
            self.socket.close()
            self.socket = None