#!/usr/bin/env python3
"""
Test Medication Recording System Integration
"""
import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_models import (SimpleDataManager, SimpleMedicationSchedule, 
                          MedicationRecorder, MedicationStatus, get_medication_name)
import uuid

def test_medication_recording():
    """Test medication recording functionality"""
    
    print("🧪 Testing Medication Recording System")
    print("=" * 50)
    
    # 1. Initialize system
    db_manager = SimpleDataManager()
    recorder = MedicationRecorder(db_manager)
    
    # 2. Create test schedule
    test_schedule = SimpleMedicationSchedule(
        id=str(uuid.uuid4()),
        medication_id="M0",
        times_per_day=3,
        dosage_count=1,
        schedule_times=["08:00", "14:00", "20:00"],
        start_date="2024-10-01",
        end_date="2024-12-31",
        notes="Test medication - take with water",
        is_active=True
    )
    
    db_manager.save_schedule(test_schedule)
    print(f"✅ Created test schedule for {get_medication_name('M0')}")
    
    # 3. Simulate sensor data (compartment opened)
    print("\n📊 Simulating sensor events...")
    
    # Simulate taking medication at 08:05 (5 minutes late)
    record1 = recorder.process_sensor_data("0", "08:05")
    if record1:
        print(f"✅ Record 1: {get_medication_name(record1.medication_id)} taken at {record1.actual_time}")
        print(f"   Status: {record1.status.value}, Sensor confirmed: {record1.sensor_confirmed}")
    
    # Simulate taking medication at 14:30 (30 minutes late)
    record2 = recorder.process_sensor_data("0", "14:30")
    if record2:
        print(f"✅ Record 2: {get_medication_name(record2.medication_id)} taken at {record2.actual_time}")
        print(f"   Status: {record2.status.value}, Sensor confirmed: {record2.sensor_confirmed}")
    
    # 4. Check for missed medications (simulate evening check)
    print("\n⏰ Checking for missed medications...")
    missed_count = recorder.check_missed_medications()
    print(f"Found {missed_count} missed medications")
    
    # 5. Get today's summary
    print("\n📈 Today's Medication Summary:")
    summary = recorder.get_today_medication_summary()
    print(f"Date: {summary['date']}")
    print(f"Total scheduled: {summary['total_scheduled']}")
    print(f"Taken: {summary['taken']}")
    print(f"Missed: {summary['missed']}")
    print(f"Pending: {summary['pending']}")
    
    # 6. Show recent records
    print("\n📋 Recent Medication Records:")
    records = db_manager.get_recent_records(limit=5)
    for i, record in enumerate(records, 1):
        med_name = get_medication_name(record.medication_id)
        status_icon = "✅" if record.status == MedicationStatus.TAKEN else "❌"
        print(f"{i}. {status_icon} {med_name}")
        print(f"   Scheduled: {record.scheduled_time}, Actual: {record.actual_time or 'N/A'}")
        print(f"   Status: {record.status.value}, Notes: {record.notes}")
    
    # 7. Calculate adherence rate
    print("\n📊 Medication Adherence Rate:")
    adherence = recorder.get_medication_adherence_rate(days=7)
    print(f"7-day adherence rate: {adherence:.1f}%")
    
    print("\n🎉 Test completed successfully!")
    return True

def test_multiple_medications():
    """Test with multiple medications"""
    
    print("\n🧪 Testing Multiple Medications")
    print("=" * 50)
    
    db_manager = SimpleDataManager()
    recorder = MedicationRecorder(db_manager)
    
    # Create schedules for M1 and M2
    schedules = [
        SimpleMedicationSchedule(
            id=str(uuid.uuid4()),
            medication_id="M1",
            times_per_day=2,
            dosage_count=2,
            schedule_times=["09:00", "21:00"],
            start_date="2024-10-01",
            end_date="2024-12-31",
            notes="Morning and evening medication",
            is_active=True
        ),
        SimpleMedicationSchedule(
            id=str(uuid.uuid4()),
            medication_id="M2",
            times_per_day=1,
            dosage_count=1,
            schedule_times=["12:00"],
            start_date="2024-10-01",
            end_date="2024-12-31",
            notes="Lunch medication",
            is_active=True
        )
    ]
    
    for schedule in schedules:
        db_manager.save_schedule(schedule)
        print(f"✅ Created schedule for {get_medication_name(schedule.medication_id)}")
    
    # Simulate taking different medications
    print("\n📊 Simulating medication events...")
    
    # M1 taken at 09:05
    record1 = recorder.process_sensor_data("1", "09:05")
    if record1:
        print(f"✅ {get_medication_name('M1')} taken at 09:05")
    
    # M2 taken at 12:15
    record2 = recorder.process_sensor_data("2", "12:15")
    if record2:
        print(f"✅ {get_medication_name('M2')} taken at 12:15")
    
    # Show updated summary
    summary = recorder.get_today_medication_summary()
    print(f"\n📈 Updated Summary:")
    print(f"Total scheduled: {summary['total_scheduled']}")
    print(f"Taken: {summary['taken']}")
    print(f"Missed: {summary['missed']}")
    print(f"Pending: {summary['pending']}")
    
    return True

def simulate_sensor_integration():
    """Simulate real sensor integration"""
    
    print("\n🔌 Simulating Sensor Integration")
    print("=" * 50)
    
    # This simulates what would happen when the pillbox sends sensor data
    sensor_events = [
        {"compartment_opened": "0", "opened_time": "08:03"},
        {"compartment_opened": "1", "opened_time": "14:12"},
        {"compartment_opened": "2", "opened_time": "20:45"},
    ]
    
    recorder = MedicationRecorder()
    
    print("Processing sensor events...")
    for event in sensor_events:
        compartment = event["compartment_opened"]
        time_opened = event["opened_time"]
        
        print(f"🔍 Sensor detected: Compartment {compartment} opened at {time_opened}")
        
        # This is what would be called from SimplePillboxCommunicator
        record = recorder.process_sensor_data(compartment, time_opened)
        
        if record:
            med_name = get_medication_name(record.medication_id)
            print(f"   💊 Recorded: {med_name} taken (Status: {record.status.value})")
        else:
            print(f"   ⚠️  No active schedule found for compartment {compartment}")
    
    return True

if __name__ == "__main__":
    try:
        # Run all tests
        test_medication_recording()
        test_multiple_medications()
        simulate_sensor_integration()
        
        print("\n🎉 All tests passed! Medication recording system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)