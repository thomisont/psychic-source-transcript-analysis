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
    # sync_key = request.headers.get('X-Sync-Key')
    # expected_key = current_app.config.get('SYNC_SECRET_KEY')
    # if not expected_key: ...
    # if not sync_key or sync_key != expected_key: ...

    current_app.logger.info("SYNC ENDPOINT: Manual sync request received. Starting sync...")
    try:
        # Pass the current app instance to the sync function
        result, status_code = sync_new_conversations(current_app._get_current_object())
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
    
    try:
        current_app.logger.info(f"API request for dashboard stats: start={start_date}, end={end_date}")
        
        # Use the ConversationService (expected to be SupabaseConversationService)
        service = current_app.conversation_service
        if not service or not hasattr(service, 'get_dashboard_stats'):
             current_app.logger.error("Conversation service or get_dashboard_stats method not found.")
             return jsonify({'error': 'Dashboard statistics service is unavailable.'}), 503 # Service Unavailable
             
        stats_data = service.get_dashboard_stats(start_date=start_date, end_date=end_date)
        
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