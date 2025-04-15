from flask import Blueprint, jsonify, current_app, request
# Removed unused import: from app.api.data_processor import DataProcessor
from app.tasks.sync import sync_new_conversations # Keep this import
import functools
import signal
from contextlib import contextmanager
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
import logging
import os
import re # Import regex module
import openai # Import openai
import textwrap # Import textwrap for dedent
import random
import requests

# Create a Blueprint for the API
api = Blueprint('api', __name__)

# Define a timeout context manager using UNIX signals (safer than threads)
class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    
    # Only use the signal-based approach on Unix platforms (not Windows)
    try:
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
    except (ValueError, AttributeError):
        # On platforms where SIGALRM is not available, just yield and hope for the best
        yield

# Simplified timeout decorator that directly returns fallback data without threading
def timeout(seconds):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with time_limit(seconds):
                    return func(*args, **kwargs)
            except TimeoutException:
                # Log the timeout
                current_app.logger.warning(f"Function {func.__name__} timed out after {seconds} seconds.")
                
                # Return empty data structure with timeout error instead of fallback data
                return jsonify({
                    "common_questions": [],
                    "concerns_skepticism": [],
                    "positive_interactions": [],
                    "sentiment_overview": {
                        "agent_avg": 0,
                        "caller_avg": 0,
                        "distribution": {
                            "negative": 0,
                            "neutral": 0,
                            "positive": 0
                        }
                    },
                    "sentiment_trends": [],
                    "theme_correlation": [],
                    "top_themes": [],
                    "total_conversations_in_range": 0,
                    "timeout": True,
                    "error": f"The operation timed out after {seconds} seconds. Try a smaller date range."
                }), 200
            except Exception as e:
                current_app.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        return wrapper
    return decorator

# Move these routes from the main_bp to here
@api.route('/conversations')
def get_conversations():
    """API endpoint to get conversation data from the database."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    try:
        # Log the requested date range and parameters
        current_app.logger.info(f"API request for conversations: start={start_date}, end={end_date}, limit={limit}, offset={offset}")
        
        # Use the ConversationService
        service = current_app.conversation_service
        # Call the CORRECT existing method
        result = service.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Check if the service returned an error
        if 'error' in result:
            current_app.logger.error(f"Service error in get_conversations: {result['error']}") # Log correct method name
            # Return the error from the service
            return jsonify({'error': result['error']}), 500
        
        # Return data in the format expected by the frontend: { data: [...], total: ... }
        # Note: service returns { conversations: [...], total_count: ... }
        formatted_response = {
            'data': result.get('conversations', []),
            'total': result.get('total_count', 0)
        }
        
        current_app.logger.info(f"Returning {len(formatted_response['data'])} conversations, total matching: {formatted_response['total']}")
        return jsonify(formatted_response)
        
    except Exception as e:
        # Catch unexpected errors during API route processing
        current_app.logger.error(f"Unexpected error in /api/conversations: {str(e)}", exc_info=True)
        return jsonify({'error': f"An unexpected server error occurred: {str(e)}"}), 500
        
@api.route('/conversations/<conversation_id>')
def get_conversation_details(conversation_id):
    """API endpoint to get details for a specific conversation from the database."""
    try:
        current_app.logger.info(f"API request for details of conversation_id: {conversation_id}")
        
        # Use the ConversationService
        service = current_app.conversation_service
        processed_data = service.get_conversation_details(conversation_id)

        # Handle case where conversation is not found (service returns None)
        if processed_data is None:
            current_app.logger.warning(f"Conversation with ID {conversation_id} not found.")
            return jsonify({'error': 'Conversation not found', 'conversation_id': conversation_id}), 404

        # Check if the service returned a dictionary with an error key
        if isinstance(processed_data, dict) and 'error' in processed_data:
            status_code = 404 if 'not found' in processed_data.get('error', '').lower() else 500
            current_app.logger.warning(f"Service error getting details for {conversation_id}: {processed_data['error']} (Status: {status_code})")
            return jsonify({'error': processed_data['error'], 'conversation_id': conversation_id}), status_code

        # The service method already formats dates to ISO strings, so no extra formatting needed here.
        current_app.logger.info(f"Successfully retrieved details for conversation_id: {conversation_id}")
        current_app.logger.debug(f"Data being sent to frontend for {conversation_id}: {processed_data}")
        return jsonify(processed_data)
        
    except Exception as e:
        # Catch unexpected errors during API route processing
        current_app.logger.error(f"Unexpected error in /api/conversations/{conversation_id}: {str(e)}", exc_info=True)
        return jsonify({'error': f"An unexpected server error occurred while fetching details: {str(e)}"}), 500

# RENAME and MODIFY the sync endpoint
@api.route('/sync-conversations', methods=['POST']) # Renamed route
def sync_conversations_route():
    """Endpoint to manually trigger the conversation sync task."""
    # REMOVE secret key check - triggered by user action within the app
    # ...

    # Get full_sync parameter from query string
    full_sync_param = request.args.get('full_sync', 'false').lower()
    full_sync = full_sync_param == 'true'

    current_app.logger.info(f"SYNC ENDPOINT: Manual sync request received (Full Sync: {full_sync}). Starting sync...")
    try:
        # Pass the current app instance AND the full_sync flag
        result, status_code = sync_new_conversations(
            app=current_app._get_current_object(), 
            full_sync=full_sync
        )
        current_app.logger.info(f"SYNC ENDPOINT: Manual sync finished with status {status_code}. Result: {result}")
        return jsonify(result), status_code
    except Exception as e:
        current_app.logger.error(f"SYNC ENDPOINT: Unhandled exception during manual sync: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Internal server error during sync: {str(e)}"}), 500

@api.route('/conversations/<conversation_id>/analysis')
def analyze_conversation(conversation_id):
    """API endpoint to get analysis for a specific conversation"""
    try:
        # This endpoint would be implemented to provide analysis
        # Currently returning a stub response
        return jsonify({
            'conversation_id': conversation_id,
            'analysis': {
                'status': 'not_implemented'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@api.route('/themes-sentiment')
def get_themes_sentiment_data():
    """API endpoint to get categorized themes and sentiment data."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        current_app.logger.info(f"API request for themes/sentiment: start={start_date}, end={end_date}")
        
        # Use the AnalysisService
        service = current_app.analysis_service
        result = service.get_categorized_themes(start_date=start_date, end_date=end_date)
        
        # The service method already structures the data
        current_app.logger.info(f"Returning themes/sentiment data with {len(result.get('common_questions',[]))} question cats, {len(result.get('concerns_skepticism',[]))} concern cats.")
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in /api/themes-sentiment: {str(e)}", exc_info=True)
        # Return an empty structure matching the expected format on error
        empty_result = {
            'common_questions': [],
            'concerns_skepticism': [],
            'other_analysis': {},
            'error': f"An unexpected server error occurred: {str(e)}"
        }
        return jsonify(empty_result), 500

# Endpoint for the full Themes & Sentiment page analysis (Temporary Renamed Route)
@api.route('/themes-sentiment/full-analysis-v2') # Renamed route
@timeout(60) # Keeping the timeout decorator, 60 seconds might be needed for LLM
def get_full_themes_sentiment_data_v2(): # Renamed function
    request_start_time = time.time()
    # Define standard no-cache headers
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

    try:
        # 1. Get date range parameters from request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Basic validation for date parameters (can be enhanced)
        if not start_date or not end_date:
            current_app.logger.error("Missing start_date or end_date parameter for full analysis.")
            return jsonify({"error": "Missing required date parameters (start_date, end_date)"}), 400, response_headers

        current_app.logger.info(f"API Request: /themes-sentiment/full-analysis-v2 - Start: {start_date}, End: {end_date}")

        # 2. Get the AnalysisService instance
        analysis_service = current_app.analysis_service
        if not analysis_service:
             current_app.logger.critical("AnalysisService not found on current_app!")
             return jsonify({"error": "Analysis service is unavailable."}), 500, response_headers

        # 3. Call the service method
        analysis_results = analysis_service.get_full_themes_sentiment_analysis(
            start_date=start_date,
            end_date=end_date
        )

        # 4. Check for errors from the service
        if isinstance(analysis_results, dict) and 'error' in analysis_results:
             current_app.logger.error(f"Analysis service returned an error: {analysis_results['error']}")
             # Determine appropriate status code based on error type if possible
             status_code = 500 # Default to internal server error
             if "not found" in analysis_results.get('error','').lower():
                 status_code = 404
             elif "unavailable" in analysis_results.get('error','').lower():
                  status_code = 503 # Service Unavailable
             # Return the error from the service
             return jsonify(analysis_results), status_code, response_headers
        
        # Log success and timing
        duration = time.time() - request_start_time
        current_app.logger.info(f"Successfully generated full themes/sentiment analysis in {duration:.2f} seconds.")

        # 5. Return the successful result
        return jsonify(analysis_results), 200, response_headers

    except TimeoutException as te:
        # This exception is raised by the @timeout decorator context manager
        duration = time.time() - request_start_time
        current_app.logger.warning(f"Request timed out after {duration:.2f} seconds for /themes-sentiment/full-analysis-v2")
        return jsonify({
            "error": "Analysis request timed out. Please try a smaller date range or try again later.",
            "timeout": True
        }), 504, response_headers # 504 Gateway Timeout

    except Exception as e:
        # Catch any other unexpected errors
        duration = time.time() - request_start_time
        current_app.logger.error(f"Unexpected error in /themes-sentiment/full-analysis-v2 after {duration:.2f}s: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500, response_headers

# --- NEW: Endpoint for Ad-hoc RAG Query --- 
@api.route('/themes-sentiment/query', methods=['POST'])
def process_rag_query():
    """Processes a natural language query using the RAG service."""
    request_start_time = time.time()
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400, response_headers
        
        query = data.get('query')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not query:
            return jsonify({"error": "Missing required field: query"}), 400, response_headers
        
        # Basic date validation (could be more robust)
        # For now, allow None dates as the service handles them
        
        current_app.logger.info(f"API Request: /themes-sentiment/query - Query: '{query[:50]}...', Start: {start_date}, End: {end_date}")
        
        analysis_service = current_app.analysis_service
        if not analysis_service:
             current_app.logger.critical("AnalysisService not found on current_app!")
             return jsonify({"error": "Analysis service is unavailable."}), 503, response_headers
             
        # Call the new RAG processing method
        result = analysis_service.process_natural_language_query(
            query=query,
            start_date=start_date,
            end_date=end_date
        )
        
        # Check for errors from the service
        if isinstance(result, dict) and 'error' in result:
             current_app.logger.error(f"RAG Query service returned an error: {result['error']}")
             status_code = 500 # Default
             if "not found" in result.get('error','').lower() or "unavailable" in result.get('error','').lower():
                 status_code = 503
             elif "embedding" in result.get('error','').lower() or "search" in result.get('error','').lower():
                  status_code = 500
             return jsonify(result), status_code, response_headers
             
        # Return the answer
        duration = time.time() - request_start_time
        current_app.logger.info(f"Successfully processed RAG query in {duration:.2f} seconds.")
        return jsonify(result), 200, response_headers
        
    except Exception as e:
        duration = time.time() - request_start_time
        current_app.logger.error(f"Unexpected error in /themes-sentiment/query after {duration:.2f}s: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500, response_headers
# --- END NEW RAG QUERY ENDPOINT --- 

def get_conversation_count(start_date=None, end_date=None):
    """Helper function to efficiently get conversation count for date range"""
    from app.extensions import db
    from app.models import Message
    from sqlalchemy import func, text
    from datetime import datetime, timezone
    
    try:
        count = 0
        session = db.session()
        
        try:
            # Optimize query with raw SQL
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                
                query = text("""
                    SELECT COUNT(DISTINCT conversation_id) 
                    FROM messages 
                    WHERE timestamp >= :start_dt AND timestamp <= :end_dt
                """)
                count = session.execute(query, {"start_dt": start_dt, "end_dt": end_dt}).scalar() or 0
            else:
                # Just count all conversations with messages
                query = text("SELECT COUNT(DISTINCT conversation_id) FROM messages")
                count = session.execute(query).scalar() or 0
                
            session.commit()
        except Exception as e:
            current_app.logger.error(f"Error counting conversations: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()
            
        return count
    except Exception as e:
        current_app.logger.error(f"Error in get_conversation_count: {e}", exc_info=True)
        return 0

# --- NEW DASHBOARD STATS ROUTE ---
@api.route('/dashboard/stats')
def get_dashboard_stats_route():
    """API endpoint to get statistics for the main dashboard."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    agent_id = request.args.get('agent_id') # Get agent_id from query params

    try:
        # Include agent_id in logging
        current_app.logger.info(f"API request for dashboard stats: start={start_date}, end={end_date}, agent_id={agent_id}")

        # Use the ConversationService (expected to be SupabaseConversationService)
        service = current_app.conversation_service
        if not service or not hasattr(service, 'get_dashboard_stats'):
             current_app.logger.error("Conversation service or get_dashboard_stats method not found.")
             return jsonify({'error': 'Dashboard statistics service is unavailable.'}), 503 # Service Unavailable

        # Pass agent_id to the service method
        stats_data = service.get_dashboard_stats(
            start_date=start_date,
            end_date=end_date,
            agent_id=agent_id
        )

        # --- Directly attempt to return the data --- 
        # Removed intermediate logging and modification
        # current_app.logger.debug(f"RAW stats_data received from service: {stats_data}") 
        # if isinstance(stats_data, dict) and 'error' in stats_data:
        #     current_app.logger.error(f"Service error in get_dashboard_stats: {stats_data['error']}")
        #     return jsonify({'error': stats_data['error']}), 500
        # stats_data['success'] = True 
        # current_app.logger.info(f"Returning dashboard stats successfully.")
        # current_app.logger.debug(f"Data being sent to frontend for dashboard stats: {stats_data}")
        
        # Check if service returned a dict before trying jsonify
        if not isinstance(stats_data, dict):
             current_app.logger.error(f"Service get_dashboard_stats did not return a dictionary. Type: {type(stats_data)}")
             return jsonify({'error': 'Internal server error: Invalid data format from service.'}), 500
             
        current_app.logger.info(f"Attempting to jsonify and return stats_data directly from service.")
        # --- Log the exact dict BEFORE jsonify --- 
        current_app.logger.debug(f"DATA PASSED TO JSONIFY: {stats_data}")
        # --- End Log --- 
        return jsonify(stats_data)
        
    except Exception as e:
        # --- Explicitly log if this exception block is hit --- 
        current_app.logger.error(f"EXCEPTION CAUGHT in /api/dashboard/stats route handler: {str(e)}", exc_info=True)
        # --- End logging ---
        return jsonify({'error': f"An unexpected server error occurred: {str(e)}", 'success': False}), 500
# --- END NEW DASHBOARD STATS ROUTE ---

# --- NEW: Endpoint for getting agent configurations ---
@api.route('/agents')
def get_supported_agents():
    """Returns the list of supported agent configurations."""
    try:
        supported_agents = current_app.config.get('SUPPORTED_AGENTS', [])
        default_agent_id = current_app.config.get('DEFAULT_AGENT_ID', None)
        current_app.logger.info(f"Returning {len(supported_agents)} supported agents. Default: {default_agent_id}")
        return jsonify({
            'agents': supported_agents,
            'default_agent_id': default_agent_id
        })
    except Exception as e:
        current_app.logger.error(f"Error retrieving agent configurations: {str(e)}", exc_info=True)
        return jsonify({'error': "Failed to retrieve agent configurations."}), 500
# --- END AGENT CONFIG ENDPOINT ---

# --- NEW: Endpoint for agent widget configuration ---
@api.route('/agents/<agent_id>/widget-config')
def get_agent_widget_config(agent_id):
    """API endpoint to get the HTML embed code for the agent widget."""
    current_app.logger.info(f"Fetching widget config (embed code) for agent_id: {agent_id}")
    
    # Define the embed codes directly here for simplicity
    widget_configs = {
        "3HFVw3nTZfIivPaHr3ne": { # Curious Caller Lilly ID
            "embed_code": '<elevenlabs-convai agent-id="3HFVw3nTZfIivPaHr3ne"></elevenlabs-convai><script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>'
        },
        "XuUk69oMnn2Z9Sx9sXVu": { # Lilly For Members ID
            "embed_code": '<elevenlabs-convai agent-id="XuUk69oMnn2Z9Sx9sXVu"></elevenlabs-convai><script src="https://elevenlabs.io/convai-widget/index.js" async type="text/javascript"></script>'
        }
        # Add other agents here if needed
    }

    config = widget_configs.get(agent_id)

    if not config:
        current_app.logger.warning(f"Widget config not found for agent_id: {agent_id}")
        return jsonify({"error": "Widget configuration not found for this agent ID"}), 404

    current_app.logger.info(f"Returning widget embed code for agent_id: {agent_id}")
    # Return the embed code directly in the response
    return jsonify(config)
# --- END WIDGET CONFIG ENDPOINT ---

# --- NEW: Endpoint for agent system prompt ---
@api.route('/agents/<agent_id>/prompt')
def get_agent_prompt(agent_id):
    """Returns the system prompt/script for a specific agent from config."""
    current_app.logger.info(f"API request for system prompt for agent_id: {agent_id}")

    # Retrieve prompts dictionary from config
    agent_prompts = current_app.config.get('AGENT_PROMPTS', {})
    
    # Get the prompt for the specific agent_id
    prompt_text = agent_prompts.get(agent_id)

    if prompt_text:
        current_app.logger.info(f"Found prompt for agent {agent_id}.")
        return jsonify({'agent_id': agent_id, 'prompt': prompt_text})
    else:
        current_app.logger.warning(f"System prompt not found in config for agent_id: {agent_id}")
        # Return a clear error message if the prompt is not configured
        return jsonify({"error": f"System prompt not configured for agent ID: {agent_id}"}), 404
# --- END PROMPT ENDPOINT ---

# --- NEW: Endpoints for viewing email templates ---
@api.route('/email-templates/<template_name>')
def get_email_template(template_name):
    """Returns the HTML content of a specific email template."""
    
    # Validate template name
    valid_templates = {
        'team': 'team_email.html',        # Updated filename
        'caller': 'caller_email.html'      # Updated filename
    }
    
    if template_name not in valid_templates:
        current_app.logger.warning(f"Invalid email template requested: {template_name}")
        return jsonify({"error": "Invalid template name specified."}), 400
        
    filename = valid_templates[template_name]
    # Construct path relative to the app directory
    # Assumes routes.py is in app/api/, goes up two levels to project root, then to app/templates/email
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    template_path = os.path.join(base_dir, 'app', 'templates', 'email', filename)
    
    current_app.logger.info(f"API request for email template: {template_name} (Path: {template_path})")
    
    try:
        # Ensure the template directory exists
        template_dir = os.path.dirname(template_path)
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)
            current_app.logger.info(f"Created missing email template directory: {template_dir}")
            # Since dir was missing, file is also missing
            raise FileNotFoundError()

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'template_name': template_name, 'html_content': content})
        
    except FileNotFoundError:
        current_app.logger.error(f"Email template file not found: {template_path}")
        # Optionally create a default template if it doesn't exist
        default_content = f"<html><body><h1>Default {template_name.capitalize()} Template</h1><p>Template file not found at {filename}. Please create it.</p></body></html>"
        try:
             with open(template_path, 'w', encoding='utf-8') as f:
                 f.write(default_content)
             current_app.logger.info(f"Created default email template file: {template_path}")
             return jsonify({'template_name': template_name, 'html_content': default_content})
        except Exception as write_err:
            current_app.logger.error(f"Failed to create default email template {template_path}: {write_err}")
            return jsonify({"error": f"Template file '{filename}' not found and could not be created."}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error reading email template {template_path}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to read email template: {str(e)}"}), 500
# --- END EMAIL TEMPLATE ENDPOINTS ---

# --- NEW: Endpoint for Ad-Hoc SQL Queries ---
@api.route('/sql-query', methods=['POST'])
def execute_sql_query():
    """Accepts a natural language query, translates it to SQL via LLM,
       validates it, executes it, and returns the results."""
    
    nl_query = None # Initialize
    generated_sql = None # Initialize
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        nl_query = data['query']
        current_app.logger.info(f"Received natural language SQL query: {nl_query}")

        # --- LLM Translation --- 
        try:
            openai.api_key = current_app.config.get('OPENAI_API_KEY')
            if not openai.api_key:
                 raise ValueError("OpenAI API key not configured.")

            schema_context = textwrap.dedent("""
                Database Schema:
                Table: conversations
                  Columns: id (int, PK), external_id (varchar, unique, ElevenLabs ID), created_at (timestamptz), agent_id (varchar), cost_credits (float), status (varchar), summary (text)
                Table: messages
                  Columns: id (int, PK), conversation_id (int, FK -> conversations.id), timestamp (timestamptz), role (varchar, 'user' or 'agent'), text (text)
                
                Join Condition: messages.conversation_id = conversations.id
            """)
            
            prompt = textwrap.dedent(f"""
                You are an expert PostgreSQL assistant. Your task is to translate the user's natural language query into a secure, read-only SQL SELECT statement based on the provided schema.
                
                {schema_context}
                
                Constraints:
                - ONLY generate SQL SELECT statements.
                - Do NOT generate UPDATE, DELETE, INSERT, DROP, ALTER, TRUNCATE, CREATE, REPLACE, or any other DML/DDL statements.
                - Do not use functions known to be dangerous like pg_sleep.
                - Query ONLY the tables provided: 'conversations' and 'messages'.
                - Use aliases 'c' for conversations and 'm' for messages if joining.
                - For simple text searches on the 'messages.text' column:
                    - If the user is searching for a specific word or name (e.g., 'Tom', 'email'), use the case-insensitive regex operator `~*` with word boundaries `\y` (e.g., `WHERE m.text ~* '\yTom\y'`).
                    - If the user implies a broader substring search (e.g., 'containing xyz'), you may use `ILIKE` (e.g., `WHERE m.text ILIKE '%xyz%'`). Prefer word boundary searches when possible.
                - For date/timestamp filtering on 'created_at' (timestamptz) or 'timestamp' (timestamptz):
                    - Determine the current year (e.g., {datetime.now().year}) and use it unless the user specifies a different year.
                    - Convert specific dates (e.g., 'April 1st', 'yesterday') into a date range condition.
                    - Use the format `WHERE column >= 'YYYY-MM-DD 00:00:00 UTC' AND column < 'YYYY-MM-DD+1 00:00:00 UTC'` replacing YYYY with the correct year.
                    - Do NOT use the DATE() function on timestamp columns.
                - Escape any single quotes within search terms properly for SQL (e.g., 'O\'Malley').
                - Do NOT include trailing semicolons in the generated SQL.
                - If the user's request cannot be translated into a safe SELECT query based on the schema, or if it seems malicious or asks for modification, respond with the single word: INVALID
                
                User Query: "{nl_query}"
                
                SQL Query:
            """)

            current_app.logger.info(f"Sending prompt to OpenAI for NL->SQL: {prompt[:200]}...")
            # Use ChatCompletion for newer models
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", # Or "gpt-4o" if available/preferred
                messages=[
                    {"role": "system", "content": "You are an expert PostgreSQL assistant generating safe SELECT queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1, # Low temperature for more deterministic SQL
                max_tokens=150 # Limit response length
            )
            
            generated_sql = response.choices[0].message.content.strip()
            
            # Clean the generated SQL: remove markdown fences, trailing whitespace, and semicolon
            if generated_sql.startswith("```sql"):
                generated_sql = generated_sql[6:] # Remove ```sql
            if generated_sql.endswith("```"):
                generated_sql = generated_sql[:-3] # Remove ```
            generated_sql = generated_sql.strip().rstrip(';') # Strip whitespace/semicolon
            
            current_app.logger.info(f"Received and cleaned SQL from OpenAI: {generated_sql}")

            # Check if LLM refused
            if generated_sql.upper() == 'INVALID':
                current_app.logger.warning("LLM determined the query was invalid or unsafe.")
                return jsonify({"error": "The query could not be translated into a safe database request."}), 400
                
        except Exception as llm_error:
             current_app.logger.error(f"Error during OpenAI API call: {llm_error}", exc_info=True)
             return jsonify({"error": f"Failed to translate query using AI: {llm_error}"}), 500
        # --- End LLM Translation ---

        # --- Enhanced SQL Validation (Applied to LLM Output) --- 
        validated_sql = None
        # Define forbidden keywords EXPLICITLY without DATE
        forbidden_keywords = [
            'UPDATE', 'DELETE', 'INSERT', 'DROP', 'ALTER', 
            'TRUNCATE', 'CREATE', 'REPLACE' 
            # Ensure 'DATE' is NOT in this list
        ]
        forbidden_patterns = [';', '--', '/*', '*/'] # Keep pattern checks
        
        if not generated_sql: 
             current_app.logger.error("LLM Translation Failed: No SQL generated.")
             return jsonify({"error": "AI translation failed to produce a query."}), 500

        sql_upper = generated_sql.strip().upper()
        
        if not sql_upper.startswith("SELECT"):
            current_app.logger.error(f"SQL Validation Failed: Does not start with SELECT. SQL: {generated_sql}")
            return jsonify({"error": "Generated SQL failed safety checks (must be SELECT)."}), 400
            
        # Refined keyword check using word boundaries to prevent partial matches like DATE in UPDATED
        if any(re.search(r'\b' + re.escape(keyword) + r'\b', sql_upper) for keyword in forbidden_keywords):
            current_app.logger.error(f"SQL Validation Failed: Contains forbidden keywords (whole word match). SQL: {generated_sql}")
            return jsonify({"error": "Generated SQL failed safety checks (forbidden keyword)."}), 400
            
        if any(pattern in generated_sql for pattern in forbidden_patterns):
            current_app.logger.error(f"SQL Validation Failed: Contains forbidden patterns (e.g., comments, semicolon). SQL: {generated_sql}")
            return jsonify({"error": "Generated SQL failed safety checks (forbidden characters)."}), 400

        validated_sql = generated_sql 
        current_app.logger.info(f"LLM-generated SQL passed validation: {validated_sql}")
        # --- End Enhanced SQL Validation --- 

        # --- Execute Query using Supabase Client (Remains the same logic) --- 
        supabase_wrapper = current_app.supabase_client 
        if not supabase_wrapper or not hasattr(supabase_wrapper, 'execute_sql'): 
            current_app.logger.error("Supabase client wrapper is not available or configured correctly.")
            return jsonify({"error": "Database client error."}), 500
            
        current_app.logger.info(f"Executing validated SQL via wrapper: {validated_sql}")
        start_time = time.time()
        
        response_data = supabase_wrapper.execute_sql(validated_sql)
        
        duration = time.time() - start_time
        current_app.logger.info(f"SQL execution completed in {duration:.3f} seconds.")

        current_app.logger.debug(f"Supabase execute_sql response data: {response_data}")

        if response_data is not None:
             data_length = len(response_data) if isinstance(response_data, list) else 1
             current_app.logger.info(f"Returning {data_length} result(s) from SQL query.")
             # Return the actual query executed (which came from the LLM)
             return jsonify({"results": response_data, "query_executed": validated_sql}) 
        else:
            current_app.logger.info("SQL query via wrapper returned None/empty result.")
            return jsonify({"results": [], "message": "Query executed successfully, but returned no data.", "query_executed": validated_sql})

    except Exception as e:
        current_app.logger.error(f"Error processing SQL query '{nl_query}': {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to execute query: {str(e)}"}), 500
# --- END SQL QUERY ENDPOINT ---

# --- NEW: Lily's Daily Report Endpoint ---
@api.route('/lily-daily-report', methods=['POST'])
def generate_lily_daily_report():
    """Generates a daily report summary and converts it to speech using ElevenLabs."""
    try:
        current_app.logger.info("Generating Lily's daily report")
        
        # 1. Generate a simple report text using hardcoded samples
        # In a real implementation, we would analyze actual conversations
        report_templates = [
            "Hello! Lily here with your operational status report. Today, I had {conversation_count} conversations with callers, primarily about relationships, career paths, and spiritual guidance. I noticed a trend of questions about {topic}. Overall, caller sentiment was {sentiment} with several positive outcomes. The busiest time was around {busy_time}. Is there anything specific you'd like me to focus on in tomorrow's conversations?",
            
            "Greetings from Lily with your daily operational update. I've completed {conversation_count} readings today, with particular interest in {topic}. Callers were generally {sentiment}, and I was able to provide guidance that seemed to resonate well. I noticed that {busy_time} was our peak time today. Looking forward to continuing to assist callers tomorrow!",
            
            "Daily briefing from Lily. Today's activity included {conversation_count} caller interactions. The most common topics were {topic}, which is {topic_trend} compared to yesterday. Caller mood was predominantly {sentiment}. I've logged all conversation details for your review. Traffic peaked at {busy_time} today. All systems are functioning optimally."
        ]
        
        # Random values for the placeholders
        conversation_count = random.randint(15, 47)
        topics = ["love and relationships", "career transitions", "spiritual awakening", "family dynamics", "personal growth"]
        topic = random.choice(topics)
        topic_trend = random.choice(["consistent", "trending upward", "slightly down"])
        sentiments = ["very positive", "generally optimistic", "mixed but leaning positive", "reflective"]
        sentiment = random.choice(sentiments)
        busy_times = ["mid-morning", "early afternoon", "late evening", "around noon"]
        busy_time = random.choice(busy_times)
        
        # Select a template and fill in the values
        report_text = random.choice(report_templates).format(
            conversation_count=conversation_count,
            topic=topic,
            topic_trend=topic_trend,
            sentiment=sentiment,
            busy_time=busy_time
        )
        
        current_app.logger.info(f"Generated report text: {report_text}")
        
        # 2. Convert the text to speech using ElevenLabs API
        voice_id = "XfNU2rGpBa01ckF309OY"  # Nichalia Schwartz voice ID
        api_key = current_app.config.get('ELEVENLABS_API_KEY')
        
        if not api_key:
            return jsonify({"error": "ElevenLabs API key not configured"}), 500
            
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": report_text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        current_app.logger.info("Sending request to ElevenLabs API")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code != 200:
            current_app.logger.error(f"ElevenLabs API error: {response.status_code}")
            current_app.logger.error(response.text)
            return jsonify({"error": f"Text-to-speech conversion failed: {response.text}"}), 500
        
        # 3. Save the audio to a temporary file
        static_dir = os.path.join(current_app.root_path, 'static', 'audio')
        os.makedirs(static_dir, exist_ok=True)
        
        # Use timestamp to ensure filename uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"lily_report_{timestamp}.mp3"
        filepath = os.path.join(static_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
            
        # 4. Return the URL to the audio file and the report text
        audio_url = f"/static/audio/{filename}"
        
        current_app.logger.info(f"Report audio saved to {filepath}")
        current_app.logger.info(f"Report audio URL: {audio_url}")
        
        return jsonify({
            "success": True,
            "report_text": report_text,
            "audio_url": audio_url,
            "timestamp": timestamp
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating Lily's daily report: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500
# --- END LILY'S DAILY REPORT ENDPOINT ---