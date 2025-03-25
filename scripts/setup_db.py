#!/usr/bin/env python3
import os
import sys
import mysql.connector
from dotenv import load_dotenv
from services.db_service import DBService

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def main():
    """Main function to set up the database and create tables"""
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
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 