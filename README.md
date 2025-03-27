# Pycube MDM - Mobile Device Management

A Flask-based web application for tracking mobile devices in healthcare environments using RFID technology.

## Overview

Pycube MDM helps hospitals and healthcare facilities track and manage their mobile device inventory. The system uses passive RFID tags attached to devices and RFID readers positioned at strategic locations to automatically track device movements.

### Key Features

- **Device Management**: Add, edit, view, and delete mobile devices
- **RFID Tracking**: Track device movements through RFID readers
- **Dashboard**: View device statistics and status at a glance
- **Location Management**: Define and manage physical locations
- **Reporting**: Generate reports on device usage and movement

## Technology Stack

- **Backend**: Python Flask
- **Database**: MySQL (AWS RDS compatible)
- **Frontend**: HTML, CSS, JavaScript with Bootstrap
- **Authentication**: Flask built-in session management

## Installation

### Prerequisites

- Python 3.7+
- MySQL or compatible database
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Pycube-FP/Pycube-MDM.git
   cd Pycube-MDM
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. Initialize the database:
   ```bash
   python -m scripts.setup_db
   ```

## Running the Application

```bash
python run.py
```

The application will be accessible at http://localhost:5000

## Project Structure

```
pycube_mdm/
├── app.py                 # Main Flask application
├── run.py                 # Application entry point
├── models/                # Data models
│   ├── device.py
│   ├── location.py
│   ├── reader_event.py
│   ├── nurse.py
│   ├── device_assignment.py
│   └── rfid_alert.py
├── routes/                # Route definitions
│   ├── dashboard.py
│   └── devices.py
├── services/              # Business logic
│   └── db_service.py
├── scripts/              # Maintenance scripts
│   ├── setup_db.py
│   └── update_epc_codes.py
├── static/               # Static assets
│   ├── css/
│   └── img/
└── templates/            # HTML templates
    ├── dashboard.html
    └── devices/
```

## Development

### Adding New Features

1. Create or modify models in the `models/` directory
2. Update database service in `services/db_service.py`
3. Add routes in `routes/` directory
4. Create templates in `templates/` directory

### Database Migrations

For database schema changes, update the `initialize_db()` method in `services/db_service.py`.

## Deployment

For production deployment:

1. Use a production WSGI server (Gunicorn, uWSGI)
2. Set up a reverse proxy (Nginx, Apache)
3. Configure your .env file with production settings
4. Use a managed database service like AWS RDS

## License

This project is proprietary and confidential.

## Contact

For support or inquiries, contact [support@pycube.com](mailto:support@pycube.com). 