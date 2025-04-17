import paho.mqtt.client as mqtt
import ssl
import os
import json
import time
import logging
import uuid
from datetime import datetime
import argparse

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
        # Ready to send commands
        logger.info("Ready to send custom command...")
        if userdata and 'command' in userdata:
            send_custom_command(client, userdata['command'])
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    """Callback when message is published"""
    logger.info(f"Command with message ID {mid} has been published")
    if reason_code is not None:
        logger.info(f"Publish result: {reason_code}")

def send_custom_command(client, command_json):
    """Send a custom command from the provided JSON"""
    try:
        # Try to parse the JSON if it's a string
        if isinstance(command_json, str):
            command_data = json.loads(command_json)
        else:
            command_data = command_json
            
        # Check command structure and format appropriately
        if 'command' in command_data:
            # If 'command' is a string (like "get_mode"), it needs special handling
            if isinstance(command_data['command'], str):
                # Create a proper command structure using the string as the type
                command_type = command_data['command']
                command_id = command_data.get('command_id', str(uuid.uuid4()))
                
                # Build a structured command
                full_command = {
                    "command": {
                        "id": command_id,
                        "type": command_type,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                # Add any payload if present
                if 'payload' in command_data:
                    full_command['command']['parameters'] = command_data['payload']
            else:
                # Command is already a nested object
                full_command = command_data
                
                # Ensure the command has an ID
                if 'id' not in full_command['command']:
                    full_command['command']['id'] = str(uuid.uuid4())
                
                # Add timestamp if not present
                if 'timestamp' not in full_command['command']:
                    full_command['command']['timestamp'] = datetime.now().isoformat()
        else:
            # Wrap in command structure if needed
            full_command = {
                "command": {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Copy all fields from input to command
            for key, value in command_data.items():
                full_command['command'][key] = value
            
        # Send the command
        command_str = json.dumps(full_command)
        logger.info(f"Sending command: {command_str}")
        result = client.publish(MQTT_COMMAND_TOPIC, command_str, qos=1)
        
        command_id = full_command['command'].get('id')
        logger.info(f"Published custom command (ID: {command_id}), result: {result}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Error sending command: {e}", exc_info=True)

def interactive_mode(client):
    """Interactive mode for sending commands"""
    print("\n=== Custom Command Sender ===")
    print("Enter JSON command (type 'exit' to quit):")
    print("Example format: {\"type\": \"GET_DEVICE_STATUS\", \"target\": \"BAYCARE-R001\", \"parameters\": {\"include_history\": true}}")
    
    while True:
        try:
            # Get user input
            user_input = input("\nEnter command (or type 'exit'): ")
            
            if user_input.lower() == 'exit':
                break
                
            # Check if it's a simplified command (just command content)
            try:
                command_data = json.loads(user_input)
                
                # Create a wrapper command structure if needed
                if 'command' not in command_data:
                    command = {
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Copy all fields from input to command
                    for key, value in command_data.items():
                        command[key] = value
                        
                    # Wrap in the full command structure
                    full_command = {"command": command}
                else:
                    full_command = command_data
                    
                # Send the command
                send_custom_command(client, full_command)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format: {e}")
                print(f"Error: {e}. Please enter valid JSON.")
                
        except KeyboardInterrupt:
            break
    
    print("Exiting interactive mode...")

def main():
    # Define global variable access first
    global MQTT_COMMAND_TOPIC
    
    parser = argparse.ArgumentParser(description='Send custom MQTT commands')
    parser.add_argument('--json', type=str, help='JSON command to send (if not provided, interactive mode is used)')
    parser.add_argument('--topic', type=str, default=MQTT_COMMAND_TOPIC, help=f'MQTT topic to publish to (default: {MQTT_COMMAND_TOPIC})')
    
    args = parser.parse_args()
    
    # Update topic if provided
    if args.topic:
        MQTT_COMMAND_TOPIC = args.topic
    
    # Create MQTT client
    client = mqtt.Client(
        protocol=mqtt.MQTTv5, 
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="custom-command-sender-" + str(uuid.uuid4())[-8:]
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # Set user data if command provided
    if args.json:
        client.user_data_set({'command': args.json})
    
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
        
        # If no command provided, enter interactive mode
        if not args.json:
            interactive_mode(client)
        else:
            # Wait for command to be published
            time.sleep(3)
        
        client.disconnect()
        client.loop_stop()
        logger.info("Disconnected from MQTT broker")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 