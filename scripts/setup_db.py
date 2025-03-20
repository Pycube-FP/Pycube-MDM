#!/usr/bin/env python3
import os
import sys
import random
from datetime import datetime, timedelta
import mysql.connector
from dotenv import load_dotenv

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.db_service import DBService
from models.device import Device
from models.location import Location
from models.movement import Movement

# Load environment variables from .env file
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to MySQL server without specifying database
        conn = mysql.connector.connect(
            host=os.environ.get('RDS_HOST', 'localhost'),
            port=int(os.environ.get('RDS_PORT', 3306)),
            user=os.environ.get('RDS_USER', 'root'),
            password=os.environ.get('RDS_PASSWORD', 'password')
        )
        
        cursor = conn.cursor()
        
        # Get the database name from environment
        db_name = os.environ.get('RDS_DB', 'pycube_mdm')
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database '{db_name}' created or already exists.")
        
        # Close connection
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

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
    
    # Common department staff roles
    staff_roles = [
        "Nurse", "Doctor", "Technician", "Administrator", "Specialist", 
        "Resident", "Intern", "Surgeon", "Anesthesiologist", "Radiologist"
    ]
    
    staff_names = [
        "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
        "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson",
        "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King",
        "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter"
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
        
        # Generate serial number and RFID tag
        serial_number = f"C{random.randint(10000000, 99999999)}PYCUB"
        rfid_tag = f"RFID-{random.randint(1000000, 9999999)}"
        
        # Assign to a staff member if in-use
        assigned_to = None
        if status == "In-Use":
            role = random.choice(staff_roles)
            name = random.choice(staff_names)
            assigned_to = f"{role} {name}"
        
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
            status=status,
            location_id=location_id,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date
        )
        
        try:
            device_id = db_service.create_device(device)
            device_ids.append(device_id)
            print(f"Created device: {device.model} with ID: {device_id}")
        except Exception as e:
            print(f"Error creating device {device.model}: {e}")
    
    return device_ids

def create_sample_movements(db_service, device_ids, location_ids):
    """Create sample movement records for devices"""
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
    
    # Generate random movements for the past 30 days
    now = datetime.now()
    
    movement_count = 0
    for device in devices:
        # Random number of movements (0-5) for each device
        num_movements = random.randint(0, 5)
        
        for i in range(num_movements):
            # Random timestamp in the past 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            timestamp = now - timedelta(days=days_ago, hours=hours_ago)
            
            # Random location with reader
            location = random.choice(reader_locations)
            
            # Random direction (IN or OUT)
            direction = random.choice(['IN', 'OUT'])
            
            movement = Movement(
                device_id=device['id'],
                rfid_tag=device['rfid_tag'],
                reader_id=location['reader_id'],
                location_id=location['id'],
                direction=direction,
                timestamp=timestamp
            )
            
            try:
                movement_id = db_service.record_movement(movement)
                movement_count += 1
                print(f"Created movement record for device {device['id']}: {direction} at {timestamp}")
            except Exception as e:
                print(f"Error creating movement for device {device['id']}: {e}")
    
    print(f"Created {movement_count} movement records")

def main():
    """Main function to set up the database and populate with sample data"""
    print("Starting database setup...")
    
    # Create database if it doesn't exist
    if not create_database():
        print("Failed to create database. Exiting.")
        return False
    
    # Initialize DB service
    db_service = DBService()
    
    # Create tables
    try:
        db_service.initialize_db()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False
    
    # Create sample data
    print("\nCreating sample locations...")
    location_ids = create_sample_locations(db_service)
    
    print("\nCreating sample devices...")
    device_ids = create_sample_devices(db_service, location_ids, count=50)
    
    print("\nCreating sample movement records...")
    create_sample_movements(db_service, device_ids, location_ids)
    
    print("\nDatabase setup complete!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 