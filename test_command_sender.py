<<<<<<< HEAD
 
=======
import paho.mqtt.client as mqtt
import ssl
import os
import json
import time
import logging
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_COMMAND_TOPIC = "6B6035_commands"  # Channel for sending commands
MQTT_PORT = 8883

# Certificate paths
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == mqtt.CONNACK_ACCEPTED:
        logger.info("Connected to MQTT broker")
        # Send command after connection is established
        send_commands(client)
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")

def on_publish(client, userdata, mid):
    """Callback when message is published"""
    logger.info(f"Command with message ID {mid} has been published")

def generate_command_message(command_type, target_id=None, parameters=None):
    """Generate a command message with a unique ID"""
    command_id = str(uuid.uuid4())
    
    message = {
        "command": {
            "id": command_id,
            "type": command_type,
            "timestamp": datetime.now().isoformat(),
            "target": target_id
        }
    }
    
    if parameters:
        message["command"]["parameters"] = parameters
        
    return message, command_id

def send_commands(client):
    """Send various test commands to the command channel"""
    
    # Command 1: Get device status
    command1, cmd_id1 = generate_command_message(
        command_type="GET_DEVICE_STATUS",
        target_id="BAYCARE-R001",  # Reader ID 
        parameters={"include_history": True}
    )
    
    result = client.publish(MQTT_COMMAND_TOPIC, json.dumps(command1), qos=1)
    logger.info(f"Published GET_DEVICE_STATUS command (ID: {cmd_id1}), result: {result}")
    time.sleep(3)  # Wait for response
    
    # Command 2: Restart reader
    command2, cmd_id2 = generate_command_message(
        command_type="RESTART_READER",
        target_id="BAYCARE-R002"  # A different reader
    )
    
    result = client.publish(MQTT_COMMAND_TOPIC, json.dumps(command2), qos=1)
    logger.info(f"Published RESTART_READER command (ID: {cmd_id2}), result: {result}")
    time.sleep(3)  # Wait for response
    
    # Command 3: Update reader configuration
    command3, cmd_id3 = generate_command_message(
        command_type="UPDATE_CONFIG",
        target_id="BAYCARE-R001",
        parameters={
            "scan_interval": 30,
            "power_level": 25,
            "filter_mode": "INCLUDE",
            "tag_pattern": "E28011*"
        }
    )
    
    result = client.publish(MQTT_COMMAND_TOPIC, json.dumps(command3), qos=1)
    logger.info(f"Published UPDATE_CONFIG command (ID: {cmd_id3}), result: {result}")
    time.sleep(3)  # Wait for response
    
    # Command 4: Get reader diagnostics
    command4, cmd_id4 = generate_command_message(
        command_type="GET_DIAGNOSTICS",
        target_id="BAYCARE-R001"
    )
    
    result = client.publish(MQTT_COMMAND_TOPIC, json.dumps(command4), qos=1)
    logger.info(f"Published GET_DIAGNOSTICS command (ID: {cmd_id4}), result: {result}")
    
    logger.info("All test commands have been sent. Check response listener for replies.")
    
def main():
    # Create MQTT client
    client = mqtt.Client(
        protocol=mqtt.MQTTv5, 
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="command-sender-client"
    )
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
        
        # Wait for all commands to be published
        time.sleep(15)
        
        client.disconnect()
        client.loop_stop()
        logger.info("Disconnected from MQTT broker")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 
>>>>>>> 7e9c7d28f18c115a500fac5c8144aac5449b9049
