from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Admin credentials - In a real application, these would be stored securely
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Function to check if user is logged in
def is_logged_in():
    return session.get('logged_in', False)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # If already logged in, redirect to dashboard
    if is_logged_in():
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Successful login', 'success')
            
            # Redirect to the requested URL or default to dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('auth.login')) 