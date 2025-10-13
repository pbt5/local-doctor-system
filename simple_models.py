"""
Simplified Data Model
Fixed patient (one person), fixed medications (M0-M9), only manages medication schedules
"""
import json
import sqlite3
from datetime import datetime, time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class MedicationStatus(Enum):
    """Medication Status"""
    PENDING = "pending"      # Pending
    TAKEN = "taken"          # Taken
    MISSED = "missed"        # Missed
    SKIPPED = "skipped"      # Skipped

# Fixed medication list
MEDICATIONS = {
    "M0": "Medication M0",
    "M1": "Medication M1", 
    "M2": "Medication M2",
    "M3": "Medication M3",
    "M4": "Medication M4",
    "M5": "Medication M5",
    "M6": "Medication M6",
    "M7": "Medication M7",
    "M8": "Medication M8",
    "M9": "Medication M9"
}

@dataclass
class SimpleMedicationSchedule:
    """Simplified Medication Schedule"""
    id: str
    medication_id: str  # M0-M9
    times_per_day: int
    dosage_count: int  # Pills per dose
    schedule_times: List[str]  # Medication times ["08:00", "14:00", "20:00"]
    start_date: str
    end_date: str
    notes: str = ""  # Instructions, will be sent to pillbox
    is_active: bool = True
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

@dataclass
class SimpleMedicationRecord:
    """Simplified Medication Record"""
    id: str
    schedule_id: str
    medication_id: str
    scheduled_time: str
    actual_time: Optional[str]
    status: MedicationStatus
    sensor_confirmed: bool = False
    notes: str = ""
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self):
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        data['status'] = MedicationStatus(data['status'])
        return cls(**data)

class SimpleDataManager:
    """Simplified Data Manager"""
    
    def __init__(self, db_path: str = "simple_pillbox.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Medication schedule table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medication_schedules (
                id TEXT PRIMARY KEY,
                medication_id TEXT,
                times_per_day INTEGER,
                dosage_count INTEGER,
                schedule_times TEXT,
                start_date TEXT,
                end_date TEXT,
                notes TEXT,
                is_active BOOLEAN
            )
        ''')
        
        # Medication record table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS medication_records (
                id TEXT PRIMARY KEY,
                schedule_id TEXT,
                medication_id TEXT,
                scheduled_time TEXT,
                actual_time TEXT,
                status TEXT,
                sensor_confirmed BOOLEAN,
                notes TEXT,
                created_at TEXT,
                FOREIGN KEY (schedule_id) REFERENCES medication_schedules (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_schedule(self, schedule: SimpleMedicationSchedule):
        """Save Medication Schedule"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO medication_schedules 
            (id, medication_id, times_per_day, dosage_count, 
             schedule_times, start_date, end_date, notes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (schedule.id, schedule.medication_id, schedule.times_per_day,
              schedule.dosage_count, json.dumps(schedule.schedule_times),
              schedule.start_date, schedule.end_date, schedule.notes, schedule.is_active))
        conn.commit()
        conn.close()
    
    def get_all_schedules(self) -> List[SimpleMedicationSchedule]:
        """Get All Medication Schedules"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM medication_schedules')
        rows = cursor.fetchall()
        conn.close()
        
        schedules = []
        for row in rows:
            schedule = SimpleMedicationSchedule(
                id=row[0], medication_id=row[1], times_per_day=row[2],
                dosage_count=row[3], schedule_times=json.loads(row[4]),
                start_date=row[5], end_date=row[6], notes=row[7], is_active=row[8]
            )
            schedules.append(schedule)
        return schedules
    
    def get_active_schedules(self) -> List[SimpleMedicationSchedule]:
        """Get Active Medication Schedules"""
        schedules = self.get_all_schedules()
        return [s for s in schedules if s.is_active]
    
    def delete_schedule(self, schedule_id: str):
        """Delete Medication Schedule"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM medication_schedules WHERE id = ?', (schedule_id,))
        cursor.execute('DELETE FROM medication_records WHERE schedule_id = ?', (schedule_id,))
        conn.commit()
        conn.close()
    
    def save_record(self, record: SimpleMedicationRecord):
        """Save Medication Record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO medication_records 
            (id, schedule_id, medication_id, scheduled_time, 
             actual_time, status, sensor_confirmed, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (record.id, record.schedule_id, record.medication_id,
              record.scheduled_time, record.actual_time, record.status.value,
              record.sensor_confirmed, record.notes, record.created_at))
        conn.commit()
        conn.close()
    
    def get_recent_records(self, limit: int = 50) -> List[SimpleMedicationRecord]:
        """Get Recent Medication Records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM medication_records 
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            record = SimpleMedicationRecord(
                id=row[0], schedule_id=row[1], medication_id=row[2],
                scheduled_time=row[3], actual_time=row[4],
                status=MedicationStatus(row[5]), sensor_confirmed=row[6],
                notes=row[7], created_at=row[8]
            )
            records.append(record)
        return records

def get_medication_name(medication_id: str) -> str:
    """Get Medication Name"""
    return MEDICATIONS.get(medication_id, f"Unknown Medication {medication_id}")

def create_sample_schedule():
    """Create Sample Schedule"""
    db = SimpleDataManager()
    
    sample_schedule = SimpleMedicationSchedule(
        id=str(uuid.uuid4()),
        medication_id="M0",
        times_per_day=3,
        dosage_count=1,
        schedule_times=["08:00", "14:00", "20:00"],
        start_date="2024-10-01",
        end_date="2024-12-31",
        notes="Take after meals, drink plenty of water",
        is_active=True
    )
    
    db.save_schedule(sample_schedule)
    print("Sample schedule created!")

if __name__ == "__main__":
    # Test simplified model
    create_sample_schedule()
    
    db = SimpleDataManager()
    schedules = db.get_all_schedules()
    
    print("Current schedules:")
    for schedule in schedules:
        med_name = get_medication_name(schedule.medication_id)
        print(f"- {med_name}: {schedule.dosage_count} pills, {schedule.times_per_day} times daily")
        print(f"  Times: {', '.join(schedule.schedule_times)}")
        print(f"  Instructions: {schedule.notes}")