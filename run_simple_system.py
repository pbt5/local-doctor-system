#!/usr/bin/env python3
"""
Simplified Smart Pillbox Management System Startup Script
"""
import sys
import os

# Ensure local modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check dependency packages"""
    missing_packages = []
    
    try:
        import PyQt6
    except ImportError:
        missing_packages.append("PyQt6")
    
    if missing_packages:
        print("Missing required packages, please install the following packages:")
        for package in missing_packages:
            print(f"  pip install {package}")
        return False
    
    return True

def initialize_system():
    """Initialize system"""
    from simple_models import SimpleDataManager, create_sample_schedule
    
    print("Initializing Simplified Smart Pillbox Management System...")
    
    # Initialize database
    db_manager = SimpleDataManager()
    
    # Check if sample data needs to be created
    schedules = db_manager.get_all_schedules()
    
    if not schedules:
        print("Empty database detected, create sample schedules? (y/n): ", end="")
        choice = input().lower().strip()
        if choice in ['y', 'yes']:
            create_sample_schedule()
            print("Sample schedules created!")
    
    return db_manager

def main():
    """Main program"""
    print("=" * 50)
    print("Smart Pillbox Management System v1.0 (Simplified Version)")
    print("EE542 Project")
    print("=" * 50)
    print("Simplification description:")
    print("- Patient: Fixed to single patient")
    print("- Medications: Fixed to M0-M9 (10 types)")
    print("- Functions: Medication scheduling + Pillbox communication + Instructions transmission")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Initialize system
    try:
        db_manager = initialize_system()
    except Exception as e:
        print(f"System initialization failed: {e}")
        sys.exit(1)
    
    # Start GUI
    print("Starting graphical interface...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from simple_main import SimpleMainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("Smart Pillbox Management System")
        app.setApplicationVersion("1.0 (Simplified Version)")
        app.setOrganizationName("EE542")
        
        window = SimpleMainWindow()
        window.show()
        
        print("System started successfully!")
        print("Usage instructions:")
        print("1. Set M0-M9 medication schedules in the 'Medication Schedule Management' tab")
        print("2. Connect to pillbox and test functions in the 'Pillbox Connection & Testing' tab")
        print("3. Instructions will be sent directly to the pillbox screen for display")
        print("4. Test basic communication functions in the 'Simple Communication Test' tab")
        
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all required packages are installed: pip install PyQt6")
        sys.exit(1)
    except Exception as e:
        print(f"System startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()