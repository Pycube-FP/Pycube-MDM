import paho.mqtt.client as mqtt
import ssl
import os
import json
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_TOPIC = "7758D5_OFC1_events"
MQTT_PORT = 8883

# Certificate paths
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == mqtt.CONNACK_ACCEPTED:
        logger.info("Connected to MQTT broker")
        # Send multiple test messages
        for i in range(5):  # Send 5 test messages
            test_message = {
                "type": "test",
                "message": f"Test message #{i+1} from EC2",
                "timestamp": datetime.now().isoformat()
            }
            result = client.publish(MQTT_TOPIC, json.dumps(test_message), qos=1)
            logger.info(f"Published test message #{i+1}, result: {result}")
            time.sleep(2)  # Wait 2 seconds between messages
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")

def on_publish(client, userdata, mid):
    """Callback when message is published"""
    logger.info(f"Message {mid} has been published")

def main():
    # Create MQTT client
    client = mqtt.Client(protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # Configure TLS
    client.tls_set(
        ca_certs=ROOT_CA,
        certfile=CERTIFICATE,
        keyfile=PRIVATE_KEY,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    
    try:
        logger.info("Connecting to MQTT broker...")
        client.connect(MQTT_ENDPOINT, MQTT_PORT, 60)
        client.loop_start()
        
        # Wait longer for messages to be published
        time.sleep(15)  # Wait 15 seconds total
        
        client.disconnect()
        client.loop_stop()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 