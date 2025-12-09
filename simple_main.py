import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QTabWidget, QPushButton, QLabel,
                            QLineEdit, QTextEdit, QMessageBox, QGroupBox,
                            QFormLayout, QSpinBox, QComboBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPixmap, QImage

# Import simplified modules
from simple_models import SimpleDataManager, MEDICATIONS, get_medication_name
from simple_host_sender import SimplePillboxCommunicator, ESP32Sender, SimpleAlert, ESP32CamCommunicator
from simple_doctor_interface import SimpleDoctorInterface
from photo_handler import PhotoHandler


class CameraPreviewWidget(QWidget):
    """Camera Preview Tab - Shows live video from ESP32-CAM"""

    def __init__(self, cam_comm, photo_handler):
        super().__init__()
        self.cam_comm = cam_comm
        self.photo_handler = photo_handler
        self.is_streaming = False
        self.pending_capture = False
        self.current_box = 0
        self.current_med_name = ""

        self.setup_ui()

        # Timer for requesting frames
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.request_frame)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("ESP32-CAM Live Preview")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Video display area
        self.video_label = QLabel("Camera Preview\n\nClick 'Start Preview' to begin")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet(
            "background-color: #1a1a1a; color: #888; border: 2px solid #333; font-size: 14px;"
        )
        layout.addWidget(self.video_label)

        # Control buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Preview")
        self.start_btn.clicked.connect(self.start_streaming)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop Preview")
        self.stop_btn.clicked.connect(self.stop_streaming)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        btn_layout.addWidget(self.stop_btn)

        self.capture_btn = QPushButton("Manual Capture")
        self.capture_btn.clicked.connect(self.manual_capture)
        self.capture_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        btn_layout.addWidget(self.capture_btn)

        layout.addLayout(btn_layout)

        # Status label
        self.status_label = QLabel("Status: Idle | Connect to ESP32-CAM first")
        self.status_label.setStyleSheet("color: #666; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # Info label
        info_label = QLabel("When a pill box opens, the current frame will be automatically captured and saved.")
        info_label.setStyleSheet("color: #888; font-size: 11px; margin-top: 10px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        layout.addStretch()

    def start_streaming(self):
        if not self.cam_comm.is_connected:
            self.status_label.setText("Status: ESP32-CAM not connected! Go to 'Pillbox Connection' tab first.")
            self.status_label.setStyleSheet("color: red;")
            return

        self.is_streaming = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.frame_timer.start(150)  # ~6-7 FPS for stability
        self.status_label.setText("Status: Streaming...")
        self.status_label.setStyleSheet("color: green;")

    def stop_streaming(self):
        self.is_streaming = False
        self.frame_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Status: Stopped")
        self.status_label.setStyleSheet("color: #666;")

    def request_frame(self):
        if self.is_streaming and self.cam_comm.is_connected:
            self.cam_comm.get_frame()

    def display_frame(self, frame_data: bytes, width: int, height: int):
        """Display frame on video_label"""
        try:
            image = QImage.fromData(frame_data, "JPEG")
            if image.isNull():
                return

            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)

            # Check if we need to capture
            if self.pending_capture:
                self.save_capture(frame_data)
                self.pending_capture = False

        except Exception as e:
            print(f"Display frame error: {e}")

    def trigger_capture(self, box: int, med_name: str):
        """Called when box opens - triggers capture of next frame"""
        self.pending_capture = True
        self.current_box = box
        self.current_med_name = med_name
        self.status_label.setText(f"Status: Capturing for Box {box} ({med_name})...")
        self.status_label.setStyleSheet("color: orange;")

    def save_capture(self, frame_data: bytes):
        """Save captured frame to record folder"""
        try:
            # Create record folder
            base_dir = self.photo_handler.base_dir
            date_str = datetime.now().strftime("%Y-%m-%d")
            record_dir = os.path.join(base_dir, date_str)
            os.makedirs(record_dir, exist_ok=True)

            # Generate filename
            time_str = datetime.now().strftime("%H%M%S")
            filename = f"{self.current_med_name}_{time_str}_1.jpg"
            save_path = os.path.join(record_dir, filename)

            # Save file
            with open(save_path, 'wb') as f:
                f.write(frame_data)

            self.status_label.setText(f"Status: Saved {filename}")
            self.status_label.setStyleSheet("color: green;")
            print(f"[CAPTURE] Saved: {save_path}")

        except Exception as e:
            self.status_label.setText(f"Status: Save failed - {e}")
            self.status_label.setStyleSheet("color: red;")
            print(f"[CAPTURE] Error: {e}")

    def manual_capture(self):
        """Manual capture button"""
        if not self.cam_comm.is_connected:
            self.status_label.setText("Status: Connect to ESP32-CAM first!")
            self.status_label.setStyleSheet("color: red;")
            return

        self.trigger_capture(0, "Manual")
        # Request a frame if not streaming
        if not self.is_streaming:
            self.cam_comm.get_frame()


class SystemStatusWidget(QWidget):
    """System Status Monitoring Panel"""

    def __init__(self, pillbox_comm: SimplePillboxCommunicator):
        super().__init__()
        self.pillbox_comm = pillbox_comm
        self.db_manager = SimpleDataManager()

        # Initialize ESP32-CAM communicator and PhotoHandler
        self.photo_handler = PhotoHandler(base_dir="record")
        self.cam_comm = ESP32CamCommunicator()
        self.cam_comm.photo_handler = self.photo_handler

        self.setup_ui()

        # Set timer to update status
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # Update every 5 seconds

        # Setup message queue polling timer (thread-safe)
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.process_message_queue)
        self.message_timer.start(100)  # Check message queue every 100ms

        # Setup CAM message queue polling timer
        self.cam_message_timer = QTimer()
        self.cam_message_timer.timeout.connect(self.process_cam_message_queue)
        self.cam_message_timer.start(100)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Pillbox connection status
        pillbox_group = QGroupBox("Pillbox Connection Status")
        pillbox_layout = QFormLayout(pillbox_group)
        
        self.pillbox_status_label = QLabel("Not connected")
        self.pillbox_ip_edit = QLineEdit("192.168.4.2")
        self.pillbox_port_spin = QSpinBox()
        self.pillbox_port_spin.setRange(1000, 9999)
        self.pillbox_port_spin.setValue(8080)

        # Auto discover button
        self.discover_btn = QPushButton("Auto Discover ESP32")
        self.discover_btn.clicked.connect(self.auto_discover_esp32)
        self.discover_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.connect_btn = QPushButton("Connect Pillbox")
        self.connect_btn.clicked.connect(self.connect_pillbox)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_pillbox)

        pillbox_layout.addRow("Status:", self.pillbox_status_label)

        # IP input with discover button
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(self.pillbox_ip_edit)
        ip_layout.addWidget(self.discover_btn)
        pillbox_layout.addRow("IP Address:", ip_layout)

        pillbox_layout.addRow("Port:", self.pillbox_port_spin)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        pillbox_layout.addRow(button_layout)
        
        layout.addWidget(pillbox_group)

        # ESP32-CAM connection status
        cam_group = QGroupBox("ESP32-CAM Connection")
        cam_layout = QFormLayout(cam_group)

        self.cam_status_label = QLabel("Not connected")
        self.cam_ip_edit = QLineEdit("192.168.4.200")  # ESP32-CAM static IP on hotspot network
        self.cam_port_spin = QSpinBox()
        self.cam_port_spin.setRange(1000, 9999)
        self.cam_port_spin.setValue(8081)

        # Auto discover CAM button
        self.cam_discover_btn = QPushButton("Auto Discover CAM")
        self.cam_discover_btn.clicked.connect(self.auto_discover_cam)
        self.cam_discover_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

        self.cam_connect_btn = QPushButton("Connect CAM")
        self.cam_connect_btn.clicked.connect(self.connect_cam)
        self.cam_disconnect_btn = QPushButton("Disconnect")
        self.cam_disconnect_btn.clicked.connect(self.disconnect_cam)

        cam_layout.addRow("Status:", self.cam_status_label)

        # CAM IP input with discover button
        cam_ip_layout = QHBoxLayout()
        cam_ip_layout.addWidget(self.cam_ip_edit)
        cam_ip_layout.addWidget(self.cam_discover_btn)
        cam_layout.addRow("IP Address:", cam_ip_layout)

        cam_layout.addRow("Port:", self.cam_port_spin)

        cam_button_layout = QHBoxLayout()
        cam_button_layout.addWidget(self.cam_connect_btn)
        cam_button_layout.addWidget(self.cam_disconnect_btn)
        cam_layout.addRow(cam_button_layout)

        # Photo count display
        self.photo_count_label = QLabel("Photos today: 0")
        cam_layout.addRow("", self.photo_count_label)

        layout.addWidget(cam_group)

        # Test functions
        test_group = QGroupBox("Test Functions")
        test_layout = QVBoxLayout(test_group)
        
        # Send configuration
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("Send medication configuration:"))
        self.send_config_btn = QPushButton("Send Current Schedule Configuration")
        self.send_config_btn.clicked.connect(self.send_current_config)
        config_layout.addWidget(self.send_config_btn)
        test_layout.addLayout(config_layout)
        
        # Test reminder
        reminder_layout = QFormLayout()
        
        self.test_medication_combo = QComboBox()
        for med_id, med_name in MEDICATIONS.items():
            self.test_medication_combo.addItem(f"{med_id} - {med_name}", med_id)
        reminder_layout.addRow("Test medication:", self.test_medication_combo)
        
        self.test_dosage_spin = QSpinBox()
        self.test_dosage_spin.setRange(1, 10)
        self.test_dosage_spin.setValue(1)
        reminder_layout.addRow("Test dosage:", self.test_dosage_spin)
        
        self.test_notes_edit = QLineEdit("Test instructions: Take after meals")
        reminder_layout.addRow("Test instructions:", self.test_notes_edit)
        
        self.send_reminder_btn = QPushButton("Send Test Reminder")
        self.send_reminder_btn.clicked.connect(self.send_test_reminder)
        reminder_layout.addRow(self.send_reminder_btn)
        
        test_layout.addLayout(reminder_layout)
        
        # Simple message test
        simple_layout = QHBoxLayout()
        self.simple_message_edit = QLineEdit("Test message")
        self.send_simple_btn = QPushButton("Send Simple Message")
        self.send_simple_btn.clicked.connect(self.send_simple_message)
        simple_layout.addWidget(self.simple_message_edit)
        simple_layout.addWidget(self.send_simple_btn)
        test_layout.addLayout(simple_layout)

        # Set time button
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Sync ESP32 time to computer time:"))
        self.set_time_btn = QPushButton("Set ESP32 Time")
        self.set_time_btn.clicked.connect(self.set_esp32_time)
        time_layout.addWidget(self.set_time_btn)
        test_layout.addLayout(time_layout)

        layout.addWidget(test_group)
        
        # Status display
        status_group = QGroupBox("Pillbox Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(status_group)
        
        layout.addStretch()
    
    def update_status(self):
        """Update status display"""
        # Update pillbox status
        if self.pillbox_comm.is_connected:
            self.pillbox_status_label.setText("✓ Connected")
            self.pillbox_status_label.setStyleSheet("color: green")
        else:
            self.pillbox_status_label.setText("✗ Not connected")
            self.pillbox_status_label.setStyleSheet("color: red")

        # Update CAM status
        if self.cam_comm.is_connected:
            self.cam_status_label.setText("✓ Connected")
            self.cam_status_label.setStyleSheet("color: green")
        else:
            self.cam_status_label.setText("✗ Not connected")
            self.cam_status_label.setStyleSheet("color: red")

        # Update photo count
        photo_count = self.photo_handler.get_photo_count()
        self.photo_count_label.setText(f"Photos today: {photo_count}")
    
    def auto_discover_esp32(self):
        """Auto discover ESP32 via UDP broadcast and fill IP"""
        self.discover_btn.setEnabled(False)
        self.discover_btn.setText("Searching...")
        QApplication.processEvents()

        try:
            from esp32_discovery import discover_esp32
            ip, port = discover_esp32(timeout=3, max_retries=2)

            if ip:
                self.pillbox_ip_edit.setText(ip)
                self.pillbox_port_spin.setValue(port)
                self.pillbox_status_label.setText(f"Found: {ip}:{port}")
                self.pillbox_status_label.setStyleSheet("color: blue")
                QMessageBox.information(self, "Discovery Success",
                    f"Found ESP32 Pillbox!\n\nIP: {ip}\nPort: {port}\n\nClick 'Connect Pillbox' to connect.")
            else:
                self.pillbox_status_label.setText("ESP32 not found")
                self.pillbox_status_label.setStyleSheet("color: orange")
                QMessageBox.warning(self, "Discovery Failed",
                    "Could not find ESP32 device.\n\nPlease check:\n"
                    "1. ESP32 is powered on\n"
                    "2. ESP32 is connected to WiFi\n"
                    "3. Computer and ESP32 are on the same network")
        except ImportError:
            QMessageBox.critical(self, "Error", "esp32_discovery module not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Discovery error: {str(e)}")
        finally:
            self.discover_btn.setEnabled(True)
            self.discover_btn.setText("Auto Discover ESP32")

    def connect_pillbox(self):
        """Connect pillbox"""
        ip = self.pillbox_ip_edit.text().strip()
        port = self.pillbox_port_spin.value()

        self.pillbox_comm.ip = ip
        self.pillbox_comm.port = port

        if self.pillbox_comm.connect():
            QMessageBox.information(self, "Success", "Pillbox connected successfully")
        else:
            QMessageBox.warning(self, "Failed", "Pillbox connection failed")
    
    def disconnect_pillbox(self):
        """Disconnect pillbox"""
        self.pillbox_comm.disconnect()
        QMessageBox.information(self, "Info", "Pillbox connection disconnected")

    def auto_discover_cam(self):
        """Auto discover ESP32-CAM via UDP broadcast and fill IP"""
        self.cam_discover_btn.setEnabled(False)
        self.cam_discover_btn.setText("Searching...")
        QApplication.processEvents()

        try:
            from esp32_discovery import discover_esp32_cam
            ip, port = discover_esp32_cam(timeout=3, max_retries=2)

            if ip:
                self.cam_ip_edit.setText(ip)
                self.cam_port_spin.setValue(port)
                self.cam_status_label.setText(f"Found: {ip}:{port}")
                self.cam_status_label.setStyleSheet("color: blue")
                QMessageBox.information(self, "Discovery Success",
                    f"Found ESP32-CAM!\n\nIP: {ip}\nPort: {port}\n\nClick 'Connect CAM' to connect.")
            else:
                self.cam_status_label.setText("ESP32-CAM not found")
                self.cam_status_label.setStyleSheet("color: orange")
                QMessageBox.warning(self, "Discovery Failed",
                    "Could not find ESP32-CAM device.\n\nPlease check:\n"
                    "1. ESP32-CAM is powered on\n"
                    "2. ESP32-CAM is connected to WiFi\n"
                    "3. Computer and ESP32-CAM are on the same network")
        except ImportError:
            QMessageBox.critical(self, "Error", "esp32_discovery module not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Discovery error: {str(e)}")
        finally:
            self.cam_discover_btn.setEnabled(True)
            self.cam_discover_btn.setText("Auto Discover CAM")

    def connect_cam(self):
        """Connect to ESP32-CAM"""
        ip = self.cam_ip_edit.text().strip()
        port = self.cam_port_spin.value()

        self.cam_comm.ip = ip
        self.cam_comm.port = port

        if self.cam_comm.connect():
            QMessageBox.information(self, "Success", "ESP32-CAM connected successfully")
        else:
            QMessageBox.warning(self, "Failed", "ESP32-CAM connection failed")

    def disconnect_cam(self):
        """Disconnect from ESP32-CAM"""
        self.cam_comm.disconnect()
        QMessageBox.information(self, "Info", "ESP32-CAM connection disconnected")

    def process_cam_message_queue(self):
        """Process messages from ESP32-CAM message queue"""
        try:
            while not self.cam_comm.message_queue.empty():
                msg_type, data = self.cam_comm.message_queue.get_nowait()
                self.handle_cam_message(msg_type, data)
        except Exception:
            pass

    def handle_cam_message(self, msg_type: str, data):
        """Handle messages from ESP32-CAM"""
        try:
            # Handle frame_data - forward to camera preview widget
            if msg_type == 'frame_data':
                # Forward to camera preview widget in main window
                main_window = self.window()
                if hasattr(main_window, 'camera_preview') and main_window.camera_preview:
                    main_window.camera_preview.display_frame(
                        data.get('data'),
                        data.get('width', 640),
                        data.get('height', 480)
                    )
                return  # Don't add frame_data to status text

            current_text = self.status_text.toPlainText()

            if msg_type == 'photo_received':
                filename = data.get('filename', 'unknown')
                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] Photo received: {filename}\n"
            elif msg_type == 'photo_complete':
                count = data.get('count', 0)
                box = data.get('box', 0)
                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] Photo capture complete: {count} photos for Box {box}\n"
            elif msg_type == 'cam_error':
                message = data.get('message', 'unknown')
                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] CAM Error: {message}\n"
            else:
                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] CAM: {msg_type}\n"

            # Limit display lines
            lines = current_text.split('\n')
            if len(lines) > 20:
                lines = lines[-15:]
                current_text = '\n'.join(lines)

            self.status_text.setPlainText(current_text + new_line)

            # Scroll to bottom
            cursor = self.status_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.status_text.setTextCursor(cursor)

            # Update photo count
            photo_count = self.photo_handler.get_photo_count()
            self.photo_count_label.setText(f"Photos today: {photo_count}")

        except Exception as e:
            print(f"Error handling CAM message: {e}")

    def get_medication_name_for_box(self, box: int) -> str:
        """Get medication name assigned to a specific box"""
        # Get active schedules and find the medication assigned to this box
        schedules = self.db_manager.get_active_schedules()
        # Box assignment: medication index % 7 = box (0-indexed)
        for i, schedule in enumerate(schedules):
            if i % 7 == (box - 1):  # box is 1-indexed
                return get_medication_name(schedule.medication_id)
        return "Unknown"

    def send_current_config(self):
        """Send current schedule configuration"""
        if not self.pillbox_comm.is_connected:
            QMessageBox.warning(self, "Warning", "Please connect to pillbox first")
            return
        
        # Get current active schedules
        schedules = self.db_manager.get_active_schedules()
        
        if not schedules:
            QMessageBox.warning(self, "Warning", "No active medication schedules")
            return
        
        # Create simple compartment configuration (assume M0 corresponds to compartment 0, M1 to compartment 1...)
        config = {}
        for i, schedule in enumerate(schedules[:10]):  # Maximum 10 compartments
            config[str(i)] = schedule.medication_id
        
        if self.pillbox_comm.send_medication_config(config):
            config_str = ", ".join([f"Compartment{k}:{v}" for k, v in config.items()])
            QMessageBox.information(self, "Success", f"Configuration sent: {config_str}")
        else:
            QMessageBox.warning(self, "Failed", "Configuration send failed")
    
    def send_test_reminder(self):
        """Send test reminder"""
        if not self.pillbox_comm.is_connected:
            QMessageBox.warning(self, "Warning", "Please connect to pillbox first")
            return
        
        medication_id = self.test_medication_combo.currentData()
        dosage_count = self.test_dosage_spin.value()
        notes = self.test_notes_edit.text().strip()
        current_time = "Now"
        
        # Send complete reminder to screen
        if self.pillbox_comm.send_display_message(medication_id, dosage_count, 
                                                current_time, notes, duration=15):
            QMessageBox.information(self, "Success", "Test reminder sent")
        else:
            QMessageBox.warning(self, "Failed", "Reminder send failed")
    
    def send_simple_message(self):
        """Send simple message"""
        if not self.pillbox_comm.is_connected:
            QMessageBox.warning(self, "Warning", "Please connect to pillbox first")
            return

        message = self.simple_message_edit.text().strip()
        if not message:
            return

        # Use display_message to send
        simple_data = {
            'type': 'simple_message',
            'message': message,
            'timestamp': 'now'
        }

        if self.pillbox_comm._send_json(simple_data):
            QMessageBox.information(self, "Success", "Message sent")
        else:
            QMessageBox.warning(self, "Failed", "Message send failed")

    def set_esp32_time(self):
        """Set ESP32 RTC time to computer time"""
        if not self.pillbox_comm.is_connected:
            QMessageBox.warning(self, "Warning", "Please connect to pillbox first")
            return

        # Get current computer time
        now = datetime.now()
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # Send SET_TIME command
        time_data = {
            'cmd': 'SET_TIME',
            'datetime': datetime_str
        }

        if self.pillbox_comm._send_json(time_data):
            QMessageBox.information(self, "Success", f"ESP32 time set to: {datetime_str}")
        else:
            QMessageBox.warning(self, "Failed", "Failed to set ESP32 time")
    
    def process_message_queue(self):
        """Process messages from pillbox message queue (runs in GUI thread)"""
        try:
            # Process all pending messages in the queue
            while not self.pillbox_comm.message_queue.empty():
                msg_type, data = self.pillbox_comm.message_queue.get_nowait()
                self.handle_pillbox_status(msg_type, data)
        except Exception:
            pass  # Silently handle exceptions

    def handle_pillbox_status(self, status_type: str, data):
        """Handle pillbox status callback (now called from GUI thread)"""
        print(f"[DEBUG] handle_pillbox_status called: type={status_type}, data={data}")
        try:
            current_text = self.status_text.toPlainText()

            # 特殊處理用藥記錄事件
            if status_type == 'medication_taken':
                medication_id = data.get('medication_id', 'Unknown')
                time_taken = data.get('time', 'Unknown')
                status = data.get('status', 'unknown')

                from simple_models import get_medication_name
                med_name = get_medication_name(medication_id)

                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] 💊 {med_name} taken at {time_taken} ({status})\n"

            # Handle box_event - trigger photo capture when box opens
            # Note: data is a BoxEvent dataclass, not a dict
            elif status_type == 'box_event':
                box = data.box
                state = data.state
                time_str = data.time

                if state == 'open':
                    new_line = f"[{datetime.now().strftime('%H:%M:%S')}] Box {box} OPENED at {time_str}\n"

                    med_name = self.get_medication_name_for_box(box)

                    # Trigger camera preview capture (captures next frame from live preview)
                    main_window = self.window()
                    if hasattr(main_window, 'camera_preview') and main_window.camera_preview:
                        print(f"[AUTO] Triggering camera preview capture for Box {box} ({med_name})")
                        main_window.camera_preview.trigger_capture(box, med_name)

                        # If not streaming, request a single frame
                        if not main_window.camera_preview.is_streaming and self.cam_comm.is_connected:
                            self.cam_comm.get_frame()
                    else:
                        print(f"[AUTO] Camera preview not available")
                else:
                    new_line = f"[{datetime.now().strftime('%H:%M:%S')}] Box {box} closed at {time_str}\n"

            else:
                new_line = f"[{datetime.now().strftime('%H:%M:%S')}] {status_type}: {data}\n"

            # Limit display lines
            lines = current_text.split('\n')
            if len(lines) > 20:
                lines = lines[-15:]  # Keep latest 15 lines
                current_text = '\n'.join(lines)

            self.status_text.setPlainText(current_text + new_line)

            # Scroll to bottom
            cursor = self.status_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.status_text.setTextCursor(cursor)

            # 如果是用藥事件，更新統計顯示
            if status_type == 'medication_taken':
                self.update_medication_summary()

        except Exception as e:
            print(f"Error handling status: {e}")
    
    def update_medication_summary(self):
        """Update medication summary display"""
        try:
            from simple_models import MedicationRecorder
            recorder = MedicationRecorder(self.db_manager)
            summary = recorder.get_today_medication_summary()
            
            # 更新狀態顯示 (如果有summary widget的話)
            summary_text = f"Today's Summary: {summary['taken']}/{summary['total_scheduled']} taken, {summary['missed']} missed"
            print(summary_text)  # 或者更新到某個label
            
        except Exception as e:
            print(f"Error updating summary: {e}")

class SimpleMainWindow(QMainWindow):
    """Main Window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.pillbox_comm = SimplePillboxCommunicator()
        from simple_models import SimpleDataManager
        from enhanced_notifications import EnhancedMedicationRecorder
        self.db_manager = SimpleDataManager()
        self.medication_recorder = EnhancedMedicationRecorder(self.db_manager, enable_notifications=True)
        
        self.setWindowTitle('Smart Pillbox Management System')
        self.setGeometry(100, 100, 1200, 800)
        
        # Set font
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        
        # Setup auto-check for missed medications
        self.missed_check_timer = QTimer()
        self.missed_check_timer.timeout.connect(self.check_missed_medications)
        self.missed_check_timer.start(60000)  # Check every minute
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Smart Pillbox Management System")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        info_label = QLabel("Patient: Default Patient | Medications: M0-M9 | Functions: Schedule Management + Pillbox Communication")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(info_label)
        
        # Tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Medication schedule tab
        self.doctor_interface = SimpleDoctorInterface(pillbox_comm=self.pillbox_comm)
        tab_widget.addTab(self.doctor_interface.centralWidget(), "Medication Schedule Management")
        
        # NEW: Medication Calendar tab
        try:
            from medication_calendar import MedicationCalendarWidget
            self.calendar_widget = MedicationCalendarWidget()
            tab_widget.addTab(self.calendar_widget, "📅 Medication Records Calendar")
        except ImportError:
            print("⚠️ Medication calendar not available")
        
        # System status tab
        self.status_widget = SystemStatusWidget(self.pillbox_comm)
        tab_widget.addTab(self.status_widget, "Pillbox Connection & Testing")

        # Camera Preview tab
        self.camera_preview = CameraPreviewWidget(
            self.status_widget.cam_comm,
            self.status_widget.photo_handler
        )
        tab_widget.addTab(self.camera_preview, "Camera Preview")
    
    def check_missed_medications(self):
        """Check for missed medications periodically"""
        try:
            missed_count = self.medication_recorder.check_missed_medications()
            if missed_count > 0:
                print(f"Found {missed_count} missed medications")
            
            # Trigger notification check for EnhancedMedicationRecorder
            if hasattr(self.medication_recorder, 'check_and_send_notifications'):
                self.medication_recorder.check_and_send_notifications()
                
        except Exception as e:
            print(f"Error checking missed medications: {e}")
    
    def closeEvent(self, event):
        """Cleanup when closing program"""
        # Stop timers
        self.missed_check_timer.stop()

        # Disconnect pillbox connection
        self.pillbox_comm.disconnect()

        # Disconnect ESP32-CAM connection
        if hasattr(self, 'status_widget') and hasattr(self.status_widget, 'cam_comm'):
            self.status_widget.cam_comm.disconnect()

        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application information
    app.setApplicationName("Smart Pillbox Management System")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("EE542")
    
    window = SimpleMainWindow()
    window.show()
    
    sys.exit(app.exec())