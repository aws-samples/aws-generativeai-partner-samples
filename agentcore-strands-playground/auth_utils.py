"""
Cognito Authentication Module for Streamlit AgentCore Chat
"""

import os
import boto3
import streamlit as st
from typing import Dict, Optional
from boto3.session import Session
from dotenv import load_dotenv
import yaml

# Load environment variables
load_dotenv()

class CognitoAuth:
    """Handles Cognito authentication for the Streamlit app"""
    
    def __init__(self):
        self.pool_id = os.getenv('COGNITO_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.region = os.getenv('AWS_REGION', 'us-west-2')
        
        # Get discovery URL from .env first, then try YAML file
        self.discovery_url = os.getenv('COGNITO_DISCOVERY_URL', '').strip()
        
        # If not in .env, try to read from .bedrock_agentcore.yaml
        if not self.discovery_url:
            try:
                yaml_path = 'agentcore_agent/.bedrock_agentcore.yaml'
                if os.path.exists(yaml_path):
                    with open(yaml_path, 'r') as f:
                        config = yaml.safe_load(f)
                        # Try to get discoveryUrl from the default agent or ac_auth agent
                        default_agent = config.get('default_agent', 'ac_auth')
                        agent_config = config.get('agents', {}).get(default_agent, {})
                        auth_config = agent_config.get('authorizer_configuration', {})
                        jwt_config = auth_config.get('customJWTAuthorizer', {})
                        self.discovery_url = jwt_config.get('discoveryUrl', '').strip()
                        
                        # Also try to extract pool_id and client_id from discovery URL if not set
                        if self.discovery_url and not self.pool_id:
                            # Extract pool_id from discovery URL
                            # Format: https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/...
                            parts = self.discovery_url.split('/')
                            if len(parts) >= 4:
                                self.pool_id = parts[3]
                        
                        # Get client_id from allowedClients if not set
                        if not self.client_id:
                            allowed_clients = jwt_config.get('allowedClients', [])
                            if allowed_clients:
                                self.client_id = allowed_clients[0]
            except Exception as e:
                # Silently fail - will be caught by config_available check
                pass
        
        self.default_username = os.getenv('DEFAULT_USERNAME', 'testuser1')
        self.default_password = os.getenv('DEFAULT_PASSWORD', 'MyPassword123!')
        
        # Check if configuration is available
        self.config_available = all([self.pool_id, self.client_id])
        
        # Initialize Cognito client only if config is available
        if self.config_available:
            try:
                self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
            except Exception as e:
                st.error(f"❌ Failed to initialize Cognito client: {str(e)}")
                self.config_available = False
                self.cognito_client = None
        else:
            self.cognito_client = None
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """
        Authenticate user with Cognito and return tokens
        
        Args:
            username: Cognito username
            password: User password
            
        Returns:
            Dict with success status and tokens or error message
        """
        try:
            auth_response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            return {
                'success': True,
                'access_token': auth_response['AuthenticationResult']['AccessToken'],
                'id_token': auth_response['AuthenticationResult']['IdToken'],
                'refresh_token': auth_response['AuthenticationResult']['RefreshToken'],
                'expires_in': auth_response['AuthenticationResult']['ExpiresIn']
            }
            
        except self.cognito_client.exceptions.NotAuthorizedException:
            return {'success': False, 'error': 'Invalid username or password'}
        except self.cognito_client.exceptions.UserNotFoundException:
            return {'success': False, 'error': 'User not found'}
        except Exception as e:
            return {'success': False, 'error': f'Authentication failed: {str(e)}'}
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Cognito refresh token
            
        Returns:
            Dict with success status and new access token or error message
        """
        try:
            auth_response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            return {
                'success': True,
                'access_token': auth_response['AuthenticationResult']['AccessToken'],
                'expires_in': auth_response['AuthenticationResult']['ExpiresIn']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Token refresh failed: {str(e)}'}
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return st.session_state.get('authenticated', False)
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token from session"""
        return st.session_state.get('access_token')
    
    def get_username(self) -> Optional[str]:
        """Get current username from session"""
        return st.session_state.get('username')
    
    def logout(self):
        """Clear authentication session"""
        keys_to_clear = [
            'authenticated', 
            'access_token', 
            'id_token', 
            'refresh_token', 
            'username',
            'token_expires_at'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def show_login_form(self):
        """Display login form and handle authentication"""
        st.title("🔐 Login to AgentCore Chat")
        
        # Check if configuration is available
        if not self.config_available:
            st.error("❌ Cognito configuration missing. Please check your .env file.")
            st.info("""
            **Required environment variables:**
            - COGNITO_POOL_ID
            - COGNITO_CLIENT_ID
            - AWS_REGION (optional, defaults to us-west-2)
            
            Please update your .env file and restart the application.
            """)
            st.stop()
            return
        
        # Show configuration info
        with st.expander("ℹ️ Configuration Info"):
            st.write(f"**User Pool ID:** {self.pool_id}")
            st.write(f"**Client ID:** {self.client_id}")
            st.write(f"**Region:** {self.region}")
        
        with st.form("login_form"):
            st.write("### Enter your credentials")
            
            username = st.text_input(
                "Username",
                value=self.default_username,
                help="Default: testuser (from notebook example)"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                value=self.default_password,
                help="Default: MyPassword123! (from notebook example)"
            )
            
            submit = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit:
                if username and password:
                    with st.spinner("🔄 Authenticating with Cognito..."):
                        result = self.authenticate_user(username, password)
                        
                    if result['success']:
                        # Store authentication data in session
                        st.session_state.authenticated = True
                        st.session_state.access_token = result['access_token']
                        st.session_state.id_token = result['id_token']
                        st.session_state.refresh_token = result['refresh_token']
                        st.session_state.username = username
                        
                        st.success("✅ Login successful!")
                        st.balloons()
                        
                        # Immediately rerun to load authenticated app
                        st.rerun()
                    else:
                        st.error(f"❌ Login failed: {result['error']}")
                else:
                    st.error("⚠️ Please enter both username and password")
    
def get_auth_instance() -> CognitoAuth:
    """Get or create CognitoAuth instance"""
    if 'auth_instance' not in st.session_state:
        st.session_state.auth_instance = CognitoAuth()
    return st.session_state.auth_instance


def require_authentication():
    """Decorator-like function to require authentication"""
    auth = get_auth_instance()
    
    if not auth.is_authenticated():
        auth.show_login_form()
        st.stop()
    
    return auth