#!/usr/bin/env python3
"""
Test Medication Calendar with Sample Data
測試用藥記錄月曆功能
"""
import sys
import os
from datetime import datetime, date, timedelta
import uuid

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_sample_data():
    """Create sample medication schedules and records for calendar testing"""
    
    from simple_models import (SimpleDataManager, SimpleMedicationSchedule, 
                              SimpleMedicationRecord, MedicationStatus)
    
    print("📊 Creating sample medication data for calendar testing...")
    
    db_manager = SimpleDataManager()
    
    # Create sample schedules
    schedules = [
        SimpleMedicationSchedule(
            id=str(uuid.uuid4()),
            medication_id="M0",
            times_per_day=3,
            dosage_count=1,
            schedule_times=["08:00", "14:00", "20:00"],
            start_date="2024-10-01",
            end_date="2024-12-31",
            notes="Morning, afternoon, and evening doses",
            is_active=True
        ),
        SimpleMedicationSchedule(
            id=str(uuid.uuid4()),
            medication_id="M1",
            times_per_day=2,
            dosage_count=2,
            schedule_times=["09:00", "21:00"],
            start_date="2024-10-01",
            end_date="2024-12-31", 
            notes="Take with food, morning and night",
            is_active=True
        ),
        SimpleMedicationSchedule(
            id=str(uuid.uuid4()),
            medication_id="M2",
            times_per_day=1,
            dosage_count=1,
            schedule_times=["12:00"],
            start_date="2024-10-05",
            end_date="2024-11-30",
            notes="Lunch medication, take after meal",
            is_active=True
        )
    ]
    
    # Save schedules
    for schedule in schedules:
        db_manager.save_schedule(schedule)
        from simple_models import get_medication_name
        print(f"✅ Created schedule: {get_medication_name(schedule.medication_id)}")
    
    # Create sample records for the past few days
    today = datetime.now().date()
    
    sample_records = []
    
    # Simulate medication records for past 10 days
    for days_ago in range(10, 0, -1):
        record_date = today - timedelta(days=days_ago)
        record_datetime = datetime.combine(record_date, datetime.min.time())
        
        # M0 records (3 times daily)
        if days_ago <= 8:  # Started 8 days ago
            # Morning dose - usually taken
            if days_ago != 3:  # Missed 3 days ago
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[0].id,
                    medication_id="M0",
                    scheduled_time="08:00",
                    actual_time="08:05" if days_ago % 2 == 0 else "08:15",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Morning dose taken",
                    created_at=(record_datetime + timedelta(hours=8, minutes=5)).isoformat()
                )
                sample_records.append(record)
            
            # Afternoon dose - sometimes missed
            if days_ago not in [2, 5]:  # Missed 2 and 5 days ago
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[0].id,
                    medication_id="M0",
                    scheduled_time="14:00",
                    actual_time="14:10" if days_ago % 3 == 0 else "14:25",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Afternoon dose taken",
                    created_at=(record_datetime + timedelta(hours=14, minutes=10)).isoformat()
                )
                sample_records.append(record)
            else:
                # Create missed record
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[0].id,
                    medication_id="M0",
                    scheduled_time="14:00",
                    actual_time=None,
                    status=MedicationStatus.MISSED,
                    sensor_confirmed=False,
                    notes="Afternoon dose missed",
                    created_at=(record_datetime + timedelta(hours=15)).isoformat()
                )
                sample_records.append(record)
            
            # Evening dose - mostly taken
            if days_ago != 1:  # Missed yesterday
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[0].id,
                    medication_id="M0",
                    scheduled_time="20:00",
                    actual_time="20:05",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Evening dose taken",
                    created_at=(record_datetime + timedelta(hours=20, minutes=5)).isoformat()
                )
                sample_records.append(record)
        
        # M1 records (2 times daily)
        if days_ago <= 7:  # Started 7 days ago
            # Morning dose
            if days_ago not in [4, 6]:
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[1].id,
                    medication_id="M1",
                    scheduled_time="09:00",
                    actual_time="09:08",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Morning M1 dose",
                    created_at=(record_datetime + timedelta(hours=9, minutes=8)).isoformat()
                )
                sample_records.append(record)
            
            # Evening dose
            if days_ago not in [2, 4]:
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[1].id,
                    medication_id="M1", 
                    scheduled_time="21:00",
                    actual_time="21:12",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Evening M1 dose",
                    created_at=(record_datetime + timedelta(hours=21, minutes=12)).isoformat()
                )
                sample_records.append(record)
        
        # M2 records (1 time daily, started 5 days ago)
        if days_ago <= 5:
            if days_ago != 3:  # Missed 3 days ago
                record = SimpleMedicationRecord(
                    id=str(uuid.uuid4()),
                    schedule_id=schedules[2].id,
                    medication_id="M2",
                    scheduled_time="12:00",
                    actual_time="12:15",
                    status=MedicationStatus.TAKEN,
                    sensor_confirmed=True,
                    notes="Lunch M2 dose",
                    created_at=(record_datetime + timedelta(hours=12, minutes=15)).isoformat()
                )
                sample_records.append(record)
    
    # Save all records
    for record in sample_records:
        db_manager.save_record(record)
    
    print(f"✅ Created {len(sample_records)} sample medication records")
    
    # Show summary
    print("\n📊 Sample Data Summary:")
    print("Schedules:")
    print("• M0 (Medication M0): 3x daily (08:00, 14:00, 20:00)")
    print("• M1 (Medication M1): 2x daily (09:00, 21:00)") 
    print("• M2 (Medication M2): 1x daily (12:00)")
    print("\nRecords: 10 days of simulated medication taking with some missed doses")
    print("📅 Check the calendar to see the visual representation!")

def test_calendar_display():
    """Test calendar widget display"""
    
    print("\n🖥️ Testing Calendar Widget...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from medication_calendar import MedicationCalendarWidget
        
        app = QApplication(sys.argv)
        
        calendar = MedicationCalendarWidget()
        calendar.setWindowTitle("Medication Records Calendar - Test")
        calendar.resize(1200, 800)
        calendar.show()
        
        print("✅ Calendar widget created successfully!")
        print("🎯 Features to test:")
        print("   • Monthly view with colored dates")
        print("   • Click on dates to see daily details") 
        print("   • Green = all medications taken")
        print("   • Yellow = partially taken")
        print("   • Red = missed medications")
        print("   • White = no schedules")
        print("   • Month/year navigation")
        print("   • Monthly statistics")
        
        return app.exec()
        
    except ImportError as e:
        print(f"❌ Cannot test calendar widget: {e}")
        print("💡 Make sure PyQt6 is installed: pip install PyQt6")
        return False

def show_text_calendar():
    """Show text-based calendar for systems without PyQt6"""
    
    print("\n📅 Text-based Calendar Preview:")
    print("=" * 50)
    
    from simple_models import SimpleDataManager, MedicationRecorder
    
    db_manager = SimpleDataManager()
    recorder = MedicationRecorder(db_manager)
    
    # Show recent days
    today = datetime.now().date()
    
    print("📊 Recent Medication Status:")
    
    for days_ago in range(7, 0, -1):
        check_date = today - timedelta(days=days_ago)
        
        # Get day's records
        records = db_manager.get_recent_records(limit=100)
        day_records = [r for r in records if r.created_at.startswith(check_date.strftime('%Y-%m-%d'))]
        
        taken_count = len([r for r in day_records if r.status.value == "taken"])
        missed_count = len([r for r in day_records if r.status.value == "missed"])
        
        if taken_count > 0 and missed_count == 0:
            status = "🟢 Perfect"
        elif taken_count > 0:
            status = "🟡 Partial"
        elif missed_count > 0:
            status = "🔴 Missed"
        else:
            status = "⚪ No data"
        
        print(f"{check_date.strftime('%Y-%m-%d')}: {status} (Taken: {taken_count}, Missed: {missed_count})")
    
    # Monthly summary
    summary = recorder.get_today_medication_summary()
    print(f"\n📈 Today's Status: Taken: {summary['taken']}, Missed: {summary['missed']}, Pending: {summary['pending']}")
    
    adherence = recorder.get_medication_adherence_rate(days=7)
    print(f"📊 7-day Adherence Rate: {adherence:.1f}%")

if __name__ == "__main__":
    print("🏥 Medication Calendar Test System")
    print("=" * 50)
    
    try:
        # Create sample data
        create_sample_data()
        
        # Try to show GUI calendar
        if "--gui" in sys.argv or len(sys.argv) == 1:
            success = test_calendar_display()
            if not success:
                show_text_calendar()
        else:
            show_text_calendar()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Fallback: Showing text-based summary")
        show_text_calendar()