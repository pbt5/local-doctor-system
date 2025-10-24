"""
Simplified Doctor Interface
Only manages medication schedules, medications are fixed as M0-M9
"""
import sys
import uuid
from datetime import datetime, date
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTableWidget, QTableWidgetItem,
                            QPushButton, QLabel, QComboBox, QSpinBox,
                            QTextEdit, QDateEdit, QTimeEdit, QMessageBox, 
                            QGroupBox, QFormLayout, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont

from simple_models import (SimpleDataManager, SimpleMedicationSchedule, 
                          MEDICATIONS, get_medication_name)

class AddScheduleDialog(QDialog):
    """Add Medication Schedule Dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Medication Schedule")
        self.setModal(True)
        self.resize(500, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form = QFormLayout()
        
        # Medication selection
        self.medication_combo = QComboBox()
        for med_id, med_name in MEDICATIONS.items():
            self.medication_combo.addItem(f"{med_id} - {med_name}", med_id)
        form.addRow("Medication *:", self.medication_combo)
        
        # Times per day
        self.times_per_day_spin = QSpinBox()
        self.times_per_day_spin.setRange(1, 6)
        self.times_per_day_spin.setValue(3)
        self.times_per_day_spin.valueChanged.connect(self.update_time_inputs)
        form.addRow("Times per day:", self.times_per_day_spin)
        
        # Dosage per time
        self.dosage_count_spin = QSpinBox()
        self.dosage_count_spin.setRange(1, 10)
        self.dosage_count_spin.setValue(1)
        form.addRow("Pills per dose:", self.dosage_count_spin)
        
        layout.addLayout(form)
        
        # Medication time settings
        time_group = QGroupBox("Medication Times")
        self.time_layout = QVBoxLayout(time_group)
        self.time_edits = []
        self.update_time_inputs()
        layout.addWidget(time_group)
        
        # Date range
        date_group = QGroupBox("Treatment Period")
        date_layout = QFormLayout(date_group)
        
        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        date_layout.addRow("Start date:", self.start_date_edit)
        
        self.end_date_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.end_date_edit.setCalendarPopup(True)
        date_layout.addRow("End date:", self.end_date_edit)
        
        layout.addWidget(date_group)
        
        # Instructions
        notes_group = QGroupBox("Instructions (will be sent to pillbox display)")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.setPlaceholderText("e.g.: Take after meals, drink plenty of water, avoid on empty stomach...")
        notes_layout.addWidget(self.notes_edit)
        layout.addWidget(notes_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                 QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def update_time_inputs(self):
        """Update Time Input Fields"""
        # Clear existing time input fields
        for edit in self.time_edits:
            edit.setParent(None)
        self.time_edits.clear()
        
        # Clear widgets in layout
        while self.time_layout.count():
            child = self.time_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
        
        # Create time input fields based on times per day
        times_per_day = self.times_per_day_spin.value()
        default_times = ["08:00", "14:00", "20:00", "06:00", "12:00", "18:00"]
        
        for i in range(times_per_day):
            time_edit = QTimeEdit(QTime.fromString(default_times[i], "hh:mm"))
            time_edit.setDisplayFormat("hh:mm")
            self.time_edits.append(time_edit)
            
            time_layout = QHBoxLayout()
            time_layout.addWidget(QLabel(f"Time {i+1}:"))
            time_layout.addWidget(time_edit)
            time_layout.addStretch()
            
            self.time_layout.addLayout(time_layout)
    
    def _clear_layout(self, layout):
        """Recursively Clear Layout"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())
    
    def get_schedule_data(self):
        """Get Schedule Data"""
        schedule_times = []
        for time_edit in self.time_edits:
            schedule_times.append(time_edit.time().toString("hh:mm"))
        
        return {
            'id': str(uuid.uuid4()),
            'medication_id': self.medication_combo.currentData(),
            'times_per_day': self.times_per_day_spin.value(),
            'dosage_count': self.dosage_count_spin.value(),
            'schedule_times': schedule_times,
            'start_date': self.start_date_edit.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date_edit.date().toString("yyyy-MM-dd"),
            'notes': self.notes_edit.toPlainText().strip(),
            'is_active': True
        }

class SimpleDoctorInterface(QMainWindow):
    """Simplified Doctor Interface"""

    def __init__(self, pillbox_comm=None):
        super().__init__()
        self.db_manager = SimpleDataManager()
        self.pillbox_comm = pillbox_comm
        self.setWindowTitle("Smart Pillbox Management System - Medication Schedule")
        self.setGeometry(100, 100, 1000, 600)
        
        # Set font
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        self.setup_ui()
        self.load_schedules()
    
    def setup_ui(self):
        """Setup User Interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Medication Schedule Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        info_label = QLabel("Patient: Default Patient | Available Medications: M0-M9")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(info_label)
        
        # Button area
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Schedule")
        add_btn.clicked.connect(self.add_schedule)
        button_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Schedule")
        edit_btn.clicked.connect(self.edit_schedule)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Schedule")
        delete_btn.clicked.connect(self.delete_schedule)
        button_layout.addWidget(delete_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_schedules)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Schedule list
        self.schedules_table = QTableWidget()
        self.schedules_table.setColumnCount(7)
        self.schedules_table.setHorizontalHeaderLabels([
            "Medication", "Times/Day", "Pills/Dose", "Medication Times", "Treatment Period", "Status", "Instructions"
        ])
        
        # Set column widths
        header = self.schedules_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.schedules_table.setColumnWidth(0, 100)
        self.schedules_table.setColumnWidth(1, 80)
        self.schedules_table.setColumnWidth(2, 80)
        self.schedules_table.setColumnWidth(3, 150)
        self.schedules_table.setColumnWidth(4, 200)
        self.schedules_table.setColumnWidth(5, 60)
        
        # Set selection mode
        self.schedules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.schedules_table)
        
        # Test area
        test_group = QGroupBox("Test Functions")
        test_layout = QHBoxLayout(test_group)
        
        send_config_btn = QPushButton("Send Config to Pillbox")
        send_config_btn.clicked.connect(self.send_config_to_pillbox)
        test_layout.addWidget(send_config_btn)
        
        send_reminder_btn = QPushButton("Send Test Reminder")
        send_reminder_btn.clicked.connect(self.send_test_reminder)
        test_layout.addWidget(send_reminder_btn)
        
        layout.addWidget(test_group)
    
    def load_schedules(self):
        """Load Schedule Data"""
        schedules = self.db_manager.get_all_schedules()
        self.schedules_table.setRowCount(len(schedules))
        
        for row, schedule in enumerate(schedules):
            # Medication
            med_name = get_medication_name(schedule.medication_id)
            self.schedules_table.setItem(row, 0, QTableWidgetItem(f"{schedule.medication_id} - {med_name}"))
            
            # Times per day
            self.schedules_table.setItem(row, 1, QTableWidgetItem(str(schedule.times_per_day)))
            
            # Pills per dose
            self.schedules_table.setItem(row, 2, QTableWidgetItem(str(schedule.dosage_count)))
            
            # Medication times
            times_str = ", ".join(schedule.schedule_times)
            self.schedules_table.setItem(row, 3, QTableWidgetItem(times_str))
            
            # Treatment period
            period_str = f"{schedule.start_date} to {schedule.end_date}"
            self.schedules_table.setItem(row, 4, QTableWidgetItem(period_str))
            
            # Status
            status_str = "Active" if schedule.is_active else "Inactive"
            self.schedules_table.setItem(row, 5, QTableWidgetItem(status_str))
            
            # Instructions
            notes_preview = schedule.notes[:50] + "..." if len(schedule.notes) > 50 else schedule.notes
            self.schedules_table.setItem(row, 6, QTableWidgetItem(notes_preview))
            
            # Store schedule ID in first column data
            self.schedules_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, schedule.id)
    
    def add_schedule(self):
        """Add Schedule"""
        dialog = AddScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_schedule_data()
                schedule = SimpleMedicationSchedule(**data)
                self.db_manager.save_schedule(schedule)
                self.load_schedules()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add schedule: {str(e)}")
    
    def edit_schedule(self):
        """Edit Schedule"""
        current_row = self.schedules_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a schedule to edit first")
            return
        
        QMessageBox.information(self, "Feature Notice", "Edit function not yet implemented, please delete and recreate")
    
    def delete_schedule(self):
        """Delete Schedule"""
        current_row = self.schedules_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a schedule to delete first")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                   "Are you sure you want to delete this medication schedule?",
                                   QMessageBox.StandardButton.Yes | 
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Get schedule ID
                schedule_id = self.schedules_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
                self.db_manager.delete_schedule(schedule_id)
                self.load_schedules()
                QMessageBox.information(self, "Success", "Schedule deleted")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Deletion failed: {str(e)}")
    
    def send_config_to_pillbox(self):
        """Send Configuration to Pillbox"""
        if not self.pillbox_comm:
            QMessageBox.warning(self, "Warning", "Pillbox communicator not available")
            return

        if not self.pillbox_comm.is_connected:
            QMessageBox.warning(self, "Warning", "Not connected to pillbox. Please connect first.")
            return

        # Get all active schedules
        schedules = self.db_manager.get_all_schedules()
        active_schedules = [s for s in schedules if s.is_active]

        if not active_schedules:
            QMessageBox.warning(self, "Warning", "No active medication schedules to send")
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Send",
            f"Send {len(active_schedules)} active medication schedule(s) to pillbox?\n\n"
            f"ESP32 will automatically assign medications to storage boxes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Convert to dict format
        schedules_data = []
        for schedule in active_schedules:
            schedules_data.append({
                'medication_id': schedule.medication_id,
                'times_per_day': schedule.times_per_day,
                'dosage_count': schedule.dosage_count,
                'schedule_times': schedule.schedule_times,
                'start_date': schedule.start_date,
                'end_date': schedule.end_date,
                'notes': schedule.notes,
                'is_active': schedule.is_active
            })

        # Send to ESP32
        try:
            response = self.pillbox_comm.send_schedule_config(schedules_data)

            if response.get('status') == 'OK':
                # Success - show assignment results
                assignments = response.get('assignments', [])

                message = f"Configuration sent successfully!\n\n"
                message += f"ESP32 Assignment Results:\n"
                for assignment in assignments:
                    med_id = assignment.get('medication_id', 'Unknown')
                    box = assignment.get('box', -1)
                    message += f"  {med_id} -> Box {box}\n"

                QMessageBox.information(self, "Success", message)

            elif response.get('status') == 'TIMEOUT':
                QMessageBox.warning(
                    self,
                    "Timeout",
                    "No response from ESP32. Configuration may have been received.\n\n"
                    "Please check ESP32 serial output."
                )
            else:
                # Error
                error_msg = response.get('message', 'Unknown error')
                QMessageBox.critical(
                    self,
                    "Send Failed",
                    f"Failed to send configuration:\n{error_msg}"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Unexpected error:\n{str(e)}"
            )
    
    def send_test_reminder(self):
        """Send Test Reminder"""
        current_row = self.schedules_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a schedule first to send test reminder")
            return
        
        QMessageBox.information(self, "Notice", "Test reminder function will be integrated in main program")
    
    def view_medication_records(self):
        """View Medication Records"""
        from simple_models import MedicationRecorder
        
        try:
            recorder = MedicationRecorder(self.db_manager)
            summary = recorder.get_today_medication_summary()
            
            # 建立記錄顯示對話框
            dialog = QDialog(self)
            dialog.setWindowTitle("Medication Records")
            dialog.setModal(True)
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            # 今日統計
            summary_label = QLabel(f"""
            📊 Today's Summary ({summary['date']})
            Total Scheduled: {summary['total_scheduled']}
            ✅ Taken: {summary['taken']}
            ❌ Missed: {summary['missed']}
            ⏳ Pending: {summary['pending']}
            """)
            layout.addWidget(summary_label)
            
            # 記錄列表
            records_text = QTextEdit()
            records_text.setReadOnly(True)
            
            records_content = "📋 Recent Records:\n\n"
            for record in summary['records']:
                from simple_models import get_medication_name, MedicationStatus
                
                med_name = get_medication_name(record.medication_id)
                status_icon = "✅" if record.status == MedicationStatus.TAKEN else "❌"
                
                records_content += f"{status_icon} {med_name}\n"
                records_content += f"   Scheduled: {record.scheduled_time}\n"
                records_content += f"   Actual: {record.actual_time or 'Not taken'}\n"
                records_content += f"   Status: {record.status.value}\n"
                if record.notes:
                    records_content += f"   Notes: {record.notes}\n"
                records_content += "\n"
            
            records_text.setPlainText(records_content)
            layout.addWidget(records_text)
            
            # 依從率
            adherence = recorder.get_medication_adherence_rate(days=7)
            adherence_label = QLabel(f"📈 7-day Adherence Rate: {adherence:.1f}%")
            layout.addWidget(adherence_label)
            
            # 關閉按鈕
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load medication records: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleDoctorInterface()
    window.show()
    sys.exit(app.exec())