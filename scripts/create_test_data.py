#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
import uuid

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import DBService
from models.device import Device
from models.nurse import Nurse
from models.location import Location

def format_date(date):
    """Return the date object as is, since the database expects datetime objects"""
    return date if date else None

def create_test_data():
    """Create test data in the database"""
    db_service = DBService()
    
    print("Creating test data...")
    
    # Create test locations
    locations = [
        Location(
            name="Emergency Department",
            type="Department",
            building="Main Building",
            floor="1st Floor",
            has_reader=True,
            reader_id="ED-READER-001"
        ),
        Location(
            name="ICU",
            type="Department",
            building="Main Building",
            floor="2nd Floor",
            has_reader=True,
            reader_id="ICU-READER-001"
        ),
        Location(
            name="Medical/Surgical Unit",
            type="Department",
            building="Main Building",
            floor="3rd Floor",
            has_reader=True,
            reader_id="MSU-READER-001"
        )
    ]
    
    location_ids = []
    for location in locations:
        try:
            location_id = db_service.create_location(location)
            location_ids.append(location_id)
            print(f"Created location: {location.name}")
        except Exception as e:
            print(f"Error creating location {location.name}: {e}")
    
    # Create test nurses
    nurses = [
        Nurse(
            badge_id="N1001",
            first_name="John",
            last_name="Smith",
            department="Emergency Department",
            shift="Day"
        ),
        Nurse(
            badge_id="N1002",
            first_name="Sarah",
            last_name="Johnson",
            department="ICU",
            shift="Night"
        ),
        Nurse(
            badge_id="N1003",
            first_name="Michael",
            last_name="Brown",
            department="Medical/Surgical Unit",
            shift="Evening"
        ),
        Nurse(
            badge_id="N1004",
            first_name="Emily",
            last_name="Davis",
            department="Emergency Department",
            shift="Day"
        ),
        Nurse(
            badge_id="N1005",
            first_name="David",
            last_name="Wilson",
            department="ICU",
            shift="Night"
        ),
        Nurse(
            badge_id="N1006",
            first_name="Jennifer",
            last_name="Lee",
            department="Medical/Surgical Unit",
            shift="Day"
        )
    ]
    
    nurse_ids = []
    for nurse in nurses:
        try:
            nurse_id = db_service.create_nurse(nurse)
            nurse_ids.append(nurse_id)
            print(f"Created nurse: {nurse.first_name} {nurse.last_name}")
        except Exception as e:
            print(f"Error creating nurse {nurse.first_name} {nurse.last_name}: {e}")
    
    # Create test devices with various EOL statuses
    current_date = datetime.now()
    devices = [
        Device(
            serial_number="IP14-001",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID001",
            barcode="BC001",
            status="Available",
            location_id=location_ids[0],
            purchase_date=format_date(current_date - timedelta(days=365*2)),  # 2 years old
            last_maintenance_date=format_date(current_date - timedelta(days=7)),
            eol_date=format_date(current_date + timedelta(days=365)),  # 1 year until EOL
            eol_status="Active",
            eol_notes="Device in good condition, regular maintenance performed"
        ),
        Device(
            serial_number="IP14-002",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID002",
            barcode="BC002",
            status="Available",
            location_id=location_ids[1],
            purchase_date=format_date(current_date - timedelta(days=365*3)),  # 3 years old
            last_maintenance_date=format_date(current_date - timedelta(days=30)),
            eol_date=format_date(current_date + timedelta(days=90)),  # 90 days until EOL
            eol_status="Warning",
            eol_notes="Approaching end of life, plan for replacement"
        ),
        Device(
            serial_number="IP14-003",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID003",
            barcode="BC003",
            status="Available",
            location_id=location_ids[2],
            purchase_date=format_date(current_date - timedelta(days=365*3.5)),  # 3.5 years old
            last_maintenance_date=format_date(current_date - timedelta(days=60)),
            eol_date=format_date(current_date + timedelta(days=30)),  # 30 days until EOL
            eol_status="Critical",
            eol_notes="Critical: Device needs immediate replacement planning"
        ),
        Device(
            serial_number="IP14-004",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID004",
            barcode="BC004",
            status="Available",
            location_id=location_ids[0],
            purchase_date=format_date(current_date - timedelta(days=365*4)),  # 4 years old
            last_maintenance_date=format_date(current_date - timedelta(days=90)),
            eol_date=format_date(current_date - timedelta(days=30)),  # 30 days past EOL
            eol_status="Expired",
            eol_notes="Device has exceeded its end-of-life date, requires immediate replacement"
        ),
        Device(
            serial_number="IP14-005",
            model="iPhone 15",  # Newer model
            manufacturer="Apple",
            rfid_tag="RFID005",
            barcode="BC005",
            status="Available",
            location_id=location_ids[1],
            purchase_date=format_date(current_date - timedelta(days=30)),  # Just 30 days old
            last_maintenance_date=format_date(current_date - timedelta(days=7)),
            eol_date=format_date(current_date + timedelta(days=365*3)),  # 3 years until EOL
            eol_status="Active",
            eol_notes="New device, recently deployed"
        )
    ]
    
    for device in devices:
        try:
            device_id = db_service.create_device(device)
            print(f"Created device: {device.serial_number}")
        except Exception as e:
            print(f"Error creating device {device.serial_number}: {e}")
    
    print("\nTest data creation completed!")
    print("Summary:")
    print(f"- Created {len(location_ids)} locations")
    print(f"- Created {len(nurse_ids)} nurses")
    print(f"- Created {len(devices)} devices (all in Available status)")
    print("\nYou can now start assigning devices to nurses!")

if __name__ == "__main__":
    create_test_data() 