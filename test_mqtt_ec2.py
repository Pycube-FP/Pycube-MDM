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
import sys

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout)  # Ensure logs go to stdout
    ]
)
logger = logging.getLogger(__name__)

# Enable APScheduler logging
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Enable Paho MQTT debug
logger_paho = logging.getLogger('paho.mqtt')
logger_paho.setLevel(logging.DEBUG)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_TOPIC = "6B6035_tagdata"
MQTT_PORT = 8883
KEEP_ALIVE = 60

# Logging configuration
LOG_DIRECTORY = os.path.expanduser("~/logs")

# Timezone configuration
TIMEZONE = pytz.timezone('America/New_York')

# Readers at exit gates (for status change logic)
EXIT_GATES = ["EXIT1", "EXIT2", "EXIT3"]  # Replace with actual exit reader IDs

# Certificate paths for EC2
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

# Constants for status change thresholds
STATUS_CHANGE_THRESHOLD = timedelta(minutes=0)  # No delay between status changes
MISSING_THRESHOLD = timedelta(minutes=2)  # Time after which a temporarily out device is considered missing

def get_current_est_time():
    """Get current time in Eastern Time"""
    return datetime.now(TIMEZONE)

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

class MQTTClient:
    def __init__(self, broker=MQTT_ENDPOINT, port=MQTT_PORT, topics=[MQTT_TOPIC], exit_gates=EXIT_GATES):
        """Initialize the MQTT client"""
        # Set up the MQTT client
        self.broker = broker
        self.port = port
        self.topics = topics if isinstance(topics, list) else [topics]
        self.exit_gates = exit_gates
        self.scheduler = None
        
        # Create a new client instance
        client_id = f'pycube-mdm-client-{os.getpid()}-{time.time()}'
        self.client = mqtt.Client(client_id=client_id)
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Configure TLS with the certificate files from constants
        if all(os.path.exists(f) for f in [ROOT_CA, CERTIFICATE, PRIVATE_KEY]):
            logger.info("Setting up TLS with certificates")
            self.client.tls_set(
                ca_certs=ROOT_CA,
                certfile=CERTIFICATE,
                keyfile=PRIVATE_KEY,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            # Set reconnect behavior
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        else:
            logger.warning("Certificates not found, connecting without TLS")
        
        self.connected = False
        self.message_count = 0
        self.last_message_time = None
        self.connection_time = None
        self.db_service = DBService()
        
        # Set clean session to False to maintain subscription state
        self.clean_session = False
        
        # Enable internal MQTT client debugging
        self.enable_logger(logger)

    def initialize_database(self):
        """Initialize database connection and tables"""
        try:
            logger.info("Initializing database connection...")
            # Check if the DBService has an initialize_db method
            if hasattr(self.db_service, 'initialize_db'):
                self.db_service.initialize_db()
                logger.info("Database initialized successfully")
            else:
                # If not, assume the constructor handles initialization
                logger.info("Using pre-initialized database connection")
            
            # Test the connection by getting a device or some simple operation
            try:
                result = self.db_service.execute_query("SELECT 1")
                logger.info("Database connection test successful")
            except Exception as e:
                logger.error(f"Database connection test failed: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)

    def check_for_missing_devices(self):
        """Check for devices that have been temporarily out for too long and mark them as missing"""
        try:
            logger.info("Checking for devices that have been temporarily out for too long...")
            with self.db_service.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    query = """
                        SELECT id, updated_at, serial_number
                        FROM devices
                        WHERE status = 'Temporarily Out'
                    """
                    cursor.execute(query)
                    temp_out_devices = cursor.fetchall()
                    
                    logger.info(f"Found {len(temp_out_devices)} devices with 'Temporarily Out' status")
                    
                    if len(temp_out_devices) == 0:
                        logger.info("No devices to check for missing status")
                        return
                    
                    current_time = get_current_est_time()
                    marked_missing_count = 0
                    
                    for device in temp_out_devices:
                        # Make sure the timestamp has timezone info
                        last_update = device['updated_at']
                        if not last_update.tzinfo:
                            last_update = TIMEZONE.localize(last_update)
                            
                        time_since_update = current_time - last_update
                        time_minutes = time_since_update.total_seconds() / 60
                        
                        logger.info(f"Device {device['id']} ({device.get('serial_number', 'Unknown')}) has been out for {time_minutes:.1f} minutes (threshold: {MISSING_THRESHOLD.total_seconds()/60} minutes)")
                        
                        if time_since_update >= MISSING_THRESHOLD:
                            result = self.db_service.update_device_status(device['id'], 'Missing')
                            logger.info(f"Device {device['id']} has been out for {time_minutes:.1f} minutes - marking as Missing - success: {result}")
                            marked_missing_count += 1
                        else:
                            logger.info(f"Device {device['id']} has not exceeded the threshold ({time_minutes:.1f} < {MISSING_THRESHOLD.total_seconds()/60} minutes) - no status change")
                    
                    logger.info(f"Marked {marked_missing_count} of {len(temp_out_devices)} devices as Missing based on time threshold")
            
            logger.info("Finished checking for missing devices")
        except Exception as e:
            logger.error(f"Error checking for missing devices: {e}", exc_info=True)

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

    def on_connect(self, client, userdata, flags, rc):
        """Callback when the client receives a CONNACK response from the server"""
        connection_status = {
            0: "Connection successful",
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier",
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorised"
        }
        
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            # Subscribe to topics on successful connection
            for topic in self.topics:
                self.client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            status = connection_status.get(rc, f"Unknown error (code {rc})")
            logger.error(f"Failed to connect to MQTT broker: {status}")

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
        """Callback when disconnected from MQTT broker"""
        if rc == 0:
            logger.info("Disconnected from MQTT broker")
        else:
            logger.warning(f"Unexpected disconnect from MQTT broker with code {rc}")
        self.connected = False

    def run(self):
        """Connect to the MQTT broker and run forever"""
        # Set up logging for APScheduler
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)
        
        # Initialize database
        self.initialize_database()
        
        # Start the scheduler
        logger.info("Starting scheduler service...")
        self.start_scheduler()

        try:
            # Connect to the MQTT broker
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, 60)
            
            # Start the MQTT client loop - this will handle reconnections automatically
            logger.info("Starting MQTT client loop...")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Error in MQTT connection: {e}", exc_info=True)
        finally:
            # Clean up
            logger.info("Shutting down MQTT client and scheduler...")
            self.client.loop_stop()
            self.shutdown_scheduler()
            if self.client.is_connected():
                self.client.disconnect()
            logger.info("Shutdown complete")

    def log_scheduler_status(self):
        """Log that the scheduler is running and list all jobs"""
        try:
            if self.scheduler and self.scheduler.running:
                jobs = self.scheduler.get_jobs()
                logger.info("SCHEDULER STATUS: Running with %d jobs", len(jobs))
                for job in jobs:
                    logger.info("SCHEDULER JOB: %s, next run: %s", job.id, job.next_run_time)
            else:
                logger.warning("SCHEDULER STATUS: Not running")
                self.start_scheduler()
        except Exception as e:
            logger.error(f"Error logging scheduler status: {e}", exc_info=True)
    
    def start_scheduler(self):
        """Start the scheduler if it's not already running"""
        try:
            if not self.scheduler or not self.scheduler.running:
                logger.info("Starting scheduler...")
                self.scheduler = BackgroundScheduler(timezone=TIMEZONE, daemon=False)
                self.scheduler.add_job(
                    self.check_for_missing_devices, 
                    'interval', 
                    minutes=2,
                    id='check_missing_devices',
                    next_run_time=datetime.now(TIMEZONE) + timedelta(seconds=5)
                )
                self.scheduler.add_job(
                    self.log_scheduler_status,
                    'interval',
                    seconds=60,
                    id='log_scheduler_status',
                    next_run_time=datetime.now(TIMEZONE) + timedelta(seconds=15)
                )
                self.scheduler.start()
                logger.info("Scheduler restarted successfully with %d jobs", len(self.scheduler.get_jobs()))
                
                # Force immediate run
                self.check_for_missing_devices()
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)
    
    def shutdown_scheduler(self):
        """Safely shut down the scheduler"""
        if hasattr(self, 'scheduler') and self.scheduler:
            logger.info("Shutting down scheduler...")
            try:
                self.scheduler.shutdown()
                logger.info("Scheduler shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down scheduler: {e}", exc_info=True)

    def enable_logger(self, logger):
        """Enable MQTT client internal logging"""
        try:
            self.client.enable_logger(logger)
            logger.info("MQTT client internal logging enabled")
        except Exception as e:
            logger.warning(f"Failed to enable MQTT client internal logging: {e}")
            # Continue without internal logging

def main():
    # Verify certificates exist
    for cert_file in [ROOT_CA, CERTIFICATE, PRIVATE_KEY]:
        if not os.path.exists(cert_file):
            logger.error(f"Certificate file not found: {cert_file}")
            sys.exit(1)
    
    try:
        # Log directory check and creation
        if not os.path.exists(LOG_DIRECTORY):
            os.makedirs(LOG_DIRECTORY)
            logger.info(f"Created log directory: {LOG_DIRECTORY}")
        
        # Create and run MQTT client
        client = MQTTClient(
            broker=MQTT_ENDPOINT,
            port=MQTT_PORT,
            topics=[MQTT_TOPIC],
            exit_gates=EXIT_GATES
        )
        
        # Run the client (this will handle connections, scheduler, etc.)
        client.run()
        
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    
    logger.info("MQTT service exiting")

if __name__ == "__main__":
    main() 