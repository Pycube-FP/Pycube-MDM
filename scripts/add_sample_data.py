#!/usr/bin/env python3
import os
import sys
import random
from datetime import datetime, timedelta
import uuid
from dotenv import load_dotenv

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import DBService
from models.device import Device
from models.location import Location
from models.nurse import Nurse
from models.device_assignment import DeviceAssignment
from models.rfid_alert import RFIDAlert
from models.reader_event import ReaderEvent

# Load environment variables from .env file
load_dotenv()

def create_sample_locations(db_service):
    """Create sample hospital locations with RFID readers"""
    locations = [
        # Main entrances/exits with readers
        Location(
            name="Main Entrance",
            type="Entrance",
            building="Main Building",
            floor="1",
            room="Lobby",
            has_reader=True,
            reader_id="READER001"
        ),
        Location(
            name="Emergency Exit",
            type="Exit",
            building="Main Building",
            floor="1",
            room="East Wing",
            has_reader=True,
            reader_id="READER002"
        ),
        Location(
            name="Staff Entrance",
            type="Entrance",
            building="Main Building",
            floor="1",
            room="North Wing",
            has_reader=True,
            reader_id="READER003"
        ),
        Location(
            name="Loading Dock",
            type="Exit",
            building="Service Building",
            floor="1",
            room="Dock Area",
            has_reader=True,
            reader_id="READER004"
        ),
        
        # Departments without readers
        Location(
            name="Emergency Department",
            type="Department",
            building="Main Building",
            floor="1",
            room="South Wing",
            has_reader=False
        ),
        Location(
            name="ICU",
            type="Department",
            building="Main Building",
            floor="2",
            room="East Wing",
            has_reader=False
        ),
        Location(
            name="Cardiology",
            type="Department",
            building="Main Building",
            floor="3",
            room="West Wing",
            has_reader=False
        ),
        Location(
            name="Radiology",
            type="Department",
            building="Main Building",
            floor="2",
            room="Center Wing",
            has_reader=False
        ),
        Location(
            name="Pharmacy",
            type="Department",
            building="Main Building",
            floor="1",
            room="South-East Corner",
            has_reader=False
        ),
        Location(
            name="Orthopedics",
            type="Department",
            building="Medical Building",
            floor="2",
            room="East Wing",
            has_reader=False
        )
    ]
    
    location_ids = []
    for location in locations:
        try:
            location_id = db_service.create_location(location)
            location_ids.append(location_id)
            print(f"Created location: {location.name} with ID: {location_id}")
        except Exception as e:
            print(f"Error creating location {location.name}: {e}")
    
    return location_ids

def create_sample_nurses(db_service, count=20):
    """Create sample nurse records"""
    departments = ["Emergency", "ICU", "Cardiology", "Radiology", "Orthopedics"]
    shifts = ["Morning", "Evening", "Night"]
    first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
                  "Harper", "Evelyn", "Abigail", "Emily", "Elizabeth", "Sofia", "Avery", "Ella", "Scarlett", "Grace"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                 "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    
    nurse_ids = []
    for i in range(1, count + 1):
        nurse = Nurse(
            badge_id=f"N{i:04d}",
            first_name=random.choice(first_names),
            last_name=random.choice(last_names),
            department=random.choice(departments),
            shift=random.choice(shifts)
        )
        
        try:
            nurse_id = db_service.create_nurse(nurse)
            nurse_ids.append(nurse_id)
            print(f"Created nurse: {nurse.first_name} {nurse.last_name} with badge ID: {nurse.badge_id}")
        except Exception as e:
            print(f"Error creating nurse: {e}")
    
    return nurse_ids

def create_sample_devices(db_service, location_ids, count=50):
    """Create sample iPhone devices from iPhone 12 to iPhone 16"""
    # iPhone models and storage options
    iphone_models = [
        "iPhone 12", "iPhone 12 Mini", "iPhone 12 Pro", "iPhone 12 Pro Max",
        "iPhone 13", "iPhone 13 Mini", "iPhone 13 Pro", "iPhone 13 Pro Max",
        "iPhone 14", "iPhone 14 Plus", "iPhone 14 Pro", "iPhone 14 Pro Max",
        "iPhone 15", "iPhone 15 Plus", "iPhone 15 Pro", "iPhone 15 Pro Max",
        "iPhone 16", "iPhone 16 Plus", "iPhone 16 Pro", "iPhone 16 Pro Max"
    ]
    
    storage_options = ["128GB", "256GB", "512GB", "1TB"]
    colors = ["Black", "White", "Blue", "Green", "Red", "Gold", "Silver", "Graphite", "Pacific Blue", "Sierra Blue"]
    
    # Status options with weighted probabilities
    status_options = [
        ("Available", 0.5),   # 50% chance of being available
        ("In-Use", 0.3),      # 30% chance of being in use
        ("Maintenance", 0.1), # 10% chance of being in maintenance
        ("Missing", 0.1)      # 10% chance of being missing
    ]
    
    device_ids = []
    for i in range(1, count + 1):
        # Generate device details
        model = random.choice(iphone_models)
        storage = random.choice(storage_options)
        color = random.choice(colors)
        
        # Create a weighted random status selection
        status = random.choices(
            [status for status, _ in status_options],
            weights=[weight for _, weight in status_options],
            k=1
        )[0]
        
        # Generate serial number, RFID tag, and barcode
        serial_number = f"C{random.randint(10000000, 99999999)}PYCUB"
        rfid_tag = f"RFID-{random.randint(1000000, 9999999)}"
        # Generate barcode in format BC-YYMM-XXXX where YY=year, MM=month, XXXX=sequential number
        barcode = f"BC-{datetime.now().strftime('%y%m')}-{i:04d}"
        
        # Random location if available or in-use, None if missing
        location_id = None
        if status in ["Available", "In-Use"]:
            location_id = random.choice(location_ids)
        
        # Generate random purchase date in the last 4 years
        days_ago = random.randint(30, 4*365)  # Between 1 month and 4 years ago
        purchase_date = (datetime.now() - timedelta(days=days_ago)).date()
        
        # Generate random maintenance date for some devices
        last_maintenance_date = None
        if random.random() < 0.7:  # 70% chance of having maintenance record
            maintenance_days_ago = random.randint(1, min(days_ago, 365))  # Within the last year or since purchase
            last_maintenance_date = (datetime.now() - timedelta(days=maintenance_days_ago)).date()
        
        # Create device
        device = Device(
            serial_number=serial_number,
            model=f"{model} {storage} {color}",
            manufacturer="Apple",
            rfid_tag=rfid_tag,
            barcode=barcode,
            status=status,
            location_id=location_id,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date
        )
        
        try:
            device_id = db_service.create_device(device)
            device_ids.append(device_id)
            print(f"Created device: {device.model} with ID: {device_id}, Barcode: {barcode}")
        except Exception as e:
            print(f"Error creating device {device.model}: {e}")
    
    return device_ids

def create_sample_reader_events(db_service, device_ids, location_ids):
    """Create sample reader events for devices"""
    # Get devices that have location
    devices = []
    for device_id in device_ids:
        device = db_service.get_device(device_id)
        if device and device['status'] != 'Missing':
            devices.append(device)
    
    # Get locations with readers
    reader_locations = []
    for location_id in location_ids:
        location = db_service.get_location(location_id)
        if location and location['has_reader']:
            reader_locations.append(location)
    
    # Generate random reader events for the past 30 days
    now = datetime.now()
    
    event_count = 0
    for device in devices:
        # Random number of events (0-5) for each device
        num_events = random.randint(0, 5)
        
        for i in range(num_events):
            # Random timestamp in the past 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            timestamp = now - timedelta(days=days_ago, hours=hours_ago)
            
            # Random location with reader
            location = random.choice(reader_locations)
            
            event = ReaderEvent(
                device_id=device['id'],
                rfid_tag=device['rfid_tag'],
                reader_id=location['reader_id'],
                location_id=location['id'],
                timestamp=timestamp
            )
            
            try:
                event_id = db_service.record_movement(event)
                event_count += 1
                print(f"Created reader event for device {device['id']} at {timestamp}")
            except Exception as e:
                print(f"Error creating reader event for device {device['id']}: {e}")
    
    print(f"Created {event_count} reader events")

def create_sample_device_assignments(db_service, device_ids, nurse_ids):
    """Create sample device assignments"""
    # Get available devices
    available_devices = []
    for device_id in device_ids:
        device = db_service.get_device(device_id)
        if device and device['status'] == 'Available':
            available_devices.append(device)
    
    # Randomly assign some devices to nurses
    assignment_count = min(len(available_devices), len(nurse_ids))
    assignments = random.sample(list(zip(available_devices, nurse_ids)), assignment_count)
    
    for device, nurse_id in assignments:
        # Create assignment with random start time in the past week
        hours_ago = random.randint(1, 168)  # Up to 1 week ago
        assigned_at = datetime.now() - timedelta(hours=hours_ago)
        
        assignment = DeviceAssignment(
            device_id=device['id'],
            nurse_id=nurse_id,
            assigned_at=assigned_at,
            status='Active'
        )
        
        try:
            assignment_id = db_service.create_device_assignment(assignment)
            # Update device status to In-Use
            db_service.update_device_status(device['id'], 'In-Use')
            print(f"Created device assignment: Device {device['id']} assigned to nurse {nurse_id}")
        except Exception as e:
            print(f"Error creating device assignment: {e}")

def main():
    """Main function to populate the database with sample data"""
    print("Starting sample data creation...")
    
    # Initialize DB service
    db_service = DBService()
    
    print("\nCreating sample locations...")
    location_ids = create_sample_locations(db_service)
    
    print("\nCreating sample nurses...")
    nurse_ids = create_sample_nurses(db_service)
    
    print("\nCreating sample devices...")
    device_ids = create_sample_devices(db_service, location_ids)
    
    print("\nCreating sample device assignments...")
    create_sample_device_assignments(db_service, device_ids, nurse_ids)
    
    print("\nCreating sample reader events...")
    create_sample_reader_events(db_service, device_ids, location_ids)
    
    print("\nSample data creation complete!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 