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

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only console output
    ]
)
logger = logging.getLogger(__name__)

# Enable Paho MQTT debug
logger_paho = logging.getLogger('paho.mqtt')
logger_paho.setLevel(logging.DEBUG)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_TOPIC = "6B6035_tagdata"
MQTT_PORT = 8883
KEEP_ALIVE = 60

# Timezone configuration
TIMEZONE = pytz.timezone('America/New_York')

# Certificate paths for EC2
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

# Duplicate alert threshold
DUPLICATE_THRESHOLD = timedelta(minutes=30)  # Minimum time between alerts for same device

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

class MQTTClient(mqtt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False
        self.message_count = 0
        self.last_message_time = None
        self.connection_time = None
        self.db_service = DBService()
        
        # Set clean session to False to maintain subscription state
        self.clean_session = False
        
        # Enable internal MQTT client debugging
        self.enable_logger(logger)

    def check_recent_alert(self, rfid_tag):
        """Check if there's a recent alert for this RFID tag"""
        try:
            with self.db_service.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    # Get the most recent alert for this RFID tag
                    query = """
                        SELECT timestamp 
                        FROM rfid_alerts 
                        WHERE rfid_tag = %s 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """
                    cursor.execute(query, (rfid_tag,))
                    result = cursor.fetchone()
                    
                    if result:
                        last_alert_time = result['timestamp']
                        # Make sure the timestamp has timezone info
                        if not last_alert_time.tzinfo:
                            last_alert_time = TIMEZONE.localize(last_alert_time)
                            
                        time_since_last = get_current_est_time() - last_alert_time
                        if time_since_last < DUPLICATE_THRESHOLD:
                            logger.info(f"Found recent alert from {last_alert_time.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                                      f"({time_since_last.total_seconds():.0f} seconds ago)")
                            return True
                            
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking recent alerts: {e}")
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
                    
                    # Check for recent alerts for this RFID tag
                    if self.check_recent_alert(rfid_tag):
                        logger.info(f"Skipping duplicate alert for RFID tag {rfid_tag}")
                        return
                    
                    # Look up device by RFID tag
                    device = self.db_service.get_device_by_rfid(rfid_tag)
                    if device:
                        logger.info(f"Found device for RFID tag {rfid_tag}: {device['model']} ({device['serial_number']})")
                        
                        # Update device status to Missing
                        try:
                            update_query = """
                                UPDATE devices 
                                SET status = 'Missing',
                                    updated_at = %s,
                                    serial_number = serial_number,
                                    model = model,
                                    manufacturer = manufacturer,
                                    rfid_tag = rfid_tag,
                                    barcode = barcode,
                                    hospital_id = hospital_id,
                                    location_id = location_id,
                                    assigned_to = assigned_to,
                                    purchase_date = purchase_date,
                                    last_maintenance_date = last_maintenance_date,
                                    eol_date = eol_date,
                                    eol_status = eol_status,
                                    eol_notes = eol_notes,
                                    created_at = created_at
                                WHERE id = %s
                            """
                            with self.db_service.get_connection() as connection:
                                with connection.cursor() as cursor:
                                    cursor.execute(update_query, (get_current_est_time(), device['id']))
                                    connection.commit()
                            logger.info(f"Updated device {device['id']} status to Missing while preserving other fields")
                        except Exception as e:
                            logger.error(f"Error updating device status: {e}")
                        
                        # Create RFID alert with Eastern Time
                        alert = RFIDAlert(
                            device_id=device['id'],
                            reader_code=reader_code,
                            antenna_number=antenna_number,
                            rfid_tag=rfid_tag,
                            timestamp=get_current_est_time()
                        )
                        
                        # Record the movement (this will create both reader_event and rfid_alert)
                        try:
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
        client.connect(MQTT_ENDPOINT, MQTT_PORT, KEEP_ALIVE)
        
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