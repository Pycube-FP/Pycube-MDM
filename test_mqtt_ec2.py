import paho.mqtt.client as mqtt
import time
import logging
import ssl
import os
import json
from pathlib import Path
from datetime import datetime

# Set up logging
log_filename = f'mqtt_client_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)

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

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.connection_time = datetime.now()
            logger.info("Successfully connected to MQTT broker!")
            self.subscribe(MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
            self.connected = True
        else:
            logger.error(f"Failed to connect, reason code: {reason_code}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        duration = ""
        if self.connection_time:
            duration = f" (Connection duration: {datetime.now() - self.connection_time})"
        logger.warning(f"Disconnected from MQTT broker with code: {rc}{duration}")

    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()
            
            logger.info(f"Message #{self.message_count} received on topic: {msg.topic}")
            payload = msg.payload.decode()
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
                logger.info(f"Parsed JSON data: {json.dumps(data, indent=2)}")
                
                # Add your message processing logic here
                # For example:
                # process_rfid_event(data)
                
            except json.JSONDecodeError:
                logger.warning(f"Received message is not valid JSON: {payload}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def get_status(self):
        """Get current client status"""
        status = {
            "connected": self.connected,
            "messages_received": self.message_count,
            "last_message_time": self.last_message_time,
            "connection_time": self.connection_time
        }
        return status

def main():
    # Verify certificates exist
    verify_certificates()
    
    # Create MQTT client
    client = MQTTClient(protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        # Configure TLS/SSL
        logger.info("Setting up TLS configuration...")
        client.tls_set(
            ca_certs=ROOT_CA,
            certfile=CERTIFICATE,
            keyfile=PRIVATE_KEY,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        
        # Configure reconnection behavior
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        
        while True:
            try:
                if not client.connected:
                    logger.info(f"Attempting to connect to {MQTT_ENDPOINT}...")
                    client.connect(MQTT_ENDPOINT, MQTT_PORT, KEEP_ALIVE)
                    client.loop_start()
                
                # Keep the script running and monitor connection
                while client.connected:
                    time.sleep(1)
                    # Log status every hour
                    if datetime.now().minute == 0 and datetime.now().second == 0:
                        status = client.get_status()
                        logger.info(f"Status update: {json.dumps(status, default=str)}")
                
                # If we get here, we lost connection
                logger.warning("Lost connection, attempting to reconnect...")
                client.loop_stop()
                time.sleep(5)  # Wait before reconnecting
                
            except Exception as e:
                logger.error(f"Connection error: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying
                
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        status = client.get_status()
        logger.info(f"Final status: {json.dumps(status, default=str)}")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 