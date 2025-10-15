"""
Medication Calendar Widget
Monthly calendar view for medication records with schedule tracking
"""
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QCalendarWidget, QTextEdit, QComboBox, QPushButton,
                           QGroupBox, QFormLayout, QScrollArea, QFrame,
                           QApplication, QMainWindow)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QTextCharFormat

from simple_models import (SimpleDataManager, MedicationRecorder, 
                          MedicationStatus, get_medication_name, 
                          SimpleMedicationRecord, SimpleMedicationSchedule)

class MedicationCalendarWidget(QWidget):
    """Medication Calendar Widget - Monthly view with medication records"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = SimpleDataManager()
        self.recorder = MedicationRecorder(self.db_manager)
        self.current_date = datetime.now().date()
        self.selected_date = None
        self.medication_records = {}  # {date: {medication_id: [records]}}
        self.schedules = {}  # {medication_id: schedule}
        
        self.setup_ui()
        self.load_current_month_data()
        
    def setup_ui(self):
        """Setup calendar UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("📅 Medication Records Calendar")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Month selector
        self.month_combo = QComboBox()
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        self.month_combo.addItems(months)
        self.month_combo.setCurrentIndex(self.current_date.month - 1)
        self.month_combo.currentIndexChanged.connect(self.month_changed)
        controls_layout.addWidget(QLabel("Month:"))
        controls_layout.addWidget(self.month_combo)
        
        # Year selector
        self.year_combo = QComboBox()
        current_year = self.current_date.year
        for year in range(current_year - 2, current_year + 3):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentIndexChanged.connect(self.year_changed)
        controls_layout.addWidget(QLabel("Year:"))
        controls_layout.addWidget(self.year_combo)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(refresh_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Main content
        content_layout = QHBoxLayout()
        
        # Calendar
        calendar_group = QGroupBox("Calendar View")
        calendar_layout = QVBoxLayout(calendar_group)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.date_selected)
        calendar_layout.addWidget(self.calendar)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("🟢 All taken"))
        legend_layout.addWidget(QLabel("🟡 Partial"))
        legend_layout.addWidget(QLabel("🔴 Missed"))
        legend_layout.addWidget(QLabel("⚪ No schedule"))
        calendar_layout.addLayout(legend_layout)
        
        content_layout.addWidget(calendar_group, 2)
        
        # Daily details
        details_group = QGroupBox("Daily Medication Details")
        details_layout = QVBoxLayout(details_group)
        
        self.date_label = QLabel("Select a date to view details")
        self.date_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        details_layout.addWidget(self.date_label)
        
        # Scroll area for medication details
        scroll = QScrollArea()
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        scroll.setWidget(self.details_widget)
        scroll.setWidgetResizable(True)
        details_layout.addWidget(scroll)
        
        content_layout.addWidget(details_group, 1)
        
        layout.addLayout(content_layout)
        
        # Statistics
        stats_group = QGroupBox("Monthly Statistics")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_group)
    
    def month_changed(self):
        """Month selection changed"""
        self.update_calendar_date()
    
    def year_changed(self):
        """Year selection changed"""
        self.update_calendar_date()
    
    def update_calendar_date(self):
        """Update calendar to selected month/year"""
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())
        
        # Set calendar to first day of selected month
        new_date = QDate(year, month, 1)
        self.calendar.setSelectedDate(new_date)
        
        # Update current tracking date
        self.current_date = date(year, month, 1)
        
        # Reload data for new month
        self.load_current_month_data()
    
    def load_current_month_data(self):
        """Load medication data for current month"""
        # Get month range
        year = self.current_date.year
        month = self.current_date.month
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Load schedules - get ALL schedules including active and inactive
        all_schedules = self.db_manager.get_all_schedules()
        self.schedules = {s.medication_id: s for s in all_schedules}
        
        print(f"📊 Calendar: Loaded {len(all_schedules)} total schedules")
        active_count = len([s for s in all_schedules if s.is_active])
        print(f"📊 Calendar: {active_count} active schedules")
        
        # Debug: List all schedules
        for schedule in all_schedules:
            med_name = get_medication_name(schedule.medication_id)
            status = "Active" if schedule.is_active else "Inactive"
            print(f"   • {schedule.medication_id} - {med_name} ({status}) {schedule.start_date} to {schedule.end_date}")
        
        # Load records for the month - increase limit to get more records
        all_records = self.db_manager.get_recent_records(limit=2000)
        
        print(f"📊 Calendar: Loaded {len(all_records)} total records")
        
        # Organize records by date
        self.medication_records = {}
        month_records_count = 0
        
        for record in all_records:
            try:
                # Handle different datetime formats
                if record.created_at:
                    if 'T' in record.created_at:
                        record_date = datetime.fromisoformat(record.created_at.replace('Z', '+00:00')).date()
                    else:
                        record_date = datetime.strptime(record.created_at[:10], "%Y-%m-%d").date()
                else:
                    continue
                
                if start_date <= record_date <= end_date:
                    month_records_count += 1
                    
                    if record_date not in self.medication_records:
                        self.medication_records[record_date] = {}
                    
                    if record.medication_id not in self.medication_records[record_date]:
                        self.medication_records[record_date][record.medication_id] = []
                    
                    self.medication_records[record_date][record.medication_id].append(record)
            except Exception as e:
                print(f"⚠️ Error parsing record date: {record.created_at} - {e}")
                continue
        
        print(f"📊 Calendar: Found {month_records_count} records for {year}-{month:02d}")
        
        # Debug: Show daily record counts
        for record_date, day_records in self.medication_records.items():
            total_for_day = sum(len(records) for records in day_records.values())
            medications = list(day_records.keys())
            print(f"   • {record_date}: {total_for_day} records for medications {medications}")
        
        # Update calendar colors
        self.update_calendar_colors()
        self.update_monthly_statistics()
    
    def update_calendar_colors(self):
        """Update calendar cell colors based on medication status"""
        # Clear existing formats
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        
        # Get current month range
        year = self.current_date.year
        month = self.current_date.month
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Check each day in the month
        current_date_check = start_date
        while current_date_check <= end_date:
            qdate = QDate(current_date_check.year, current_date_check.month, current_date_check.day)
            
            # Get daily status
            daily_status = self.get_daily_medication_status(current_date_check)
            
            # Set color based on status
            format = QTextCharFormat()
            if daily_status == "all_taken":
                format.setBackground(QColor(144, 238, 144))  # Light green
            elif daily_status == "partial":
                format.setBackground(QColor(255, 255, 144))  # Light yellow
            elif daily_status == "missed":
                format.setBackground(QColor(255, 182, 193))  # Light red
            # No color for no_schedule
            
            if daily_status != "no_schedule":
                self.calendar.setDateTextFormat(qdate, format)
            
            current_date_check += timedelta(days=1)
    
    def get_daily_medication_status(self, check_date: date) -> str:
        """Get overall medication status for a specific date"""
        # Check if there are active schedules for this date
        active_schedules = []
        for schedule in self.schedules.values():
            start = datetime.strptime(schedule.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(schedule.end_date, "%Y-%m-%d").date()
            
            if start <= check_date <= end and schedule.is_active:
                active_schedules.append(schedule)
        
        if not active_schedules:
            return "no_schedule"
        
        # Count expected vs actual medications
        total_expected = sum(len(s.schedule_times) for s in active_schedules)
        taken_count = 0
        missed_count = 0
        
        if check_date in self.medication_records:
            day_records = self.medication_records[check_date]
            
            for medication_id, records in day_records.items():
                for record in records:
                    if record.status == MedicationStatus.TAKEN:
                        taken_count += 1
                    elif record.status == MedicationStatus.MISSED:
                        missed_count += 1
        
        # Determine status
        if taken_count == total_expected:
            return "all_taken"
        elif taken_count > 0:
            return "partial"
        elif missed_count > 0 or check_date < datetime.now().date():
            return "missed"
        else:
            return "no_schedule"
    
    def date_selected(self, qdate: QDate):
        """Handle date selection"""
        # Convert QDate to Python date - compatible with all PyQt6 versions
        selected_date = date(qdate.year(), qdate.month(), qdate.day())
        self.selected_date = selected_date
        self.update_daily_details(selected_date)
    
    def update_daily_details(self, selected_date: date):
        """Update daily medication details panel"""
        # Update date label
        self.date_label.setText(f"📅 {selected_date.strftime('%B %d, %Y')}")
        
        # Clear existing details
        for i in reversed(range(self.details_layout.count())):
            child = self.details_layout.takeAt(i).widget()
            if child:
                child.setParent(None)
        
        # Get active schedules for this date
        active_schedules = []
        for schedule in self.schedules.values():
            start = datetime.strptime(schedule.start_date, "%Y-%m-%d").date()
            end = datetime.strptime(schedule.end_date, "%Y-%m-%d").date()
            
            if start <= selected_date <= end and schedule.is_active:
                active_schedules.append(schedule)
        
        if not active_schedules:
            no_schedule_label = QLabel("ℹ️ No medication schedules for this date")
            no_schedule_label.setStyleSheet("color: gray; padding: 10px;")
            self.details_layout.addWidget(no_schedule_label)
            return
        
        # Get records for this date
        day_records = self.medication_records.get(selected_date, {})
        
        # Debug: Show how many schedules we found
        if active_schedules:
            debug_label = QLabel(f"🔍 Found {len(active_schedules)} active medication(s) for this date")
            debug_label.setStyleSheet("color: blue; font-size: 10px; padding: 5px;")
            self.details_layout.addWidget(debug_label)
        
        # Display each medication
        for schedule in active_schedules:
            med_frame = QFrame()
            med_frame.setFrameStyle(QFrame.Shape.Box)
            med_frame.setStyleSheet("QFrame { border: 1px solid gray; margin: 5px; padding: 5px; }")
            
            med_layout = QVBoxLayout(med_frame)
            
            # Medication header
            med_name = get_medication_name(schedule.medication_id)
            header_label = QLabel(f"💊 {schedule.medication_id} - {med_name}")
            header_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            med_layout.addWidget(header_label)
            
            # Dosage info
            dosage_label = QLabel(f"Dosage: {schedule.dosage_count} pills, {len(schedule.schedule_times)} times daily")
            dosage_label.setStyleSheet("color: gray;")
            med_layout.addWidget(dosage_label)
            
            # Show schedule period for debugging
            period_label = QLabel(f"Period: {schedule.start_date} to {schedule.end_date}")
            period_label.setStyleSheet("color: gray; font-size: 9px;")
            med_layout.addWidget(period_label)
            
            # Schedule times and actual records
            records_for_med = day_records.get(schedule.medication_id, [])
            
            # Debug: Show records found
            if records_for_med:
                debug_records = QLabel(f"📋 Found {len(records_for_med)} record(s) for {schedule.medication_id}")
                debug_records.setStyleSheet("color: green; font-size: 9px;")
                med_layout.addWidget(debug_records)
            
            for scheduled_time in schedule.schedule_times:
                # Find matching record
                matching_record = None
                for record in records_for_med:
                    if record.scheduled_time == scheduled_time:
                        matching_record = record
                        break
                
                if matching_record:
                    if matching_record.status == MedicationStatus.TAKEN:
                        status_text = f"✅ {scheduled_time} → Taken at {matching_record.actual_time or 'Unknown'}"
                        status_color = "green"
                    elif matching_record.status == MedicationStatus.MISSED:
                        status_text = f"❌ {scheduled_time} → Missed"
                        status_color = "red"
                    else:
                        status_text = f"⏳ {scheduled_time} → {matching_record.status.value}"
                        status_color = "orange"
                else:
                    # Check if time has passed
                    if selected_date < datetime.now().date():
                        status_text = f"❌ {scheduled_time} → No record (Likely missed)"
                        status_color = "red"
                    elif selected_date == datetime.now().date():
                        current_time = datetime.now().time()
                        try:
                            scheduled_time_obj = datetime.strptime(scheduled_time, "%H:%M").time()
                            if current_time > scheduled_time_obj:
                                status_text = f"⏳ {scheduled_time} → Pending check"
                                status_color = "orange"
                            else:
                                status_text = f"⏰ {scheduled_time} → Upcoming"
                                status_color = "blue"
                        except ValueError:
                            status_text = f"⏰ {scheduled_time} → Scheduled"
                            status_color = "blue"
                    else:
                        status_text = f"⏰ {scheduled_time} → Scheduled"
                        status_color = "blue"
                
                status_label = QLabel(status_text)
                status_label.setStyleSheet(f"color: {status_color}; padding: 2px;")
                med_layout.addWidget(status_label)
            
            # Instructions
            if schedule.notes:
                notes_label = QLabel(f"📝 Instructions: {schedule.notes}")
                notes_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
                notes_label.setWordWrap(True)
                med_layout.addWidget(notes_label)
            
            self.details_layout.addWidget(med_frame)
        
        # Add stretch at the end
        self.details_layout.addStretch()
    
    def update_monthly_statistics(self):
        """Update monthly statistics"""
        # Get current month range
        year = self.current_date.year
        month = self.current_date.month
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Calculate statistics
        total_scheduled = 0
        total_taken = 0
        total_missed = 0
        days_with_all_taken = 0
        days_with_schedules = 0
        
        current_date_check = start_date
        while current_date_check <= end_date:
            # Skip future dates
            if current_date_check > datetime.now().date():
                current_date_check += timedelta(days=1)
                continue
            
            # Get active schedules for this date
            active_schedules = []
            for schedule in self.schedules.values():
                sched_start = datetime.strptime(schedule.start_date, "%Y-%m-%d").date()
                sched_end = datetime.strptime(schedule.end_date, "%Y-%m-%d").date()
                
                if sched_start <= current_date_check <= sched_end and schedule.is_active:
                    active_schedules.append(schedule)
            
            if active_schedules:
                days_with_schedules += 1
                daily_scheduled = sum(len(s.schedule_times) for s in active_schedules)
                total_scheduled += daily_scheduled
                
                daily_taken = 0
                daily_missed = 0
                
                if current_date_check in self.medication_records:
                    day_records = self.medication_records[current_date_check]
                    
                    for records_list in day_records.values():
                        for record in records_list:
                            if record.status == MedicationStatus.TAKEN:
                                daily_taken += 1
                            elif record.status == MedicationStatus.MISSED:
                                daily_missed += 1
                
                total_taken += daily_taken
                total_missed += daily_missed
                
                if daily_taken == daily_scheduled:
                    days_with_all_taken += 1
            
            current_date_check += timedelta(days=1)
        
        # Calculate percentages
        adherence_rate = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0
        perfect_days_rate = (days_with_all_taken / days_with_schedules * 100) if days_with_schedules > 0 else 0
        
        # Update statistics display
        stats_text = f"""
📊 {self.current_date.strftime('%B %Y')} Statistics:
• Total Scheduled: {total_scheduled}
• Total Taken: {total_taken} ({adherence_rate:.1f}%)
• Total Missed: {total_missed}
• Perfect Days: {days_with_all_taken}/{days_with_schedules} ({perfect_days_rate:.1f}%)
        """.strip()
        
        self.stats_label.setText(stats_text)
    
    def refresh_data(self):
        """Refresh all data"""
        self.load_current_month_data()
        if self.selected_date:
            self.update_daily_details(self.selected_date)

# Test application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Medication Calendar")
    window.setGeometry(100, 100, 1200, 800)
    
    calendar_widget = MedicationCalendarWidget()
    window.setCentralWidget(calendar_widget)
    
    window.show()
    sys.exit(app.exec())