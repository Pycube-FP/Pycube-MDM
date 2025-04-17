import paho.mqtt.client as mqtt
import ssl
import os
import json
import time
import logging
from datetime import datetime
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT configuration
MQTT_ENDPOINT = "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com"
MQTT_RESPONSE_TOPIC = "6B6035_responses"  # Channel for receiving command responses
MQTT_PORT = 8883

# Certificate paths
CERTS_DIR = os.path.expanduser("~/certs")
PRIVATE_KEY = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key")
CERTIFICATE = os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt")
ROOT_CA = os.path.join(CERTS_DIR, "AmazonRootCA1.pem")

# Track received responses
received_responses = {}
stop_event = threading.Event()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == mqtt.CONNACK_ACCEPTED:
        logger.info("Connected to MQTT broker")
        # Subscribe to response topic
        logger.info(f"Subscribing to topic: {MQTT_RESPONSE_TOPIC}")
        client.subscribe(MQTT_RESPONSE_TOPIC, qos=1)
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")

def on_message(client, userdata, msg):
    """Callback when a message is received"""
    try:
        logger.info(f"Received message on topic: {msg.topic}")
        payload = msg.payload.decode()
        logger.info(f"Raw message payload: {payload}")
        
        # Try to parse JSON
        try:
            data = json.loads(payload)
            
            # Handle different response formats
            if 'response' in data:
                # Check if 'response' is a string (success/failure) or an object
                if isinstance(data['response'], str):
                    # Handle simple success/failure response
                    response_status = data['response']
                    command_id = data.get('command_id', 'unknown')
                    
                    logger.info(f"Response status: {response_status}")
                    logger.info(f"Command ID: {command_id}")
                    
                    # Check for payload with error messages
                    if 'payload' in data and isinstance(data['payload'], dict):
                        payload_data = data['payload']
                        if 'code' in payload_data:
                            logger.info(f"Response code: {payload_data['code']}")
                        if 'message' in payload_data:
                            logger.info(f"Response message: {payload_data['message']}")
                        
                        # Log the full payload for debugging
                        logger.info(f"Full payload: {json.dumps(payload_data, indent=2)}")
                    
                    # Store in received_responses
                    received_responses[command_id] = {
                        'status': response_status,
                        'payload': data.get('payload', {})
                    }
                else:
                    # Original format where 'response' is an object
                    response = data['response']
                    command_id = response.get('command_id')
                    
                    if command_id:
                        received_responses[command_id] = response
                        
                        # Print detailed information about the response
                        logger.info(f"Received response for command ID: {command_id}")
                        logger.info(f"Response status: {response.get('status', 'UNKNOWN')}")
                        logger.info(f"Response type: {response.get('type', 'UNKNOWN')}")
                        
                        if 'data' in response:
                            logger.info(f"Response data: {json.dumps(response['data'], indent=2)}")
                        
                        if 'error' in response:
                            logger.info(f"Response error: {response['error']}")
                    else:
                        logger.warning("Received response with no command ID")
            else:
                logger.info(f"Received non-response message: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message as JSON: {e}")
            logger.info(f"Raw message: {payload}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

def on_subscribe(client, userdata, mid, reason_code, properties):
    """Callback when subscription is confirmed"""
    logger.info(f"Subscription confirmed. Message ID: {mid}")
    if isinstance(reason_code, list):
        for i, rc in enumerate(reason_code):
            logger.info(f"QoS for subscription {i+1}: {rc}")
    else:
        logger.info(f"QoS: {reason_code}")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected"""
    logger.warning(f"Disconnected with result code: {rc}")

def user_input_thread():
    """Thread to wait for user input to stop the program"""
    input("Press Enter to stop the response listener...\n")
    stop_event.set()

def main():
    # Create MQTT client
    client = mqtt.Client(
        protocol=mqtt.MQTTv5, 
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="response-listener-client"
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
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
        
        # Wait for user to press Enter or a timeout (whichever comes first)
        # This keeps the script running until explicitly stopped
        start_time = time.time()
        while not stop_event.is_set() and (time.time() - start_time < 3600):  # Max 1 hour
            time.sleep(1)
            
            # Print a message every 30 seconds to show we're still alive
            elapsed = time.time() - start_time
            if elapsed % 30 < 1:
                logger.info(f"Listener active for {int(elapsed)} seconds, waiting for responses...")
        
        # Summary of received responses
        logger.info(f"Received {len(received_responses)} command responses")
        
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