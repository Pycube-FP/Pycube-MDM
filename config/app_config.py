import os
from datetime import timedelta
import pytz

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Timezone configuration
TIMEZONE = pytz.timezone('America/New_York')

# Device Status Thresholds
MISSING_THRESHOLD = timedelta(minutes=2)  # Time after which a temporarily out device is considered missing

# MQTT configuration
MQTT_ENDPOINT = os.environ.get("MQTT_ENDPOINT", "a2zl2pb12jbe1o-ats.iot.us-east-1.amazonaws.com")
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "6B6035_tagdata")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_KEEP_ALIVE = int(os.environ.get("MQTT_KEEP_ALIVE", 60))

# Certificate paths
CERTS_DIR = os.environ.get("CERTS_DIR", os.path.expanduser("~/certs"))
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-private.pem.key"))
CERTIFICATE = os.environ.get("CERTIFICATE", os.path.join(CERTS_DIR, "011d91c58df6cf46eff8bc6138893756f79cfa35a55c9cc806b4d73b1ab4cb15-certificate.pem.crt"))
ROOT_CA = os.environ.get("ROOT_CA", os.path.join(CERTS_DIR, "AmazonRootCA1.pem"))

# Scheduler Configuration
SCHEDULER_CHECK_MISSING_INTERVAL = 2  # minutes
SCHEDULER_LOG_STATUS_INTERVAL = 30  # seconds

# Helper Functions
def get_current_est_time():
    """Get current time in Eastern Time"""
    # Create a timezone-aware UTC time 
    from datetime import datetime
    import pytz
    
    utc_now = datetime.now(pytz.UTC)
    
    # Convert to EST
    est_now = utc_now.astimezone(TIMEZONE)
    
    return est_now 