import os
import sys
import json
import logging
import traceback
import random
import math
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify, send_file, current_app, redirect, flash
import io
from app.utils.export import DataExporter
from app.utils.analysis import ConversationAnalyzer
from app.api.elevenlabs_client import ElevenLabsClient
import pandas as pd
from sqlalchemy import func
import time
from pathlib import Path

# Import db and models for test route
from app.extensions import db
from app.models import Conversation, Message

# Import Supabase services
sys.path.append(str(Path(__file__).parent.parent))
try:
    from app.services.supabase_conversation_service import SupabaseConversationService
    SUPABASE_AVAILABLE = True
    logging.info("Supabase services available, will attempt to use them first")
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("Supabase services not available, will use default services")

main_bp = Blueprint('main', __name__)

@main_bp.route('/test-db')
def test_db_connection():
    """Simple route to test database connection during runtime."""
    try:
        # Attempt a simple query (even if table doesn't exist, connection is tested)
        count = db.session.query(Conversation).count()
        return jsonify({'status': 'success', 'message': f'Successfully connected and queried. Found {count} conversations.'})
    except Exception as e:
        # Log the full error for debugging
        logging.error(f"Database connection test failed: {e}", exc_info=True)
        # Return error information
        return jsonify({'status': 'error', 'message': f'Database connection failed: {str(e)}'}), 500

@main_bp.route('/')
def index():
    """Home page with dashboard overview"""
    try:
        # Hardcoded README.md content for simplicity and reliability
        readme_content = """
<h1>Psychic Source Transcript Analysis Tool</h1>

<p>A web application for analyzing call transcripts from ElevenLabs' Conversational Voice Agent for Psychic Source with additional outbound calling capabilities.</p>

<h2>Current Features</h2>

<ul>
<li><strong>Conversation Browser</strong>: View and search through psychic reading conversations with an iMessage-style transcript viewer</li>
<li><strong>Dashboard</strong>: Interactive overview with KPIs, charts, and metrics showing conversation data</li>
<li><strong>Agent Selection</strong>: Support for multiple Lilly agents (filter dashboard by agent)</li>
<li><strong>Admin Panel</strong>: View agent prompts, email templates, and interact directly with the agent through a widget</li>
<li><strong>Ad-Hoc SQL Querying</strong>: Ask questions about conversation data in natural language (LLM-translated to SQL)</li>
<li><strong>Outbound Calling</strong>: Make personalized outbound calls to previous callers using ElevenLabs' voice synthesis</li>
<li><strong>Sentiment Analysis</strong>: Analyze the emotional tone of conversations</li>
<li><strong>Topic Extraction</strong>: Identify key themes and topics discussed</li>
<li><strong>Data Visualization</strong>: Interactive charts and graphs showing trends and patterns</li>
</ul>

<h2>Architecture</h2>

<p>The application uses a service-oriented architecture with Supabase as the primary database:</p>

<ul>
<li><strong>Flask Backend</strong>: Handles API requests, data processing, and rendering</li>
<li><strong>Service Layer</strong>: Separates business logic from API integration and presentation</li>
<li><strong>Supabase Integration</strong>: PostgreSQL-based cloud database for scalable data storage</li>
<li><strong>ElevenLabs API Integration</strong>: Retrieves conversation data and enables outbound calling</li>
<li><strong>Analysis Engine</strong>: Processes conversation data to extract insights</li>
<li><strong>Responsive UI</strong>: Bootstrap-based interface with Chart.js visualizations</li>
</ul>

<h2>Outbound Calling System</h2>

<p>The application includes a complete outbound calling system:</p>

<ul>
<li><strong>Client Library</strong>: JavaScript and Python clients for initiating calls</li>
<li><strong>FastAPI Service</strong>: REST API for managing outbound calls</li>
<li><strong>ElevenLabs Integration</strong>: Uses ElevenLabs' text-to-speech for natural-sounding calls</li>
<li><strong>Twilio Integration</strong>: Handles actual phone call placement and status updates</li>
<li><strong>Hospitality Feature</strong>: Personalized follow-up calls to previous customers</li>
</ul>

<h2>Recent Updates</h2>

<h3>1. Dashboard Enhancements (April 2025)</h3>

<ul>
<li><strong>Multi-Agent Support</strong>: Added ability to filter dashboard by different Lilly agents</li>
<li><strong>Agent Administration Panel</strong>: Added viewing of agent prompts and email templates</li>
<li><strong>Natural Language SQL Interface</strong>: Added ability to query the database using plain English</li>
<li><strong>Cost Tracking</strong>: Added month-to-date cost tracking with budget visualization</li>
<li><strong>UI Improvements</strong>: Enhanced card design and tooltips for better information display</li>
</ul>

<h3>2. Supabase Integration (April 2025)</h3>

<ul>
<li>Migrated data storage from SQLAlchemy to Supabase for improved scalability</li>
<li>Implemented hybrid approach with fallback to original database if needed</li>
<li>Updated sync task to write data to Supabase</li>
<li>Created RPC functions for custom queries</li>
<li>Updated services to use Supabase client</li>
</ul>

<h3>3. Outbound Calling System (April 2025)</h3>

<ul>
<li>Added complete outbound calling functionality with ElevenLabs integration</li>
<li>Created hospitality calling feature for personalized customer follow-up</li>
<li>Implemented both JavaScript and Python clients</li>
<li>Added FastAPI service for call management</li>
<li>Created documentation with function maps</li>
</ul>

<h3>4. Fun Features (April 2025)</h3>

<ul>
<li>Added expandable Tom images in the Fun section</li>
<li>Added function map visualization for the outbound calling system</li>
<li>Enhanced documentation and sample data</li>
</ul>
"""
        
        # Add debug logging to help identify rendering issues
        logging.info("Rendering index.html template with hardcoded README content")
        return render_template('index.html', readme_content=readme_content)
    except Exception as e:
        # Log the error but still try to render something
        logging.error(f"Error rendering index page: {e}", exc_info=True)
        # Return a very simple HTML page directly
        return """
        <html>
            <head>
                <title>Psychic Source - Dashboard</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="bg-light">
                <div class="container mt-5">
                    <div class="alert alert-warning">
                        <h2>Dashboard Error</h2>
                        <p>The dashboard encountered an error. Please check the server logs for details.</p>
                        <p>Error: """ + str(e) + """</p>
                        <a href="/themes-sentiment" class="btn btn-primary">Try Themes & Sentiment Page</a>
                    </div>
                </div>
            </body>
        </html>
        """

@main_bp.route('/data-selection')
def data_selection():
    """Page for selecting conversation data"""
    # Only provide the current date as end_date, leave start_date empty 
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Check if a specific conversation ID was requested
    conversation_id = request.args.get('conversation_id')
    quote = request.args.get('quote')
    conversation_data = None
    
    if conversation_id:
        try:
            # Use the conversation service to fetch conversation details
            conversation_data = current_app.conversation_service.get_conversation_details(conversation_id)
            
            # If no data was returned, log a warning
            if not conversation_data or not conversation_data.get('transcript'):
                logging.warning(f"No conversation data found for ID: {conversation_id}")
                flash(f"No conversation data found for ID: {conversation_id}", "warning")
            
        except Exception as e:
            logging.error(f"Error fetching conversation {conversation_id}: {e}")
            flash(f"Error loading conversation {conversation_id}: {str(e)}", "error")
    
    return render_template('data_selection.html', 
                          start_date="",
                          end_date=end_date,
                          conversation_id=conversation_id,
                          quote=quote,
                          conversation_data=conversation_data)

@main_bp.route('/api/export/<format>')
def export_data(format):
    """API endpoint to export data in different formats"""
    data_type = request.args.get('type', 'conversations')
    conversation_id = request.args.get('conversation_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get data based on request parameters
        if data_type == 'conversation' and conversation_id:
            # Export a single conversation
            data = current_app.conversation_service.get_conversation_details(conversation_id)
            filename = current_app.export_service.generate_filename('conversation', conversation_id)
        else:
            # Export multiple conversations
            result = current_app.conversation_service.get_conversations(
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Increased limit for exports
            )
            data = result.get('conversations', [])
            date_range = f"{start_date}_to_{end_date}" if start_date and end_date else "all"
            filename = current_app.export_service.generate_filename('conversations', date_range)
            
        # Export the data using the export service
        buffer, mimetype = current_app.export_service.export_data(data, format)
        
        if not buffer or not mimetype:
            return jsonify({'error': 'Failed to export data'}), 500
            
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{filename}.{format}"
        )
        
    except Exception as e:
        logging.error(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/analysis')
def analysis_page():
    """Page for analyzing conversation data"""
    return render_template('analysis.html')

@main_bp.route('/themes-sentiment')
def themes_sentiment_page():
    """Renders the refactored Themes & Sentiment analysis page."""
    return render_template('themes_sentiment_refactored.html')

@main_bp.route('/api/total_conversations')
def total_conversations():
    """API endpoint to get the total number of conversations from the database."""
    try:
        # --- Query database count --- 
        from app.extensions import db
        from app.models import Conversation
        from sqlalchemy import func
        
        try:
            total = db.session.query(func.count(Conversation.id)).scalar() or 0
            logging.info(f"Total conversations count from DB: {total}")
        except Exception as db_err:
            logging.error(f"Database error getting conversation count: {db_err}", exc_info=True)
            # Fallback to a fixed count if database query fails
            total = 150  # Fallback to a reasonable value
            logging.warning(f"Using fallback total conversations count: {total}")
        
        # Create response with unique timestamp for cache control
        timestamp = datetime.now().isoformat()
        random_value = str(random.randint(10000, 99999))
        
        result = {
            'total': total,
            'timestamp': timestamp,
            'random': random_value,
            'is_fallback': not isinstance(total, int) or db_err if 'db_err' in locals() else False
        }
        
        # Use jsonify to ensure proper JSON encoding
        response = jsonify(result)
        
        # Add extremely aggressive cache control headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Expires'] = '0'  # For Nginx
        response.headers['X-Cache-Control'] = 'no-cache'
        response.headers['Surrogate-Control'] = 'no-store'
        response.headers['Vary'] = '*'  # Ensure unique caching per request
        response.headers['Content-Type'] = 'application/json; charset=utf-8'  # Explicit content type
        
        return response
        
    except Exception as e:
        # Generic error handling for database query issues
        logging.error(f"Error getting total conversations from DB: {e}", exc_info=True)
        return jsonify({
            'error': f"Failed to retrieve total conversation count: {str(e)}",
            'total': 150,  # Fallback value
            'is_fallback': True
        }), 200  # Return 200 instead of 500 to avoid breaking the frontend

@main_bp.route('/api/visualization/data')
def visualization_data():
    """API endpoint to get data for the visualization page using improved sample data."""
    try:
        # Get timeframe, start_date, end_date from request arguments
        timeframe = request.args.get('timeframe') # e.g., 'last_7_days', 'last_30_days', etc.
        start_date_str = request.args.get('start_date') # e.g., '2023-10-01'
        end_date_str = request.args.get('end_date') # e.g., '2023-10-31'

        logging.info(
            f"API Request: /api/visualization/data - Timeframe: {timeframe}, "
            f"Start: {start_date_str}, End: {end_date_str}"
        )

        # --- Date Handling: Calculate dates based on timeframe if provided --- 
        # Priority: Custom dates > Timeframe preset > Default (30 days)
        
        if not start_date_str and not end_date_str and timeframe: 
            # Calculate dates from timeframe preset
            logging.info(f"Calculating date range from timeframe: {timeframe}")
            today = datetime.now(timezone.utc)
            end_dt_naive = today # End date is today
            end_date_str = end_dt_naive.strftime('%Y-%m-%d')
            
            start_dt_naive = today # Start from today
            if timeframe == 'last_7_days':
                start_dt_naive -= timedelta(days=7)
            elif timeframe == 'last_30_days':
                start_dt_naive -= timedelta(days=30)
            elif timeframe == 'last_90_days':
                start_dt_naive -= timedelta(days=90)
            elif timeframe == 'all_time':
                 # Use a very early date for all_time
                 start_dt_naive = datetime(2020, 1, 1, tzinfo=timezone.utc)
            else: # Default to last 30 days if timeframe is unrecognized
                logging.warning(f"Unrecognized timeframe '{timeframe}', defaulting to last 30 days.")
                start_dt_naive -= timedelta(days=30)
                timeframe = 'last_30_days' # Correct the timeframe variable for the response
                
            start_date_str = start_dt_naive.strftime('%Y-%m-%d')
            logging.info(f"Calculated range from timeframe: {start_date_str} to {end_date_str}")
        
        # Generate a realistic date range from start_date to end_date
        date_range = []
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                current_dt = start_dt
                while current_dt <= end_dt:
                    date_range.append(current_dt.strftime('%Y-%m-%d'))
                    current_dt += timedelta(days=1)
            except Exception as date_err:
                logging.error(f"Error generating date range: {date_err}")
                # Fallback to a 7-day range
                date_range = [
                    '2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', 
                    '2025-04-05', '2025-04-06', '2025-04-07', '2025-04-08'
                ]
        else:
            # Default date range
            date_range = [
                '2025-04-01', '2025-04-02', '2025-04-03', '2025-04-04', 
                '2025-04-05', '2025-04-06', '2025-04-07', '2025-04-08'
            ]
            
        # Generate realistic volume data (vary by day of week)
        volume_data = []
        for date_str in date_range:
            # Create a pattern where weekends have fewer calls
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            if date_obj.weekday() >= 5:  # Weekend
                volume_data.append(random.randint(8, 15))
            else:  # Weekday
                volume_data.append(random.randint(15, 30))
        
        # Generate realistic duration data (4-8 minutes)
        duration_data = [random.randint(240, 480) for _ in date_range]
        
        # Use improved visualization data
        metrics_data = {
            'volume': {
                'labels': date_range,
                'data': volume_data
            },
            'duration': {
                'labels': date_range,
                'data': duration_data
            },
            'time_of_day': {
                'labels': [f'{h}:00' for h in range(24)],
                'data': [2, 1, 0, 0, 0, 1, 3, 5, 12, 18, 25, 29, 32, 30, 26, 22, 18, 15, 12, 10, 8, 5, 3, 2]
            },
            'day_of_week': {
                'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                'data': [94, 102, 115, 108, 90, 55, 42]
            },
            'date_range': {
                'start_date': start_date_str,
                'end_date': end_date_str
            }
        }
            
        # Add timeframe to metrics data
        if timeframe:
            metrics_data['timeframe'] = timeframe
                
        logging.info("Returning enhanced sample data for visualization metrics")
        return jsonify(metrics_data), 200

    except Exception as e:
        # Catch unexpected errors in the route handler itself
        logging.error(f"Unexpected error in /api/visualization/data route: {e}", exc_info=True)
        # Return a generic error response with empty chart structure
        return jsonify(generate_empty_visualization_response(
            start_date_str if 'start_date_str' in locals() else None,
            end_date_str if 'end_date_str' in locals() else None,
            timeframe if 'timeframe' in locals() else 'last_30_days',
            error=f"Unexpected error: {str(e)}"
        )), 200  # Return 200 to avoid breaking the frontend

# Helper function to generate empty visualization response
def generate_empty_visualization_response(start_date=None, end_date=None, timeframe=None, error=None):
    """Generate a consistent empty response structure for visualization data."""
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    response = {
        'volume': {'labels': [], 'data': []},
        'duration': {'labels': [], 'data': []},
        'time_of_day': {'labels': [f'{h}:00' for h in range(24)], 'data': [0] * 24},
        'day_of_week': {'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], 'data': [0] * 7},
        'completion': {'labels': [], 'data': []},
        'date_range': {
            'start_date': start_date,
            'end_date': end_date
        }
    }
    
    if timeframe:
        response['timeframe'] = timeframe
    
    if error:
        response['error'] = error
    
    return response

@main_bp.route('/api/themes-sentiment/data')
def themes_sentiment_data():
    """API endpoint to get themes and sentiment analysis data"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        timeframe = request.args.get('timeframe', 'day')  # day, week, month
        
        logging.info(f"Themes-sentiment data requested for timeframe: {timeframe}, date range: {start_date} to {end_date}")
        
        # Apply preset timeframes if requested - match the pattern from visualization_data
        if timeframe:
            logging.info(f"Using timeframe: {timeframe}")
            end_date = datetime.now().strftime('%Y-%m-%d')
            if timeframe == 'last_7_days':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                logging.info(f"Setting start_date to 7 days ago: {start_date}")
            elif timeframe == 'last_30_days':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                logging.info(f"Setting start_date to 30 days ago: {start_date}")
            elif timeframe == 'last_90_days':
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                logging.info(f"Setting start_date to 90 days ago: {start_date}")
            elif timeframe == 'all':
                # Set to beginning of 2025 for "all time"
                start_date = '2025-01-01'
                logging.info(f"Setting start_date to all time: {start_date}")
        
        # Get conversations for this date range
        result = current_app.conversation_service.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        conversations = result.get('conversations', [])
        
        logging.info(f"Retrieved {len(conversations)} conversations for themes analysis")
        
        # Use analysis service to analyze themes and sentiment
        analysis_result = current_app.analysis_service.analyze_conversations_over_time(
            conversations=conversations,
            timeframe=timeframe
        )
        
        # Check if we have data
        if not analysis_result or not analysis_result.get('sentiment_over_time'):
            logging.warning("No analysis data returned from analysis service")
        
        # Return the analysis results
        return jsonify({
            'status': 'success',
            'data': analysis_result,
            'metadata': {
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe,
                'conversation_count': len(conversations)
            }
        })
    except Exception as e:
        logging.error(f"Error generating themes-sentiment data: {e}")
        logging.error(traceback.format_exc())
        
        # Return empty data structure with success status (match other endpoints pattern)
        # This ensures the UI can still load and show appropriate empty states
        return jsonify({
            'status': 'success',
            'data': {
                'sentiment_over_time': [],
                'top_themes': [],
                'sentiment_by_theme': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': []
            },
            'metadata': {
                'start_date': start_date if 'start_date' in locals() else None,
                'end_date': end_date if 'end_date' in locals() else None,
                'timeframe': timeframe if 'timeframe' in locals() else 'day',
                'conversation_count': 0,
                'error': str(e)
            }
        }), 200  # Use 200 for consistency with other endpoints

@main_bp.route('/api/themes-sentiment/refresh', methods=['POST'])
def refresh_themes_sentiment_data():
    """API endpoint to force a refresh of themes and sentiment analysis data"""
    try:
        timeframe = request.args.get('timeframe', 'last_30_days')
        logging.info(f"Force refreshing themes-sentiment data for timeframe: {timeframe}")
        
        # Apply preset timeframes
        end_date = datetime.now().strftime('%Y-%m-%d')
        if timeframe == 'last_7_days':
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        elif timeframe == 'last_30_days':
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif timeframe == 'last_90_days':
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        elif timeframe == 'all':
            start_date = '2025-01-01'
        else:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Clear any cached data by reinitializing the analyzer if needed
        if hasattr(current_app.analysis_service.analyzer, 'initialize_openai'):
            current_app.analysis_service.analyzer.initialize_openai()
            
        # Clear the backend analysis cache
        current_app.analysis_service.clear_cache()
        logging.info("Cleared backend analysis cache for refresh.")
        
        # Get conversations using the conversation service with a force refresh parameter
        result = current_app.conversation_service.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=1000,
            force_refresh=True  # Add this parameter to the method signature
        )
        
        # Get conversations data
        conversations = result.get('conversations', [])
        logging.info(f"Received {len(conversations)} conversations for refresh")
        
        # Force refresh by calling analyze_conversations_over_time directly
        analysis_result = current_app.analysis_service.analyze_conversations_over_time(
            conversations=conversations, 
            timeframe=timeframe
        )
        
        # Log results
        sentiment_over_time = analysis_result.get('sentiment_over_time', [])
        top_themes = analysis_result.get('top_themes', [])
        sentiment_by_theme = analysis_result.get('sentiment_by_theme', [])
        
        return jsonify({
            'status': 'success',
            'message': f'Refreshed themes and sentiment data for {timeframe}',
            'data': {
                'conversation_count': len(conversations),
                'themes_count': len(top_themes),
                'sentiment_by_theme_count': len(sentiment_by_theme),
                'sentiment_points': len(sentiment_over_time)
            }
        })
    except Exception as e:
        logging.error(f"Error refreshing themes-sentiment data: {e}")
        logging.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@main_bp.route('/api/status')
def api_status():
    """API endpoint to check the status of various services"""
    # Import necessary modules within the function if they cause issues at import time
    from app.extensions import db
    import sys
    from pathlib import Path
    
    # Initialize the response with default 'error' states
    status = {
        'database': {'status': 'error', 'message': 'Check failed'},
        'elevenlabs': {'status': 'error', 'message': 'Check failed'},
        'analysis': {'status': 'error', 'message': 'Check failed'},
        'supabase': {'status': 'error', 'message': 'Check failed'},
        'openai': {'status': 'error', 'message': 'Check failed'}
    }

    try: 
        # --- Database Check ---
        try:
            result = db.session.execute(db.select(db.text("1"))).scalar()
            if result == 1:
                status['database']['status'] = 'connected'
                status['database']['message'] = 'Connected to database'
            else:
                 status['database']['status'] = 'disconnected'
                 status['database']['message'] = 'Query returned unexpected result'
        except Exception as e:
            status['database']['status'] = 'error'
            status['database']['message'] = f"DB Error: {str(e)[:100]}" # Truncate long errors

        # --- ElevenLabs Check ---
        try:
            client = getattr(current_app, 'elevenlabs_client', None)
            if client and client.api_key:
                # Client object exists and seems configured, try a real API call
                current_app.logger.info("API Status: Attempting ElevenLabs client.test_connection()...")
                try:
                    is_connected = client.test_connection() # Use the correct test method
                    current_app.logger.info(f"API Status: test_connection() response: {is_connected}") 
                    
                    if is_connected:
                        status['elevenlabs']['status'] = 'connected'
                        status['elevenlabs']['message'] = 'ElevenLabs API client connected and verified.'
                    else:
                        status['elevenlabs']['status'] = 'error' # Or 'disconnected'
                        status['elevenlabs']['message'] = 'API connection test failed. Key invalid or service unreachable.'
                        current_app.logger.warning(f"API Status: test_connection() returned false.")
                except Exception as api_call_e:
                    status['elevenlabs']['status'] = 'error' # Or 'disconnected'
                    status['elevenlabs']['message'] = f'API connection test failed: {str(api_call_e)[:100]}'
                    current_app.logger.error(f"API Status: test_connection() call failed: {api_call_e}", exc_info=True) # Log the exception
            elif client:
                status['elevenlabs']['status'] = 'disconnected'
                status['elevenlabs']['message'] = 'Client configured but missing API key' # Updated message
            else:
                 status['elevenlabs']['status'] = 'disconnected'
                 status['elevenlabs']['message'] = 'Client not initialized'
        except Exception as e:
            status['elevenlabs']['status'] = 'error'
            status['elevenlabs']['message'] = f"ElevenLabs Check Error: {str(e)[:100]}"
            current_app.logger.error(f"API Status: Outer exception during ElevenLabs check: {e}", exc_info=True) # Log outer exception

        # --- Analysis Service Check ---
        try:
            if (hasattr(current_app, 'analysis_service') and 
                current_app.analysis_service and 
                hasattr(current_app.analysis_service, 'analyzer') and
                current_app.analysis_service.analyzer):
                
                analyzer = current_app.analysis_service.analyzer
                if analyzer.openai_client:
                    status['analysis']['status'] = 'available'
                    status['analysis']['message'] = f"Analysis service ready (OpenAI: {'lightweight' if analyzer.lightweight_mode else 'full'})"
                else:
                    status['analysis']['status'] = 'limited'
                    status['analysis']['message'] = "Limited analysis available (no OpenAI)"
            else:
                 status['analysis']['status'] = 'unavailable'
                 status['analysis']['message'] = "Analysis service not initialized"
        except Exception as e:
             status['analysis']['status'] = 'error'
             status['analysis']['message'] = f"Analysis Error: {str(e)[:100]}"

        # --- OpenAI Check (within Analysis Service check is logical) ---
        # This assumes the analysis service check above succeeded and found the analyzer
        try:
            if (status['analysis']['status'] != 'error' and 
                hasattr(current_app, 'analysis_service') and 
                current_app.analysis_service and 
                hasattr(current_app.analysis_service, 'analyzer')):
                
                analyzer = current_app.analysis_service.analyzer
                # Check if analyzer object itself exists AND has the openai_client attribute
                if analyzer and hasattr(analyzer, 'openai_client') and analyzer.openai_client:
                    status['openai']['status'] = 'available'
                    status['openai']['message'] = 'OpenAI client configured'
                else:
                    status['openai']['status'] = 'unavailable'
                    status['openai']['message'] = 'OpenAI client not configured or analysis limited'
            else:
                 status['openai']['status'] = 'unavailable'
                 status['openai']['message'] = 'Analysis service unavailable, cannot check OpenAI'
        except Exception as e:
            status['openai']['status'] = 'error'
            status['openai']['message'] = f"OpenAI Check Error: {str(e)[:100]}"

        # --- Supabase Check ---
        try:
            # >>> REVISED SUPABASE CHECK <<<
            # Check if the supabase_client was successfully initialized in create_app
            if hasattr(current_app, 'supabase_client') and current_app.supabase_client and current_app.supabase_client.client:
                # Client object exists, now try a lightweight query to confirm connection
                try:
                    # Use the existing client instance from the app context
                    supabase_client = current_app.supabase_client
                    # Example: Try to list tables via RPC (adjust if get_tables uses RPC differently or choose another simple query)
                    tables_result = supabase_client.get_tables() # Assumes get_tables is a light RPC call
                    
                    # Check if the result indicates success (e.g., is a list)
                    if isinstance(tables_result, list):
                        status['supabase']['status'] = 'connected'
                        status['supabase']['message'] = 'Supabase client connected and query successful.'
                    else:
                        status['supabase']['status'] = 'limited'
                        status['supabase']['message'] = f'Client connected but test query failed or returned unexpected data: {str(tables_result)[:50]}'
                except Exception as query_e:
                    # Query failed, but client exists
                    status['supabase']['status'] = 'disconnected' # Or 'limited' depending on desired state
                    status['supabase']['message'] = f'Client initialized but connection query failed: {str(query_e)[:100]}'
            elif hasattr(current_app, 'conversation_service') and isinstance(current_app.conversation_service, SupabaseConversationService):
                # Fallback: If client isn't on app context, check if the service is Supabase type
                # This suggests Supabase was intended but client might not be stored globally
                status['supabase']['status'] = 'limited' # Consider this limited as direct client access failed
                status['supabase']['message'] = 'Supabase service active, but client check failed.' 
            else:
                # Neither client nor Supabase service seems active
                status['supabase']['status'] = 'disconnected' # Or 'unavailable'
                status['supabase']['message'] = 'Supabase client or service not initialized.'
            # >>> END REVISED CHECK <<<

        except Exception as e:
            # Catch errors in the status checking logic itself
            status['supabase']['status'] = 'error'
            status['supabase']['message'] = f"Supabase Check Error: {str(e)[:100]}"

        # Return the final status object as JSON
        return jsonify(status)

    except Exception as main_e:
        # Catch any unexpected error during the overall status check
        logging.error(f"Critical error in /api/status endpoint: {main_e}", exc_info=True)
        # Return the partially filled status object with an added top-level error
        status['error'] = f"Endpoint failure: {str(main_e)[:100]}"
        return jsonify(status), 500 # Return 500 here as the endpoint itself failed

@main_bp.route('/debug-info')
def debug_info():
    """Show comprehensive debug information for troubleshooting"""
    from flask import request
    import sys
    import platform
    import os
    
    # Get debug information
    debug_data = {
        'timestamp': datetime.now().isoformat(),
        'request': {
            'host': request.host,
            'url': request.url,
            'scheme': request.scheme,
            'headers': dict(request.headers),
        },
        'system': {
            'python_version': sys.version,
            'platform': platform.platform(),
            'env_vars': {k: v for k, v in os.environ.items() if not k.startswith('_') and 'SECRET' not in k.upper() and 'KEY' not in k.upper()}
        },
        'flask': {
            'app_name': current_app.name,
            'config': {k: str(v) for k, v in current_app.config.items() if 'SECRET' not in k and 'KEY' not in k},
            'endpoints': list(current_app.url_map.iter_rules()),
        },
        'db': {
            'connected': False,
        },
        'services': {
            'conversation_service': hasattr(current_app, 'conversation_service'),
            'analysis_service': hasattr(current_app, 'analysis_service'),
            'export_service': hasattr(current_app, 'export_service'),
        }
    }
    
    # Test database connection
    try:
        count = db.session.query(func.count(Conversation.id)).scalar() or 0
        debug_data['db']['connected'] = True
        debug_data['db']['conversations_count'] = count
    except Exception as e:
        debug_data['db']['error'] = str(e)
    
    # Return HTML page with debug data
    return f"""
    <html>
        <head>
            <title>Debug Information</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-3">
                <h1>Debug Information</h1>
                <div class="card mt-3">
                    <div class="card-body">
                        <pre>{json.dumps(debug_data, indent=2, default=str)}</pre>
                    </div>
                </div>
                <div class="mt-3">
                    <a href="/" class="btn btn-primary">Back to Dashboard</a>
                </div>
            </div>
        </body>
    </html>
    """ 

@main_bp.route('/api/conversations', methods=['GET'])
def get_conversations():
    """
    API endpoint to get conversation list with metadata from Supabase, optionally filtered by date.
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    logging.info(f"Fetching conversations from Supabase: limit={limit}, offset={offset}, start={start_date}, end={end_date}")

    if not SUPABASE_AVAILABLE:
        logging.error("Supabase is not available. Cannot fetch conversations.")
        return jsonify({"error": "Supabase backend is unavailable", "conversations": [], "total_count": 0}), 503

    try:
        # Get the conversation service instance from the current app context
        conversation_service = current_app.conversation_service
        if not conversation_service:
            logging.error("Conversation service not available. Cannot fetch conversations.")
            return jsonify({"error": "Conversation service unavailable", "conversations": [], "total_count": 0}), 503

        # Check if the service is initialized (relevant for both DB and Supabase)
        # Note: The DB service doesn't have an `initialized` attribute, so we only check Supabase
        if isinstance(conversation_service, SupabaseConversationService) and not conversation_service.initialized:
            logging.error("Supabase conversation service is not initialized. Cannot fetch conversations.")
            return jsonify({"error": "Supabase service initialization failed", "conversations": [], "total_count": 0}), 500

        # Call the method on the correct service instance
        result = conversation_service.get_conversations(
            start_date=start_date, 
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        if not result:
             logging.warning(f"Supabase service returned no result for conversations query.")
             return jsonify({"conversations": [], "total_count": 0}) # Return empty list if no result

        logging.info(f"Successfully fetched {len(result.get('conversations', []))} conversations from Supabase (Total: {result.get('total_count', 0)})")
        return jsonify(result)
            
    except Exception as e:
        logging.error(f"Error getting conversations directly from Supabase: {e}", exc_info=True)
        return jsonify({"error": f"Error fetching from Supabase: {str(e)}", "conversations": [], "total_count": 0}), 500

@main_bp.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation_details(conversation_id):
    """
    API endpoint to get details of a specific conversation from Supabase.
    """
    logging.info(f"Fetching conversation details from Supabase for ID: {conversation_id}")

    if not SUPABASE_AVAILABLE:
        logging.error("Supabase is not available. Cannot fetch conversation details.")
        return jsonify({"error": "Supabase backend is unavailable"}), 503
        
    try:
        supabase_service = SupabaseConversationService()
        if not supabase_service.initialized:
            logging.error("Supabase service could not be initialized. Cannot fetch conversation details.")
            return jsonify({"error": "Supabase service initialization failed"}), 500

        conversation = supabase_service.get_conversation_details(conversation_id)
        
        if not conversation:
            logging.warning(f"Conversation {conversation_id} not found in Supabase.")
            return jsonify({"error": "Conversation not found in Supabase"}), 404
        
        logging.info(f"Successfully fetched details for conversation {conversation_id} from Supabase.")
        return jsonify(conversation)
    
    except Exception as e:
        logging.error(f"Error getting conversation details directly from Supabase for ID {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": f"Error fetching from Supabase: {str(e)}"}), 500 

@main_bp.route('/api/themes-sentiment/full-analysis')
def get_full_themes_sentiment_data():
    """API endpoint for full themes and sentiment analysis based on date range."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'

    if start_date == 'null': start_date = None
    if end_date == 'null': end_date = None
    
    # Ensure analysis_service is available
    if not hasattr(current_app, 'analysis_service') or not current_app.analysis_service:
        return jsonify({"error": "Analysis service is unavailable"}), 503

    analysis_service = current_app.analysis_service
    
    # Clear cache only if forced
    if force_refresh:
        try:
            # Use the main analysis service instance which should have the cache
            analysis_service.clear_cache()
            logging.info(f"Cache cleared for themes/sentiment due to force_refresh=true")
        except Exception as e:
             logging.error(f"Error attempting to clear cache: {e}", exc_info=True)

    # Construct a cache key based on dates
    cache_key = f"themes_full_{start_date}_{end_date}"
    
    # Try fetching from cache first (if cache is configured on the service)
    if analysis_service.cache:
        cached_result = analysis_service.cache.get(cache_key)
        if cached_result:
            logging.info(f"Returning cached themes/sentiment result for key: {cache_key}")
            return jsonify(cached_result)
            
    logging.info(f"Cache miss for themes/sentiment: {cache_key}. Fetching data...")

    # --- Fetch Conversation Data using SupabaseConversationService ---
    conversations_data = []
    try:
        # Get the correct conversation service (might be Supabase or DB fallback)
        conversation_service = current_app.conversation_service 
        if not conversation_service:
            raise Exception("Conversation service not available in app context.")

        # Only proceed if the service is the Supabase one (as this logic is Supabase specific)
        if not isinstance(conversation_service, SupabaseConversationService):
             # Log that we cannot perform this specific analysis without Supabase
             logging.warning("Full themes analysis requires Supabase backend, but it's not active. Returning empty results.")
             # Set conversations_data to empty list and skip fetching
             conversations_data = [] 
        elif not conversation_service.initialized:
             # Log that the intended Supabase service failed init
             logging.error("Supabase conversation service is not initialized. Cannot fetch data for analysis.")
             raise Exception("Supabase service initialization failed")
        else:
             # We have a valid SupabaseConversationService, proceed with fetching
             logging.info(f"Fetching ALL conversations from Supabase for themes analysis: {start_date} to {end_date}")
             # Use a large limit, or implement pagination if needed
             supabase_result = conversation_service.get_conversations( # Use the instance from app context
                 start_date=start_date, 
                 end_date=end_date,
                 limit=5000 # Adjust limit as needed, potential performance issue
             )
        
             if supabase_result and 'conversations' in supabase_result:
                 conversations_data = supabase_result['conversations']
                 logging.info(f"Fetched {len(conversations_data)} conversations from Supabase for analysis.")
             else:
                 logging.warning(f"Supabase returned no conversations for range {start_date}-{end_date}")
                 conversations_data = []

    except Exception as e:
        logging.error(f"Failed to fetch conversations from Supabase for analysis: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch data: {e}"}), 500
    # --- End Fetch --- 

    # --- Perform Analysis --- 
    try:
        if not conversations_data:
            logging.warning("No conversations found for the selected period to analyze.")
            # Return empty structure but success
            analysis_result = {
                'sentiment_over_time': [], 'top_themes': [], 'sentiment_by_theme': [],
                'common_questions': [], 'concerns_skepticism': [], 'positive_interactions': []
            }
        else:
            # Call the analysis method (which might use its own internal cache via memoize)
            analysis_result = analysis_service.analyze_conversations_over_time(conversations_data)
        
        # Store result in our manual cache if cache is configured
        if analysis_service.cache:
             analysis_service.cache.set(cache_key, analysis_result, timeout=3600) # Cache for 1 hour
             logging.info(f"Stored themes/sentiment result in cache key: {cache_key}")
             
        return jsonify(analysis_result)
        
    except Exception as e:
        logging.error(f"Error during conversation analysis: {e}", exc_info=True)
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500 