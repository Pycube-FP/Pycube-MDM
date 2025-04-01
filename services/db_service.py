import os
import mysql.connector
from mysql.connector import pooling
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import uuid
import pytz

# Load environment variables from .env file
load_dotenv()

# Configure timezone
TIMEZONE = pytz.timezone('America/New_York')

# Define time threshold constants
MISSING_THRESHOLD = timedelta(minutes=45)  # Time after which a temporarily out device is considered missing

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
            # Create hospitals table first (no dependencies)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hospitals (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    address TEXT,
                    city VARCHAR(100),
                    state VARCHAR(50),
                    zip_code VARCHAR(20),
                    status ENUM('Active', 'Inactive') DEFAULT 'Active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Create locations table (depends on hospitals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    type ENUM('Entrance', 'Exit', 'Room', 'Ward', 'Department') NOT NULL,
                    hospital_id VARCHAR(36) NOT NULL,
                    building VARCHAR(100),
                    floor VARCHAR(20),
                    room VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
                )
            """)
            
            # Create nurses table (depends on hospitals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nurses (
                    id VARCHAR(36) PRIMARY KEY,
                    badge_id VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    hospital_id VARCHAR(36) NOT NULL,
                    department VARCHAR(100),
                    shift VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                    UNIQUE KEY unique_badge_hospital (badge_id, hospital_id)
                )
            """)
            
            # Create readers table (depends on hospitals and locations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS readers (
                    id VARCHAR(36) PRIMARY KEY,
                    reader_code VARCHAR(100) NOT NULL,
                    antenna_number INT NOT NULL,
                    name VARCHAR(100),
                    hospital_id VARCHAR(36) NOT NULL,
                    location_id VARCHAR(36) NOT NULL,
                    status ENUM('Active', 'Inactive', 'Maintenance') DEFAULT 'Active',
                    last_heartbeat DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id),
                    UNIQUE KEY unique_reader_antenna (reader_code, antenna_number)
                )
            """)
            
            # Create devices table (depends on hospitals and locations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id VARCHAR(36) PRIMARY KEY,
                    serial_number VARCHAR(100) UNIQUE,
                    model VARCHAR(100),
                    manufacturer VARCHAR(100),
                    rfid_tag VARCHAR(100) UNIQUE,
                    barcode VARCHAR(100) UNIQUE,
                    status ENUM('In-Facility', 'Missing', 'Temporarily Out') DEFAULT 'In-Facility',
                    hospital_id VARCHAR(36),
                    location_id VARCHAR(36),
                    assigned_to VARCHAR(100),
                    purchase_date DATE,
                    last_maintenance_date DATE,
                    eol_date DATE,
                    eol_status ENUM('Active', 'Warning', 'Critical', 'Expired') DEFAULT 'Active',
                    eol_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)
            
            # Create users table (depends on hospitals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'nurse', 'hospital_admin') NOT NULL,
                    hospital_id VARCHAR(36),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
                )
            """)
            
            # Create device_assignments table (depends on devices, nurses, and hospitals)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_assignments (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    nurse_id VARCHAR(36),
                    hospital_id VARCHAR(36),
                    assigned_at DATETIME,
                    returned_at DATETIME,
                    status ENUM('Active', 'Transferred', 'Lost', 'Returned') DEFAULT 'Active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (nurse_id) REFERENCES nurses(id),
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
                )
            """)
            
            # Update reader_events table to reference readers directly
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reader_events (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    rfid_tag VARCHAR(100),
                    reader_code VARCHAR(100),
                    antenna_number INT,
                    hospital_id VARCHAR(36),
                    location_id VARCHAR(36),
                    timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id),
                    FOREIGN KEY (reader_code, antenna_number) REFERENCES readers(reader_code, antenna_number)
                )
            """)

            # Create rfid_alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rfid_alerts (
                    id VARCHAR(36) PRIMARY KEY,
                    device_id VARCHAR(36),
                    reader_id VARCHAR(36),
                    hospital_id VARCHAR(36),
                    location_id VARCHAR(36),
                    status VARCHAR(50) DEFAULT 'Temporarily Out',
                    previous_status VARCHAR(50) DEFAULT NULL,
                    timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id),
                    FOREIGN KEY (reader_id) REFERENCES readers(id),
                    FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                )
            """)

            connection.commit()
            print("All tables created successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            connection.rollback()
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
                    status, hospital_id, location_id, assigned_to, purchase_date, 
                    last_maintenance_date, eol_date, eol_status, eol_notes,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                device.id, device.serial_number, device.model, device.manufacturer,
                device.rfid_tag, device.barcode, device.status, device.hospital_id,
                device.location_id, device.assigned_to, device.purchase_date,
                device.last_maintenance_date, device.eol_date, device.eol_status,
                device.eol_notes, device.created_at, device.updated_at
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
            query = """
                SELECT d.*, h.name as hospital_name, l.name as location_name
                FROM devices d
                LEFT JOIN hospitals h ON d.hospital_id = h.id
                LEFT JOIN locations l ON d.location_id = l.id
                WHERE d.id = %s
            """
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
            query = """
                SELECT d.*, h.name as hospital_name, l.name as location_name
                FROM devices d
                LEFT JOIN hospitals h ON d.hospital_id = h.id
                LEFT JOIN locations l ON d.location_id = l.id
                WHERE d.rfid_tag = %s
            """
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
            query = """
                SELECT d.*, h.name as hospital_name, l.name as location_name
                FROM devices d
                LEFT JOIN hospitals h ON d.hospital_id = h.id
                LEFT JOIN locations l ON d.location_id = l.id
                WHERE d.barcode = %s
            """
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
        cursor = connection.cursor(dictionary=True)
        
        try:
            # First get existing device data
            cursor.execute("SELECT * FROM devices WHERE id = %s", (device.id,))
            existing_device = cursor.fetchone()
            
            if not existing_device:
                raise Exception(f"Device with id {device.id} not found")
            
            # Use existing values if new values are None
            query = """
                UPDATE devices 
                SET serial_number = %s,
                    model = %s,
                    manufacturer = %s,
                    rfid_tag = %s,
                    barcode = %s,
                    status = %s,
                    hospital_id = %s,
                    location_id = %s,
                    assigned_to = %s,
                    purchase_date = %s,
                    last_maintenance_date = %s,
                    eol_date = %s,
                    eol_status = %s,
                    eol_notes = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            values = (
                device.serial_number or existing_device['serial_number'],
                device.model or existing_device['model'],
                device.manufacturer or existing_device['manufacturer'],
                device.rfid_tag or existing_device['rfid_tag'],
                device.barcode or existing_device['barcode'],
                device.status or existing_device['status'],
                device.hospital_id or existing_device['hospital_id'],
                device.location_id or existing_device['location_id'],
                device.assigned_to if device.assigned_to is not None else existing_device['assigned_to'],
                device.purchase_date or existing_device['purchase_date'],
                device.last_maintenance_date or existing_device['last_maintenance_date'],
                device.eol_date or existing_device['eol_date'],
                device.eol_status or existing_device['eol_status'],
                device.eol_notes or existing_device['eol_notes'],
                datetime.now(),
                device.id
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
                    id, name, type, hospital_id, building, floor, room,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                location.id, location.name, location.type, location.hospital_id,
                location.building, location.floor, location.room,
                location.created_at, location.updated_at
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
    def record_movement(self, rfid_alert):
        """Record a device reader event and create RFID alert"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # First get the reader details to validate and get location
            reader_query = """
                SELECT r.*, l.id as location_id, h.id as hospital_id
                FROM readers r
                LEFT JOIN locations l ON r.location_id = l.id
                LEFT JOIN hospitals h ON r.hospital_id = h.id
                WHERE r.reader_code = %s AND r.antenna_number = %s
            """
            cursor.execute(reader_query, (rfid_alert.reader_code, rfid_alert.antenna_number))
            reader = cursor.fetchone()
            
            if not reader:
                raise Exception(f"Reader {rfid_alert.reader_code} with antenna {rfid_alert.antenna_number} not found")
            
            # Get device by RFID tag
            device_query = "SELECT id FROM devices WHERE rfid_tag = %s"
            cursor.execute(device_query, (rfid_alert.rfid_tag,))
            device = cursor.fetchone()
            
            if not device:
                raise Exception(f"Device with RFID tag {rfid_alert.rfid_tag} not found")
            
            # Ensure we have timezone-aware timestamps
            current_time = datetime.now(TIMEZONE)
            
            # Ensure rfid_alert timestamp has timezone info
            alert_timestamp = rfid_alert.timestamp
            if alert_timestamp and not alert_timestamp.tzinfo:
                alert_timestamp = TIMEZONE.localize(alert_timestamp)
            
            # Record the reader event for history
            event_query = """
                INSERT INTO reader_events (
                    id, device_id, rfid_tag, reader_code, antenna_number,
                    hospital_id, location_id, timestamp, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            event_values = (
                str(uuid.uuid4()),  # New ID for the event
                device['id'],
                rfid_alert.rfid_tag,
                rfid_alert.reader_code,
                rfid_alert.antenna_number,
                reader['hospital_id'],
                reader['location_id'],
                alert_timestamp,
                current_time
            )
            
            cursor.execute(event_query, event_values)
            
            # Create RFID alert
            alert_query = """
                INSERT INTO rfid_alerts (
                    id, device_id, reader_id, hospital_id, location_id,
                    status, previous_status, timestamp, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Use the status from the alert object if available, otherwise get it from the database
            device_status = getattr(rfid_alert, 'status', None)
            if device_status is None:
                # Fall back to getting status from the database
                status_query = "SELECT status FROM devices WHERE id = %s"
                cursor.execute(status_query, (device['id'],))
                device_status_row = cursor.fetchone()
                device_status = device_status_row['status'] if device_status_row else 'Temporarily Out'
            
            # Get previous status from alert object
            previous_status = getattr(rfid_alert, 'previous_status', None)
            
            alert_values = (
                rfid_alert.id,  # Use the ID from the RFIDAlert object
                device['id'],
                reader['id'],
                reader['hospital_id'],
                reader['location_id'],
                device_status,
                previous_status,
                alert_timestamp,
                current_time,
                current_time
            )
            
            cursor.execute(alert_query, alert_values)
            
            # Update device location
            update_query = """
                UPDATE devices 
                SET location_id = %s, updated_at = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (reader['location_id'], current_time, device['id']))
            
            connection.commit()
            return rfid_alert.id
            
        except Exception as e:
            connection.rollback()
            print(f"Error recording reader event: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_device_movements(self, device_id, limit=50):
        """Get reader events for a specific device with location information and ordered by time"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # First, get the current device status to use for comparison
            cursor.execute("SELECT status FROM devices WHERE id = %s", (device_id,))
            current_device = cursor.fetchone()
            current_status = current_device['status'] if current_device else 'In-Facility'
            
            # We need to find status transitions by comparing event timestamps
            query = """
                SELECT 
                    re.id,
                    re.timestamp,
                    re.device_id,
                    re.location_id,
                    re.rfid_tag,
                    re.reader_code,
                    re.antenna_number,
                    l.name as location_name,
                    r.name as reader_name,
                    CONCAT(re.reader_code, ' (', r.name, ')') as reader_id
                FROM reader_events re
                LEFT JOIN locations l ON re.location_id = l.id
                LEFT JOIN readers r ON re.reader_code = r.reader_code AND re.antenna_number = r.antenna_number
                WHERE re.device_id = %s
                ORDER BY re.timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (device_id, limit))
            events = cursor.fetchall()
            
            if not events:
                return []
                
            # Get previous state for each event
            previous_state = current_status  # Start with current device state
            
            for event in events:
                # Reset event status info
                event['event_status'] = None
                event['status_transition'] = None
                
                # For the first event (most recent), we need to determine what happened
                if event == events[0]:
                    if current_status == 'Missing':
                        # If device is currently missing - first event triggered missing status
                        event['event_status'] = 'Missing'
                        event['status_transition'] = 'Temporarily Out → Missing'
                    elif current_status == 'Temporarily Out':
                        # If device is temporarily out - first event triggered temporary out
                        event['event_status'] = 'Temporarily Out'
                        event['status_transition'] = 'In-Facility → Temporarily Out'
                    elif current_status == 'In-Facility':
                        # If device is currently in-facility - three possible cases:
                        if len(events) > 1:
                            # Compare with previous event
                            time_diff = (event['timestamp'] - events[1]['timestamp']).total_seconds()
                            
                            # Get device status history (if available)
                            status_query = """
                                SELECT status 
                                FROM reader_events re
                                JOIN devices d ON re.device_id = d.id
                                WHERE re.id = %s
                            """
                            cursor.execute(status_query, (events[1]['id'],))
                            prev_status_result = cursor.fetchone()
                            prev_status = prev_status_result['status'] if prev_status_result else None
                            
                            if prev_status == 'Missing':
                                # If previous status was Missing, this event is returning from Missing
                                event['event_status'] = 'In-Facility'
                                event['status_transition'] = 'Missing → In-Facility'
                            elif time_diff < MISSING_THRESHOLD.total_seconds():
                                # If the two most recent events are within the threshold,
                                # this was likely a return to facility
                                event['event_status'] = 'In-Facility'
                                event['status_transition'] = 'Temporarily Out → In-Facility'
                            else:
                                # Otherwise it's a standard exit
                                event['event_status'] = 'Temporarily Out'
                                event['status_transition'] = 'In-Facility → Temporarily Out'
                        else:
                            # First event for device, so it's an exit
                            event['event_status'] = 'Temporarily Out'
                            event['status_transition'] = 'In-Facility → Temporarily Out'
                else:
                    # For other events, alternate between "exit" and "return" events
                    # based on the likely state transitions
                    prev_idx = events.index(event) - 1
                    prev_event = events[prev_idx]
                    
                    if prev_event['status_transition'] == 'In-Facility → Temporarily Out':
                        # After an exit event comes a return event
                        event['event_status'] = 'In-Facility'
                        event['status_transition'] = 'Temporarily Out → In-Facility'
                    else:
                        # After a return event comes an exit event
                        event['event_status'] = 'Temporarily Out'
                        event['status_transition'] = 'In-Facility → Temporarily Out'
                
            return events
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

    def get_rfid_alerts(self, limit=None, offset=None, sort_by=None, sort_dir='asc', device_id=None, start_date=None, end_date=None):
        """Get RFID alerts with optional filtering and sorting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Changed to dictionary cursor
            
            # Start building the query with a WHERE 1=1 clause to make dynamic filtering easier
            query = """
                SELECT a.id, a.timestamp, a.device_id, a.location_id, a.status as alert_status,
                       d.model as device_name, d.serial_number, d.status as device_status,
                       l.name as location_name
                FROM rfid_alerts a
                LEFT JOIN devices d ON a.device_id = d.id
                LEFT JOIN locations l ON a.location_id = l.id
                WHERE 1=1
            """
            
            # Initialize parameters list
            params = []
            
            # Add filters if provided
            if device_id:
                query += " AND a.device_id = %s"
                params.append(device_id)
                
            if start_date:
                query += " AND a.timestamp >= %s"
                params.append(start_date)
                
            if end_date:
                query += " AND a.timestamp <= %s"
                params.append(end_date)
            
            # Add sorting if provided
            valid_sort_columns = ['timestamp', 'device_name', 'location_name']
            if sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.upper() in ['ASC', 'DESC'] else 'ASC'
                if sort_by == 'device_name':
                    query += f" ORDER BY d.model {sort_dir}"
                elif sort_by == 'location_name':
                    query += f" ORDER BY l.name {sort_dir}"
                else:
                    query += f" ORDER BY a.{sort_by} {sort_dir}"
            else:
                # Default sort by timestamp descending
                query += " ORDER BY a.timestamp DESC"
            
            # Add pagination if provided
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
                
                if offset is not None:
                    query += " OFFSET %s"
                    params.append(offset)
            
            cursor.execute(query, tuple(params))
            alerts = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return alerts
            
        except Exception as e:
            print(f"Error getting RFID alerts: {str(e)}")
            return []

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
            
            # Handle both dictionary and object input
            if isinstance(assignment, dict):
                values = (
                    assignment['id'],
                    assignment['device_id'],
                    assignment['nurse_id'],
                    assignment['assigned_at'],
                    assignment.get('returned_at'),
                    assignment['status'],
                    assignment['created_at'],
                    assignment['updated_at']
                )
            else:
                values = (
                    assignment.id,
                    assignment.device_id,
                    assignment.nurse_id,
                    assignment.assigned_at,
                    assignment.returned_at,
                    assignment.status,
                    assignment.created_at,
                    assignment.updated_at
                )
            
            cursor.execute(query, values)
            connection.commit()
            return assignment['id'] if isinstance(assignment, dict) else assignment.id
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
            
            # Use timezone-aware timestamp
            current_time = datetime.now(TIMEZONE)
            
            values = (status, current_time, device_id)
            
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
        """Get total number of nurses"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM nurses")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"Error getting nurse count: {e}")
            return 0
        finally:
            cursor.close()
            connection.close()

    # User management methods
    def create_user(self, user_data):
        """Create a new user"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO users (
                    id, username, password_hash, role, first_name,
                    last_name, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                user_data['id'],
                user_data['username'],
                user_data['password_hash'],
                user_data['role'],
                user_data.get('first_name'),
                user_data.get('last_name'),
                datetime.now(),
                datetime.now()
            )
            
            cursor.execute(query, values)
            connection.commit()
            return user_data['id']
        except Exception as e:
            connection.rollback()
            print(f"Error creating user: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_user_by_username(self, username):
        """Get a user by username"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            return user
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    def get_user(self, user_id):
        """Get a user by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    def update_user(self, user_data):
        """Update a user's information"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE users SET
                    username = %s,
                    role = %s,
                    first_name = %s,
                    last_name = %s,
                    updated_at = %s
                WHERE id = %s
            """
            
            values = (
                user_data['username'],
                user_data['role'],
                user_data.get('first_name'),
                user_data.get('last_name'),
                datetime.now(),
                user_data['id']
            )
            
            cursor.execute(query, values)
            connection.commit()
            return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating user: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    def update_user_password(self, user_id, password_hash):
        """Update a user's password"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s"
            values = (password_hash, datetime.now(), user_id)
            
            cursor.execute(query, values)
            connection.commit()
            return True
        except Exception as e:
            connection.rollback()
            print(f"Error updating user password: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    # Hospital management methods
    def create_hospital(self, hospital):
        """Create a new hospital"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO hospitals (
                    id, name, code, address, city, state,
                    zip_code, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                hospital.id,
                hospital.name,
                hospital.code,
                hospital.address,
                hospital.city,
                hospital.state,
                hospital.zip_code,
                hospital.status,
                datetime.now(),
                datetime.now()
            )
            
            cursor.execute(query, values)
            connection.commit()
            return hospital.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating hospital: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_hospital(self, hospital_id):
        """Get a hospital by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM hospitals WHERE id = %s"
            cursor.execute(query, (hospital_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error retrieving hospital: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_all_hospitals(self, sort_by=None, sort_dir='asc'):
        """Get all hospitals with optional sorting"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Define valid sort columns and their SQL equivalents
            valid_sort_columns = {
                'name': 'name',
                'code': 'code',
                'status': 'status',
                'created_at': 'created_at'
            }
            
            # Base query
            query = """
                SELECT h.*, COUNT(r.id) as reader_count
                FROM hospitals h
                LEFT JOIN readers r ON h.id = r.hospital_id
                GROUP BY h.id
            """
            
            # Add sorting if valid column is provided
            if sort_by and sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.lower() in ['asc', 'desc'] else 'ASC'
                query += f" ORDER BY {valid_sort_columns[sort_by]} {sort_dir}"
            else:
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving hospitals: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def update_hospital(self, hospital):
        """Update a hospital"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE hospitals 
                SET name = %s, code = %s, address = %s,
                    city = %s, state = %s, zip_code = %s,
                    status = %s, updated_at = %s
                WHERE id = %s
            """
            
            values = (
                hospital.name,
                hospital.code,
                hospital.address,
                hospital.city,
                hospital.state,
                hospital.zip_code,
                hospital.status,
                datetime.now(),
                hospital.id
            )
            
            cursor.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating hospital: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_hospital_statistics(self, hospital_id):
        """Get statistics for a hospital"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            stats = {}
            
            # Get device counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM devices
                WHERE hospital_id = %s
                GROUP BY status
            """, (hospital_id,))
            stats['devices'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Get total nurses
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM nurses
                WHERE hospital_id = %s
            """, (hospital_id,))
            stats['nurse_count'] = cursor.fetchone()['count']
            
            # Get active reader-antenna combinations
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM readers
                WHERE hospital_id = %s AND status = 'Active'
            """, (hospital_id,))
            stats['active_readers'] = cursor.fetchone()['count']
            
            # Get recent alerts
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM rfid_alerts
                WHERE hospital_id = %s
                AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """, (hospital_id,))
            stats['recent_alerts'] = cursor.fetchone()['count']
            
            return stats
        except Exception as e:
            print(f"Error retrieving hospital statistics: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    # Reader management methods
    def create_reader(self, reader):
        """Create a new reader"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                INSERT INTO readers (
                    id, reader_code, antenna_number, name, hospital_id, location_id,
                    status, last_heartbeat, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                reader.id,
                reader.reader_code,
                reader.antenna_number,
                reader.name,
                reader.hospital_id,
                reader.location_id,
                reader.status,
                reader.last_heartbeat,
                datetime.now(),
                datetime.now()
            )
            
            cursor.execute(query, values)
            connection.commit()
            return reader.id
        except Exception as e:
            connection.rollback()
            print(f"Error creating reader: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_reader(self, reader_id):
        """Get a reader by ID"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT r.*, h.name as hospital_name, l.name as location_name
                FROM readers r
                LEFT JOIN hospitals h ON r.hospital_id = h.id
                LEFT JOIN locations l ON r.location_id = l.id
                WHERE r.id = %s
            """
            cursor.execute(query, (reader_id,))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error retrieving reader: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_all_readers(self, sort_by=None, sort_dir='asc'):
        """Get all readers with optional sorting"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Define valid sort columns and their SQL equivalents
            valid_sort_columns = {
                'reader_code': 'reader_code',
                'antenna': 'antenna_number',
                'name': 'name',
                'hospital': 'h.name',
                'location': 'l.name',
                'status': 'status',
                'last_heartbeat': 'last_heartbeat'
            }
            
            # Base query
            query = """
                SELECT r.*, h.name as hospital_name, l.name as location_name
                FROM readers r
                LEFT JOIN hospitals h ON r.hospital_id = h.id
                LEFT JOIN locations l ON r.location_id = l.id
            """
            
            # Add sorting if valid column is provided
            if sort_by and sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.lower() in ['asc', 'desc'] else 'ASC'
                query += f" ORDER BY {valid_sort_columns[sort_by]} {sort_dir}"
            else:
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving readers: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_hospital_readers(self, hospital_id):
        """Get all readers for a hospital"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT r.*, l.name as location_name
                FROM readers r
                LEFT JOIN locations l ON r.location_id = l.id
                WHERE r.hospital_id = %s
                ORDER BY r.name ASC
            """
            cursor.execute(query, (hospital_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving hospital readers: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def update_reader(self, reader):
        """Update a reader"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            query = """
                UPDATE readers 
                SET reader_code = %s, name = %s, hospital_id = %s,
                    status = %s, last_heartbeat = %s, updated_at = %s
                WHERE id = %s
            """
            
            values = (
                reader.reader_code,
                reader.name,
                reader.hospital_id,
                reader.status,
                reader.last_heartbeat,
                datetime.now(),
                reader.id
            )
            
            cursor.execute(query, values)
            connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            connection.rollback()
            print(f"Error updating reader: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_reader_statistics(self, reader_id):
        """Get statistics for a reader"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # First get the reader details to get reader_code and antenna_number
            cursor.execute("""
                SELECT reader_code, antenna_number, last_heartbeat, status,
                       TIMESTAMPDIFF(MINUTE, last_heartbeat, NOW()) as minutes_since_heartbeat
                FROM readers
                WHERE id = %s
            """, (reader_id,))
            reader = cursor.fetchone()
            
            if not reader:
                raise Exception(f"Reader with id {reader_id} not found")
            
            stats = {}
            
            # Get total events (all time)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM reader_events
                WHERE reader_code = %s AND antenna_number = %s
            """, (reader['reader_code'], reader['antenna_number']))
            stats['total_events'] = cursor.fetchone()['count']
            
            # Get recent events (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM reader_events
                WHERE reader_code = %s AND antenna_number = %s
                AND timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """, (reader['reader_code'], reader['antenna_number']))
            stats['recent_events'] = cursor.fetchone()['count']
            
            # Get unique devices tracked (all time)
            cursor.execute("""
                SELECT COUNT(DISTINCT device_id) as count
                FROM reader_events
                WHERE reader_code = %s AND antenna_number = %s
            """, (reader['reader_code'], reader['antenna_number']))
            stats['devices_tracked'] = cursor.fetchone()['count']
            
            # Calculate uptime percentage based on heartbeat
            # Consider reader up if last heartbeat was within last 5 minutes
            if reader['status'] == 'Active':
                minutes_since_heartbeat = reader['minutes_since_heartbeat'] or float('inf')
                stats['uptime_percentage'] = 100 if minutes_since_heartbeat <= 5 else 0
            else:
                stats['uptime_percentage'] = 0
            
            return stats
        except Exception as e:
            print(f"Error retrieving reader statistics: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def get_reader_events(self, reader_id, limit=10):
        """Get recent events for a reader"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # First get the reader details
            cursor.execute("""
                SELECT reader_code, antenna_number
                FROM readers
                WHERE id = %s
            """, (reader_id,))
            reader = cursor.fetchone()
            
            if not reader:
                raise Exception(f"Reader with id {reader_id} not found")
            
            query = """
                SELECT re.*, d.model, d.serial_number
                FROM reader_events re
                LEFT JOIN devices d ON re.device_id = d.id
                WHERE re.reader_code = %s AND re.antenna_number = %s
                ORDER BY re.timestamp DESC
                LIMIT %s
            """
            cursor.execute(query, (reader['reader_code'], reader['antenna_number'], limit))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving reader events: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_reader_by_code_and_antenna(self, reader_code, antenna_number):
        """Get a reader by reader code and antenna number"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT r.*, h.name as hospital_name, l.name as location_name
                FROM readers r
                LEFT JOIN hospitals h ON r.hospital_id = h.id
                LEFT JOIN locations l ON r.location_id = l.id
                WHERE r.reader_code = %s AND r.antenna_number = %s
            """
            cursor.execute(query, (reader_code, antenna_number))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error retrieving reader by code and antenna: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_all_users(self, sort_by=None, sort_dir='asc'):
        """Get all users with optional sorting"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Define valid sort columns and their SQL equivalents
            valid_sort_columns = {
                'username': 'username',
                'role': 'role',
                'name': 'CONCAT(first_name, " ", last_name)',
                'created_at': 'created_at'
            }
            
            # Base query
            query = "SELECT * FROM users"
            
            # Add sorting if valid column is provided
            if sort_by and sort_by in valid_sort_columns:
                sort_dir = sort_dir.upper() if sort_dir.lower() in ['asc', 'desc'] else 'ASC'
                query += f" ORDER BY {valid_sort_columns[sort_by]} {sort_dir}"
            else:
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Error retrieving users: {e}")
            raise
        finally:
            cursor.close()
            connection.close()

    def get_rfid_alerts_count(self):
        """Get total count of RFID alerts"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT COUNT(*) 
                FROM rfid_alerts
            """
            
            cursor.execute(query)
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            print(f"Error getting RFID alerts count: {str(e)}")
            return 0

    def get_rfid_alert(self, alert_id):
        """Get detailed information about a specific RFID alert"""
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            query = """
                SELECT 
                    ra.*,
                    d.model as device_name,
                    d.serial_number,
                    d.model,
                    d.status as device_status,
                    d.rfid_tag as asset_tag,
                    l.name as location_name,
                    l.type as location_type,
                    CONCAT_WS(', ',
                        NULLIF(l.building, ''),
                        NULLIF(l.floor, ''),
                        NULLIF(l.room, '')
                    ) as location_description,
                    h.name as hospital_name,
                    r.name as reader_name,
                    r.reader_code as reader_serial,
                    r.antenna_number
                FROM rfid_alerts ra
                LEFT JOIN devices d ON ra.device_id = d.id
                LEFT JOIN locations l ON ra.location_id = l.id
                LEFT JOIN hospitals h ON l.hospital_id = h.id
                LEFT JOIN readers r ON ra.reader_id = r.id
                WHERE ra.id = %s
            """
            cursor.execute(query, (alert_id,))
            alert = cursor.fetchone()
            
            # Default alert status if not present in the database
            if alert and 'status' not in alert:
                alert['status'] = 'Temporarily Out'
                
            return alert
        finally:
            cursor.close()
            connection.close() 