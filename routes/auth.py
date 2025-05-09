from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from services.db_service import DBService
from models.user import User
import uuid
import jwt
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Secret key for JWT token generation
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'development-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Token valid for 24 hours

# Admin credentials - In a real application, these would be stored securely
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def is_logged_in():
    """Check if user is logged in"""
    return session.get('logged_in', False)

def get_user_role():
    """Get the role of the logged-in user"""
    return session.get('role')

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Decorator to require specific role(s) for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_logged_in():
                flash('Please log in to access this page', 'error')
                return redirect(url_for('auth.login', next=request.url))
            
            user_role = get_user_role()
            if user_role not in roles:
                flash('You do not have permission to access this page', 'error')
                return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_jwt_token(user_id, username, role):
    """Generate a JWT token for API authentication"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def validate_jwt_token(token):
    """Validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
        
def api_auth_required(f):
    """Decorator to require JWT authentication for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for token in header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token is missing or invalid'}), 401
        
        token = auth_header.split(' ')[1]
        payload = validate_jwt_token(token)
        
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Set user info in request for use in the route
        request.user = payload
        
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if is_logged_in():
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db_service = DBService()
        user_data = db_service.get_user_by_username(username)
        
        if user_data:
            user = User.from_dict(user_data)
            if user.check_password(password):
                session['logged_in'] = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                session['first_name'] = user_data.get('first_name')
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """Handle API login requests"""
    if not request.is_json:
        return jsonify({
            'success': False,
            'message': 'Content-Type must be application/json'
        }), 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required'
        }), 400
    
    db_service = DBService()
    user_data = db_service.get_user_by_username(username)
    
    if user_data:
        user = User.from_dict(user_data)
        if user.check_password(password):
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'firstName': user_data.get('first_name'),
                    'lastName': user_data.get('last_name'),
                    'role': user.role
                }
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid username or password'
    }), 401

@auth_bp.route('/api/token', methods=['POST'])
def generate_api_token():
    """Generate a JWT token for API access"""
    if not request.is_json:
        return jsonify({
            'success': False,
            'message': 'Content-Type must be application/json'
        }), 400
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required'
        }), 400
    
    db_service = DBService()
    user_data = db_service.get_user_by_username(username)
    
    if user_data:
        user = User.from_dict(user_data)
        if user.check_password(password):
            # Generate JWT token
            token = generate_jwt_token(user.id, user.username, user.role)
            
            return jsonify({
                'success': True,
                'token': token,
                'expires_in': JWT_EXPIRATION_HOURS * 3600,  # in seconds
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid username or password'
    }), 401

# Admin-only route for user management
@auth_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def create_user():
    """Create a new user (admin only)"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        db_service = DBService()
        
        # Check if username already exists
        if db_service.get_user_by_username(username):
            flash('Username already exists', 'error')
            return redirect(url_for('auth.create_user'))
        
        # Create new user
        user = User(
            username=username,
            role=role,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        try:
            db_service.create_user(user.to_dict())
            flash(f'User {username} ({role}) created successfully', 'success')
            return redirect(url_for('auth.list_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('auth/create_user.html')

@auth_bp.route('/users')
@login_required
@role_required(['admin'])
def list_users():
    """List all users"""
    db_service = DBService()
    
    # Get sort parameters from request
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    users = db_service.get_all_users(sort_by=sort_by, sort_dir=sort_dir)
    return render_template('auth/users.html', 
                         users=users,
                         sort_by=sort_by,
                         sort_dir=sort_dir)

@auth_bp.route('/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def edit_user(user_id):
    """Edit a user (admin only)"""
    db_service = DBService()
    user_data = db_service.get_user(user_id)
    
    if not user_data:
        flash('User not found', 'error')
        return redirect(url_for('auth.list_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        new_password = request.form.get('password')
        
        # Check if username is taken by another user
        existing_user = db_service.get_user_by_username(username)
        if existing_user and existing_user['id'] != user_id:
            flash('Username already exists', 'error')
            return redirect(url_for('auth.edit_user', user_id=user_id))
        
        # Update user data
        user = User(
            username=username,
            role=role,
            first_name=first_name,
            last_name=last_name,
            id=user_id
        )
        
        # Update password if provided
        if new_password:
            user.set_password(new_password)
            db_service.update_user_password(user_id, user.password_hash)
        
        try:
            db_service.update_user(user.to_dict())
            flash('User updated successfully', 'success')
            return redirect(url_for('auth.list_users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('auth/edit_user.html', user=user_data)

@auth_bp.route('/users/<user_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_user(user_id):
    """Delete a user (admin only)"""
    db_service = DBService()
    user_data = db_service.get_user(user_id)
    
    if not user_data:
        flash('User not found', 'error')
        return redirect(url_for('auth.list_users'))
    
    # Prevent deleting own account or last admin
    if user_id == session.get('user_id'):
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('auth.list_users'))
    
    # Prevent deleting the default admin user
    if user_data['username'] == ADMIN_USERNAME:
        flash('Cannot delete the default admin user', 'error')
        return redirect(url_for('auth.list_users'))
    
    if user_data['role'] == 'admin':
        # Count remaining admins
        connection = db_service.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                flash('Cannot delete the last admin user', 'error')
                return redirect(url_for('auth.list_users'))
        finally:
            cursor.close()
            connection.close()
    
    try:
        # Delete user
        connection = db_service.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            connection.commit()
            flash('User deleted successfully', 'success')
        finally:
            cursor.close()
            connection.close()
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('auth.list_users')) 