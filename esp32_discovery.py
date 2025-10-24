"""
ESP32 IP Address Auto-Discovery Module using UDP Broadcast
Simple and reliable discovery method
"""

import socket
import json
import time
from typing import Optional, Tuple

class ESP32Discovery:
    """ESP32 UDP Auto-Discovery Class"""

    def __init__(self, timeout=3, udp_port=8888):
        self.timeout = timeout
        self.udp_port = udp_port

    def discover(self) -> Tuple[Optional[str], Optional[int]]:
        """
        Auto-discover ESP32 IP address using UDP broadcast
        Returns: (ip_address, port) or (None, None)
        """
        print("[Discovery] Searching for ESP32 device via UDP broadcast...")

        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(self.timeout)

            # Send discovery broadcast
            discovery_message = b"DISCOVER_ESP32"
            sock.sendto(discovery_message, ('<broadcast>', self.udp_port))
            print(f"  [Broadcast] Sent broadcast to port {self.udp_port}")

            # Wait for response
            try:
                data, addr = sock.recvfrom(1024)
                response = json.loads(data.decode('utf-8'))

                if response.get('device') == 'ESP32-Pillbox':
                    ip = response.get('ip')
                    port = response.get('port', 8080)

                    print(f"  [Success] Found ESP32-Pillbox at {ip}:{port}")
                    print(f"    Device info: {response.get('boxes', 0)} boxes, Time: {response.get('time', 'N/A')}")

                    sock.close()
                    return ip, port

            except socket.timeout:
                print("  [Failed] No response from ESP32 (timeout)")
            except json.JSONDecodeError as e:
                print(f"  [Error] Invalid JSON response: {e}")
            finally:
                sock.close()

        except Exception as e:
            print(f"  [Error] Discovery error: {e}")

        return None, None

    def discover_with_retry(self, max_retries=3) -> Tuple[Optional[str], Optional[int]]:
        """
        Try to discover ESP32 with retries
        Returns: (ip_address, port) or (None, None)
        """
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n[Retry] Retry attempt {attempt}/{max_retries}...")

            result = self.discover()
            if result[0]:
                return result

            if attempt < max_retries:
                time.sleep(1)

        return None, None


def discover_esp32(timeout=3, max_retries=3) -> Tuple[Optional[str], Optional[int]]:
    """
    Convenience function to discover ESP32

    Args:
        timeout: Seconds to wait for response
        max_retries: Number of retry attempts

    Returns:
        (ip_address, port) or (None, None)

    Example:
        ip, port = discover_esp32()
        if ip:
            print(f"Found ESP32 at {ip}:{port}")
    """
    discovery = ESP32Discovery(timeout=timeout)
    return discovery.discover_with_retry(max_retries=max_retries)


def save_to_config(ip: str, port: int, config_file="system_config.json"):
    """Save discovered IP to config file"""
    try:
        # Read existing config
        config = {}
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except:
            pass

        # Update IP and port
        config['pillbox_ip'] = ip
        config['pillbox_port'] = port

        # Write back
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"  [Saved] Saved IP to {config_file}")
        return True
    except Exception as e:
        print(f"  [Warning] Failed to save config: {e}")
        return False


def load_from_config(config_file="system_config.json") -> Tuple[Optional[str], Optional[int]]:
    """Load IP from config file as fallback"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('pillbox_ip'), config.get('pillbox_port', 8080)
    except:
        return None, None


# Test function
if __name__ == "__main__":
    print("=" * 60)
    print("ESP32 UDP Auto-Discovery Test")
    print("=" * 60)
    print("\nMake sure:")
    print("  1. ESP32 is powered on and connected to WiFi")
    print("  2. ESP32 and computer are on the same network")
    print("  3. ESP32 is running the UDP discovery listener")
    print("\nStarting discovery...\n")

    ip, port = discover_esp32(timeout=3, max_retries=3)

    print("\n" + "=" * 60)
    if ip:
        print(f"[Success] SUCCESS! Found ESP32 at {ip}:{port}")

        # Save to config
        if save_to_config(ip, port):
            print(f"[Success] Configuration saved")

        print("\nYou can now use this IP in your Python programs:")
        print(f"  from simple_host_sender import SimplePillboxCommunicator")
        print(f"  comm = SimplePillboxCommunicator('{ip}', {port})")

    else:
        print("[Failed] FAILED to find ESP32")
        print("\nTroubleshooting:")
        print("  1. Check ESP32 serial monitor - is it connected to WiFi?")
        print("  2. Verify ESP32 IP address from serial monitor")
        print("  3. Make sure firewall is not blocking UDP port 8888")
        print("  4. Check that ESP32 and computer are on same network")
        print("  5. Try manually setting IP in system_config.json")

        # Try to load from config as fallback
        print("\nChecking config file for saved IP...")
        config_ip, config_port = load_from_config()
        if config_ip:
            print(f"  Found saved IP in config: {config_ip}:{config_port}")
            print(f"  You can try using this IP if it hasn't changed")

    print("=" * 60)
