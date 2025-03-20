from flask import Flask, redirect, url_for
import os
from routes import dashboard_bp, devices_bp
from services.db_service import DBService
from datetime import datetime

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-flask-session')
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(devices_bp)
    
    # Initialize the database
    with app.app_context():
        db_service = DBService()
        db_service.initialize_db()
    
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