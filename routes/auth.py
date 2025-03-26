from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from services.db_service import DBService
from models.user import User
import uuid

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

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
                
                flash('Login successful', 'success')
                
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
                    'role': user.role,
                    'nurseId': user_data.get('nurse_id')
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
        nurse_id = request.form.get('nurse_id') if role == 'nurse' else None
        
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
            last_name=last_name,
            nurse_id=nurse_id
        )
        user.set_password(password)
        
        try:
            db_service.create_user(user.to_dict())
            flash(f'User {username} ({role}) created successfully', 'success')
            return redirect(url_for('auth.list_users'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
    
    # Get all nurses for the dropdown
    db_service = DBService()
    connection = db_service.get_connection()
    cursor = connection.cursor(dictionary=True)
    nurses = []
    try:
        cursor.execute("SELECT * FROM nurses ORDER BY badge_id")
        nurses = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    
    return render_template('auth/create_user.html', nurses=nurses)

@auth_bp.route('/users')
@login_required
@role_required(['admin'])
def list_users():
    """List all users (admin only)"""
    db_service = DBService()
    
    # Get all users from database
    query = """
        SELECT u.*, n.badge_id, n.department
        FROM users u
        LEFT JOIN nurses n ON u.nurse_id = n.id
        ORDER BY u.created_at DESC
    """
    connection = db_service.get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute(query)
        users = cursor.fetchall()
        return render_template('auth/users.html', users=users)
    except Exception as e:
        flash(f'Error retrieving users: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))
    finally:
        cursor.close()
        connection.close()

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
        nurse_id = request.form.get('nurse_id') if role == 'nurse' else None
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
            nurse_id=nurse_id,
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
    
    # Get nurses for dropdown if editing a nurse user
    nurses = []
    if user_data['role'] == 'nurse':
        connection = db_service.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM nurses ORDER BY first_name, last_name")
            nurses = cursor.fetchall()
        finally:
            cursor.close()
            connection.close()
    
    return render_template('auth/edit_user.html', user=user_data, nurses=nurses)

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