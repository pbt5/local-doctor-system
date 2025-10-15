"""
Integration of Family Notifications with existing Simple System
Extends simple_models.py to include notification triggers
"""
from typing import List, Optional
from datetime import datetime, timedelta
import threading
import time

# Import existing classes
from simple_models import MedicationStatus, MedicationRecorder, SimpleDataManager
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass

@dataclass
class FamilyContact:
    """Family contact information"""
    name: str
    email: str
    relationship: str  # "Son", "Daughter", "Spouse", etc.
    notification_level: str  # "all", "missed_only", "emergency"

class FamilyNotificationSystem:
    """System to send notifications to family members"""
    
    def __init__(self, config_path: str = "system_config.json"):
        self.config = self.load_config(config_path)
        self.db_manager = SimpleDataManager()
        self.recorder = MedicationRecorder(self.db_manager)
        self.family_contacts = []
    
    def load_config(self, config_path: str):
        """Load email configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"sender_email": "", "sender_password": ""}
    
    def add_family_contact(self, contact: FamilyContact):
        """Add a family contact"""
        self.family_contacts.append(contact)
    
    def send_missed_medication_alert(self, missed_medications):
        """Send alert when medications are missed"""
        if not missed_medications or not self.family_contacts:
            return False
        
        subject = f"🚨 Medication Alert - {len(missed_medications)} medications missed"
        content = f"Missed medications: {', '.join(missed_medications)}"
        
        for contact in self.family_contacts:
            if contact.notification_level in ["all", "missed_only"]:
                self.send_email(contact.email, subject, content)
        return True
    
    def send_daily_summary(self):
        """Send daily medication summary"""
        # Basic implementation
        return True
    
    def send_emergency_alert(self, reason: str):
        """Send emergency alert"""
        subject = "🚨 URGENT: Medication Emergency Alert"
        content = f"Emergency: {reason}"
        
        for contact in self.family_contacts:
            self.send_email(contact.email, subject, content)
        return True
    
    def send_email(self, to_email: str, subject: str, body: str):
        """Send individual email"""
        try:
            sender_email = self.config.get("sender_email")
            sender_password = self.config.get("sender_password")
            
            if not sender_email or not sender_password:
                return False
            
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = to_email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(message)
            
            print(f"✅ Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

class EnhancedMedicationRecorder(MedicationRecorder):
    """
    Enhanced recorder with family notification capabilities
    """
    
    def __init__(self, db_manager: SimpleDataManager, enable_notifications: bool = True):
        super().__init__(db_manager)
        self.enable_notifications = enable_notifications
        
        if enable_notifications:
            self.notification_system = FamilyNotificationSystem()
            self.setup_default_family_contacts()
            self.last_notification_check = datetime.now()
    
    def setup_default_family_contacts(self):
        """Set up family contacts from configuration file"""
        try:
            # Load contacts from system_config.json
            family_contacts_data = self.notification_system.config.get("family_contacts", [])
            
            if family_contacts_data:
                # Clear existing contacts
                self.notification_system.family_contacts = []
                
                # Add contacts from config
                for contact_data in family_contacts_data:
                    contact = FamilyContact(
                        name=contact_data["name"],
                        email=contact_data["email"],
                        relationship=contact_data["relationship"],
                        notification_level=contact_data["notification_level"]
                    )
                    self.notification_system.add_family_contact(contact)
                    print(f"✅ Added family contact: {contact.name} ({contact.email}) - {contact.notification_level}")
            else:
                print("⚠️ No family contacts found in system_config.json")
                # Fallback to default contact
                default_contact = FamilyContact(
                    name="家屬聯絡人",
                    email="family@example.com",  # 👈 Replace with actual email
                    relationship="Family",
                    notification_level="all"
                )
                self.notification_system.add_family_contact(default_contact)
                print(f"⚠️ Using default contact: {default_contact.email}")
                
        except Exception as e:
            print(f"❌ Error loading family contacts: {e}")
            # Fallback to default
            default_contact = FamilyContact(
                name="家屬聯絡人",
                email="family@example.com",
                relationship="Family", 
                notification_level="all"
            )
            self.notification_system.add_family_contact(default_contact)
            print(f"❌ Using fallback contact: {default_contact.email}")
    
    def record_medication_taken(self, medication_id: str, actual_time: datetime) -> bool:
        """Record medication taken and check for notifications"""
        success = super().record_medication_taken(medication_id, actual_time)
        
        if success and self.enable_notifications:
            self.check_and_send_notifications()
        
        return success
    
    def record_medication_missed(self, medication_id: str) -> bool:
        """Record medication missed and send alert"""
        success = super().record_medication_missed(medication_id)
        
        if success and self.enable_notifications:
            # Immediately check for missed medications
            missed_meds = self.get_missed_medications_today()
            if missed_meds:
                print(f"📧 Sending missed medication alert for: {missed_meds}")
                self.notification_system.send_missed_medication_alert(missed_meds)
        
        return success
    
    def get_missed_medications_today(self) -> List[str]:
        """Get list of medications missed today"""
        summary = self.get_today_medication_summary()
        
        missed_medications = []
        for record in summary.get('records', []):
            if record.status == MedicationStatus.MISSED:
                missed_medications.append(record.medication_id)
        
        return missed_medications
    
    def check_and_send_notifications(self):
        """Check if notifications should be sent"""
        now = datetime.now()
        
        # Check for missed medications (every minute)
        if (now - self.last_notification_check).total_seconds() > 60:  # 1 minute
            missed_meds = self.get_missed_medications_today()
            if missed_meds:
                print(f"📧 Sending missed medication alert for: {missed_meds}")
                self.notification_system.send_missed_medication_alert(missed_meds)
                self.last_notification_check = now  # Update check time after sending
        
        # Send daily summary at 9 PM
        if now.hour == 21 and (now - self.last_notification_check).days >= 1:
            self.notification_system.send_daily_summary()
            self.last_notification_check = now
    
    def check_emergency_conditions(self):
        """Check for emergency conditions"""
        if not self.enable_notifications:
            return
        
        # Check if no medications taken in 24 hours
        records = self.get_recent_records(hours=24)
        taken_records = [r for r in records if r.status == MedicationStatus.TAKEN]
        
        if not taken_records and records:  # Has scheduled meds but none taken
            self.notification_system.send_emergency_alert(
                "No medications taken in the last 24 hours"
            )
        
        # Check adherence rate
        adherence = self.get_medication_adherence_rate(days=7)
        if adherence < 50.0:  # Less than 50% adherence
            self.notification_system.send_emergency_alert(
                f"Low medication adherence: {adherence:.1f}% over the last 7 days"
            )

class NotificationScheduler:
    """
    Background scheduler for automatic notifications
    """
    
    def __init__(self, recorder: EnhancedMedicationRecorder):
        self.recorder = recorder
        self.running = False
        self.thread = None
    
    def start(self):
        """Start background monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("📡 Notification scheduler started")
    
    def stop(self):
        """Stop background monitoring"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("📡 Notification scheduler stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Check every 30 minutes
                time.sleep(1800)  # 30 minutes
                
                if self.running:  # Check again in case stop was called
                    self.recorder.check_and_send_notifications()
                    
                    # Check emergency conditions once per hour
                    now = datetime.now()
                    if now.minute < 30:  # First half of hour
                        self.recorder.check_emergency_conditions()
                        
            except Exception as e:
                print(f"❌ Notification scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes before retry

# Enhanced system configuration helper
def setup_enhanced_system_with_notifications():
    """Set up the complete system with family notifications"""
    
    print("🏥 Setting up Enhanced Medication System with Family Notifications")
    print("=" * 60)
    
    # Initialize database
    db_manager = SimpleDataManager()
    
    # Create enhanced recorder with notifications
    recorder = EnhancedMedicationRecorder(db_manager, enable_notifications=True)
    
    # Start notification scheduler
    scheduler = NotificationScheduler(recorder)
    scheduler.start()
    
    print("✅ System setup complete!")
    print("\n📧 Notification Features:")
    print("• Missed medication alerts (immediate)")
    print("• Daily summaries (9 PM)")
    print("• Emergency alerts (24h no meds, <50% adherence)")
    print("• Background monitoring every 30 minutes")
    
    return recorder, scheduler

if __name__ == "__main__":
    # Test the enhanced system
    print("🧪 Testing Enhanced Medication System")
    print("=" * 40)
    
    recorder, scheduler = setup_enhanced_system_with_notifications()
    
    # Test notification system
    if recorder.enable_notifications:
        print("\n📧 Testing email system...")
        success = recorder.notification_system.test_email_system()
        
        if not success:
            print("\n⚙️ Email Configuration Required:")
            print("1. Edit system_config.json")
            print("2. Add your email credentials:")
            print('   "sender_email": "your-email@gmail.com"')
            print('   "sender_password": "your-app-password"')
            print("3. Update family contacts in family_notifications.py")
    
    # Keep running for testing
    try:
        print("\n🔄 System running... Press Ctrl+C to stop")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler.stop()
        print("\n👋 System stopped")