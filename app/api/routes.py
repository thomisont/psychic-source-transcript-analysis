from flask import Blueprint, jsonify, current_app, request, abort
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
from app.__init__ import get_supabase_client

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

# +++ NEW Route to save Human Input notes +++
@api.route('/conversations/<conversation_id>/notes', methods=['POST'])
def save_conversation_hi_notes(conversation_id):
    """API endpoint to save human input notes for a specific conversation."""
    try:
        data = request.get_json()
        if not data or 'hi_notes' not in data:
            current_app.logger.warning(f"Missing hi_notes in request for conversation {conversation_id}")
            return jsonify({'error': 'Missing hi_notes in request body'}), 400

        hi_notes_text = data['hi_notes']
        
        current_app.logger.info(f"Attempting to save HI notes for conversation_id (external): {conversation_id}")

        # Use the ConversationService to update the notes
        service = current_app.conversation_service
        success, message = service.update_conversation_notes(conversation_id, hi_notes_text)

        if success:
            current_app.logger.info(f"Successfully saved HI notes for conversation {conversation_id}")
            return jsonify({'success': True, 'message': message})
        else:
            current_app.logger.error(f"Failed to save HI notes for conversation {conversation_id}: {message}")
            status_code = 404 if "not found" in message.lower() else 500
            return jsonify({'success': False, 'error': message}), status_code
            
    except Exception as e:
        current_app.logger.error(f"Unexpected error in /api/conversations/{conversation_id}/notes: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': f"An unexpected server error occurred: {str(e)}"}), 500
# +++ END NEW Route +++

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
    from app.services.supabase_conversation_service import SupabaseConversationService
    try:
        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        agent_id = request.args.get('agent_id')
        # Optionally handle 'timeframe' if needed for logging/debug

        # Get the Supabase service using the robust helper
        supabase_client = get_supabase_client()
        supabase_service = SupabaseConversationService(supabase_client)

        # Fetch dashboard stats
        stats = supabase_service.get_dashboard_stats(start_date, end_date, agent_id)

        # If error, return error structure with 500
        error_val = stats.get('error')
        if error_val and isinstance(error_val, str):
            return jsonify({'error': error_val}), 500

        # Remove 'error' key if it exists and is not a string
        if 'error' in stats:
            del stats['error']

        # On success, return the stats dict directly (not wrapped)
        return jsonify(stats), 200
    except Exception as e:
        current_app.logger.error(f"Error in /dashboard/stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
# --- END NEW DASHBOARD STATS ROUTE ---

# --- NEW: Endpoint for getting agent configurations ---
@api.route('/agents')
def get_supported_agents():
    try:
        supabase_client = get_supabase_client()
        agents = []
        default_agent_id = None
        if supabase_client:
            try:
                # Use the SupabaseClient's query method to fetch all agent fields
                response = supabase_client.query(
                    table_name='agents',
                    select='id, name, status, type, voice_id, description',
                    order='name.asc'
                )
                if response:
                    # Normalize any "Lilly" → "Lily" in agent names for consistent UI spelling
                    normalized_agents = []
                    for agent in response:
                        if not agent.get('id') or not agent.get('name'):
                            continue  # Skip invalid rows
                        name_corrected = agent['name'].replace('Lilly', 'Lily')
                        normalized_agents.append({
                            'id': agent['id'],
                            'name': name_corrected,
                            'status': agent.get('status'),
                            'type': agent.get('type'),
                            'voice_id': agent.get('voice_id'),
                            'description': agent.get('description'),
                        })
                    agents = normalized_agents
                    if agents:
                        default_agent_id = agents[0]['id']
            except Exception as e:
                current_app.logger.warning(f"Could not fetch agents from Supabase: {e}")
        # Fallback: Use config or hardcoded agents if Supabase is not available or returns nothing
        if not agents:
            agents = [
                {'id': 'curious_caller', 'name': 'Curious Caller', 'status': 'active', 'type': 'main', 'voice_id': None, 'description': None},
                {'id': 'lily_main', 'name': 'Lily (Main)', 'status': 'active', 'type': 'main', 'voice_id': None, 'description': None},
            ]
            default_agent_id = agents[0]['id']
        return jsonify({'agents': agents, 'default_agent_id': default_agent_id})
    except Exception as e:
        current_app.logger.error(f"Error in /api/agents: {e}", exc_info=True)
        return jsonify({'agents': [], 'default_agent_id': None, 'error': str(e)}), 500
# --- END AGENT CONFIG ENDPOINT ---

# --- NEW: Endpoint for agent widget configuration ---
@api.route('/agents/<agent_id>/widget-config')
def get_agent_widget_config(agent_id):
    try:
        # Use the provided widget tag structure
        embed_code = f'<elevenlabs-convai agent-id="{agent_id}" variant="expandable"></elevenlabs-convai>'
        
        # Ensure API key is present (still needed by the widget loaded via base.html)
        if not current_app.config.get('ELEVENLABS_API_KEY'):
            current_app.logger.error("ElevenLabs API key is missing in config for widget.")
            return jsonify({"error": "Widget configuration incomplete (missing API key)."}), 500

        return jsonify({"embed_code": embed_code})
    except Exception as e:
        current_app.logger.error(f"Error getting widget config for agent {agent_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate widget configuration."}), 500
# --- END WIDGET CONFIG ENDPOINT ---

# --- NEW: Endpoint for agent system prompt ---
@api.route('/agents/<agent_id>/prompt')
def get_agent_prompt(agent_id):
    try:
        prompts = current_app.config.get('AGENT_PROMPTS', {})
        prompt_text = prompts.get(agent_id, "No system prompt configured for this agent.")
        
        # Sanitize for HTML display (basic newline to <br>)
        prompt_html = prompt_text.replace('\n', '<br>')
        
        return jsonify({"agent_id": agent_id, "prompt": prompt_html})
    except Exception as e:
        current_app.logger.error(f"Error getting prompt for agent {agent_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve agent prompt."}), 500
# --- END PROMPT ENDPOINT ---

# --- NEW: Endpoints for viewing email templates ---
@api.route('/email-templates/<template_name>')
def get_email_template(template_name):
    # Validate template name to prevent directory traversal
    if not re.match(r'^[a-zA-Z0-9_-]+$', template_name):
        return jsonify({"error": "Invalid template name"}), 400

    try:
        template_dir = os.path.join(current_app.root_path, 'templates', 'email')
        filepath = os.path.join(template_dir, f"{template_name}.html")

        # Ensure directory exists
        os.makedirs(template_dir, exist_ok=True)

        # Create a placeholder if the file doesn't exist
        if not os.path.exists(filepath):
            placeholder_content = f"<html><body><h1>Placeholder for {template_name}.html</h1><p>This template needs to be created.</p></body></html>"
            with open(filepath, 'w') as f:
                f.write(placeholder_content)
            current_app.logger.info(f"Created placeholder email template: {filepath}")

        # Read the file content
        with open(filepath, 'r') as f:
            html_content = f.read()
            
        return jsonify({"template_name": template_name, "html_content": html_content})
    except FileNotFoundError:
         current_app.logger.error(f"Email template file not found: {filepath}")
         return jsonify({"error": "Email template not found."}), 404
    except Exception as e:
        current_app.logger.error(f"Error reading email template {template_name}: {e}", exc_info=True)
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

@api.route('/glassfrog/roles/<int:role_id>')
def get_glassfrog_role(role_id):
    """Fetch role details from GlassFrog via service (cached)."""
    refresh = request.args.get('refresh', '0') == '1'
    try:
        service = current_app.glassfrog_service
        if not service:
            return jsonify({'error': 'GlassFrog service not configured'}), 500
        data = service.get_role(role_id, force_refresh=refresh)
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        current_app.logger.error(f"GlassFrog API error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500

# === Voice SDK integration ===
@api.route('/voice-sdk/token')
def get_voice_sdk_token():
    """Return ElevenLabs API key (or a short-lived token) for frontend SDK use."""
    api_key = os.getenv('ELEVENLABS_API_KEY') or os.getenv('ELEVENLABS_API_KEY_PUBLIC')
    if not api_key:
        return jsonify({'error': 'ElevenLabs API key not configured'}), 500
    # In production we would mint a short-lived token; for now return the key directly
    return jsonify({'token': api_key})


@api.route('/voice-sdk/chat/<agent_id>', methods=['POST'])
def voice_sdk_chat(agent_id):
    """Proxy user text to the existing agent chat endpoint or fall back to echo."""
    data = request.get_json(silent=True) or {}
    user_text = data.get('text', '').strip()
    if not user_text:
        return jsonify({'error': 'Text is required'}), 400

    # Try to forward to existing route if present
    forward_path = f'/api/agents/{agent_id}/chat'
    # We call internally via Flask test_client to avoid extra HTTP roundtrip
    try:
        with current_app.test_client() as client:
            resp = client.post(forward_path, json={'text': user_text})
            if resp.status_code == 200:
                payload = resp.get_json()
                if 'reply' in payload:
                    return jsonify({'reply': payload['reply']})
    except Exception as e:
        current_app.logger.warning(f"Voice SDK proxy failed: {e}")

    # Fallback – simple echo
    return jsonify({'reply': f"You said: {user_text}"})

# === ElevenLabs TTS for Voice SDK ===
@api.route('/voice-sdk/tts', methods=['POST'])
def voice_sdk_tts():
    """Convert text to speech via ElevenLabs API and return a temporary audio URL.

    Expected JSON payload: { "text": "Hello world", "voice_id": "<optional>" }
    Returns: { "audio_url": "/static/audio/<file>.mp3" }
    """
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400

        voice_id = data.get('voice_id') or current_app.config.get('ELEVENLABS_VOICE_ID') or os.getenv('ELEVENLABS_VOICE_ID') or 'EXAVITQu4vr4xnSDxMaL'
        api_key = os.getenv('ELEVENLABS_API_KEY') or current_app.config.get('ELEVENLABS_API_KEY')
        if not api_key:
            return jsonify({'error': 'ElevenLabs API key not configured'}), 500

        # Call ElevenLabs TTS endpoint (non-streaming for simplicity)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {
                "stability": 0.35,
                "similarity_boost": 0.85
            }
        }
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            current_app.logger.error(f"ElevenLabs TTS error {resp.status_code}: {resp.text}")
            return jsonify({'error': f'TTS failed: {resp.text}'}), 500

        # Save audio file
        from datetime import datetime
        import uuid, os as _os
        static_audio_dir = _os.path.join(current_app.root_path, 'static', 'audio')
        _os.makedirs(static_audio_dir, exist_ok=True)
        filename = f"voice_sdk_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
        filepath = _os.path.join(static_audio_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(resp.content)

        audio_url = f"/static/audio/{filename}"
        return jsonify({'audio_url': audio_url})
    except Exception as e:
        current_app.logger.error(f"Voice SDK TTS error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@api.route('/voice-sdk/signed-url/<agent_id>')
def voice_sdk_signed_url(agent_id):
    """Generate a short-lived signedUrl for private ElevenLabs agents."""
    api_key = os.getenv('ELEVENLABS_API_KEY') or current_app.config.get('ELEVENLABS_API_KEY')
    if not api_key:
        return jsonify({'error': 'ElevenLabs API key not configured'}), 500

    try:
        url = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
        headers = { 'xi-api-key': api_key }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            current_app.logger.error(f"Signed URL fetch failed {resp.status_code}: {resp.text}")
            return jsonify({'error': 'Failed to get signed URL'}), 500
        data = resp.json()
        signed_url = data.get('signed_url') or data.get('signedUrl') or data.get('url')
        if not signed_url:
            return jsonify({'error': 'signed_url missing'}), 500
        return jsonify({'signed_url': signed_url})
    except Exception as e:
        current_app.logger.error(f"Signed URL error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
# --- END voice-sdk signed url ---