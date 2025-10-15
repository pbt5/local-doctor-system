"""
Simplified Data Model
Fixed patient (one person), fixed medications (M0-M9), only manages medication schedules
"""
import json
import sqlite3
from datetime import datetime, time, timedelta
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

class MedicationRecorder:
    """Medication Time Recording System"""
    
    def __init__(self, db_manager: Optional[SimpleDataManager] = None):
        self.db_manager = db_manager or SimpleDataManager()
        
    def process_sensor_data(self, compartment_id: str, opened_time: str = None):
        """Process sensor data when compartment is opened"""
        
        if opened_time is None:
            opened_time = datetime.now().strftime("%H:%M")
        
        # 1. 找到對應的藥物排程
        schedules = self.db_manager.get_active_schedules()
        target_schedule = None
        
        medication_id = f"M{compartment_id}" if compartment_id.isdigit() else compartment_id
        
        for schedule in schedules:
            if schedule.medication_id == medication_id:
                target_schedule = schedule
                break
        
        if not target_schedule:
            print(f"No active schedule found for compartment {compartment_id}")
            return None
        
        # 2. 判斷用藥狀態
        current_time = datetime.now()
        status = self._determine_medication_status(target_schedule, current_time)
        
        # 3. 建立用藥記錄
        record = SimpleMedicationRecord(
            id=str(uuid.uuid4()),
            schedule_id=target_schedule.id,
            medication_id=target_schedule.medication_id,
            scheduled_time=self._get_nearest_scheduled_time(target_schedule, current_time),
            actual_time=opened_time,
            status=status,
            sensor_confirmed=True,
            notes=f"Compartment {compartment_id} opened at {opened_time}"
        )
        
        # 4. 儲存記錄
        self.db_manager.save_record(record)
        
        med_name = get_medication_name(target_schedule.medication_id)
        print(f"✅ Medication record saved: {med_name} at {opened_time} (Status: {status.value})")
        
        return record
    
    def _determine_medication_status(self, schedule, actual_time) -> MedicationStatus:
        """Determine medication status based on timing"""
        
        nearest_scheduled = self._get_nearest_scheduled_time(schedule, actual_time)
        if not nearest_scheduled:
            return MedicationStatus.TAKEN
            
        # 解析時間
        try:
            scheduled_dt = datetime.strptime(nearest_scheduled, "%H:%M")
        except ValueError:
            return MedicationStatus.TAKEN
        
        # 轉換為同一天的時間進行比較
        scheduled_today = actual_time.replace(
            hour=scheduled_dt.hour, 
            minute=scheduled_dt.minute, 
            second=0, 
            microsecond=0
        )
        
        time_diff = abs((actual_time - scheduled_today).total_seconds() / 60)  # 分鐘差異
        
        if time_diff <= 15:  # 15分鐘內算準時
            return MedicationStatus.TAKEN
        elif time_diff <= 60:  # 1小時內算延遲但已服用
            return MedicationStatus.TAKEN
        else:  # 超過1小時算逾期
            return MedicationStatus.TAKEN  # 還是算已服用，只是逾期了
    
    def _get_nearest_scheduled_time(self, schedule, current_time) -> Optional[str]:
        """Find the nearest scheduled time"""
        
        current_time_str = current_time.strftime("%H:%M")
        
        # 找到最接近的排程時間
        nearest_time = None
        min_diff = float('inf')
        
        for time_str in schedule.schedule_times:
            try:
                scheduled_dt = datetime.strptime(time_str, "%H:%M")
                current_dt = datetime.strptime(current_time_str, "%H:%M")
                
                diff = abs((scheduled_dt - current_dt).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    nearest_time = time_str
            except ValueError:
                continue
                
        return nearest_time or (schedule.schedule_times[0] if schedule.schedule_times else None)
    
    def check_missed_medications(self):
        """Check for missed medications and update status"""
        
        schedules = self.db_manager.get_active_schedules()
        current_time = datetime.now()
        current_date = current_time.date().strftime('%Y-%m-%d')
        
        missed_count = 0
        
        for schedule in schedules:
            for time_str in schedule.schedule_times:
                try:
                    # 解析預定時間
                    hour, minute = map(int, time_str.split(':'))
                    scheduled_today = current_time.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0
                    )

                    # 如果預定時間已過1分鐘且沒有用藥記錄
                    if current_time > scheduled_today + timedelta(minutes=1):
                        if not self._has_recent_record(schedule, time_str, current_date):
                            # 建立錯過用藥的記錄
                            missed_record = SimpleMedicationRecord(
                                id=str(uuid.uuid4()),
                                schedule_id=schedule.id,
                                medication_id=schedule.medication_id,
                                scheduled_time=time_str,
                                actual_time=None,
                                status=MedicationStatus.MISSED,
                                sensor_confirmed=False,
                                notes=f"Missed medication at scheduled time {time_str}"
                            )
                            
                            self.db_manager.save_record(missed_record)
                            med_name = get_medication_name(schedule.medication_id)
                            print(f"⚠️ Missed medication recorded: {med_name} at {time_str}")
                            missed_count += 1
                            
                except ValueError:
                    continue
        
        return missed_count
    
    def _has_recent_record(self, schedule, time_str: str, date_str: str) -> bool:
        """Check if there's a recent record for this schedule and time"""
        
        records = self.db_manager.get_recent_records(limit=100)
        
        for record in records:
            if (record.schedule_id == schedule.id and 
                record.scheduled_time == time_str and
                record.created_at.startswith(date_str)):
                return True
                
        return False
    
    def get_today_medication_summary(self) -> dict:
        """Get today's medication summary"""
        
        today = datetime.now().date().strftime('%Y-%m-%d')
        records = self.db_manager.get_recent_records(limit=100)
        
        today_records = [r for r in records if r.created_at.startswith(today)]
        
        summary = {
            'date': today,
            'total_scheduled': 0,
            'taken': len([r for r in today_records if r.status == MedicationStatus.TAKEN]),
            'missed': len([r for r in today_records if r.status == MedicationStatus.MISSED]),
            'pending': 0,  # 計算當日剩餘待服用
            'records': today_records
        }
        
        # 計算今日總預定用藥次數
        schedules = self.db_manager.get_active_schedules()
        for schedule in schedules:
            summary['total_scheduled'] += len(schedule.schedule_times)
        
        # 計算待服用數量
        summary['pending'] = summary['total_scheduled'] - summary['taken'] - summary['missed']
        
        return summary
    
    def get_medication_adherence_rate(self, days: int = 7) -> float:
        """Calculate medication adherence rate for recent days"""
        
        records = self.db_manager.get_recent_records(limit=500)
        
        # 過濾最近幾天的記錄
        cutoff_date = (datetime.now() - timedelta(days=days)).date().strftime('%Y-%m-%d')
        recent_records = [r for r in records if r.created_at >= cutoff_date]
        
        if not recent_records:
            return 0.0
        
        taken_count = len([r for r in recent_records if r.status == MedicationStatus.TAKEN])
        total_count = len(recent_records)
        
        return (taken_count / total_count) * 100 if total_count > 0 else 0.0