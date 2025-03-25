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
                    barcode VARCHAR(100) UNIQUE,
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
            
            # Create reader_events table (formerly movements)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reader_events (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    rfid_tag VARCHAR(100),
                    reader_id VARCHAR(100),
                    location_id VARCHAR(36),
                    timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)

            # Create nurses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nurses (
                    id VARCHAR(36) PRIMARY KEY,
                    badge_id VARCHAR(100) UNIQUE,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    department VARCHAR(100),
                    shift VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)

            # Create device_assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_assignments (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    nurse_id VARCHAR(36),
                    assigned_at DATETIME,
                    returned_at DATETIME,
                    status ENUM('Active', 'Returned', 'Lost') DEFAULT 'Active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (nurse_id) REFERENCES nurses(id)
                )
            """)

            # Create rfid_alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rfid_alerts (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    reader_id VARCHAR(100),
                    location VARCHAR(100),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id)
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
                    id, serial_number, model, manufacturer, rfid_tag, barcode,
                    status, location_id, assigned_to, purchase_date, 
                    last_maintenance_date, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                device.id, device.serial_number, device.model, device.manufacturer,
                device.rfid_tag, device.barcode, device.status, device.location_id,
                device.assigned_to, device.purchase_date, device.last_maintenance_date,
                device.created_at, device.updated_at
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
    
    def get_device_by_barcode(self, barcode):
        """Get a device by barcode"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM devices WHERE barcode = %s"
            cursor.execute(query, (barcode,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving device by barcode: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_all_devices(self, limit=100, offset=0, status=None, sort_by=None, sort_dir='asc'):
        """Get all devices with optional filtering and sorting"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Define valid sort columns and their SQL equivalents
            valid_sort_columns = {
                'status': 'status',
                'model': 'CONCAT(manufacturer, " ", model)',
                'serial_number': 'serial_number',
                'assigned_to': 'assigned_to',
                'created_at': 'created_at'
            }
            
            # Base query
            query = "SELECT * FROM devices"
            params = []
            
            # Add status filter if provided
            if status:
                query += " WHERE status = %s"
                params.append(status)
            
            # Add sorting if valid column is provided
            if sort_by and sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.lower() in ['asc', 'desc'] else 'ASC'
                query += f" ORDER BY {valid_sort_columns[sort_by]} {sort_dir}"
            else:
                query += " ORDER BY created_at DESC"
            
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
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
                    rfid_tag = %s, barcode = %s, status = %s, location_id = %s, 
                    assigned_to = %s, purchase_date = %s, last_maintenance_date = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            values = (
                device.serial_number, device.model, device.manufacturer,
                device.rfid_tag, device.barcode, device.status, device.location_id,
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
        """Record a device reader event"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO reader_events (
                    id, device_id, rfid_tag, reader_id, location_id,
                    timestamp, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                movement.id, movement.device_id, movement.rfid_tag,
                movement.reader_id, movement.location_id, movement.timestamp,
                movement.created_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            
            # Update device location
            update_query = """
                UPDATE devices 
                SET location_id = %s, updated_at = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (movement.location_id, datetime.now(), movement.device_id))
            connection.commit()
            
            return movement.id
        except Exception as e:
            connection.rollback()
            print(f"Error recording reader event: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_device_movements(self, device_id, limit=10):
        """Get reader events for a specific device"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT re.*, l.name as location_name
                FROM reader_events re
                LEFT JOIN locations l ON re.location_id = l.id
                WHERE re.device_id = %s
                ORDER BY re.timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (device_id, limit))
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving device reader events: {e}")
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
                FROM reader_events 
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

    def get_rfid_alerts(self, device_id=None, alert_type=None, start_date=None, end_date=None, limit=100, offset=0):
        """Get RFID alerts with optional filtering"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT a.*, d.model, d.serial_number, d.status
                FROM rfid_alerts a
                LEFT JOIN devices d ON a.device_id = d.id
                WHERE 1=1
            """
            params = []
            
            if device_id:
                query += " AND a.device_id = %s"
                params.append(device_id)
            
            if alert_type:
                query += " AND a.alert_type = %s"
                params.append(alert_type)
            
            if start_date:
                query += " AND a.timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND a.timestamp <= %s"
                params.append(end_date)
            
            query += " ORDER BY a.timestamp DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            alerts = cursor.fetchall()
            
            # Convert to RFIDAlert objects with device info
            for alert in alerts:
                alert['device'] = {
                    'id': alert['device_id'],
                    'model': alert['model'],
                    'serial_number': alert['serial_number'],
                    'status': alert['status']
                }
            
            return alerts
        except Exception as e:
            print(f"Error retrieving RFID alerts: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def create_rfid_alert(self, alert):
        """Create a new RFID alert"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO rfid_alerts (
                    id, device_id, reader_id, alert_type, location,
                    timestamp, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                alert.id, alert.device_id, alert.reader_id,
                alert.alert_type, alert.location, alert.timestamp,
                alert.created_at, alert.updated_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            return alert.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating RFID alert: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def create_nurse(self, nurse):
        """Create a new nurse record"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO nurses (
                    id, badge_id, first_name, last_name,
                    department, shift, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                nurse.id, nurse.badge_id, nurse.first_name, nurse.last_name,
                nurse.department, nurse.shift, nurse.created_at, nurse.updated_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            return nurse.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating nurse: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def create_device_assignment(self, assignment):
        """Create a new device assignment"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO device_assignments (
                    id, device_id, nurse_id, assigned_at,
                    returned_at, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                assignment.id, assignment.device_id, assignment.nurse_id,
                assignment.assigned_at, assignment.returned_at, assignment.status,
                assignment.created_at, assignment.updated_at
            )
            
            cursor.execute(query, values)
            connection.commit()
            return assignment.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating device assignment: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def update_device_status(self, device_id, status):
        """Update device status"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE devices 
                SET status = %s, updated_at = %s
                WHERE id = %s
            """
            
            values = (status, datetime.now(), device_id)
            
            cursor.execute(query, values)
            connection.commit()
            return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating device status: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_nurse(self, nurse_id):
        """Get a nurse by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT id, badge_id, first_name, last_name, department, shift,
                       created_at, updated_at
                FROM nurses
                WHERE id = %s
            """
            cursor.execute(query, (nurse_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving nurse: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_nurse_by_badge(self, badge_id):
        """Get a nurse by badge ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT id, badge_id, first_name, last_name, department, shift,
                       created_at, updated_at
                FROM nurses
                WHERE badge_id = %s
            """
            cursor.execute(query, (badge_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving nurse by badge: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_nurse_by_barcode(self, barcode):
        """Get a nurse by barcode (alias for get_nurse_by_badge)"""
        return self.get_nurse_by_badge(barcode)

    def get_all_nurses(self, limit=10, offset=0, sort_by=None, sort_dir='asc'):
        """Get all nurses with pagination and sorting"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Define valid sort columns and their SQL equivalents
            valid_sort_columns = {
                'badge_id': 'badge_id',
                'name': 'CONCAT(first_name, " ", last_name)',
                'department': 'department',
                'shift': 'shift',
                'created_at': 'created_at'
            }
            
            # Base query
            query = """
                SELECT id, badge_id, first_name, last_name, department, shift,
                       created_at, updated_at
                FROM nurses
            """
            
            # Add sorting if valid column is provided
            if sort_by and sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.lower() in ['asc', 'desc'] else 'ASC'
                query += f" ORDER BY {valid_sort_columns[sort_by]} {sort_dir}"
            else:
                query += " ORDER BY created_at DESC"
            
            query += " LIMIT %s OFFSET %s"
            cursor.execute(query, (limit, offset))
            results = cursor.fetchall()
            return results
        except Exception as e:
            print(f"Error retrieving nurses: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def update_nurse(self, nurse):
        """Update an existing nurse"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE nurses
                SET first_name = %s,
                    last_name = %s,
                    badge_id = %s,
                    department = %s,
                    shift = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            values = (
                nurse.first_name,
                nurse.last_name,
                nurse.badge_id,
                nurse.department,
                nurse.shift,
                nurse.id
            )
            
            cursor.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating nurse: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_active_assignment(self, device_id):
        """Get the active assignment for a device"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT da.*, n.first_name, n.last_name, n.department
                FROM device_assignments da
                LEFT JOIN nurses n ON da.nurse_id = n.id
                WHERE da.device_id = %s AND da.status = 'Active'
                ORDER BY da.assigned_at DESC
                LIMIT 1
            """
            cursor.execute(query, (device_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            print(f"Error retrieving active assignment: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def update_device_assignment(self, assignment):
        """Update a device assignment"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE device_assignments 
                SET status = %s, returned_at = %s, updated_at = %s
                WHERE id = %s
            """
            
            values = (
                assignment.status,
                assignment.returned_at,
                datetime.now(),
                assignment.id
            )
            
            cursor.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating device assignment: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_device_assignments(self, device_id):
        """Get all assignments for a device"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT 
                    da.*,
                    n.first_name,
                    n.last_name,
                    n.department,
                    CONCAT(n.first_name, ' ', n.last_name) as nurse_name
                FROM device_assignments da
                LEFT JOIN nurses n ON da.nurse_id = n.id
                WHERE da.device_id = %s
                ORDER BY da.created_at DESC
            """
            cursor.execute(query, (device_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving device assignments: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def delete_nurse(self, nurse_id):
        """Delete a nurse by ID"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            # First, check if the nurse has any active assignments
            query = """
                SELECT COUNT(*) FROM device_assignments 
                WHERE nurse_id = %s AND status = 'Active'
            """
            cursor.execute(query, (nurse_id,))
            active_assignments = cursor.fetchone()[0]
            
            if active_assignments > 0:
                raise Exception("Cannot delete nurse with active device assignments")
            
            # Delete the nurse
            query = "DELETE FROM nurses WHERE id = %s"
            cursor.execute(query, (nurse_id,))
            connection.commit()
            return nurse_id
        except Exception as e:
            connection.rollback()
            print(f"Error deleting nurse: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_nurse_assignments(self, nurse_id):
        """Get all assignments for a nurse"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT 
                    da.*,
                    d.model as device_model,
                    d.serial_number as device_serial,
                    d.manufacturer
                FROM device_assignments da
                LEFT JOIN devices d ON da.device_id = d.id
                WHERE da.nurse_id = %s
                ORDER BY da.created_at DESC
            """
            cursor.execute(query, (nurse_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving nurse assignments: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_nurse_active_assignment(self, nurse_id):
        """Get the active device assignment for a nurse"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT da.*, d.model, d.serial_number, d.manufacturer
                FROM device_assignments da
                LEFT JOIN devices d ON da.device_id = d.id
                WHERE da.nurse_id = %s AND da.status = 'Active'
                ORDER BY da.assigned_at DESC
                LIMIT 1
            """
            cursor.execute(query, (nurse_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error retrieving nurse's active assignment: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_device_count(self, status=None):
        """Get total count of devices with optional status filter"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            if status:
                query = "SELECT COUNT(*) FROM devices WHERE status = %s"
                cursor.execute(query, (status,))
            else:
                query = "SELECT COUNT(*) FROM devices"
                cursor.execute(query)
            
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting device count: {e}")
            return 0
        finally:
            cursor.close()
            connection.close()

    def get_nurse_count(self):
        """Get total count of nurses"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = "SELECT COUNT(*) FROM nurses"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting nurse count: {e}")
            return 0
        finally:
            cursor.close()
            connection.close() 