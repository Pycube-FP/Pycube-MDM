import paho.mqtt.client as mqtt
import time
import logging
import ssl
import os
import json
from pathlib import Path
from datetime import datetime

# Set up logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mqtt_debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Enable Paho MQTT debug
logger_paho = logging.getLogger('paho.mqtt')
logger_paho.setLevel(logging.DEBUG)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_TOPIC = "7758D5_OFC1_events"
MQTT_PORT = 8883
KEEP_ALIVE = 60

# Certificate paths for EC2
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

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
        
        # Set clean session to False to maintain subscription state
        self.clean_session = False
        
        # Enable internal MQTT client debugging
        self.enable_logger(logger)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.connection_time = datetime.now()
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
                "timestamp": datetime.now().isoformat()
            }
            self.publish(MQTT_TOPIC, json.dumps(test_msg), qos=1)
        else:
            logger.error(f"Failed to connect, reason code: {reason_code}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()
            
            logger.info(f"Received message on topic: {msg.topic}")
            logger.info(f"Message payload: {msg.payload.decode()}")
            
            # Parse and log the specific fields we expect
            try:
                data = json.loads(msg.payload.decode())
                if 'data' in data and 'MAC' in data['data']:
                    logger.info(f"Received RFID event from MAC: {data['data']['MAC']}")
                    logger.info(f"Event Number: {data['data'].get('eventNum')}")
                    logger.info(f"ID Hex: {data['data'].get('idHex')}")
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