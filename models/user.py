import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """User model for authentication and authorization"""
    
    def __init__(self, username, role, first_name=None, last_name=None, nurse_id=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.username = username
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.nurse_id = nurse_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def set_password(self, password):
        """Set the password hash for the user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': getattr(self, 'password_hash', None),
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'nurse_id': self.nurse_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_dict(data):
        """Create a user object from dictionary data"""
        user = User(
            username=data['username'],
            role=data['role'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            nurse_id=data.get('nurse_id'),
            id=data.get('id')
        )
        if 'password_hash' in data:
            user.password_hash = data['password_hash']
        return user 