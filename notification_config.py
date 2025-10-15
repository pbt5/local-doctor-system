"""
Configuration helper for Family Notification System
Easy setup for email and family contacts
"""
import json
import os
from typing import Dict, List

def create_notification_config():
    """Create or update notification configuration"""
    
    print("📧 Smart Pillbox Family Notification Setup")
    print("=" * 45)
    
    config_path = "system_config.json"
    
    # Load existing config or create new one
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("✅ Found existing system_config.json")
    else:
        config = {}
        print("📝 Creating new system_config.json")
    
    # Email configuration
    print("\n📮 Email Configuration (for sending notifications):")
    print("Note: For Gmail, you need an 'App Password', not your regular password")
    print("How to get Gmail App Password: https://support.google.com/accounts/answer/185833")
    
    current_email = config.get("sender_email", "")
    if current_email:
        print(f"Current email: {current_email}")
        change = input("Change email? (y/n): ").lower().strip()
        if change == 'y':
            config["sender_email"] = input("Enter your email address: ").strip()
    else:
        config["sender_email"] = input("Enter your email address: ").strip()
    
    current_password = config.get("sender_password", "")
    if current_password:
        print("Email password is already set")
        change = input("Update password? (y/n): ").lower().strip()
        if change == 'y':
            config["sender_password"] = input("Enter your app password: ").strip()
    else:
        config["sender_password"] = input("Enter your app password: ").strip()
    
    # SMTP settings
    config.update({
        "smtp_server": config.get("smtp_server", "smtp.gmail.com"),
        "smtp_port": config.get("smtp_port", 587)
    })
    
    # Family contacts configuration
    print("\n👥 Family Contacts Configuration:")
    print("💡 提示: 接收通知的郵箱可以跟發送者郵箱相同或不同")
    
    family_contacts = []
    
    while True:
        print(f"\n--- Adding Family Contact #{len(family_contacts) + 1} ---")
        
        name = input("Contact name (or 'done' to finish): ").strip()
        if name.lower() == 'done':
            break
        
        print(f"📧 發送者郵箱: {config.get('sender_email', 'Not set')}")
        use_same = input("使用相同郵箱接收通知? (y/n): ").lower().strip()
        
        if use_same == 'y':
            email = config.get('sender_email', '')
            print(f"✅ 使用發送者郵箱: {email}")
        else:
            email = input("輸入接收通知的郵箱: ").strip()
        relationship = input("Relationship (e.g., Son, Daughter, Spouse, Caregiver): ").strip()
        
        print("\nNotification levels:")
        print("1. all - Receives all notifications (daily summaries, missed meds, emergencies)")
        print("2. missed_only - Only missed medication alerts and emergencies")
        print("3. emergency - Only emergency alerts")
        
        level_choice = input("Choose notification level (1-3): ").strip()
        level_map = {"1": "all", "2": "missed_only", "3": "emergency"}
        notification_level = level_map.get(level_choice, "missed_only")
        
        family_contacts.append({
            "name": name,
            "email": email,
            "relationship": relationship,
            "notification_level": notification_level
        })
        
        print(f"✅ Added: {name} ({email}) - {notification_level} notifications")
        
        if len(family_contacts) >= 5:  # Reasonable limit
            break
    
    # Save family contacts
    config["family_contacts"] = family_contacts
    
    # Save configuration
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Configuration saved to {config_path}")
    
    # Display summary
    print("\n📋 Configuration Summary:")
    print(f"📧 Email: {config['sender_email']}")
    print(f"👥 Family contacts: {len(family_contacts)}")
    
    for contact in family_contacts:
        print(f"   • {contact['name']} ({contact['relationship']}) - {contact['notification_level']}")
    
    return config

def load_family_contacts_from_config():
    """Load family contacts from configuration file"""
    from enhanced_notifications import FamilyContact, FamilyNotificationSystem
    
    try:
        with open("system_config.json", 'r') as f:
            config = json.load(f)
        
        family_contacts = config.get("family_contacts", [])
        notification_system = FamilyNotificationSystem()
        
        for contact_data in family_contacts:
            contact = FamilyContact(
                name=contact_data["name"],
                email=contact_data["email"],
                relationship=contact_data["relationship"],
                notification_level=contact_data["notification_level"]
            )
            notification_system.add_family_contact(contact)
        
        return notification_system
        
    except FileNotFoundError:
        print("⚠️ No configuration file found. Run setup first.")
        return None
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return None

def test_notification_setup():
    """Test the notification system setup"""
    
    print("🧪 Testing Notification System Setup")
    print("=" * 35)
    
    # Load system
    notification_system = load_family_contacts_from_config()
    
    if not notification_system:
        print("❌ Could not load notification system")
        return False
    
    if not notification_system.family_contacts:
        print("⚠️ No family contacts configured")
        return False
    
    print(f"✅ Loaded {len(notification_system.family_contacts)} family contacts")
    
    # Test email sending
    print("\n📧 Testing email system...")
    success = notification_system.test_email_system()
    
    if success:
        print("✅ Email test successful! Check family members' inboxes.")
    else:
        print("❌ Email test failed. Please check configuration.")
    
    return success

def show_usage_examples():
    """Show examples of how to use the notification system"""
    
    print("💡 Usage Examples")
    print("=" * 20)
    
    print("\n1. Basic integration in your main system:")
    print("""
from enhanced_notifications import setup_enhanced_system_with_notifications

# Set up system with notifications
recorder, scheduler = setup_enhanced_system_with_notifications()

# Normal medication recording - notifications automatic
recorder.record_medication_taken("MED001", datetime.now())
recorder.record_medication_missed("MED002")
""")
    
    print("\n2. Manual notification sending:")
    print("""
from notification_config import load_family_contacts_from_config

# Load configured notification system
notification_system = load_family_contacts_from_config()

# Send manual alert
notification_system.send_missed_medication_alert(["MED001", "MED002"])

# Send daily summary
notification_system.send_daily_summary()

# Send emergency alert
notification_system.send_emergency_alert("Patient hasn't taken meds for 24 hours")
""")
    
    print("\n3. Configuration file structure (system_config.json):")
    print("""
{
  "sender_email": "your-email@gmail.com",
  "sender_password": "your-app-password",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "family_contacts": [
    {
      "name": "張小明",
      "email": "son@example.com",
      "relationship": "Son",
      "notification_level": "all"
    }
  ]
}
""")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            create_notification_config()
        elif command == "test":
            test_notification_setup()
        elif command == "examples":
            show_usage_examples()
        else:
            print("Usage: python notification_config.py [setup|test|examples]")
    else:
        # Interactive menu
        while True:
            print("\n🏥 Smart Pillbox Notification Configuration")
            print("=" * 45)
            print("1. Setup email and family contacts")
            print("2. Test notification system")
            print("3. Show usage examples")
            print("4. Exit")
            
            choice = input("\nChoose option (1-4): ").strip()
            
            if choice == "1":
                create_notification_config()
            elif choice == "2":
                test_notification_setup()
            elif choice == "3":
                show_usage_examples()
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")