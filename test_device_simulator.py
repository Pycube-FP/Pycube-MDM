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
import threading
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_COMMAND_TOPIC = "6B6035_commands"  # Channel to listen for commands
MQTT_RESPONSE_TOPIC = "6B6035_response"  # Channel to send responses
MQTT_PORT = 8883

# Certificate paths
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

# Device configuration
DEVICE_ID = "BAYCARE-R001"  # This device's ID
SUPPORTED_COMMANDS = [
    "GET_DEVICE_STATUS", 
    "RESTART_READER", 
    "UPDATE_CONFIG", 
    "GET_DIAGNOSTICS"
]

# Track state
stop_event = threading.Event()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == mqtt.CONNACK_ACCEPTED:
        logger.info("Connected to MQTT broker")
        # Subscribe to command topic
        logger.info(f"Subscribing to command topic: {MQTT_COMMAND_TOPIC}")
        client.subscribe(MQTT_COMMAND_TOPIC, qos=1)
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")

def on_message(client, userdata, msg):
    """Callback when a message is received - process command and send response"""
    try:
        logger.info(f"Received message on topic: {msg.topic}")
        payload = msg.payload.decode()
        logger.info(f"Message payload: {payload}")
        
        # Try to parse JSON
        try:
            data = json.loads(payload)
            
            # Check if this is a command
            if 'command' in data:
                command = data['command']
                command_id = command.get('id')
                command_type = command.get('type')
                target_id = command.get('target')
                params = command.get('parameters', {})
                
                logger.info(f"Received command: {command_type}, ID: {command_id}, Target: {target_id}")
                
                # Check if the command is for this device or is a broadcast
                if target_id and target_id != DEVICE_ID:
                    logger.info(f"Command not for this device, ignoring (Target: {target_id}, This device: {DEVICE_ID})")
                    return
                
                # Process command and create response
                response_data = process_command(command_type, params)
                
                # Build response message
                response = {
                    "response": {
                        "command_id": command_id,
                        "type": command_type,
                        "device_id": DEVICE_ID,
                        "timestamp": datetime.now().isoformat(),
                        "status": response_data.get("status", "SUCCESS")
                    }
                }
                
                # Add any data or error
                if "data" in response_data:
                    response["response"]["data"] = response_data["data"]
                if "error" in response_data:
                    response["response"]["error"] = response_data["error"]
                
                # Simulate processing delay (0.5-2 seconds)
                time.sleep(random.uniform(0.5, 2))
                
                # Send response
                result = client.publish(MQTT_RESPONSE_TOPIC, json.dumps(response), qos=1)
                logger.info(f"Published response for command {command_id}, result: {result}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message as JSON: {e}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

def process_command(command_type, params):
    """Process the received command and generate appropriate response"""
    
    # Check if command is supported
    if command_type not in SUPPORTED_COMMANDS:
        return {
            "status": "ERROR",
            "error": f"Unsupported command: {command_type}"
        }
    
    # Process different command types
    if command_type == "GET_DEVICE_STATUS":
        # Return simulated device status
        return {
            "status": "SUCCESS",
            "data": {
                "device_id": DEVICE_ID,
                "status": "ONLINE",
                "uptime": random.randint(100, 10000),
                "battery": "90%",
                "signal_strength": random.randint(70, 99),
                "last_seen": datetime.now().isoformat(),
                "firmware_version": "v2.3.1",
                "tag_reads_today": random.randint(50, 500),
                "history": generate_history() if params.get("include_history") else None
            }
        }
        
    elif command_type == "RESTART_READER":
        # Simulate reader restart
        return {
            "status": "SUCCESS",
            "data": {
                "device_id": DEVICE_ID,
                "restart_initiated": True,
                "estimated_boot_time": "30 seconds"
            }
        }
        
    elif command_type == "UPDATE_CONFIG":
        # Check if all required parameters are present
        required_params = ["scan_interval", "power_level"]
        missing_params = [p for p in required_params if p not in params]
        
        if missing_params:
            return {
                "status": "ERROR",
                "error": f"Missing required parameters: {', '.join(missing_params)}"
            }
        
        # Validate parameter values
        if params.get("power_level", 0) > 30:
            return {
                "status": "WARNING",
                "data": {
                    "power_level_adjusted": True,
                    "original_value": params.get("power_level"),
                    "adjusted_value": 30,
                    "scan_interval": params.get("scan_interval"),
                    "filter_mode": params.get("filter_mode", "NONE"),
                    "tag_pattern": params.get("tag_pattern", "")
                },
                "error": "Power level adjusted to maximum allowed value of 30"
            }
        
        # Return success response for config update
        return {
            "status": "SUCCESS",
            "data": {
                "config_updated": True,
                "applied_settings": {
                    "scan_interval": params.get("scan_interval"),
                    "power_level": params.get("power_level"),
                    "filter_mode": params.get("filter_mode", "NONE"),
                    "tag_pattern": params.get("tag_pattern", "")
                }
            }
        }
        
    elif command_type == "GET_DIAGNOSTICS":
        # Return simulated diagnostics data
        return {
            "status": "SUCCESS",
            "data": {
                "device_id": DEVICE_ID,
                "cpu_usage": f"{random.randint(5, 80)}%",
                "memory_usage": f"{random.randint(30, 90)}%",
                "disk_usage": f"{random.randint(10, 70)}%",
                "temperature": f"{random.randint(35, 65)}°C",
                "network": {
                    "connected": True,
                    "signal_strength": random.randint(70, 99),
                    "ip_address": "192.168.1." + str(random.randint(2, 254)),
                    "mac_address": "00:1A:2B:3C:4D:5E"
                },
                "antennas": [
                    {"id": 1, "status": "ACTIVE", "power": 25},
                    {"id": 2, "status": "ACTIVE", "power": 25},
                    {"id": 3, "status": "ACTIVE", "power": 25},
                    {"id": 4, "status": "ACTIVE", "power": 25}
                ],
                "last_error": None,
                "firmware": {
                    "version": "v2.3.1",
                    "last_updated": "2023-04-01T10:30:00Z"
                }
            }
        }
    
    # Default error response for unhandled command
    return {
        "status": "ERROR",
        "error": "Command processing failed"
    }

def generate_history():
    """Generate simulated device history"""
    history = []
    now = datetime.now()
    
    for i in range(5):
        hours_ago = i * 2
        timestamp = (now.replace(microsecond=0) - 
                    datetime.timedelta(hours=hours_ago, 
                                      minutes=random.randint(0, 59)))
        
        history.append({
            "timestamp": timestamp.isoformat(),
            "event": random.choice(["BOOT", "CONFIG_CHANGE", "TAG_READ", "ALERT"]),
            "details": f"Simulated history event #{i+1}"
        })
    
    return history

def on_subscribe(client, userdata, mid, reason_code, properties):
    """Callback when subscription is confirmed"""
    logger.info(f"Subscription confirmed. Message ID: {mid}")
    if isinstance(reason_code, list):
        for i, rc in enumerate(reason_code):
            logger.info(f"QoS for subscription {i+1}: {rc}")
    else:
        logger.info(f"QoS: {reason_code}")

def on_publish(client, userdata, mid):
    """Callback when message is published"""
    logger.info(f"Response with message ID {mid} has been published")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected"""
    logger.warning(f"Disconnected with result code: {rc}")

def user_input_thread():
    """Thread to wait for user input to stop the program"""
    input("Press Enter to stop the device simulator...\n")
    stop_event.set()

def main():
    # Create MQTT client
    client = mqtt.Client(
        protocol=mqtt.MQTTv5, 
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"device-simulator-{DEVICE_ID}"
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    
    # Configure TLS
    client.tls_set(
        ca_certs=ROOT_CA,
        certfile=CERTIFICATE,
        keyfile=PRIVATE_KEY,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    
    # Create a thread for user input
    input_thread = threading.Thread(target=user_input_thread)
    input_thread.daemon = True
    
    try:
        # Connect to broker
        logger.info(f"Connecting to MQTT broker at {MQTT_ENDPOINT}...")
        client.connect(MQTT_ENDPOINT, MQTT_PORT, 60)
        
        # Start the loop and user input thread
        client.loop_start()
        input_thread.start()
        
        # Log that we're ready to process commands
        logger.info(f"Device simulator for {DEVICE_ID} is running!")
        logger.info(f"Supported commands: {', '.join(SUPPORTED_COMMANDS)}")
        
        # Wait for user to press Enter or a timeout (whichever comes first)
        start_time = time.time()
        while not stop_event.is_set() and (time.time() - start_time < 3600):  # Max 1 hour
            time.sleep(1)
            
            # Print a message every 30 seconds to show we're still alive
            elapsed = time.time() - start_time
            if elapsed % 30 < 1:
                logger.info(f"Device simulator active for {int(elapsed)} seconds, waiting for commands...")
        
        # Clean disconnect
        logger.info("Disconnecting from MQTT broker...")
        client.disconnect()
        client.loop_stop()
        logger.info("Disconnected from MQTT broker")
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        client.disconnect()
        client.loop_stop()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        if client.is_connected():
            client.disconnect()
            client.loop_stop()

if __name__ == "__main__":
    main() 
>>>>>>> 7e9c7d28f18c115a500fac5c8144aac5449b9049
