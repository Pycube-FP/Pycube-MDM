import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import DBService
from models.user import User
import uuid

def create_admin_user():
    """Create the initial admin user"""
    db_service = DBService()
    
    # Check if admin user already exists
    if db_service.get_user_by_username('admin'):
        print("Admin user already exists")
        return
    
    # Create admin user with specified schema
    admin = User(
        username='admin',
        role='admin',
        first_name='System',
        last_name='Administrator',
        hospital_id=None  # No specific hospital for system admin
    )
    admin.set_password('admin123')  # Default password - should be changed after first login
    
    try:
        db_service.create_user(admin.to_dict())
        print("Admin user created successfully")
        print("Username: admin")
        print("Password: admin123")
        print("Please change the password after first login")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == '__main__':
    create_admin_user() 