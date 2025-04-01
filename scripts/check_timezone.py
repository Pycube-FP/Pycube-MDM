#!/usr/bin/env python3
import os
import sys
from datetime import datetime
import pytz

# Add pycube_mdm directory to path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import DBService

# Configure timezone
TIMEZONE = pytz.timezone('America/New_York')

def get_current_est_time():
    """Get current time in Eastern Time"""
    utc_now = datetime.now(pytz.UTC)
    return utc_now.astimezone(TIMEZONE)

def check_database_timezone():
    """Check database timezone settings and timestamps"""
    db_service = DBService()

    print("\n===== DATABASE TIMEZONE CHECK =====")
    
    try:
        # Check database timezone settings
        with db_service.get_connection() as connection:
            with connection.cursor() as cursor:
                # Check MySQL timezone settings
                cursor.execute("SELECT @@global.time_zone, @@session.time_zone")
                global_tz, session_tz = cursor.fetchone()
                print(f"MySQL timezone settings:")
                print(f"  Global timezone: {global_tz}")
                print(f"  Session timezone: {session_tz}")
                
                # Compare database timestamp with Python timestamp
                cursor.execute("SELECT NOW(), UTC_TIMESTAMP(), UNIX_TIMESTAMP(NOW())")
                db_now, db_utc, db_unix = cursor.fetchone()
                
                # Get Python timestamps in different formats
                py_now = datetime.now()
                py_now_utc = datetime.now(pytz.UTC)
                py_est = get_current_est_time()
                
                print("\nTimestamp comparison:")
                print(f"  Database NOW():          {db_now}")
                print(f"  Database UTC_TIMESTAMP(): {db_utc}")
                print(f"  Python datetime.now():   {py_now}")
                print(f"  Python UTC now:          {py_now_utc}")
                print(f"  Python EST now:          {py_est}")
                
                # Check if database timestamps are in UTC
                time_diff_seconds = (py_now_utc - pytz.UTC.localize(db_utc)).total_seconds()
                print(f"\nTime difference between Python UTC and Database UTC: {time_diff_seconds:.2f} seconds")
                
                # Check a device updated_at timestamp
                cursor.execute("SELECT id, serial_number, status, updated_at FROM devices LIMIT 1")
                device = cursor.fetchone()
                if device:
                    device_id, serial, status, updated_at = device
                    print(f"\nDevice timestamp check:")
                    print(f"  Device {device_id} ({serial}): status={status}, updated_at={updated_at}")
                    
                    # Compare with current time
                    if updated_at and not updated_at.tzinfo:
                        # Assuming updated_at is in UTC
                        updated_at_utc = pytz.UTC.localize(updated_at)
                        updated_at_est = updated_at_utc.astimezone(TIMEZONE)
                        
                        time_diff = (py_now_utc - updated_at_utc).total_seconds()
                        print(f"  Updated {time_diff/60:.1f} minutes ago (assuming UTC)")
                        print(f"  Timestamp in EST would be: {updated_at_est}")
                        
                        # If session_tz is not UTC, also try that timezone
                        if session_tz != '+00:00' and session_tz != 'UTC':
                            try:
                                session_pytz = pytz.timezone(session_tz.replace(':', ''))
                                updated_at_session = session_pytz.localize(updated_at)
                                updated_at_est_alt = updated_at_session.astimezone(TIMEZONE)
                                time_diff_alt = (py_now_utc - updated_at_session.astimezone(pytz.UTC)).total_seconds()
                                print(f"  Updated {time_diff_alt/60:.1f} minutes ago (assuming {session_tz})")
                                print(f"  Timestamp in EST would be: {updated_at_est_alt}")
                            except:
                                print(f"  Could not convert using session timezone: {session_tz}")
    
    except Exception as e:
        print(f"Error checking database timezone: {e}")
    
    print("\n===== END DATABASE TIMEZONE CHECK =====")

if __name__ == "__main__":
    check_database_timezone() 