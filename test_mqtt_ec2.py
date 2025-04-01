import paho.mqtt.client as mqtt
import time
import logging
import ssl
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import mysql.connector
import pytz
from services.db_service import DBService
from models.rfid_alert import RFIDAlert
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
import traceback

# Import configuration
try:
    from pycube_mdm.config.app_config import (
        MISSING_THRESHOLD, 
        TIMEZONE, 
        MQTT_ENDPOINT, 
        MQTT_TOPIC, 
        MQTT_PORT, 
        MQTT_KEEP_ALIVE,
        CERTS_DIR,
        PRIVATE_KEY,
        CERTIFICATE,
        ROOT_CA,
        SCHEDULER_CHECK_MISSING_INTERVAL,
        SCHEDULER_LOG_STATUS_INTERVAL,
        get_current_est_time
    )
except ImportError:
    # Try relative import for when running within the package
    try:
        from config.app_config import (
            MISSING_THRESHOLD, 
            TIMEZONE, 
            MQTT_ENDPOINT, 
            MQTT_TOPIC, 
            MQTT_PORT, 
            MQTT_KEEP_ALIVE,
            CERTS_DIR,
            PRIVATE_KEY,
            CERTIFICATE,
            ROOT_CA,
            SCHEDULER_CHECK_MISSING_INTERVAL,
            SCHEDULER_LOG_STATUS_INTERVAL,
            get_current_est_time
        )
    except ImportError:
        # We'll define fallback constants here in case the config module is not available
        import pytz
        from datetime import timedelta, datetime
        
        # Timezone configuration
        TIMEZONE = pytz.timezone('America/New_York')
        
        # Define time threshold constants
        MISSING_THRESHOLD = timedelta(minutes=2)  # Time after which a temporarily out device is considered missing
        
        # MQTT configuration
        MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
        MQTT_TOPIC = "6B6035_tagdata"
        MQTT_PORT = 8883
        MQTT_KEEP_ALIVE = 60
        
        # Certificate paths for EC2
        CERTS_DIR = os.path.expanduser("~/certs")
        PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
        CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
        ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")
        
        # Scheduler Configuration
        SCHEDULER_CHECK_MISSING_INTERVAL = 2  # minutes
        SCHEDULER_LOG_STATUS_INTERVAL = 30  # seconds
        
        def get_current_est_time():
            """Get current time in Eastern Time"""
            # Create a timezone-aware UTC time 
            utc_now = datetime.now(pytz.UTC)
            
            # Convert to EST
            est_now = utc_now.astimezone(TIMEZONE)
            
            return est_now

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only console output
    ]
)
logger = logging.getLogger(__name__)

# Enable Paho MQTT debug
logger_paho = logging.getLogger('paho.mqtt')
logger_paho.setLevel(logging.DEBUG)

# Constants for status change thresholds
STATUS_CHANGE_THRESHOLD = timedelta(minutes=0)  # No delay between status changes

def verify_certificates():
    """Verify all certificate files exist and are readable"""
    for cert_file in [PRIVATE_KEY, CERTIFICATE, ROOT_CA]:
        if not os.path.exists(cert_file):
            raise FileNotFoundError(f"Certificate file not found: {cert_file}")
        if not os.access(cert_file, os.R_OK):
            raise PermissionError(f"Cannot read certificate file: {cert_file}")
        logger.info(f"Found certificate: {cert_file}")
        
        # Verify file permissions
        stat = os.stat(cert_file)
        if stat.st_mode & 0o077:  # Check if group or others have any permissions
            logger.warning(f"Warning: {cert_file} has loose permissions. Recommended: chmod 600")

class MQTTClient(mqtt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.message_count = 0
        self.last_message_time = None
        self.connection_time = None
        self.db_service = DBService()
        self.scheduler = None
        
        # Set clean session to False to maintain subscription state
        self.clean_session = False
        
        # Enable internal MQTT client debugging
        self.enable_logger(logger)
        
        # Initialize scheduler
        self._init_scheduler()

    def _init_scheduler(self):
        """Initialize the scheduler"""
        if not self.scheduler or not self.scheduler.running:
            logger.info("Initializing scheduler...")
            # Enable APScheduler logging
            logging.getLogger('apscheduler').setLevel(logging.DEBUG)
            
            self.scheduler = BackgroundScheduler(timezone=TIMEZONE)
            
            # Add the check_for_missing_devices job
            self.scheduler.add_job(
                self.check_for_missing_devices, 
                'interval', 
                minutes=SCHEDULER_CHECK_MISSING_INTERVAL,  # Check based on config
                id='check_missing_devices',
                next_run_time=datetime.now(TIMEZONE) + timedelta(seconds=15)  # Run 15 seconds after startup
            )
            
            # Add a job to periodically log scheduler status
            self.scheduler.add_job(
                self._log_scheduler_status,
                'interval',
                seconds=SCHEDULER_LOG_STATUS_INTERVAL,  # Log status based on config
                id='log_scheduler_status',
                next_run_time=datetime.now(TIMEZONE) + timedelta(seconds=5)  # Start after 5 seconds
            )
            
            # Start the scheduler
            logger.info("Starting scheduler")
            self.scheduler.start()
            logger.info(f"Scheduler started with {len(self.scheduler.get_jobs())} jobs")
            logger.info(f"Will check for missing devices every {SCHEDULER_CHECK_MISSING_INTERVAL} minutes")

    def _log_scheduler_status(self):
        """Log scheduler status for diagnostics"""
        try:
            if self.scheduler and self.scheduler.running:
                jobs = self.scheduler.get_jobs()
                logger.info(f"SCHEDULER STATUS: Running with {len(jobs)} jobs")
                for job in jobs:
                    logger.info(f"  JOB: {job.id}, next run at: {job.next_run_time}")
            else:
                logger.warning("SCHEDULER STATUS: Not running - attempting to restart")
                self._init_scheduler()
        except Exception as e:
            logger.error(f"Error in _log_scheduler_status: {e}", exc_info=True)

    def initialize_database(self):
        """Initialize database connection and tables"""
        try:
            logger.info("Initializing database connection...")
            # Use DBService's initialize_db method if it exists
            if hasattr(self.db_service, 'initialize_db'):
                self.db_service.initialize_db()
                logger.info("Database initialized successfully")
            else:
                # Just test the connection
                with self.db_service.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                logger.info("Database connection successful")
                
            # Check database server timezone settings
            with self.db_service.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT @@global.time_zone, @@session.time_zone")
                    global_tz, session_tz = cursor.fetchone()
                    logger.info(f"Database timezone settings - Global: {global_tz}, Session: {session_tz}")
                    
                    # Compare database and system time
                    cursor.execute("SELECT NOW(), UTC_TIMESTAMP()")
                    db_now, db_utc = cursor.fetchone()
                    
                    logger.info(f"Database NOW(): {db_now} (TZ info: {db_now.tzinfo if hasattr(db_now, 'tzinfo') else 'None'})")
                    logger.info(f"Database UTC_TIMESTAMP(): {db_utc} (TZ info: {db_utc.tzinfo if hasattr(db_utc, 'tzinfo') else 'None'})")
                    
                    # Get system times
                    system_now = datetime.now()
                    system_utc = datetime.now(pytz.UTC)
                    system_est = get_current_est_time()
                    
                    logger.info(f"System local time: {system_now}")
                    logger.info(f"System UTC time: {system_utc}")
                    logger.info(f"System EST time: {system_est}")
                    
                    # Check if database has any Temporarily Out devices
                    cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'Temporarily Out'")
                    temp_out_count = cursor.fetchone()[0]
                    logger.info(f"Found {temp_out_count} devices with 'Temporarily Out' status in database")
                    
                    if temp_out_count > 0:
                        # Check one device as example
                        cursor.execute("SELECT id, serial_number, status, updated_at FROM devices WHERE status = 'Temporarily Out' LIMIT 1")
                        device = cursor.fetchone()
                        if device:
                            device_id, serial, status, updated_at = device
                            logger.info(f"Example device - ID: {device_id}, Serial: {serial}, Status: {status}")
                            logger.info(f"Updated at: {updated_at} (TZ info: {updated_at.tzinfo if hasattr(updated_at, 'tzinfo') else 'None'})")
                            
                            # Check time difference assuming UTC
                            if not updated_at.tzinfo:
                                updated_at_utc = pytz.UTC.localize(updated_at)
                                time_diff = (system_utc - updated_at_utc).total_seconds() / 60
                                logger.info(f"Time since update: {time_diff:.1f} minutes (assuming UTC)")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def check_for_missing_devices(self):
        """Check for devices that have been temporarily out for too long and mark them as missing"""
        print(f"Checking for devices that have been temporarily out for too long...")
        
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Get current time in EST
            current_time_est = get_current_est_time()
            print(f"Current time (EST): {current_time_est}")
            
            # Time threshold - devices that have been temporarily out for more than this will be marked as missing
            time_threshold = current_time_est - timedelta(hours=24)
            print(f"Time threshold (EST): {time_threshold}")
            
            # Find devices marked as "Temporarily Out" with last update before the threshold
            query = """
                WITH latest_reader_events AS (
                    SELECT 
                        re.device_id,
                        re.reader_code,
                        re.antenna_number,
                        re.timestamp,
                        ROW_NUMBER() OVER (PARTITION BY re.device_id ORDER BY re.timestamp DESC) as rn
                    FROM 
                        reader_events re
                    JOIN 
                        devices d ON re.device_id = d.id
                    WHERE 
                        d.status = 'Temporarily Out'
                )
                SELECT 
                    d.id as device_id, 
                    d.name as device_name,
                    d.mac_address,
                    d.asset_number,
                    d.status as current_status,
                    d.updated_at as last_update,
                    h.id as hospital_id,
                    lre.reader_code,
                    lre.antenna_number,
                    lre.timestamp as last_reader_event_time
                FROM 
                    devices d
                LEFT JOIN 
                    hospitals h ON d.hospital_id = h.id
                LEFT JOIN
                    latest_reader_events lre ON d.id = lre.device_id AND lre.rn = 1
                WHERE 
                    d.status = 'Temporarily Out'
                    AND d.updated_at < %s
            """
            
            cursor.execute(query, (time_threshold,))
            devices = cursor.fetchall()
            
            print(f"Found {len(devices)} devices that have been temporarily out for too long")
            
            # For each device, update status to "Missing" and create an alert
            count = 0
            for device in devices:
                device_id = device['device_id']
                last_update = device['last_update']
                
                # Warning if last_update is naive
                if not is_aware(last_update):
                    print(f"WARNING: Device {device_id} has a naive datetime for last_update: {last_update}")
                    # Assume it's in EST
                    last_update = TIMEZONE.localize(last_update)
                
                if last_update.tzinfo != TIMEZONE:
                    print(f"WARNING: Device {device_id} has a last_update with timezone {last_update.tzinfo} instead of {TIMEZONE}")
                    # Convert to EST
                    last_update = last_update.astimezone(TIMEZONE)
                
                # Hours since last update
                hours_since_update = (current_time_est - last_update).total_seconds() / 3600
                
                print(f"Device {device_id} ({device['device_name']}) - Last updated: {last_update} ({hours_since_update:.2f} hours ago)")
                print(f"  - MAC: {device['mac_address']}, Asset #: {device['asset_number']}")
                print(f"  - Reader Code: {device['reader_code']}, Antenna: {device['antenna_number']}")
                
                # Update device status to "Missing"
                update_query = """
                    UPDATE devices
                    SET status = 'Missing', updated_at = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (current_time_est, device_id))
                
                # Create RFID alert (using reader_code and antenna_number from last reader event)
                alert_id = str(uuid.uuid4())
                rfid_alert = RFIDAlert(
                    id=alert_id,
                    device_id=device_id,
                    hospital_id=device['hospital_id'],
                    location_id=None,  # Location is unknown for missing devices
                    reader_code=device['reader_code'],
                    antenna_number=device['antenna_number'],
                    previous_status='Temporarily Out',
                    timestamp=current_time_est
                )
                
                try:
                    # Create alert for missing device
                    db_service = DBService()
                    db_service.create_alert_for_missing_device(rfid_alert)
                    count += 1
                except Exception as e:
                    print(f"Error creating alert for missing device {device_id}: {e}")
            
            if count > 0:
                connection.commit()
                print(f"Updated {count} devices from 'Temporarily Out' to 'Missing'")
            else:
                print("No devices were updated to 'Missing'")
                
        except Exception as e:
            connection.rollback()
            print(f"Error checking for missing devices: {e}")
            traceback.print_exc()
        finally:
            cursor.close()
            connection.close()

    def check_and_update_status(self, device_id, current_status):
        """Check device status and update if needed based on time thresholds"""
        try:
            with self.db_service.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    # Get the current status for this device
                    query = """
                        SELECT status 
                        FROM devices 
                        WHERE id = %s
                    """
                    cursor.execute(query, (device_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        return False
                    
                    # If device is temporarily out or missing and read again, mark it as In-Facility
                    if current_status == 'Temporarily Out' or current_status == 'Missing':
                        result = self.db_service.update_device_status(device_id, 'In-Facility')
                        logger.info(f"Device {device_id} has returned to facility - marking as In-Facility (previous status: {current_status}) - success: {result}")
                        return True
                    
                    # If device is in facility, mark as temporarily out
                    if current_status == 'In-Facility':
                        result = self.db_service.update_device_status(device_id, 'Temporarily Out')
                        logger.info(f"Device {device_id} marked as Temporarily Out - success: {result}")
                        return True
                    
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking device status: {e}")
            return False

    def update_device_status(self, device_id, new_status):
        """Update device status while preserving other fields"""
        try:
            with self.db_service.get_connection() as connection:
                with connection.cursor() as cursor:
                    update_query = """
                        UPDATE devices 
                        SET status = %s,
                            updated_at = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (new_status, get_current_est_time(), device_id))
                    connection.commit()
                    logger.info(f"Updated device {device_id} status to {new_status}")
                    return True
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.connection_time = get_current_est_time()
            logger.info("Successfully connected to MQTT broker!")
            logger.debug(f"Connection flags: {flags}")
            logger.debug(f"Properties: {properties}")
            
            # Subscribe with QoS 1
            result, mid = self.subscribe([(MQTT_TOPIC, 1)])
            logger.info(f"Subscribed to topic: {MQTT_TOPIC} with QoS 1, Result: {result}, Message ID: {mid}")
            self.connected = True
            
            # Publish a test message to verify publishing works
            test_msg = {
                "test": "connection",
                "timestamp": get_current_est_time().isoformat()
            }
            self.publish(MQTT_TOPIC, json.dumps(test_msg), qos=1)
            
            # Ensure scheduler is running
            if not self.scheduler or not self.scheduler.running:
                logger.info("Scheduler not running on connect, starting...")
                self._init_scheduler()
            else:
                logger.info(f"Scheduler is already running with {len(self.scheduler.get_jobs())} jobs")
        else:
            logger.error(f"Failed to connect, reason code: {reason_code}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            self.message_count += 1
            self.last_message_time = get_current_est_time()
            
            logger.info(f"Received message on topic: {msg.topic}")
            logger.info(f"Message payload: {msg.payload.decode()}")
            
            # Parse and process the message
            try:
                data = json.loads(msg.payload.decode())
                if 'data' in data:
                    msg_data = data['data']
                    reader_code = msg_data.get('hostName')
                    antenna_number = msg_data.get('antenna')
                    rfid_tag = msg_data.get('idHex')
                    
                    if not all([reader_code, antenna_number, rfid_tag]):
                        logger.warning("Missing required fields in message")
                        return
                    
                    # First verify this is our reader
                    try:
                        reader_query = """
                            SELECT r.*, l.id as location_id, h.id as hospital_id
                            FROM readers r
                            LEFT JOIN locations l ON r.location_id = l.id
                            LEFT JOIN hospitals h ON r.hospital_id = h.id
                            WHERE r.reader_code = %s AND r.antenna_number = %s
                        """
                        with self.db_service.get_connection() as connection:
                            with connection.cursor(dictionary=True) as cursor:
                                cursor.execute(reader_query, (reader_code, antenna_number))
                                reader = cursor.fetchone()
                                
                        if not reader:
                            logger.info(f"Ignoring message - Reader {reader_code} with antenna {antenna_number} not found in our database")
                            return
                        
                        logger.info(f"Found reader {reader_code} at location {reader['location_id']}")
                    except Exception as e:
                        logger.error(f"Error checking reader: {e}")
                        return
                    
                    # Look up device by RFID tag
                    device = self.db_service.get_device_by_rfid(rfid_tag)
                    if device:
                        logger.info(f"Found device for RFID tag {rfid_tag}: {device['model']} ({device['serial_number']})")
                        logger.info(f"Device current status: {device['status']}, Last update time: {device['updated_at']}")
                        
                        # Store previous status for alert
                        previous_status = device['status']
                        current_status = None  # Will be set based on the transition
                        
                        # If device is in facility, mark as temporarily out immediately
                        if device['status'] == 'In-Facility':
                            logger.info(f"Attempting to change device status from In-Facility to Temporarily Out")
                            result = self.db_service.update_device_status(device['id'], 'Temporarily Out')
                            current_status = 'Temporarily Out'
                            logger.info(f"Device {device['id']} marked as Temporarily Out - success: {result}")
                        # If device is temporarily out or missing, mark as in-facility immediately
                        elif device['status'] == 'Temporarily Out' or device['status'] == 'Missing':
                            logger.info(f"Attempting to change device status from {device['status']} to In-Facility")
                            result = self.db_service.update_device_status(device['id'], 'In-Facility')
                            current_status = 'In-Facility'
                            logger.info(f"Device {device['id']} marked as In-Facility (was: {device['status']}) - success: {result}")
                        else:
                            # For any unexpected status, use the current status
                            current_status = device['status']
                            logger.info(f"Device {device['id']} status unchanged: {current_status}")
                        
                        # Create RFID alert regardless of status change
                        try:
                            alert = RFIDAlert(
                                device_id=device['id'],
                                reader_code=reader_code,
                                antenna_number=antenna_number,
                                rfid_tag=rfid_tag,
                                timestamp=get_current_est_time()
                            )
                            
                            # Add status information to the alert
                            alert.status = current_status
                            alert.previous_status = previous_status
                            
                            # Record the movement (this will create both reader_event and rfid_alert)
                            logger.info(f"Creating alert with status: {alert.status}, previous status: {alert.previous_status}")
                            self.db_service.record_movement(alert)
                            logger.info(f"Created alert for device {device['id']} at reader {reader_code} (antenna {antenna_number})")
                        except Exception as e:
                            logger.error(f"Error recording movement: {e}")
                    else:
                        logger.info(f"No device found for RFID tag: {rfid_tag}")
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse message as JSON")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def on_subscribe(self, client, userdata, mid, reason_code, properties):
        """Callback when subscription is confirmed"""
        logger.info(f"Subscription confirmed. Message ID: {mid}, Reason code: {reason_code}")
        if isinstance(reason_code, list):
            for rc in reason_code:
                logger.info(f"Subscription QoS level: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected"""
        self.connected = False
        logger.warning(f"Disconnected with result code: {rc}")
        if rc != 0:
            logger.error("Unexpected disconnection. Will attempt to reconnect.")

    def run(self):
        """Start the MQTT client and connect to the broker"""
        try:
            # Connect to database and initialize tables if needed
            self.initialize_database()
            
            # Make sure scheduler is running
            if not self.scheduler or not self.scheduler.running:
                logger.info("Scheduler not running, initializing...")
                self._init_scheduler()
                
            # Try to connect
            if self.connect():
                logger.info("Connected to the MQTT broker")
                
                # Start the scheduler to check for missing devices periodically
                logger.info("Starting scheduler for regular maintenance tasks")
                
                # Keep the main thread running
                while True:
                    if not self.client.is_connected():
                        logger.warning("Connection lost, attempting to reconnect...")
                        self.connect()
                    
                    # Periodically log that scheduler is running to confirm it's active
                    if self.scheduler and self.scheduler.running:
                        logger.debug(f"Scheduler is running with {len(self.scheduler.get_jobs())} jobs")
                    else:
                        logger.warning("Scheduler is not running! Attempting to restart...")
                        self._init_scheduler()
                    
                    time.sleep(60)  # Check connection and log scheduler status every minute
            else:
                logger.error("Failed to connect to the MQTT broker")
        except KeyboardInterrupt:
            logger.info("Stopping MQTT client")
            self.shutdown_scheduler()
            if self.client.is_connected():
                self.client.disconnect()
        except Exception as e:
            logger.error(f"Error running MQTT client: {e}")
            self.shutdown_scheduler()
            if self.client.is_connected():
                self.client.disconnect()
                
    def shutdown_scheduler(self):
        """Safely shut down the scheduler"""
        if hasattr(self, 'scheduler') and self.scheduler:
            logger.info("Shutting down scheduler...")
            try:
                self.scheduler.shutdown()
                logger.info("Scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {e}")

def main():
    # Verify certificates exist
    verify_certificates()
    
    # Create MQTT client with persistent session
    client = MQTTClient(
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="ec2-rfid-client"  # Add a specific client ID
    )
    
    # Configure TLS
    client.tls_set(
        ca_certs=ROOT_CA,
        certfile=CERTIFICATE,
        keyfile=PRIVATE_KEY,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    
    # Set reconnect behavior
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    
    try:
        logger.info(f"Connecting to {MQTT_ENDPOINT}...")
        client.connect(MQTT_ENDPOINT, MQTT_PORT, MQTT_KEEP_ALIVE)
        
        # Start the loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        client.disconnect()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 