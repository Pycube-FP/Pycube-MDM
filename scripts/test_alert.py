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

    # Create four devices with sequential RFID tags
    devices = []
    base_rfid = "20000000119202400002213"
    
    for i in range(4):
        rfid_tag = f"{base_rfid}{i+2}"  # Tags from 200000001192024000022132 to 200000001192024000022135
        device = Device(
            serial_number=f"iPhone14-00{i+1}",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag=rfid_tag,
            status="In-Facility",
            hospital_id=hospital_id,
            location_id=locations[0]["id"],  # Initially in Emergency Room
            purchase_date=get_current_est_time(),
            eol_status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        )
        device_id = db_service.create_device(device)
        devices.append({"id": device_id, "model": device.model, "rfid_tag": device.rfid_tag})
        print(f"Created device: {device.model} (SN: {device.serial_number}) with RFID tag {device.rfid_tag}")

    print("\nTest data creation completed!")
    print("Summary:")
    print(f"- Created hospital: {hospital.name}")
    print(f"- Created {len(locations)} locations: {', '.join(l['name'] for l in locations)}")
    print(f"- Created reader {reader_code} with 2 antennas")
    print(f"- Created {len(devices)} devices with sequential RFID tags")
    for device in devices:
        print(f"  - {device['model']} with RFID tag {device['rfid_tag']}")

if __name__ == "__main__":
    create_test_data() 