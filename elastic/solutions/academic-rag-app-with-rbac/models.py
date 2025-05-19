from flask_login import UserMixin

class User(UserMixin):
    """User class for Flask-Login authentication and RBAC."""
    
    def __init__(self, id, username, password=None, roles=None, api_key=None):
        """
        Initialize a user with ID, username, and roles.
        
        Args:
            id: Unique user identifier
            username: User's username
            password: User's password (should be hashed in production)
            roles: List of roles assigned to the user
            api_key: Elasticsearch API key for this user
        """
        self.id = id
        self.username = username
        self.password = password
        self.roles = roles or []
        self.api_key = api_key
    
    def has_role(self, role):
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles):
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_roles(self, roles):
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)
    
    @classmethod
    def from_api_key_info(cls, api_key_info):
        """
        Create a User object from API key information.
        
        Args:
            api_key_info: Dictionary with API key information
            
        Returns:
            User object
        """
        if not api_key_info or not api_key_info.get("valid"):
            return None
        
        return cls(
            id=api_key_info.get("id"),
            username=api_key_info.get("username"),
            roles=api_key_info.get("roles", []),
            api_key=api_key_info.get("encoded_api_key")
        )
