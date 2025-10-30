#!/usr/bin/env python3
"""
Test script for Welcome message handling
"""

from simple_host_sender import SimplePillboxCommunicator
import time

def message_callback(event_type, data):
    """Callback function to handle all messages"""
    print(f"\n[Callback] Received {event_type} event")
    if event_type == 'welcome':
        print(f"  Device: {data.device}")
        print(f"  IP: {data.ip}")
        print(f"  Boxes: {data.boxes}")
        print(f"  Time: {data.time}")
    elif event_type == 'box_event':
        print(f"  Box {data.box}: {data.state} at {data.time}")
    elif event_type == 'status':
        print(f"  Time: {data.get('time')}")
        print(f"  WiFi: {data.get('wifi')}")
        print(f"  Schedules: {data.get('scheduleCount')}")

def main():
    print("=" * 60)
    print("ESP32 Welcome Message Test")
    print("=" * 60)

    # Create communicator with auto-discovery
    comm = SimplePillboxCommunicator()

    # Add callback to receive messages
    comm.add_status_callback(message_callback)

    # Connect to ESP32
    if comm.connect():
        print("\n[Success] Connected to ESP32")
        print(f"Waiting for messages... (Press Ctrl+C to exit)")

        try:
            # Keep running to receive messages
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n[Info] Disconnecting...")

        finally:
            comm.disconnect()
            print("[Info] Disconnected")

    else:
        print("\n[Failed] Could not connect to ESP32")
        print("Please check:")
        print("  1. ESP32 is powered on and connected to WiFi")
        print("  2. ESP32 IP address is correct in system_config.json")
        print("  3. ESP32 is running the TCP server on port 8080")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
