import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from search import Search
from dotenv import load_dotenv
import bedrock_claude


# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)


# Initialize services with error handling
try:
    # Use environment variable to control whether to use cloud or local Elasticsearch
    use_cloud = os.getenv("USE_ELASTIC_CLOUD", "true").lower() == "true"
    es = Search(use_cloud=use_cloud)
except Exception as e:
    print(f"Error initializing Elastic or Bedrock services: {e}")

@app.route('/')
def index():
    """Render the main page with search interface."""
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def ask():
    """API endpoint to handle Q&A requests."""
    try:
        # Get question from request
        data = request.json
        question = data.get('question', '')
        print(f"Question: {question}")
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Search Elastic for relevant documents
        search_results, search_result = es.search(question)
        # Format search results
        sources = es.format_search_results(search_results)
        
        if not sources:
            return jsonify({
                "answer": "I couldn't find any relevant documents to answer your question.",
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
def get_document(doc_id):
    """Render a page showing a specific document."""
    try:
        document = es.retrieve_document(doc_id)
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
    #app.run(host='0.0.0.0', port=port, debug=True)