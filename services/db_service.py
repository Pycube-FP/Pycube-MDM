import os
import mysql.connector
from mysql.connector import pooling
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DBService:
    """Service to handle database operations"""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBService, cls).__new__(cls)
            cls._initialize_pool()
        return cls._instance
    
    @classmethod
    def _initialize_pool(cls):
        """Initialize connection pool to RDS"""
        try:
            # Get database config from environment variables
            db_config = {
                'host': os.environ.get('RDS_HOST', 'localhost'),
                'port': int(os.environ.get('RDS_PORT', 3306)),
                'user': os.environ.get('RDS_USER', 'root'),
                'password': os.environ.get('RDS_PASSWORD', 'password'),
                'database': os.environ.get('RDS_DB', 'pycube_mdm'),
            }
            
            # Create a connection pool
            cls._pool = pooling.MySQLConnectionPool(
                pool_name="pycube_pool",
                pool_size=5,
                **db_config
            )
            print("Connection pool created successfully")
        except Exception as e:
            print(f"Error initializing DB pool: {e}")
    
    def get_connection(self):
        """Get a connection from the pool"""
        if self._pool:
            return self._pool.get_connection()
        else:
            raise Exception("Database pool not initialized")
    
    def initialize_db(self):
        """Create tables if they don't exist"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            # Create devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id VARCHAR(36) PRIMARY KEY,
                    serial_number VARCHAR(100) UNIQUE,
                    model VARCHAR(100),
                    manufacturer VARCHAR(100),
                    rfid_tag VARCHAR(100) UNIQUE,
                    status ENUM('Available', 'In-Use', 'Maintenance', 'Missing') DEFAULT 'Available',
                    location_id VARCHAR(36),
                    assigned_to VARCHAR(100),
                    purchase_date DATE,
                    last_maintenance_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create locations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type ENUM('Entrance', 'Exit', 'Room', 'Ward', 'Department') NOT NULL,
                    building VARCHAR(100),
                    floor VARCHAR(20),
                    room VARCHAR(50),
                    has_reader BOOLEAN DEFAULT FALSE,
                    reader_id VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create movements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movements (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    rfid_tag VARCHAR(100),
                    reader_id VARCHAR(100),
                    location_id VARCHAR(36),
                    direction ENUM('IN', 'OUT'),
                    timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)
            
            connection.commit()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
        finally:
            cursor.close()
            connection.close()
    
    # Device CRUD operations
    def create_device(self, device):
        """Create a new device record"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO devices (
                    id, serial_number, model, manufacturer, rfid_tag, 
                    status, location_id, assigned_to, purchase_date, 
                    last_maintenance_date, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                device.id, device.serial_number, device.model, device.manufacturer,
                device.rfid_tag, device.status, device.location_id, device.assigned_to,
                device.purchase_date, device.last_maintenance_date, device.created_at, device.updated_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            return device.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating device: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_device(self, device_id):
        """Get a device by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM devices WHERE id = %s"
            cursor.execute(query, (device_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving device: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_device_by_rfid(self, rfid_tag):
        """Get a device by RFID tag"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM devices WHERE rfid_tag = %s"
            cursor.execute(query, (rfid_tag,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving device by RFID: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_all_devices(self, limit=100, offset=0, status=None):
        """Get all devices with optional filtering"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            if status:
                query = "SELECT * FROM devices WHERE status = %s LIMIT %s OFFSET %s"
                cursor.execute(query, (status, limit, offset))
            else:
                query = "SELECT * FROM devices LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, offset))
                
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving devices: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def update_device(self, device):
        """Update a device record"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE devices 
                SET serial_number = %s, model = %s, manufacturer = %s, 
                    rfid_tag = %s, status = %s, location_id = %s, 
                    assigned_to = %s, purchase_date = %s, last_maintenance_date = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            values = (
                device.serial_number, device.model, device.manufacturer,
                device.rfid_tag, device.status, device.location_id,
                device.assigned_to, device.purchase_date, device.last_maintenance_date,
                datetime.now(), device.id
            )
            
            cursor.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating device: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def delete_device(self, device_id):
        """Delete a device record"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = "DELETE FROM devices WHERE id = %s"
            cursor.execute(query, (device_id,))
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error deleting device: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    # Location CRUD operations
    def create_location(self, location):
        """Create a new location record"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO locations (
                    id, name, type, building, floor, room,
                    has_reader, reader_id, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                location.id, location.name, location.type, location.building,
                location.floor, location.room, location.has_reader, 
                location.reader_id, location.created_at, location.updated_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            return location.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating location: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_location(self, location_id):
        """Get a location by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM locations WHERE id = %s"
            cursor.execute(query, (location_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving location: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_all_locations(self):
        """Get all locations"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM locations"
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving locations: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    # Movement operations
    def record_movement(self, movement):
        """Record a device movement"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO movements (
                    id, device_id, rfid_tag, reader_id, location_id,
                    direction, timestamp, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                movement.id, movement.device_id, movement.rfid_tag,
                movement.reader_id, movement.location_id, movement.direction,
                movement.timestamp, movement.created_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            
            # Update device location and status if it's an exit
            if movement.direction == 'OUT':
                # Update device status to "Missing"
                update_query = """
                    UPDATE devices 
                    SET status = 'Missing', location_id = NULL, updated_at = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (datetime.now(), movement.device_id))
                connection.commit()
            
            return movement.id
        except Exception as e:
            connection.rollback()
            print(f"Error recording movement: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_device_movements(self, device_id, limit=10):
        """Get movements for a specific device"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT m.*, l.name as location_name
                FROM movements m
                LEFT JOIN locations l ON m.location_id = l.id
                WHERE m.device_id = %s
                ORDER BY m.timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (device_id, limit))
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving device movements: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_statistics(self):
        """Get statistics about devices for dashboard"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            stats = {}
            
            # Count devices by status
            status_query = """
                SELECT status, COUNT(*) as count 
                FROM devices 
                GROUP BY status
            """
            cursor.execute(status_query)
            status_counts = cursor.fetchall()
            
            status_data = {}
            for item in status_counts:
                status_data[item['status']] = item['count']
            
            stats['status_counts'] = status_data
            
            # Count movements by day (last 7 days)
            movement_query = """
                SELECT DATE(timestamp) as date, COUNT(*) as count 
                FROM movements 
                WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(timestamp)
                ORDER BY date
            """
            cursor.execute(movement_query)
            movement_counts = cursor.fetchall()
            
            stats['movement_counts'] = movement_counts
            
            # Count missing devices
            missing_query = "SELECT COUNT(*) as count FROM devices WHERE status = 'Missing'"
            cursor.execute(missing_query)
            missing_count = cursor.fetchone()
            
            stats['missing_count'] = missing_count['count'] if missing_count else 0
            
            # Total devices
            total_query = "SELECT COUNT(*) as count FROM devices"
            cursor.execute(total_query)
            total_count = cursor.fetchone()
            
            stats['total_count'] = total_count['count'] if total_count else 0
            
            return stats
        except Exception as e:
            print(f"Error retrieving statistics: {e}")
            raise
        finally:
            cursor.close()
            connection.close() 