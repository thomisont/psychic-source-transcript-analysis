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

# Endpoint for the full Themes & Sentiment page analysis (Reverted Name)
@api.route('/themes-sentiment/full-analysis') # Reverted route
@timeout(60)
def get_full_themes_sentiment_data(): # Reverted function name
    # REMOVED UNIQUE ENTRY LOGGING
    # current_app.logger.critical("***** ENTERING ... V2 ... *****") 
    
    request_start_time = time.time()
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    # REMOVED OLD CACHE CHECK LOGIC
    # cache_key = f\"themes_full_{start_date}_{end_date}\"
    # cached_result = current_app.cache.get(cache_key)
    # if cached_result:
    #     current_app.logger.info(f\"Returning cached themes/sentiment result for key: {cache_key}\")
    #     return jsonify(cached_result), 200, response_headers

    # TEMPORARILY COMMENT OUT NEW CACHE LOGIC (already done)
    # ... (lines related to new cache check) ...
    
    try:
        # >>> Clear Flask-Caching specific cache if needed <<<
        # if hasattr(current_app, 'cache') and hasattr(current_app.cache, 'clear'):
        #     current_app.cache.clear()
        #     current_app.logger.info("Cleared Flask-Caching application-level cache")
        
        # Clear the analysis service's internal cache (if any - might be redundant)
        # if hasattr(current_app.analysis_service, 'clear_cache'):
        #     current_app.analysis_service.clear_cache()
        #     current_app.logger.info("Cleared analysis service internal cache")

        # Generate a unique cache key for this request (for logging/tracking)
        request_id = f"themes_full_{int(time.time())}"
        current_app.logger.info(f"Generating fresh analysis for request_id: {request_id}")
        
        # Get date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        current_app.logger.info(f"Full themes/sentiment analysis requested for date range: {start_date} to {end_date}")
        
        # Validate date parameters
        if not start_date or not end_date:
            current_app.logger.warning("Missing date parameters for themes/sentiment analysis")
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            current_app.logger.info(f"Using default date range: {start_date} to {end_date}")
        
        # Create a new database session to avoid transaction conflicts
        try:
            from app.extensions import db
            db.session.remove()  # Clear any existing session
        except Exception as db_err:
            current_app.logger.warning(f"Could not clear database session: {db_err}")
        
        try:
            # >>> Use the high-level AnalysisService method <<< 
            analysis_service = current_app.analysis_service 
            
            # Ensure the service is available
            if not analysis_service:
                raise Exception("AnalysisService is not available in the application context.")

            # Call the comprehensive analysis method directly
            analysis_result = analysis_service.get_full_themes_sentiment_analysis(
                start_date=start_date, 
                end_date=end_date
            )
            
            # >>> REMOVE redundant data fetching and lower-level analysis calls <<<
            # conversation_service = current_app.conversation_service
            # conversation_data = conversation_service.get_conversations(...)
            # if 'error' in conversation_data:
            #     ...
            # conversations = conversation_data.get('conversations', [])
            # if not conversations:
            #     ...
            # analysis_result = analysis_service.analyzer.analyze_sentiment_over_time(...)
            
            current_app.logger.info(f"Analysis completed by AnalysisService.get_full_themes_sentiment_analysis for request_id: {request_id}")

            # The analysis_result dictionary should now contain all necessary keys
            # Example: analysis_result.get('top_themes', [])
            
            # Format response (ensure keys match what the service method returns)
            response = {
                'sentiment_overview': analysis_result.get('sentiment_overview', {}), # Get the whole overview dict
                'top_themes': analysis_result.get('top_themes', []),
                'sentiment_trends': analysis_result.get('sentiment_trends', []),
                'common_questions': analysis_result.get('common_questions', []),
                'concerns_skepticism': analysis_result.get('concerns_skepticism', []),
                'positive_interactions': analysis_result.get('positive_interactions', []),
                # Add total conversations if the service method provides it, otherwise calculate if needed
                # 'total_conversations_in_range': analysis_result.get('total_conversations_in_range', 0), 
                'request_id': request_id
            }
            
            # Log success and return
            # The log message below might need adjustment based on what the service returns
            # current_app.logger.info(f"Successfully generated themes-sentiment analysis with {len(conversations)} conversations for request_id: {request_id}")
            current_app.logger.info(f"Successfully generated themes-sentiment analysis for request_id: {request_id}")
            return jsonify(response), 200, response_headers
            
        except Exception as analysis_err:
            current_app.logger.error(f"Error during analysis: {str(analysis_err)}", exc_info=True)
            # Return default empty structure matching the expected keys
            return jsonify({
                'error': f"Analysis error: {str(analysis_err)}",
                'sentiment_overview': {'caller_avg': 0, 'agent_avg': 0, 'distribution': {'positive': 0, 'negative': 0, 'neutral': 100}},
                'top_themes': [],
                'sentiment_trends': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': [],
                # 'total_conversations_in_range': 0,
                'request_id': request_id
            }), 500, response_headers # Return 500 on internal error
                
    except Exception as e:
        current_app.logger.error(f"Unhandled error in themes/sentiment endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': f"Server error: {str(e)}",
            'sentiment_overview': {'caller_avg': 0, 'agent_avg': 0, 'distribution': {'positive': 0, 'negative': 0, 'neutral': 100}},
            'top_themes': [],
            'sentiment_trends': [],
            'common_questions': [],
            'concerns_skepticism': [],
            'positive_interactions': [],
            'total_conversations_in_range': 0,
            'request_id': request_id
        }), 200, response_headers # Return 200 even on error to show empty state

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