#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timedelta
import uuid
import random

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

def format_date(date):
    """Return the date object as is, since the database expects datetime objects"""
    return date if date else None

def create_test_data():
    """Create test data in the database"""
    db_service = DBService()
    
    print("Creating test data...")
    
    # Create test hospitals
    hospitals = [
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="BayCare Alliant Hospital",
            code="BAH",
            address="601 Main St",
            city="Tampa",
            state="FL",
            zip_code="33601",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="BayCare Hospital Wesley Chapel",
            code="BHWC",
            address="602 Oak Ave",
            city="Wesley Chapel",
            state="FL",
            zip_code="33544",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Bartow Regional Medical Center",
            code="BRMC",
            address="603 Pine Rd",
            city="Bartow",
            state="FL",
            zip_code="33830",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Mease Countryside Hospital",
            code="MCH",
            address="604 Elm St",
            city="Safety Harbor",
            state="FL",
            zip_code="34695",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Mease Dunedin Hospital",
            code="MDH",
            address="605 Maple Dr",
            city="Dunedin",
            state="FL",
            zip_code="34698",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Morton Plant Hospital",
            code="MPH",
            address="606 Oak St",
            city="Clearwater",
            state="FL",
            zip_code="33756",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Morton Plant North Bay Hospital",
            code="MPNBH",
            address="607 Pine St",
            city="New Port Richey",
            state="FL",
            zip_code="34652",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="South Florida Baptist Hospital",
            code="SFBH",
            address="608 Main St",
            city="Plant City",
            state="FL",
            zip_code="33563",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Anthony's Hospital",
            code="SAH",
            address="609 Beach Dr",
            city="St. Petersburg",
            state="FL",
            zip_code="33701",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Joseph's Hospital",
            code="SJH",
            address="610 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Joseph's Children's Hospital",
            code="SJCH",
            address="611 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Joseph's Women's Hospital",
            code="SJWH",
            address="612 MLK Blvd",
            city="Tampa",
            state="FL",
            zip_code="33607",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Joseph's Hospital-North",
            code="SJHN",
            address="613 Van Dyke Rd",
            city="Lutz",
            state="FL",
            zip_code="33558",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="St. Joseph's Hospital-South",
            code="SJHS",
            address="614 Big Bend Rd",
            city="Riverview",
            state="FL",
            zip_code="33578",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Winter Haven Hospital",
            code="WHH",
            address="615 First St N",
            city="Winter Haven",
            state="FL",
            zip_code="33881",
            status="Active"
        ),
        Hospital(
            id=str(uuid.uuid4()),  # Explicitly set ID
            name="Winter Haven Women's Hospital",
            code="WHWH",
            address="616 First St N",
            city="Winter Haven",
            state="FL",
            zip_code="33881",
            status="Active"
        )
    ]
    
    hospital_ids = []
    for hospital in hospitals:
        try:
            hospital_ids.append(hospital.id)  # Store the pre-generated ID
            db_service.create_hospital(hospital)
            print(f"Created hospital: {hospital.name}")
        except Exception as e:
            print(f"Error creating hospital {hospital.name}: {e}")
    
    # Create 5 locations for each hospital
    location_types = ["Entrance", "Exit", "Room", "Ward", "Department"]
    location_names = [
        "Emergency Department Exit",
        "Main Entrance",
        "Surgery Ward Exit",
        "ICU Department",
        "Pharmacy Exit"
    ]
    
    all_locations = []
    for hospital_id in hospital_ids:
        for i in range(5):
            location = Location(
                name=location_names[i],
                type=location_types[i],
                hospital_id=hospital_id,
                building="Main Building",
                floor=f"{i+1}st Floor"
            )
            try:
                location_id = db_service.create_location(location)
                all_locations.append({
                    'id': location_id,
                    'hospital_id': hospital_id,
                    'name': location.name
                })
                print(f"Created location: {location.name} for hospital {hospital_id}")
            except Exception as e:
                print(f"Error creating location {location.name}: {e}")
    
    # Create 2 readers for each hospital with 2-3 antennas each
    all_readers = []
    for hospital_id in hospital_ids:
        hospital_locations = [loc for loc in all_locations if loc['hospital_id'] == hospital_id]
        
        for reader_num in range(2):
            # Generate a unique identifier without the number suffix
            reader_uuid = str(uuid.uuid4())[:6]
            reader_code = f"READER-{reader_uuid}"
            num_antennas = random.randint(2, 3)
            
            for antenna_num in range(1, num_antennas + 1):
                # Assign each antenna to a different location
                location = hospital_locations[reader_num * 2 + antenna_num - 1]
                reader = Reader(
                    reader_code=reader_code,
                    antenna_number=antenna_num,
                    name=f"Reader {reader_uuid} Antenna {antenna_num}",
                    hospital_id=hospital_id,
                    location_id=location['id'],
                    status="Active",
                    last_heartbeat=datetime.now()
                )
                try:
                    reader_id = db_service.create_reader(reader)
                    all_readers.append({
                        'id': reader_id,
                        'reader_code': reader_code,
                        'antenna_number': antenna_num,
                        'location_id': location['id'],
                        'hospital_id': hospital_id
                    })
                    print(f"Created reader: {reader.name} for hospital {hospital_id}")
                except Exception as e:
                    print(f"Error creating reader {reader.name}: {e}")
    
    # Create test devices
    current_date = datetime.now()
    devices = [
        Device(
            serial_number="IP14-001",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID001",
            barcode="BC001",
            status="In-Facility",
            hospital_id=hospital_ids[0],  # BayCare Alliant Hospital
            location_id=all_locations[0]['id'],  # Emergency Department Exit
            purchase_date=format_date(current_date - timedelta(days=365*2)),
            last_maintenance_date=format_date(current_date - timedelta(days=7)),
            eol_date=format_date(current_date + timedelta(days=365)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP14-002",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID002",
            barcode="BC002",
            status="In-Facility",
            hospital_id=hospital_ids[1],  # BayCare Hospital Wesley Chapel
            location_id=all_locations[5]['id'],  # Main Entrance
            purchase_date=format_date(current_date - timedelta(days=365*3)),
            last_maintenance_date=format_date(current_date - timedelta(days=30)),
            eol_date=format_date(current_date + timedelta(days=90)),
            eol_status="Warning"
        ),
        Device(
            serial_number="IP15-001",
            model="iPhone 15",
            manufacturer="Apple",
            rfid_tag="RFID003",
            barcode="BC003",
            status="Missing",
            hospital_id=hospital_ids[2],  # Bartow Regional Medical Center
            location_id=all_locations[10]['id'],  # Surgery Ward Exit
            purchase_date=format_date(current_date - timedelta(days=30)),
            last_maintenance_date=format_date(current_date - timedelta(days=7)),
            eol_date=format_date(current_date + timedelta(days=365*3)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP15-002",
            model="iPhone 15",
            manufacturer="Apple",
            rfid_tag="RFID004",
            barcode="BC004",
            status="In-Facility",
            hospital_id=hospital_ids[3],  # Mease Countryside Hospital
            location_id=all_locations[15]['id'],  # ICU Department
            purchase_date=format_date(current_date - timedelta(days=45)),
            last_maintenance_date=format_date(current_date - timedelta(days=5)),
            eol_date=format_date(current_date + timedelta(days=365*3)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP14-003",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID005",
            barcode="BC005",
            status="Missing",
            hospital_id=hospital_ids[4],  # Mease Dunedin Hospital
            location_id=all_locations[20]['id'],  # Pharmacy Exit
            purchase_date=format_date(current_date - timedelta(days=365)),
            last_maintenance_date=format_date(current_date - timedelta(days=14)),
            eol_date=format_date(current_date + timedelta(days=365*2)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP15-003",
            model="iPhone 15",
            manufacturer="Apple",
            rfid_tag="RFID006",
            barcode="BC006",
            status="In-Facility",
            hospital_id=hospital_ids[5],  # Morton Plant Hospital
            location_id=all_locations[25]['id'],  # Emergency Department Exit
            purchase_date=format_date(current_date - timedelta(days=60)),
            last_maintenance_date=format_date(current_date - timedelta(days=10)),
            eol_date=format_date(current_date + timedelta(days=365*3)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP14-004",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID007",
            barcode="BC007",
            status="In-Facility",
            hospital_id=hospital_ids[6],  # Morton Plant North Bay Hospital
            location_id=all_locations[30]['id'],  # Main Entrance
            purchase_date=format_date(current_date - timedelta(days=365*2)),
            last_maintenance_date=format_date(current_date - timedelta(days=21)),
            eol_date=format_date(current_date + timedelta(days=180)),
            eol_status="Warning"
        ),
        Device(
            serial_number="IP15-004",
            model="iPhone 15",
            manufacturer="Apple",
            rfid_tag="RFID008",
            barcode="BC008",
            status="Missing",
            hospital_id=hospital_ids[7],  # South Florida Baptist Hospital
            location_id=all_locations[35]['id'],  # Surgery Ward Exit
            purchase_date=format_date(current_date - timedelta(days=90)),
            last_maintenance_date=format_date(current_date - timedelta(days=15)),
            eol_date=format_date(current_date + timedelta(days=365*3)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP14-005",
            model="iPhone 14",
            manufacturer="Apple",
            rfid_tag="RFID009",
            barcode="BC009",
            status="In-Facility",
            hospital_id=hospital_ids[8],  # St. Anthony's Hospital
            location_id=all_locations[40]['id'],  # ICU Department
            purchase_date=format_date(current_date - timedelta(days=365*1.5)),
            last_maintenance_date=format_date(current_date - timedelta(days=3)),
            eol_date=format_date(current_date + timedelta(days=365)),
            eol_status="Active"
        ),
        Device(
            serial_number="IP15-005",
            model="iPhone 15",
            manufacturer="Apple",
            rfid_tag="RFID010",
            barcode="BC010",
            status="In-Facility",
            hospital_id=hospital_ids[9],  # St. Joseph's Hospital
            location_id=all_locations[45]['id'],  # Pharmacy Exit
            purchase_date=format_date(current_date - timedelta(days=75)),
            last_maintenance_date=format_date(current_date - timedelta(days=1)),
            eol_date=format_date(current_date + timedelta(days=365*3)),
            eol_status="Active"
        )
    ]
    
    device_ids = []
    for device in devices:
        try:
            device_id = db_service.create_device(device)
            device_ids.append({
                'id': device_id,
                'rfid_tag': device.rfid_tag,
                'hospital_id': device.hospital_id
            })
            print(f"Created device: {device.serial_number}")
        except Exception as e:
            print(f"Error creating device {device.serial_number}: {e}")
    
    # Create reader events and RFID alerts for the past week
    for device in device_ids:
        # Get readers for this device's hospital
        hospital_readers = [r for r in all_readers if r['hospital_id'] == device['hospital_id']]
        
        # Create 3-5 events per device
        num_events = random.randint(3, 5)
        for _ in range(num_events):
            reader = random.choice(hospital_readers)
            event_time = datetime.now() - timedelta(
                days=random.randint(0, 7),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # Create RFID Alert
            rfid_alert = RFIDAlert(
                device_id=device['id'],
                reader_id=reader['id'],
                hospital_id=reader['hospital_id'],
                location_id=reader['location_id'],
                timestamp=event_time,
                reader_code=reader['reader_code'],
                antenna_number=reader['antenna_number'],
                rfid_tag=device['rfid_tag']
            )
            
            try:
                # Record the movement (this will create both reader_event and rfid_alert)
                db_service.record_movement(rfid_alert)
                print(f"Created movement event for device {device['id']} at {event_time}")
            except Exception as e:
                print(f"Error creating movement event: {e}")
    
    print("\nTest data creation completed!")
    print("Summary:")
    print(f"- Created {len(hospitals)} hospitals")
    print(f"- Created {len(all_locations)} locations")
    print(f"- Created {len(all_readers)} readers")
    print(f"- Created {len(devices)} devices")
    print(f"- Created movement events for each device")

if __name__ == "__main__":
    create_test_data() 