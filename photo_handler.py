"""
Photo Handler Module for ESP32-CAM Integration
Receives and saves photos from ESP32 medication reminder system
"""

import os
import base64
from datetime import datetime


class PhotoHandler:
    """Handle photo data from ESP32-CAM"""

    def __init__(self, base_dir="record"):
        """
        Initialize photo handler

        Args:
            base_dir: Base directory for storing photos (default: 'record')
        """
        self.base_dir = base_dir
        self.ensure_base_dir()

    def ensure_base_dir(self):
        """Create base directory if it doesn't exist"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            print(f"[PHOTO] Created base directory: {self.base_dir}")

    def handle_photo_data(self, message):
        """
        Process photo data message from ESP32

        Args:
            message: Dict containing photo data
                     Format: {
                         "type": "photo_data",
                         "box": 3,
                         "filename": "box3_Aspirin_20251202_143000_1.jpg",
                         "data": "base64_encoded_data...",
                         "size": 12345
                     }

        Returns:
            bool: True if photo saved successfully, False otherwise
        """
        try:
            box_num = message.get("box")
            filename = message.get("filename")
            base64_data = message.get("data")
            size = message.get("size")

            if not all([box_num, filename, base64_data]):
                print("[PHOTO] ERROR: Missing required fields in message")
                return False

            # Parse filename: boxN_MedName_YYYYMMDD_HHMMSS_M.jpg
            parts = filename.replace('.jpg', '').split('_')
            if len(parts) < 5:
                print(f"[PHOTO] ERROR: Invalid filename format: {filename}")
                return False

            med_name = parts[1]      # e.g., "Aspirin"
            date_str = parts[2]      # e.g., "20251202"
            time_str = parts[3]      # e.g., "143000"
            photo_num = parts[4]     # e.g., "1"

            # Create date folder: record/YYYY-MM-DD/
            year = date_str[0:4]
            month = date_str[4:6]
            day = date_str[6:8]
            date_folder = f"{year}-{month}-{day}"

            record_dir = os.path.join(self.base_dir, date_folder)
            os.makedirs(record_dir, exist_ok=True)

            # Save filename: MedicationName_HHMMSS_N.jpg
            save_filename = f"{med_name}_{time_str}_{photo_num}.jpg"
            save_path = os.path.join(record_dir, save_filename)

            # Decode base64 and save
            photo_bytes = base64.b64decode(base64_data)
            with open(save_path, 'wb') as f:
                f.write(photo_bytes)

            print(f"[PHOTO] Saved: {save_path} ({len(photo_bytes)} bytes)")
            return True

        except base64.binascii.Error as e:
            print(f"[PHOTO] ERROR: Base64 decode failed: {e}")
            return False
        except IOError as e:
            print(f"[PHOTO] ERROR: File write failed: {e}")
            return False
        except Exception as e:
            print(f"[PHOTO] ERROR: Unexpected error: {e}")
            return False

    def get_photo_count(self, date_str=None):
        """
        Get count of photos for a specific date

        Args:
            date_str: Date string in format "YYYY-MM-DD" (default: today)

        Returns:
            int: Number of photos for the date
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        record_dir = os.path.join(self.base_dir, date_str)
        if not os.path.exists(record_dir):
            return 0

        photos = [f for f in os.listdir(record_dir) if f.endswith('.jpg')]
        return len(photos)

    def get_recent_photos(self, count=10):
        """
        Get list of recent photos

        Args:
            count: Number of recent photos to return

        Returns:
            list: List of photo file paths
        """
        all_photos = []

        # Walk through all date folders
        if not os.path.exists(self.base_dir):
            return []

        for date_folder in sorted(os.listdir(self.base_dir), reverse=True):
            folder_path = os.path.join(self.base_dir, date_folder)
            if not os.path.isdir(folder_path):
                continue

            photos = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.endswith('.jpg')
            ]

            # Sort by modification time
            photos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            all_photos.extend(photos)

            if len(all_photos) >= count:
                break

        return all_photos[:count]


# Example usage
if __name__ == "__main__":
    # Test photo handler
    handler = PhotoHandler()

    # Simulate ESP32 message
    test_message = {
        "type": "photo_data",
        "box": 3,
        "filename": "box3_Aspirin_20251202_143000_1.jpg",
        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",  # 1x1 pixel test image
        "size": 95
    }

    # Test saving
    if handler.handle_photo_data(test_message):
        print("Test passed!")

        # Test photo count
        count = handler.get_photo_count()
        print(f"Photos today: {count}")

        # Test recent photos
        recent = handler.get_recent_photos(5)
        print(f"Recent photos: {len(recent)}")
        for photo in recent:
            print(f"  - {photo}")
    else:
        print("Test failed!")
