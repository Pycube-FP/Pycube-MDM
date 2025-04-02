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
    
    # Create all 16 hospitals from the create_test_data.py list
    hospitals = [
        Hospital(
            name="BayCare Alliant Hospital",
            code="BAH",
            address="601 Main St",
            city="Tampa",
            state="FL",
            zip_code="33601",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="BayCare Hospital Wesley Chapel",
            code="BHWC",
            address="602 Oak Ave",
            city="Wesley Chapel",
            state="FL",
            zip_code="33544",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Bartow Regional Medical Center",
            code="BRMC",
            address="603 Pine Rd",
            city="Bartow",
            state="FL",
            zip_code="33830",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Mease Countryside Hospital",
            code="MCH",
            address="604 Elm St",
            city="Safety Harbor",
            state="FL",
            zip_code="34695",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Mease Dunedin Hospital",
            code="MDH",
            address="605 Maple Dr",
            city="Dunedin",
            state="FL",
            zip_code="34698",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Morton Plant Hospital",
            code="MPH",
            address="606 Oak St",
            city="Clearwater",
            state="FL",
            zip_code="33756",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Morton Plant North Bay Hospital",
            code="MPNBH",
            address="607 Pine St",
            city="New Port Richey",
            state="FL",
            zip_code="34652",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="South Florida Baptist Hospital",
            code="SFBH",
            address="608 Main St",
            city="Plant City",
            state="FL",
            zip_code="33563",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Anthony's Hospital",
            code="SAH",
            address="609 Beach Dr",
            city="St. Petersburg",
            state="FL",
            zip_code="33701",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Joseph's Hospital",
            code="SJH",
            address="610 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Joseph's Children's Hospital",
            code="SJCH",
            address="611 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Joseph's Women's Hospital",
            code="SJWH",
            address="612 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Joseph's Hospital-North",
            code="SJHN",
            address="613 Van Dyke Rd",
            city="Lutz",
            state="FL",
            zip_code="33558",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="St. Joseph's Hospital-South",
            code="SJHS",
            address="614 Big Bend Rd",
            city="Riverview",
            state="FL",
            zip_code="33578",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Winter Haven Hospital",
            code="WHH",
            address="615 First St N",
            city="Winter Haven",
            state="FL",
            zip_code="33881",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        ),
        Hospital(
            name="Winter Haven Women's Hospital",
            code="WHWH",
            address="616 First St N",
            city="Winter Haven",
            state="FL",
            zip_code="33881",
            status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        )
    ]
    
    hospital_ids = []
    for hospital in hospitals:
        try:
            hospital_id = db_service.create_hospital(hospital)
            hospital_ids.append({"id": hospital_id, "name": hospital.name})
            print(f"Created hospital: {hospital.name}")
        except Exception as e:
            print(f"Error creating hospital {hospital.name}: {e}")
    
    # Create exactly 2 locations for each hospital from the location_names list
    location_names = [
        "Emergency Department",
        "Main Entrance"
    ]
    
    all_locations = []
    for hospital in hospital_ids:
        hospital_locations = []
        for i, name in enumerate(location_names):
            location = Location(
                name=f"{name}",
                type="Department" if i == 0 else "Entrance",
                building="Main Building",
                floor=f"{(i % 3) + 1}st Floor",
                room=f"{100 + i}",
                hospital_id=hospital["id"],
                created_at=get_current_est_time(),
                updated_at=get_current_est_time()
            )
            location_id = db_service.create_location(location)
            hospital_locations.append({"id": location_id, "name": name})
            print(f"Created location: {name} at {hospital['name']}")
        all_locations.append({"hospital": hospital, "locations": hospital_locations})
    
    # Create one reader with two antennas for each hospital
    # Each reader will have a unique reader_code
    base_reader_code = "FX96006B6035"
    
    for i, hospital_data in enumerate(all_locations):
        # Create a unique reader_code for this hospital by incrementing the last digit
        last_digit = 5 + i  # Start with 5 and increment for each hospital
        reader_code = base_reader_code[:-1] + str(last_digit)
        
        # Create one reader with two antennas for this hospital
        for antenna_number, location in enumerate(hospital_data["locations"], 1):
            reader = Reader(
                reader_code=reader_code,
                antenna_number=antenna_number,
                name=f"Reader {reader_code} Antenna {antenna_number}",
                status="Active",
                hospital_id=hospital_data["hospital"]["id"],
                location_id=location["id"],
                last_heartbeat=get_current_est_time(),
                created_at=get_current_est_time(),
                updated_at=get_current_est_time()
            )
            db_service.create_reader(reader)
            print(f"Created reader {reader_code} antenna {antenna_number} for {location['name']} at {hospital_data['hospital']['name']}")
    
    # Create 100 devices with sequential RFID tags - mix of iPhone 14 and 15
    devices = []
    base_rfid = "20000000119202400002231"
    
    # Distribute devices across hospitals and their locations
    device_hospital_index = 0
    device_location_index = 0
    
    for i in range(100):
        # Calculate the hospital and location for this device
        hospital_data = all_locations[device_hospital_index]
        location = hospital_data["locations"][device_location_index]
        
        # Increment indices for next device
        device_location_index = (device_location_index + 1) % len(hospital_data["locations"])
        if device_location_index == 0:
            device_hospital_index = (device_hospital_index + 1) % len(all_locations)
        
        # Determine iPhone model
        model = "iPhone 14" if i % 3 != 0 else "iPhone 15"  # 2/3 iPhone 14, 1/3 iPhone 15
        color = random.choice(["Black", "White", "Blue", "Purple", "Red"])
        
        # Create RFID tag by incrementing from base tag
        # Calculate the numeric value of the base tag and add the increment
        if i == 0:
            # First device gets the base tag
            current_rfid = base_rfid
        else:
            # For each subsequent device, increment by 1 from the base
            # Convert base to integer, add the increment, convert back to string
            base_value = int(base_rfid)
            current_rfid = str(base_value + i)
        
        # Create serial number
        if model == "iPhone 14":
            serial_number = f"C7QDP{random.randint(1000, 9999)}G/A"
        else:
            serial_number = f"F9QXP{random.randint(1000, 9999)}G/A"
        
        # Set random status (most in facility, some temporarily out, few missing)
        status_random = random.random()
        
        status = "In-Facility"
            
        device = Device(
            serial_number=serial_number,
            model=f"{model} {random.choice(['Pro', 'Pro Max', ''])} {color}",
            manufacturer="Apple",
            rfid_tag=current_rfid,
            status=status,
            hospital_id=hospital_data["hospital"]["id"],
            location_id=location["id"],
            purchase_date=get_current_est_time() - timedelta(days=random.randint(30, 365)),
            eol_status="Active",
            created_at=get_current_est_time(),
            updated_at=get_current_est_time()
        )
        device_id = db_service.create_device(device)
        devices.append({
            "id": device_id, 
            "model": device.model, 
            "rfid_tag": device.rfid_tag,
            "hospital": hospital_data["hospital"]["name"],
            "location": location["name"]
        })
        print(f"Created device: {device.model} (SN: {device.serial_number}) with RFID tag {device.rfid_tag}")

    print("\nTest data creation completed!")
    print("Summary:")
    print(f"- Created {len(hospitals)} hospitals")
    for hospital in hospital_ids:
        print(f"  - {hospital['name']}")
    print(f"- Created {len(location_names) * len(hospitals)} locations ({len(location_names)} per hospital)")
    print(f"- Created {len(hospitals)} readers with 2 antennas each (1 reader per hospital)")
    print(f"- Created {len(devices)} devices with sequential RFID tags")
    print(f"  - {len([d for d in devices if 'iPhone 14' in d['model']])} iPhone 14 devices")
    print(f"  - {len([d for d in devices if 'iPhone 15' in d['model']])} iPhone 15 devices")

if __name__ == "__main__":
    create_test_data() 