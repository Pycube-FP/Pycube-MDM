from .dashboard import dashboard_bp
from .devices import devices_bp
from .auth import auth_bp, login_required
from .assignments import assignments_bp
from .rfid import rfid_bp
from .nurses import nurses_bp

__all__ = [
    'dashboard_bp',
    'devices_bp',
    'auth_bp',
    'assignments_bp',
    'rfid_bp',
    'nurses_bp'
] 