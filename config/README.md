# Configuration Module

This module centralizes application configuration settings for the BayCare iPhone Tracking system.

## Key Features

- **Single Source of Truth**: Centralizes configuration values used across multiple modules
- **Environment Variables**: Uses environment variables with sensible defaults
- **Missing Threshold**: Standardizes the threshold for when a "Temporarily Out" device is considered "Missing" (currently 2 minutes)
- **Timezone Handling**: Provides consistent timezone configuration and helpers
- **MQTT Settings**: Contains MQTT connection parameters

## Usage

Import configuration settings in your Python modules:

```python
from config.app_config import (
    MISSING_THRESHOLD,
    TIMEZONE,
    get_current_est_time
)
```

If you encounter import issues, try one of these alternative approaches:

```python
# For absolute imports
from pycube_mdm.config.app_config import MISSING_THRESHOLD

# For relative imports
from ..config.app_config import MISSING_THRESHOLD
```

## Key Configuration Values

- `MISSING_THRESHOLD`: The time after which a device in "Temporarily Out" status is marked as "Missing" (2 minutes)
- `TIMEZONE`: The application's timezone (America/New_York)
- `get_current_est_time()`: Helper function to get the current time in EST
- MQTT connection settings
- Certificate paths
- Scheduler intervals

## How to Modify

To change the `MISSING_THRESHOLD` or other settings, edit the `app_config.py` file. This will ensure the change is reflected consistently across all components of the application. 