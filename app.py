from flask import Flask, redirect, url_for
import os
from routes import dashboard_bp, devices_bp, auth_bp, assignments_bp, rfid_bp, nurses_bp
from routes.hospitals import hospitals_bp
from routes.readers import readers_bp
from services.db_service import DBService
from models.user import User
from datetime import datetime

def create_default_admin(db_service):
    """Create a default admin user if no admin exists"""
    # Check if admin user already exists
    if db_service.get_user_by_username('admin'):
        print("Admin user already exists")
        return
    
    print("No admin user found. Creating default admin user...")
    
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

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-flask-session')
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(rfid_bp)
    app.register_blueprint(nurses_bp)
    app.register_blueprint(hospitals_bp)
    app.register_blueprint(readers_bp)
    
    # Initialize the database
    with app.app_context():
        db_service = DBService()
        db_service.initialize_db()
        
        # Create default admin user if none exists
        create_default_admin(db_service)
    
    # Add template context processor for current datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
        
    return app

# Main application
app = create_app()

# Create a route for AWS health checks
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 