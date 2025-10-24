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

        # Setup message queue polling timer (thread-safe)
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.process_message_queue)
        self.message_timer.start(100)  # Check message queue every 100ms
    
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
        font.setPointSize(10)
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