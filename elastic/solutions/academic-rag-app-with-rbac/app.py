import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from search import Search
from dotenv import load_dotenv
import bedrock_claude
from models import User
from functools import wraps

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Mock user database - in production, use a real database
users = {
    '1': User('1', 'student', 'password123', ['student']),
    '2': User('2', 'faculty', 'password123', ['faculty']),
    '3': User('3', 'admin', 'password123', ['admin']),
    '4': User('4', 'researcher', 'password123', ['researcher']),
    '5': User('5', 'superuser', 'password123', ['student', 'faculty', 'admin', 'researcher'])
}

# Initialize services with error handling
try:
    # Use environment variable to control whether to use cloud or local Elasticsearch
    use_cloud = os.getenv("USE_ELASTIC_CLOUD", "true").lower() == "true"
    es = Search(use_cloud=use_cloud)
except Exception as e:
    print(f"Error initializing Elastic or Bedrock services: {e}")

@login_manager.user_loader
def load_user(user_id):
    """Load user from the mock database."""
    return users.get(user_id)

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
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find user by username
        user = next((u for u in users.values() if u.username == username), None)
        
        if user and user.password == password:  # In production, use password hashing
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/ask', methods=['POST'])
@login_required
def ask():
    """API endpoint to handle Q&A requests with RBAC."""
    try:
        # Get question from request
        data = request.json
        question = data.get('question', '')
        print(f"Question: {question}")
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Search Elastic for relevant documents with RBAC filtering
        search_results, search_result = es.search(question, user_roles=current_user.roles)
        
        # Format search results
        sources = es.format_search_results(search_results)
        
        if not sources:
            return jsonify({
                "answer": "I couldn't find any relevant documents you have access to that answer your question.",
                "sources": []
            })

        # Generate answer using Claude
        prompt = Search.create_bedrock_prompt(search_result)
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
        document = es.retrieve_document(doc_id)
        
        # Check if user has access to this document
        allowed_roles = document['_source'].get('allowed_roles', [])
        if allowed_roles and not any(role in current_user.roles for role in allowed_roles):
            flash('You do not have permission to access this document.', 'danger')
            return redirect(url_for('index'))
        
        title = document['_source'].get('attachment', {}).get('title', 'Untitled Document')
        
        # Extract and format content as paragraphs
        content = document['_source'].get('semantic_content', {}).get('inference', {}).get('chunks', [{}])[0].get('text', '')
        content = content.replace("\n", "")
        if not content:
            content = document['_source'].get('attachment', {}).get('content', '')
            content = content.replace("\n", "")

        content = content.replace("\n", "")
        paragraphs = content.split('\n')
        
        return render_template('document.html', title=title, paragraphs=paragraphs)
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
