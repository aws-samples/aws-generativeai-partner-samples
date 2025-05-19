import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import bedrock_claude
from functools import wraps
from elastic_rbac import ElasticRBAC

# Load environment variables
load_dotenv()

# User model for Flask-Login
class User:
    def __init__(self, id, username, roles, api_key=None):
        self.id = id
        self.username = username
        self.roles = roles
        self.api_key = api_key
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
    
    def get_id(self):
        return self.id

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize Elasticsearch RBAC service
elastic_rbac = ElasticRBAC()

# Create index mapping if it doesn't exist
if elastic_rbac.is_ready():
    mapping_result = elastic_rbac.create_document_mapping()
    print(mapping_result)

# Store API keys in memory (in production, use a database)
api_keys = {}

@login_manager.user_loader
def load_user(user_id):
    """Load user from API key ID or session."""
    # First check if we have an API key for this user
    if user_id in api_keys:
        return api_keys[user_id]
    
    # If elastic_rbac is not initialized, we can't validate API keys
    if not elastic_rbac.is_ready():
        return None
    
    # If not, try to validate the API key with Elasticsearch
    user_info = elastic_rbac.validate_api_key(user_id)
    if user_info:
        user = User(
            id=user_id,
            username=user_info["username"],
            roles=user_info["roles"]
        )
        api_keys[user_id] = user
        return user
    
    return None

# Role-based access control decorator
def role_required(roles):
    """
    Decorator to restrict access to users with specific roles.
    
    Args:
        roles: Single role string or list of roles
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            # Convert single role to list
            role_list = roles if isinstance(roles, list) else [roles]
            
            # Check if user has any of the required roles
            if not any(role in current_user.roles for role in role_list):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
@login_required
def index():
    """Render the main page with search interface."""
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with Elasticsearch API keys."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if elastic_rbac is initialized
        if not elastic_rbac.is_ready():
            flash('Authentication service is not available. Please try again later.', 'danger')
            return render_template('login.html')
            
        # Mock authentication - in production, validate against a database
        if username == 'student' and password == 'password123':
            # Create API key for this user
            api_key_info = elastic_rbac.create_user_api_key(username, ['student'])
            if not api_key_info:
                flash('Error creating authentication token. Please try again.', 'danger')
                return render_template('login.html')
                
            user = User(
                id=api_key_info["id"],
                username=username,
                roles=['student'],
                api_key=api_key_info["encoded_api_key"]
            )
            api_keys[api_key_info["id"]] = user
            login_user(user)
            return redirect(url_for('index'))
        elif username == 'faculty' and password == 'password123':
            api_key_info = elastic_rbac.create_user_api_key(username, ['faculty'])
            if not api_key_info:
                flash('Error creating authentication token. Please try again.', 'danger')
                return render_template('login.html')
                
            user = User(
                id=api_key_info["id"],
                username=username,
                roles=['faculty'],
                api_key=api_key_info["encoded_api_key"]
            )
            api_keys[api_key_info["id"]] = user
            login_user(user)
            return redirect(url_for('index'))
        elif username == 'admin' and password == 'password123':
            api_key_info = elastic_rbac.create_user_api_key(username, ['admin'])
            if not api_key_info:
                flash('Error creating authentication token. Please try again.', 'danger')
                return render_template('login.html')
                
            user = User(
                id=api_key_info["id"],
                username=username,
                roles=['admin'],
                api_key=api_key_info["encoded_api_key"]
            )
            api_keys[api_key_info["id"]] = user
            login_user(user)
            return redirect(url_for('index'))
        elif username == 'researcher' and password == 'password123':
            api_key_info = elastic_rbac.create_user_api_key(username, ['researcher'])
            if not api_key_info:
                flash('Error creating authentication token. Please try again.', 'danger')
                return render_template('login.html')
                
            user = User(
                id=api_key_info["id"],
                username=username,
                roles=['researcher'],
                api_key=api_key_info["encoded_api_key"]
            )
            api_keys[api_key_info["id"]] = user
            login_user(user)
            return redirect(url_for('index'))
        elif username == 'superuser' and password == 'password123':
            api_key_info = elastic_rbac.create_user_api_key(username, ['student', 'faculty', 'admin', 'researcher'])
            if not api_key_info:
                flash('Error creating authentication token. Please try again.', 'danger')
                return render_template('login.html')
                
            user = User(
                id=api_key_info["id"],
                username=username,
                roles=['student', 'faculty', 'admin', 'researcher'],
                api_key=api_key_info["encoded_api_key"]
            )
            api_keys[api_key_info["id"]] = user
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    # In a production environment, you might want to invalidate the API key
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/ask', methods=['POST'])
@login_required
def ask():
    """API endpoint to handle Q&A requests with RBAC."""
    try:
        # Check if elastic_rbac is initialized
        if not elastic_rbac.is_ready():
            return jsonify({"error": "Search service is not available"}), 503
            
        # Get question from request
        data = request.json
        question = data.get('question', '')
        print(f"Question: {question}")
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Search Elastic for relevant documents with RBAC filtering
        search_results, sources = elastic_rbac.search_documents(question, current_user.roles)
        
        if not sources:
            return jsonify({
                "answer": "I couldn't find any relevant documents you have access to that answer your question.",
                "sources": []
            })

        # Generate prompt for Claude
        prompt = f"""
        Question: {question}
        
        Please answer the question based on the following academic documents:
        
        {sources}
        
        Provide a concise, accurate answer with citations to the source documents.
        """
        
        # Generate answer using Claude
        bedrock_completion = bedrock_claude.execute_llm(prompt)
        
        # Return both the answer and sources
        return jsonify({
            "answer": bedrock_completion,
            "sources": sources
        })
    except Exception as e:
        print(f"Error processing question: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/document/<doc_id>')
@login_required
def get_document(doc_id):
    """Render a page showing a specific document with RBAC check."""
    try:
        # Check if elastic_rbac is initialized
        if not elastic_rbac.is_ready():
            flash('Document service is not available. Please try again later.', 'danger')
            return redirect(url_for('index'))
            
        # Verify document access using Elasticsearch API
        if not elastic_rbac.verify_document_access(doc_id, current_user.roles):
            flash('You do not have permission to access this document.', 'danger')
            return redirect(url_for('index'))
        
        document = elastic_rbac.retrieve_document(doc_id, current_user.roles)
        if not document:
            flash('Document not found.', 'danger')
            return redirect(url_for('index'))
            
        title = document['_source'].get('attachment', {}).get('title', 'Untitled Document')
        
        # Extract and format content as paragraphs
        content = document['_source'].get('attachment', {}).get('content', '')
        paragraphs = content.split('\n')
        
        return render_template('document.html', title=title, paragraphs=paragraphs)
    except PermissionError as e:
        flash(str(e), 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error retrieving document: {e}")
        return render_template('index.html', error=f"Error retrieving document: {str(e)}")

@app.route('/admin')
@login_required
@role_required('admin')
def admin_panel():
    """Admin panel - only accessible to users with admin role."""
    return render_template('admin.html')

# Custom Jinja filter for date formatting
@app.template_filter('date_format')
def date_format(value, format='%Y-%m-%d'):
    """Format a date string or timestamp."""
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return value
    return value.strftime(format)

# Add custom context processor for getting current time
@app.context_processor
def inject_now():
    return {'now': datetime.now}

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    # Start the Flask application
    app.run(host='0.0.0.0', port=port, debug=debug)