#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
import uuid
import random
import pytz

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import DBService
from models.device import Device
from models.nurse import Nurse
from models.location import Location
from models.hospital import Hospital
from models.reader import Reader
from models.reader_event import ReaderEvent
from models.rfid_alert import RFIDAlert

# Configure timezone
TIMEZONE = pytz.timezone('America/New_York')

def get_current_est_time():
    """Get current time in Eastern Time"""
    return datetime.now(TIMEZONE)

def format_date(date):
    """Return the date object as is, since the database expects datetime objects"""
    if not date:
        return None
    if isinstance(date, datetime) and not date.tzinfo:
        # If date has no timezone info, assume it's in EST
        return TIMEZONE.localize(date)
    return date

def create_test_data():
    """Create test data in the database"""
    db_service = DBService()
    
    # Create a hospital
    hospital = Hospital(
        name="BayCare Main Hospital",
        code="BCH001",
        city="Tampa",
        state="FL",
        zip_code="33607",
        created_at=get_current_est_time(),
        updated_at=get_current_est_time()
    )
    hospital_id = db_service.create_hospital(hospital)
    print(f"Created hospital: {hospital.name}")

    # Create two locations
    locations = []
    location_names = ["Emergency Room", "ICU"]
    for name in location_names:
        location = Location(
            name=name,
            type="Department",
            building="Main Building",
            floor="1st Floor",
            room=name,
            hospital_id=hospital_id,
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        )
        location_id = db_service.create_location(location)
        locations.append({"id": location_id, "name": name})
        print(f"Created location: {name}")

    # Create one reader with two antennas
    reader_code = "FX96006B6035"
    for i, location in enumerate(locations, 1):
        reader = Reader(
            reader_code=reader_code,
            antenna_number=i,
            name=f"Reader {reader_code} Antenna {i}",
            status="Active",
            hospital_id=hospital_id,
            location_id=location["id"],
            last_heartbeat=get_current_est_time(),
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        )
        db_service.create_reader(reader)
        print(f"Created reader {reader_code} antenna {i} in {location['name']}")

    # Create one device
    device = Device(
        serial_number="iPhone14-001",
        model="iPhone 14",
        manufacturer="Apple",
        rfid_tag="200000001192024000022132",
        status="In-Facility",
        hospital_id=hospital_id,
        location_id=locations[0]["id"],  # Initially in Emergency Room
        purchase_date=get_current_est_time(),
        eol_status="Active",
        created_at=get_current_est_time(),
        updated_at=get_current_est_time()
    )
    device_id = db_service.create_device(device)
    print(f"Created device: {device.model} with RFID tag {device.rfid_tag}")

    # Create test RFID alerts
    current_time = get_current_est_time()
    for i in range(3):
        # Alternate between locations for test alerts
        location = locations[i % 2]
        alert_time = current_time - timedelta(hours=i)
        
        alert = RFIDAlert(
            device_id=device_id,
            reader_code=reader_code,
            antenna_number=(i % 2) + 1,
            rfid_tag=device.rfid_tag,
            hospital_id=hospital_id,
            location_id=location["id"],
            timestamp=alert_time,
            created_at=alert_time,
            updated_at=alert_time
        )
        
        try:
            db_service.record_movement(alert)
            print(f"Created test alert at {alert_time.strftime('%Y-%m-%d %H:%M:%S %Z')} in {location['name']}")
        except Exception as e:
            print(f"Error creating test alert: {e}")

    print("\nTest data creation completed!")
    print("Summary:")
    print(f"- Created hospital: {hospital.name}")
    print(f"- Created {len(locations)} locations: {', '.join(l['name'] for l in locations)}")
    print(f"- Created reader {reader_code} with 2 antennas")
    print(f"- Created device: {device.model} with RFID tag {device.rfid_tag}")
    print(f"- Created 3 test alerts")

if __name__ == "__main__":
    create_test_data() 