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

class SimplePillboxCommunicator:
    """Simplified Pillbox Communicator"""

    def __init__(self, ip="192.168.4.2", port=8080):
        self.ip = ip
        self.port = port
        self.socket = None
        self.is_connected = False
        self.is_listening = False
        self.status_callbacks: List[Callable] = []
        self.listen_thread: Optional[threading.Thread] = None
        self.last_status: Dict[str, PillboxStatus] = {}
        
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
        """Listen Loop"""
        while self.is_listening and self.is_connected:
            try:
                if self.socket:
                    self.socket.settimeout(1)
                    data = self.socket.recv(1024).decode('utf-8')
                    
                    if data:
                        self._process_received_data(data)
                        
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
            
            if 'type' in status_data:
                if status_data['type'] == 'compartment_status':
                    self._handle_compartment_status(status_data)
                    
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {data}")
        except Exception as e:
            print(f"Error processing data: {e}")
    
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
            
            # Notify all callback functions
            for callback in self.status_callbacks:
                try:
                    callback('compartment_status', status)
                except Exception as e:
                    print(f"Callback error: {e}")
    


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
    """Simplified ESP32 Communication Class"""
    
    def __init__(self, ip="192.168.4.2", port=8080):
        self.ip = ip
        self.port = port
        self.socket = None

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