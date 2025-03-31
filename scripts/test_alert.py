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
    
    try:
        # Create a hospital
        hospital = Hospital(
            name='BayCare Main Hospital',
            code='BCH',  # Added required code field
            address='2985 Drew St, Clearwater, FL 33759',
            city='Clearwater',  # Added city
            state='FL',  # Added state
            zip_code='33759'  # Added zip code
        )
        hospital_id = db_service.create_hospital(hospital)
        print(f"Created hospital with ID: {hospital_id}")
        
        # Create two locations in the hospital
        location1_id = db_service.create_location({
            'name': 'Emergency Room',
            'floor': '1',
            'room': 'ER-101',
            'hospital_id': hospital_id
        })
        print(f"Created location 1 with ID: {location1_id}")
        
        location2_id = db_service.create_location({
            'name': 'ICU',
            'floor': '2',
            'room': 'ICU-201',
            'hospital_id': hospital_id
        })
        print(f"Created location 2 with ID: {location2_id}")
        
        # Create one reader with two antennas
        reader_id = db_service.create_reader({
            'reader_code': 'FX96006B6035',
            'name': 'Main Reader',
            'description': 'Two-antenna reader covering ER and ICU',
            'hospital_id': hospital_id
        })
        print(f"Created reader with ID: {reader_id}")
        
        # Create two antennas for the reader
        antenna1_id = db_service.create_antenna({
            'reader_id': reader_id,
            'antenna_number': 1,
            'location_id': location1_id,
            'name': 'ER Antenna'
        })
        print(f"Created antenna 1 with ID: {antenna1_id}")
        
        antenna2_id = db_service.create_antenna({
            'reader_id': reader_id,
            'antenna_number': 2,
            'location_id': location2_id,
            'name': 'ICU Antenna'
        })
        print(f"Created antenna 2 with ID: {antenna2_id}")
        
        # Create one device
        device_id = db_service.create_device({
            'name': 'iPhone Test Device',
            'type': 'iPhone',
            'model': 'iPhone 14',
            'serial_number': 'SN123456789',
            'rfid_tag': '200000001192024000022132',
            'status': 'In-Facility',
            'hospital_id': hospital_id,
            'location_id': location1_id  # Initially in ER
        })
        print(f"Created device with ID: {device_id}")
        
        print("Test data creation completed successfully!")
        
    except Exception as e:
        print(f"Error creating test data: {e}")
        raise

if __name__ == "__main__":
    create_test_data() 