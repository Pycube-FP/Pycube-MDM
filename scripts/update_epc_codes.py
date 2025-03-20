#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.db_service import DBService

# Load environment variables from .env file
load_dotenv()

def update_epc_codes():
    """
    Update the RFID Tag column to be renamed as EPC Code with the specified format
    """
    print("Starting EPC Code update...")
    db_service = DBService()
    
    try:
        connection = db_service.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        # First, get all devices ordered by ID
        cursor.execute("SELECT id FROM devices ORDER BY id")
        devices = cursor.fetchall()
        
        print(f"Found {len(devices)} devices to update")
        
        # Update each device with a new EPC Code format
        base_epc_code = 200000001192024000015107
        
        for i, device in enumerate(devices):
            device_id = device['id']
            epc_code = str(base_epc_code + i)
            
            # Update the device record with new EPC Code
            update_query = "UPDATE devices SET rfid_tag = %s WHERE id = %s"
            cursor.execute(update_query, (epc_code, device_id))
            print(f"Updated device {i+1}/50 with EPC Code: {epc_code}")
        
        # Commit changes
        connection.commit()
        
        # Now add a comment to the RFID Tag column to indicate it's actually an EPC Code
        try:
            cursor.execute("ALTER TABLE devices CHANGE COLUMN rfid_tag rfid_tag VARCHAR(100) COMMENT 'EPC Code'")
            connection.commit()
            print("Added 'EPC Code' comment to the rfid_tag column")
        except Exception as e:
            print(f"Warning: Could not add column comment: {e}")
        
        cursor.close()
        connection.close()
        
        print("EPC Code update completed successfully!")
        return True
    except Exception as e:
        print(f"Error updating EPC Codes: {e}")
        return False

if __name__ == "__main__":
    update_epc_codes() 