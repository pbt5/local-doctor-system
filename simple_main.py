import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                            QLineEdit, QTextEdit, QMessageBox, QGroupBox,
                            QFormLayout, QSpinBox, QComboBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

# Import simplified modules
from simple_models import SimpleDataManager, MEDICATIONS, get_medication_name
from simple_host_sender import SimplePillboxCommunicator, ESP32Sender, SimpleAlert
from simple_doctor_interface import SimpleDoctorInterface

class SystemStatusWidget(QWidget):
    """System Status Monitoring Panel"""
    
    def __init__(self, pillbox_comm: SimplePillboxCommunicator):
        super().__init__()
        self.pillbox_comm = pillbox_comm
        self.db_manager = SimpleDataManager()
        self.setup_ui()
        
        # Set timer to update status
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # Update every 5 seconds
        
        # Set pillbox status callback
        self.pillbox_comm.add_status_callback(self.handle_pillbox_status)
    
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
        
        self.connect_btn = QPushButton("Connect Pillbox")
        self.connect_btn.clicked.connect(self.connect_pillbox)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_pillbox)
        
        pillbox_layout.addRow("Status:", self.pillbox_status_label)
        pillbox_layout.addRow("IP Address:", self.pillbox_ip_edit)
        pillbox_layout.addRow("Port:", self.pillbox_port_spin)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        pillbox_layout.addRow(button_layout)
        
        layout.addWidget(pillbox_group)
        
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
    
    def handle_pillbox_status(self, status_type: str, data):
        """Handle pillbox status callback"""
        try:
            current_text = self.status_text.toPlainText()
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
            
        except Exception as e:
            print(f"Error handling status: {e}")

class SimpleMainWindow(QMainWindow):
    """Simplified Main Window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.pillbox_comm = SimplePillboxCommunicator()
        
        self.setWindowTitle('Smart Pillbox Management System (Simplified Version)')
        self.setGeometry(100, 100, 1200, 800)
        
        # Set font
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Smart Pillbox Management System (Simplified Version)")
        title_font = QFont()
        title_font.setPointSize(18)
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
        self.doctor_interface = SimpleDoctorInterface()
        tab_widget.addTab(self.doctor_interface.centralWidget(), "Medication Schedule Management")
        
        # System status tab
        self.status_widget = SystemStatusWidget(self.pillbox_comm)
        tab_widget.addTab(self.status_widget, "Pillbox Connection & Testing")
        
        # Simple communication test tab (preserve original functionality)
        self.simple_comm_widget = self.create_simple_comm_widget()
        tab_widget.addTab(self.simple_comm_widget, "Simple Communication Test")
    
    def create_simple_comm_widget(self):
        """Create simple communication test interface"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Use ESP32Sender to maintain backward compatibility
        self.esp32_sender = ESP32Sender()
        
        # Status label
        self.esp32_status_label = QLabel('Not connected')
        layout.addWidget(self.esp32_status_label)
        
        # Connect button
        connect_btn = QPushButton('Connect ESP32')
        connect_btn.clicked.connect(self.connect_esp32)
        layout.addWidget(connect_btn)
        
        # Input box
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText('Enter any characters...')
        self.input_box.returnPressed.connect(self.send_simple_message)
        layout.addWidget(self.input_box)
        
        # Send button
        send_btn = QPushButton('Send')
        send_btn.clicked.connect(self.send_simple_message)
        layout.addWidget(send_btn)
        
        layout.addStretch()
        
        return widget
    
    def connect_esp32(self):
        """Connect ESP32 (simple mode)"""
        if self.esp32_sender.connect():
            self.esp32_status_label.setText('✓ Connected')
            self.esp32_status_label.setStyleSheet('color: green')
        else:
            self.esp32_status_label.setText('✗ Connection failed')
            self.esp32_status_label.setStyleSheet('color: red')
    
    def send_simple_message(self):
        """Send simple message"""
        message = self.input_box.text()
        if message and self.esp32_sender.send(message):
            self.input_box.clear()
            print(f"Sent: {message}")
    
    def closeEvent(self, event):
        """Cleanup when closing program"""
        # Disconnect pillbox connection
        self.pillbox_comm.disconnect()
        self.esp32_sender.close()
        
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application information
    app.setApplicationName("Smart Pillbox Management System")
    app.setApplicationVersion("1.0 (Simplified Version)")
    app.setOrganizationName("EE542")
    
    window = SimpleMainWindow()
    window.show()
    
    sys.exit(app.exec())