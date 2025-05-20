from flask_login import UserMixin

class User(UserMixin):
    """User class for Flask-Login authentication and RBAC."""
    
    def __init__(self, id, username, password, roles=None):
        """
        Initialize a user with ID, username, and roles.
        
        Args:
            id: Unique user identifier
            username: User's username
            password: User's password (should be hashed in production)
            roles: List of roles assigned to the user
        """
        self.id = id
        self.username = username
        self.password = password
        self.roles = roles or []
    
    def has_role(self, role):
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles):
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_roles(self, roles):
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)
