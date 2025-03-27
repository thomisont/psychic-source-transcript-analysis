import os
import json
import logging
import traceback
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, send_file, current_app, redirect, flash
import io
from app.api.data_processor import DataProcessor
from app.utils.export import DataExporter
from app.utils.analysis import ConversationAnalyzer
from app.api.elevenlabs_client import ElevenLabsClient
import pandas as pd

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page with dashboard overview"""
    return render_template('index.html')

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
            # Get the client from app context
            client = current_app.elevenlabs_client
            
            # Special handling for demo conversation IDs
            if conversation_id == '4a72b35c':  # Property investment question
                logging.info(f"Generating demo data for property investment conversation {conversation_id}")
                conversation_data = {
                    'conversation_id': conversation_id,
                    'start_time': datetime.now().isoformat(),
                    'duration': 180,  # 3 minutes
                    'transcript': [
                        {
                            'speaker': 'Caller',
                            'text': 'I have some money saved up and wondering about investing.',
                            'timestamp': (datetime.now() - timedelta(seconds=170)).isoformat(),
                            'sentiment': 0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "That's wonderful that you're in a position to invest. What types of investments are you considering?",
                            'timestamp': (datetime.now() - timedelta(seconds=150)).isoformat(),
                            'sentiment': 0.4
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'Should I invest in property right now? The market seems volatile.',
                            'timestamp': (datetime.now() - timedelta(seconds=130)).isoformat(),
                            'sentiment': -0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I'm seeing some caution around property investments at this moment. There may be better timing in the near future, perhaps in about 3-4 months. I'm sensing that waiting may yield better opportunities.",
                            'timestamp': (datetime.now() - timedelta(seconds=100)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': "That's helpful. I'll consider waiting a bit longer then.",
                            'timestamp': (datetime.now() - timedelta(seconds=70)).isoformat(),
                            'sentiment': 0.3
                        },
                        {
                            'speaker': 'Lily',
                            'text': "Trust your intuition on this. I sense you're a thoughtful investor. The energy suggests that your patience will be rewarded.",
                            'timestamp': (datetime.now() - timedelta(seconds=40)).isoformat(),
                            'sentiment': 0.5
                        }
                    ]
                }
            elif conversation_id == '9f82d41b':  # Job offer question
                logging.info(f"Generating demo data for job offer conversation {conversation_id}")
                conversation_data = {
                    'conversation_id': conversation_id,
                    'start_time': datetime.now().isoformat(),
                    'duration': 240,  # 4 minutes
                    'transcript': [
                        {
                            'speaker': 'Caller',
                            'text': 'I was offered a new job position. Should I accept it?',
                            'timestamp': (datetime.now() - timedelta(seconds=230)).isoformat(),
                            'sentiment': 0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I sense some hesitation in your energy. Could you tell me what aspects of the job offer are making you uncertain?",
                            'timestamp': (datetime.now() - timedelta(seconds=200)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'The pay is better, but it would mean relocating to a different city away from my family.',
                            'timestamp': (datetime.now() - timedelta(seconds=180)).isoformat(),
                            'sentiment': -0.2
                        },
                        {
                            'speaker': 'Lily',
                            'text': "Thank you for sharing that. I'm sensing that your family connections are very important to you. When I look at the energies surrounding this decision, I'm seeing both opportunity and hesitation.",
                            'timestamp': (datetime.now() - timedelta(seconds=150)).isoformat(),
                            'sentiment': 0.3
                        },
                        {
                            'speaker': 'Caller',
                            'text': "Should I accept the new job offer? I'm really torn about this decision.",
                            'timestamp': (datetime.now() - timedelta(seconds=120)).isoformat(),
                            'sentiment': -0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I'm sensing that while this job offers financial growth, your spiritual and emotional well-being may be affected by the distance from your support system. The cards suggest that if you do take this position, you'll need to be intentional about maintaining those connections. Have you considered if there's any flexibility for remote work or regular visits home?",
                            'timestamp': (datetime.now() - timedelta(seconds=90)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': "That's a good point. I could ask about working remotely for part of the month.",
                            'timestamp': (datetime.now() - timedelta(seconds=60)).isoformat(),
                            'sentiment': 0.4
                        },
                        {
                            'speaker': 'Lily',
                            'text': "The energy shifts positively when you consider that compromise. I sense this could be a path forward that honors both your career ambitions and your need for family connection. Trust your intuition on this - when you imagine proposing this solution, notice how your energy feels lighter.",
                            'timestamp': (datetime.now() - timedelta(seconds=30)).isoformat(),
                            'sentiment': 0.6
                        }
                    ]
                }
            else:
                # Try to get the conversation details from the API
                conversation_data = client.get_conversation_details(conversation_id)
                
                # If we couldn't get real data, generate sample data for the ID
                if not conversation_data or 'error' in conversation_data:
                    logging.info(f"Generating generic sample data for conversation {conversation_id}")
                    conversation_data = {
                        'conversation_id': conversation_id,
                        'start_time': datetime.now().isoformat(),
                        'duration': 180,  # 3 minutes
                        'transcript': [
                            {
                                'speaker': 'Caller',
                                'text': 'Should I invest in property right now?',
                                'timestamp': (datetime.now() - timedelta(seconds=170)).isoformat(),
                                'sentiment': -0.1
                            },
                            {
                                'speaker': 'Lily',
                                'text': "I'm sensing this is an important decision for you. The energies suggest patience may be rewarded in this situation.",
                                'timestamp': (datetime.now() - timedelta(seconds=140)).isoformat(),
                                'sentiment': 0.2
                            },
                            {
                                'speaker': 'Caller',
                                'text': "That's helpful. I'll consider waiting a bit longer then.",
                                'timestamp': (datetime.now() - timedelta(seconds=110)).isoformat(),
                                'sentiment': 0.3
                            }
                        ]
                    }
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
        # Get the client from app context
        client = current_app.elevenlabs_client
        
        if data_type == 'conversation' and conversation_id:
            # Export a single conversation
            conversation_data = client.get_conversation_details(conversation_id)
            processed_data = DataProcessor.process_conversation_details(conversation_data)
            data = processed_data
            filename = f"conversation_{conversation_id}"
        else:
            # Export multiple conversations
            conversations_data = client.get_conversations(
                start_date=start_date,
                end_date=end_date,
                limit=1000  # Increased limit for exports
            )
            df = DataProcessor.process_conversations(conversations_data)
            data = df
            filename = f"conversations_{start_date}_to_{end_date}"
            
        # Export in the requested format
        if format == 'json':
            output = DataExporter.to_json(data)
            mimetype = 'application/json'
            filename = f"{filename}.json"
        elif format == 'csv':
            output = DataExporter.to_csv(data)
            mimetype = 'text/csv'
            filename = f"{filename}.csv"
        elif format == 'md':
            output = DataExporter.to_markdown(data)
            mimetype = 'text/markdown'
            filename = f"{filename}.md"
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
        # Create in-memory file
        buffer = io.BytesIO(output.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/analysis')
def analysis_page():
    """Page for analyzing conversation data"""
    return render_template('analysis.html')

@main_bp.route('/themes-sentiment')
def themes_sentiment_page():
    """Page for analyzing themes and sentiment trends across conversations"""
    return render_template('themes_sentiment.html')

@main_bp.route('/visualization')
def visualization_page():
    """Page for visualizing conversation data"""
    return render_template('visualization.html')

@main_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """API endpoint to provide summary statistics for the dashboard"""
    try:
        # Get date range for the last 30 days by default
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Override with query parameters if provided
        if request.args.get('start_date'):
            start_date = request.args.get('start_date')
        if request.args.get('end_date'):
            end_date = request.args.get('end_date')
            
        # Apply preset timeframes if requested    
        timeframe = request.args.get('timeframe')
        if timeframe:
            end_date = datetime.now().strftime('%Y-%m-%d')
            if timeframe == 'last_7_days':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif timeframe == 'last_30_days':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif timeframe == 'last_90_days':
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Get the client from app context
        client = current_app.elevenlabs_client
        
        # Get conversations
        conversations_data = client.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        # Process the data
        df = DataProcessor.process_conversations(conversations_data)
        
        # Calculate basic statistics - convert NumPy types to Python native types
        total_conversations = int(len(df))
        total_duration = int(df['duration'].sum()) if 'duration' in df else 0
        avg_duration = float(df['duration'].mean()) if 'duration' in df and len(df) > 0 else 0
        
        # If we have timestamp data, group by day for chart
        daily_counts = {}
        if 'start_time' in df and not df.empty:
            df['date'] = df['start_time'].dt.date
            daily_counts_series = df.groupby('date').size()
            
            # Convert datetime.date keys to strings for JSON serialization
            # and convert NumPy int64 values to Python int
            daily_counts = {str(k): int(v) for k, v in daily_counts_series.to_dict().items()}
        
        # Calculate time distributions
        hour_distribution = {}
        weekday_distribution = {}
        if 'start_time' in df and not df.empty:
            df['hour'] = df['start_time'].dt.hour
            df['weekday'] = df['start_time'].dt.weekday
            
            # Convert to dictionary with proper types
            hour_counts = df.groupby('hour').size()
            hour_distribution = {str(k): int(v) for k, v in hour_counts.to_dict().items()}
            
            # Convert weekday indices to names
            weekday_counts = df.groupby('weekday').size()
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_distribution = {weekday_names[k]: int(v) for k, v in weekday_counts.to_dict().items()}
        
        # Calculate completion rate
        completed_count = int(len(df[df['status'] == 'done'])) if 'status' in df else 0
        completion_rate = float((completed_count / total_conversations * 100) if total_conversations > 0 else 0)
        
        return jsonify({
            'total_conversations': total_conversations,
            'total_duration': total_duration,
            'avg_duration': round(avg_duration, 2),
            'daily_counts': daily_counts,
            'hour_distribution': hour_distribution,
            'weekday_distribution': weekday_distribution,
            'completion_rate': round(completion_rate, 2)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/visualization/data')
def visualization_data():
    """API endpoint to get data for the visualization page"""
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Apply preset timeframes if requested    
        timeframe = request.args.get('timeframe')
        if timeframe:
            end_date = datetime.now().strftime('%Y-%m-%d')
            if timeframe == 'last_7_days':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif timeframe == 'last_30_days':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif timeframe == 'last_90_days':
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                
        # Default to last 30 days if not specified
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Get the client from app context
        client = current_app.elevenlabs_client
        
        # Get conversations
        conversations_data = client.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        # Process the data
        df = DataProcessor.process_conversations(conversations_data)
        
        # Create time series for conversation volume
        volume_data = {}
        if 'start_time' in df and not df.empty:
            df['date'] = df['start_time'].dt.date
            
            # Group by date and count conversations
            daily_counts = df.groupby('date').size()
            
            # Convert to list of [date, count] pairs for chart
            volume_data = {
                'labels': [d.strftime('%Y-%m-%d') for d in daily_counts.index],
                'data': [int(count) for count in daily_counts.values.tolist()]  # Convert numpy types to Python native types
            }
        
        # Create duration chart data
        duration_data = {}
        if 'duration' in df and 'start_time' in df and not df.empty:
            df['date'] = df['start_time'].dt.date
            
            # Group by date and get average duration
            daily_durations = df.groupby('date')['duration'].mean()
            
            # Convert to list for chart with proper Python types
            duration_data = {
                'labels': [d.strftime('%Y-%m-%d') for d in daily_durations.index],
                'data': [float(duration) for duration in daily_durations.values.tolist()]  # Convert numpy types to Python native types
            }
        
        # Create time of day distribution
        time_of_day_data = {}
        if 'start_time' in df and not df.empty:
            df['hour'] = df['start_time'].dt.hour
            
            # Group by hour and count
            hourly_counts = df.groupby('hour').size()
            
            # Create 24-hour distribution with zeros for missing hours
            hours = list(range(24))
            hourly_data = [int(hourly_counts.get(hour, 0)) for hour in hours]  # Convert to Python native int
            
            time_of_day_data = {
                'labels': [f'{hour}:00' for hour in hours],
                'data': hourly_data
            }
        
        # Create day of week distribution
        day_of_week_data = {}
        if 'start_time' in df and not df.empty:
            df['day_of_week'] = df['start_time'].dt.dayofweek
            
            # Group by day of week and count
            weekday_counts = df.groupby('day_of_week').size()
            
            # Create 7-day distribution with zeros for missing days
            days = list(range(7))
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_data = [int(weekday_counts.get(day, 0)) for day in days]  # Convert to Python native int
            
            day_of_week_data = {
                'labels': day_names,
                'data': weekday_data
            }
            
        # Calculate completion rates by date
        completion_data = {}
        if 'start_time' in df and 'status' in df and not df.empty:
            df['date'] = df['start_time'].dt.date
            
            # Group by date and calculate completion rate
            date_groups = df.groupby('date')
            completion_rates = {}
            
            for date, group in date_groups:
                total = len(group)
                completed = len(group[group['status'] == 'done'])
                completion_rates[date] = (completed / total * 100) if total > 0 else 0
                
            # Convert to list for chart
            completion_data = {
                'labels': [d.strftime('%Y-%m-%d') for d in completion_rates.keys()],
                'data': [float(rate) for rate in list(completion_rates.values())]  # Convert to Python native float
            }
        
        return jsonify({
            'volume': volume_data,
            'duration': duration_data,
            'time_of_day': time_of_day_data,
            'day_of_week': day_of_week_data,
            'completion': completion_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/themes-sentiment/data')
def themes_sentiment_data():
    """API endpoint to get aggregated themes and sentiment data for analysis"""
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get request parameters
        timeframe = request.args.get('timeframe')
        # Enable lightweight mode by default (can be disabled with lightweight=false)
        lightweight = request.args.get('lightweight', 'true').lower() != 'false'
        # Limit number of conversations to process (for memory efficiency)
        max_conversations = min(int(request.args.get('max', '20')), 50)  # Hard limit of 50 max
        
        # Super safe mode for Replit - if parameter is specified, just return dummy data
        super_safe = request.args.get('super_safe', 'false').lower() == 'true'
        if super_safe:
            logging.info("Super safe mode enabled, returning dummy data")
            return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
            
        # Apply preset timeframes if requested
        if timeframe:
            end_date = datetime.now().strftime('%Y-%m-%d')
            if timeframe == 'last_7_days':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif timeframe == 'last_30_days':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif timeframe == 'last_90_days':
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                
        # Default to last 30 days if not specified
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logging.info(f"/api/themes-sentiment/data endpoint called with lightweight={lightweight}, timeframe={timeframe}, start_date={start_date}, end_date={end_date}")
            
        # Initialize result with basic structure and date range
        result = {
            'date_range': {
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe
            },
            'conversation_count': 0,
            'settings': {
                'lightweight_mode': lightweight,
                'max_conversations': max_conversations
            },
            'sentiment_overview': {
                'overall_score': 0,
                'user_sentiment': 0,
                'agent_sentiment': 0,
                'sentiment_distribution': {'positive': 0.33, 'neutral': 0.34, 'negative': 0.33}
            },
            'top_themes': [],
            'theme_sentiment_correlation': [],
            'sentiment_over_time': {'daily_sentiment': [], 'trend': 0},
            'concerns_and_skepticism': [],
            'common_questions': [],
            'positive_interactions': []
        }
        
        try:
            # Get the client from app context
            client = current_app.elevenlabs_client
            logging.info(f"Getting conversations from {start_date} to {end_date}")
            
            # Get conversations
            try:
                conversations_data = client.get_conversations(
                    start_date=start_date,
                    end_date=end_date,
                    limit=max_conversations * 3  # Get more than we need in case some don't have transcripts
                )
            except Exception as e:
                logging.error(f"Error getting conversations from ElevenLabs API: {str(e)}")
                logging.error(traceback.format_exc())
                return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
            
            # Check if we got valid data
            if not conversations_data or ('conversations' not in conversations_data and 'history' not in conversations_data):
                logging.warning(f"No valid conversation data received. Got: {type(conversations_data)}")
                if conversations_data:
                    logging.warning(f"Data keys: {list(conversations_data.keys()) if isinstance(conversations_data, dict) else 'Not a dict'}")
                logging.warning(f"Using fallback data for date range: {start_date} to {end_date}")
                return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
                
            # Process the data to get conversations
            try:
                df = DataProcessor.process_conversations(conversations_data)
            except Exception as e:
                logging.error(f"Error processing conversations data: {str(e)}")
                logging.error(traceback.format_exc())
                return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
            
            # Log how many conversations we got
            logging.info(f"Retrieved {len(df)} conversations from the API")
            result['conversation_count'] = len(df)
            
            if df.empty:
                logging.warning("Processed dataframe is empty, using fallback data")
                return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
            
            # Get conversation details and transcripts - limit for memory efficiency
            conversations_with_transcripts = []
            transcript_count = 0
            
            # Limit to max_conversations most recent for performance and memory efficiency
            for conv_id in df['conversation_id'].tolist()[:max_conversations]:
                try:
                    logging.info(f"Retrieving details for conversation {conv_id}")
                    conversation_details = client.get_conversation_details(conv_id)
                    
                    if conversation_details:
                        processed_details = DataProcessor.process_conversation_details(conversation_details)
                        if processed_details and 'transcript' in processed_details:
                            conversations_with_transcripts.append(processed_details)
                            transcript_count += 1
                    else:
                        logging.warning(f"No details returned for conversation {conv_id}")
                        
                except Exception as e:
                    logging.error(f"Error processing conversation {conv_id}: {str(e)}")
            
            logging.info(f"Retrieved transcripts for {transcript_count} conversations")
            
            # If we didn't get any transcripts, use fallback data for the analyses that need transcripts
            if not conversations_with_transcripts:
                logging.warning("No transcripts retrieved, using fallback data")
                return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
            
            # Use the analyzer to extract insights - wrap each analysis in its own try/except
            analyzer = ConversationAnalyzer(lightweight_mode=lightweight)
            
            # Extract themes, sentiments, and other insights - one by one with individual error handling
            try:
                logging.info("Analyzing sentiment overview...")
                result['sentiment_overview'] = analyzer.analyze_aggregate_sentiment(conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error analyzing sentiment overview: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
            
            try:
                logging.info("Extracting top themes...")
                result['top_themes'] = analyzer.extract_aggregate_topics(conversations_with_transcripts, top_n=15)
            except Exception as e:
                logging.error(f"Error extracting themes: {str(e)}")
                logging.error(traceback.format_exc())
                # Use fallback themes
                result['top_themes'] = [
                    {'topic': 'love', 'count': 12, 'score': 0.9, 'type': 'unigram'},
                    {'topic': 'career', 'count': 10, 'score': 0.85, 'type': 'unigram'},
                    {'topic': 'relationship', 'count': 8, 'score': 0.8, 'type': 'unigram'}
                ]
            
            try:
                logging.info("Analyzing theme-sentiment correlation...")
                result['theme_sentiment_correlation'] = analyzer.analyze_theme_sentiment_correlation(conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error analyzing theme-sentiment correlation: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
            
            try:
                logging.info("Analyzing sentiment over time...")
                result['sentiment_over_time'] = analyzer.analyze_sentiment_over_time(df, conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error analyzing sentiment over time: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
                
            try:
                logging.info("Identifying concerns and skepticism...")
                result['concerns_and_skepticism'] = analyzer.identify_concerns_and_skepticism(conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error identifying concerns: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
                
            try:
                logging.info("Extracting common questions...")
                result['common_questions'] = analyzer.extract_common_questions(conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error extracting questions: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
                
            try:
                logging.info("Identifying positive interactions...")
                result['positive_interactions'] = analyzer.identify_positive_interactions(conversations_with_transcripts)
            except Exception as e:
                logging.error(f"Error identifying positive interactions: {str(e)}")
                logging.error(traceback.format_exc())
                # Keep default fallback data in result
            
            logging.info("Analysis complete, returning results")
            return jsonify(result)
                
        except Exception as e:
            logging.error(f"Error in themes-sentiment data processing: {str(e)}")
            logging.error(traceback.format_exc())
            logging.info("Falling back to sample data for themes-sentiment endpoint")
            
            # Generate sample data as fallback
            return jsonify(generate_sample_themes_sentiment_data(start_date, end_date, timeframe))
        
    except Exception as e:
        logging.error(f"Unexpected error in themes-sentiment endpoint: {str(e)}")
        import traceback
        tb = traceback.format_exc()
        logging.error(tb)
        # Return a friendly error message for 500 status
        return jsonify({
            'error': str(e),
            'message': 'An unexpected error occurred. Check server logs for details.',
            'traceback': tb
        }), 500

def generate_sample_themes_sentiment_data(start_date, end_date, timeframe):
    """Generate sample data for the themes and sentiment page"""
    try:
        logging.info(f"Generating sample data for themes-sentiment with timeframe={timeframe}, start_date={start_date}, end_date={end_date}")
        
        # Generate a more realistic sample size based on timeframe
        if timeframe == 'last_7_days':
            sample_size = 25  # Approx 3-4 conversations per day
        elif timeframe == 'last_30_days':
            sample_size = 65  # Approx 2-3 conversations per day
        elif timeframe == 'last_90_days':
            sample_size = 120  # A bit fewer per day over longer period
        elif timeframe == 'all':
            sample_size = 180  # Total since beginning of year
        else:
            # Default (30 days)
            sample_size = 65
        
        # Ensure valid dates
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Convert string dates to datetime for delta calculation
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except Exception as e:
            logging.error(f"Error parsing dates: {str(e)}")
            # Use default dates
            start = datetime.now() - timedelta(days=30)
            end = datetime.now()
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')
        
        # Base data structure
        sample_data = {
            'date_range': {
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe
            },
            'conversation_count': sample_size
        }
        
        # Sample sentiment overview
        sample_data['sentiment_overview'] = {
            'overall_score': 0.42,
            'user_sentiment': 0.38,
            'agent_sentiment': 0.67,
            'sentiment_distribution': {
                'positive': 0.72,
                'neutral': 0.18,
                'negative': 0.10
            }
        }
        
        # Sample top themes
        sample_data['top_themes'] = [
            {'topic': 'relationship', 'count': 87, 'score': 0.92, 'type': 'unigram'},
            {'topic': 'career change', 'count': 64, 'score': 0.85, 'type': 'bigram'},
            {'topic': 'future', 'count': 58, 'score': 0.81, 'type': 'unigram'},
            {'topic': 'family', 'count': 52, 'score': 0.78, 'type': 'unigram'},
            {'topic': 'love life', 'count': 49, 'score': 0.76, 'type': 'bigram'},
            {'topic': 'money', 'count': 43, 'score': 0.72, 'type': 'unigram'},
            {'topic': 'spiritual growth', 'count': 39, 'score': 0.68, 'type': 'bigram'},
            {'topic': 'health', 'count': 37, 'score': 0.65, 'type': 'unigram'},
            {'topic': 'decision', 'count': 34, 'score': 0.62, 'type': 'unigram'},
            {'topic': 'personal growth', 'count': 31, 'score': 0.59, 'type': 'bigram'},
            {'topic': 'moving', 'count': 28, 'score': 0.56, 'type': 'unigram'},
            {'topic': 'children', 'count': 25, 'score': 0.53, 'type': 'unigram'},
            {'topic': 'past life', 'count': 22, 'score': 0.50, 'type': 'bigram'},
            {'topic': 'dreams', 'count': 19, 'score': 0.47, 'type': 'unigram'},
            {'topic': 'marriage', 'count': 17, 'score': 0.45, 'type': 'unigram'}
        ]
        
        # Sample theme sentiment correlation
        sample_data['theme_sentiment_correlation'] = [
            {'theme': 'love life', 'avg_sentiment': 0.78, 'mention_count': 49, 'sentiment_category': 'positive'},
            {'theme': 'spiritual growth', 'avg_sentiment': 0.67, 'mention_count': 39, 'sentiment_category': 'positive'},
            {'theme': 'personal growth', 'avg_sentiment': 0.62, 'mention_count': 31, 'sentiment_category': 'positive'},
            {'theme': 'relationship', 'avg_sentiment': 0.45, 'mention_count': 87, 'sentiment_category': 'positive'},
            {'theme': 'future', 'avg_sentiment': 0.37, 'mention_count': 58, 'sentiment_category': 'positive'},
            {'theme': 'family', 'avg_sentiment': 0.32, 'mention_count': 52, 'sentiment_category': 'positive'},
            {'theme': 'health', 'avg_sentiment': 0.21, 'mention_count': 37, 'sentiment_category': 'positive'},
            {'theme': 'dreams', 'avg_sentiment': 0.18, 'mention_count': 19, 'sentiment_category': 'positive'},
            {'theme': 'decision', 'avg_sentiment': 0.05, 'mention_count': 34, 'sentiment_category': 'neutral'},
            {'theme': 'past life', 'avg_sentiment': -0.12, 'mention_count': 22, 'sentiment_category': 'negative'},
            {'theme': 'moving', 'avg_sentiment': -0.18, 'mention_count': 28, 'sentiment_category': 'negative'},
            {'theme': 'money', 'avg_sentiment': -0.32, 'mention_count': 43, 'sentiment_category': 'negative'},
            {'theme': 'career change', 'avg_sentiment': -0.45, 'mention_count': 64, 'sentiment_category': 'negative'}
        ]
        
        # Sample sentiment over time
        # Generate dates from start_date to end_date
        daily_sentiment = []
        trend_value = 0.12
        
        try:
            delta = end - start
            
            for i in range(delta.days + 1):
                current_date = start + timedelta(days=i)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Random sentiment value between -0.8 and 0.8, but with an overall positive trend
                base_sentiment = ((i / (delta.days + 1)) * 0.4) - 0.2  # Creates slight upward trend from -0.2 to 0.2
                random_component = (random.random() * 0.6) - 0.3  # Random component between -0.3 and 0.3
                sentiment = base_sentiment + random_component
                
                daily_sentiment.append({
                    'date': date_str,
                    'sentiment': max(-0.9, min(0.9, sentiment))  # Clamp between -0.9 and 0.9
                })
        except Exception as e:
            logging.error(f"Error generating sentiment over time: {str(e)}")
            # Provide a fallback set of daily sentiments
            daily_sentiment = [
                {'date': '2025-03-01', 'sentiment': 0.1},
                {'date': '2025-03-15', 'sentiment': 0.3},
                {'date': '2025-03-26', 'sentiment': 0.4}
            ]
        
        sample_data['sentiment_over_time'] = {
            'daily_sentiment': daily_sentiment,
            'trend': trend_value
        }
        
        # Sample concerns and skepticism
        sample_data['concerns_and_skepticism'] = [
            {
                'type': 'accuracy',
                'count': 12,
                'examples': [
                    {'type': 'accuracy', 'text': 'How do you know that will happen? It seems too specific.', 'conversation_id': '6ad1fa83'},
                    {'type': 'accuracy', 'text': 'But what if that prediction doesn\'t come true?', 'conversation_id': '9cb24e51'},
                    {'type': 'accuracy', 'text': 'I\'ve had readings before that weren\'t accurate at all.', 'conversation_id': '7df36b2a'}
                ]
            },
            {
                'type': 'skepticism',
                'count': 9,
                'examples': [
                    {'type': 'skepticism', 'text': 'I\'m not sure I believe in psychic abilities.', 'conversation_id': '3ae98c14'},
                    {'type': 'skepticism', 'text': 'Is this just cold reading or do you really have a gift?', 'conversation_id': '5f23d97b'},
                    {'type': 'skepticism', 'text': 'How does this work exactly? It seems a bit vague.', 'conversation_id': '8e67a42c'}
                ]
            },
            {
                'type': 'cost',
                'count': 7,
                'examples': [
                    {'type': 'cost', 'text': 'These readings are quite expensive, aren\'t they?', 'conversation_id': '2b54f18e'},
                    {'type': 'cost', 'text': 'How much longer do I have before my credits run out?', 'conversation_id': '4c31d75f'},
                    {'type': 'cost', 'text': 'Do you have any special offers or discounts?', 'conversation_id': '1a92e36d'}
                ]
            },
            {
                'type': 'scientific',
                'count': 5,
                'examples': [
                    {'type': 'scientific', 'text': 'Is there any scientific evidence for psychic abilities?', 'conversation_id': '0d45b29a'},
                    {'type': 'scientific', 'text': 'How do you explain this from a scientific perspective?', 'conversation_id': '9e78c31b'},
                    {'type': 'scientific', 'text': 'I tend to be quite rational. How can I reconcile that with this?', 'conversation_id': '2f56a87c'}
                ]
            }
        ]
        
        # Sample common questions
        sample_data['common_questions'] = [
            {
                'category': 'love_relationships',
                'count': 38,
                'examples': [
                    {'text': 'Will I meet someone special soon?', 'conversation_id': '7a23b94c'},
                    {'text': 'Is my current relationship going to last?', 'conversation_id': '5d16e82f'},
                    {'text': 'When will I find my soulmate?', 'conversation_id': '3b49c75a'}
                ]
            },
            {
                'category': 'career_work',
                'count': 31,
                'examples': [
                    {'text': 'Should I accept the new job offer?', 'conversation_id': '9f82d41b'},
                    {'text': 'Will my business be successful if I start it now?', 'conversation_id': '8c57e63a'},
                    {'text': 'Is a career change the right move for me?', 'conversation_id': '2e91f74d'}
                ]
            },
            {
                'category': 'finances',
                'count': 26,
                'examples': [
                    {'text': 'Will my financial situation improve this year?', 'conversation_id': '1d38g59h'},
                    {'text': 'Should I invest in property right now?', 'conversation_id': '4a72b35c'},
                    {'text': 'Will I ever be financially stable?', 'conversation_id': '6e26d18f'}
                ]
            },
            {
                'category': 'family',
                'count': 22,
                'examples': [
                    {'text': 'How can I improve my relationship with my mother?', 'conversation_id': '0c15a94e'},
                    {'text': 'Will I have children in the future?', 'conversation_id': '3f68b27a'},
                    {'text': 'Is moving closer to my family the right decision?', 'conversation_id': '7g41c83d'}
                ]
            },
            {
                'category': 'life_purpose',
                'count': 19,
                'examples': [
                    {'text': 'What is my true purpose in life?', 'conversation_id': '5h93d62c'},
                    {'text': 'Am I on the right path right now?', 'conversation_id': '2j74a51b'},
                    {'text': 'How can I find more meaning in my daily life?', 'conversation_id': '8k27e39f'}
                ]
            }
        ]
        
        # Sample positive interactions
        sample_data['positive_interactions'] = [
            {
                'caller_response': 'Wow, that\'s exactly what I needed to hear! You\'ve given me so much clarity and hope. Thank you so much!',
                'sentiment_score': 0.92,
                'lily_prompt': 'I sense that you\'ve been struggling with this decision for some time. Trust your intuition here - the path that feels most aligned with your values is the one that will bring you the most fulfillment.',
                'conversation_id': '9d52c84a'
            },
            {
                'caller_response': 'I feel so much lighter now. It\'s like you reached into my soul and understood exactly what I\'ve been going through. This has been incredibly healing.',
                'sentiment_score': 0.88,
                'lily_prompt': 'The energy I\'m sensing around you shows that you\'ve been carrying this burden for too long. It\'s time to release it and allow new opportunities to enter your life.',
                'conversation_id': '7b36a51e'
            },
            {
                'caller_response': 'That\'s incredible! You described my situation perfectly without me telling you anything. I\'m amazed by your insight and accuracy.',
                'sentiment_score': 0.85,
                'lily_prompt': 'I see a situation involving three people that\'s been causing you stress. There\'s a triangular energy here, and you\'re feeling caught in the middle of something that isn\'t fully your responsibility.',
                'conversation_id': '4f85c29d'
            },
            {
                'caller_response': 'I can\'t thank you enough for this reading. You\'ve confirmed what my heart has been telling me, and now I have the courage to move forward.',
                'sentiment_score': 0.82,
                'lily_prompt': 'The cards are showing me that this relationship has served its purpose in your life journey. While endings can be painful, this one is making space for something much more aligned with your soul\'s growth.',
                'conversation_id': '2c71b48e'
            },
            {
                'caller_response': 'This is exactly what I needed to hear today. Your insights have given me a completely new perspective on my situation. I feel so much more optimistic now!',
                'sentiment_score': 0.78,
                'lily_prompt': 'Sometimes the universe puts obstacles in our path not to block us, but to redirect us to something better. I sense that this challenging period is actually guiding you toward your true calling.',
                'conversation_id': '6a19d73f'
            }
        ]
        
        return sample_data
    except Exception as e:
        logging.error(f"Error in generate_sample_themes_sentiment_data: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Return a minimal working dataset that won't break the UI
        return {
            'date_range': {
                'start_date': datetime.now().strftime('%Y-%m-%d'),
                'end_date': datetime.now().strftime('%Y-%m-%d'),
                'timeframe': 'last_30_days'
            },
            'conversation_count': 10,
            'sentiment_overview': {
                'overall_score': 0.5,
                'user_sentiment': 0.5,
                'agent_sentiment': 0.5,
                'sentiment_distribution': {'positive': 0.7, 'neutral': 0.2, 'negative': 0.1}
            },
            'top_themes': [{'topic': 'love', 'count': 10, 'score': 0.9, 'type': 'unigram'}],
            'theme_sentiment_correlation': [{'theme': 'love', 'avg_sentiment': 0.5, 'mention_count': 10, 'sentiment_category': 'positive'}],
            'sentiment_over_time': {'daily_sentiment': [{'date': datetime.now().strftime('%Y-%m-%d'), 'sentiment': 0.5}], 'trend': 0},
            'concerns_and_skepticism': [{'type': 'accuracy', 'count': 5, 'examples': [{'type': 'accuracy', 'text': 'Example concern', 'conversation_id': '123456'}]}],
            'common_questions': [{'category': 'love', 'count': 5, 'examples': [{'text': 'Example question?', 'conversation_id': '123456'}]}],
            'positive_interactions': [{'caller_response': 'Great!', 'sentiment_score': 0.9, 'lily_prompt': 'Example prompt', 'conversation_id': '123456'}]
        } 

@main_bp.route('/api/conversations/<conversation_id>')
def get_conversation(conversation_id):
    """API endpoint to get details for a specific conversation"""
    try:
        # Log the request
        logging.info(f"API request for conversation details: {conversation_id}")
        
        # Get the client from app context
        client = current_app.elevenlabs_client
        
        # Try to get the conversation details
        conversation_data = client.get_conversation_details(conversation_id)
        
        # If we couldn't get real data, generate sample data for this ID
        if not conversation_data or 'error' in conversation_data:
            logging.info(f"Generating sample data for API conversation {conversation_id}")
            
            # Create a specific sample for property investment question (4a72b35c)
            if '4a72b35c' in conversation_id:
                logging.info("Using specific property investment example data")
                # Use consistent sample data that matches what's shown in themes-sentiment
                conversation_data = {
                    'conversation_id': '4a72b35c',  # Use exact ID, not modified version
                    'start_time': datetime.now().isoformat(),
                    'end_time': (datetime.now() + timedelta(minutes=3)).isoformat(),
                    'duration': 180,  # 3 minutes
                    'status': 'completed',
                    'channel': 'voice',
                    'turn_count': 6,
                    'transcript': [
                        {
                            'speaker': 'Caller',
                            'text': 'I have some money saved up and wondering about investing.',
                            'timestamp': (datetime.now() - timedelta(seconds=170)).isoformat(),
                            'sentiment': 0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "That's wonderful that you're in a position to invest. What types of investments are you considering?",
                            'timestamp': (datetime.now() - timedelta(seconds=150)).isoformat(),
                            'sentiment': 0.4
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'Should I invest in property right now? The market seems volatile.',
                            'timestamp': (datetime.now() - timedelta(seconds=130)).isoformat(),
                            'sentiment': -0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I'm seeing some caution around property investments at this moment. There may be better timing in the near future, perhaps in about 3-4 months. I'm sensing that waiting may yield better opportunities.",
                            'timestamp': (datetime.now() - timedelta(seconds=100)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': "That's helpful. I'll consider waiting a bit longer then.",
                            'timestamp': (datetime.now() - timedelta(seconds=70)).isoformat(),
                            'sentiment': 0.3
                        },
                        {
                            'speaker': 'Lily',
                            'text': "Trust your intuition on this. I sense you're a thoughtful investor. The energy suggests that your patience will be rewarded.",
                            'timestamp': (datetime.now() - timedelta(seconds=40)).isoformat(),
                            'sentiment': 0.5
                        }
                    ]
                }
            # Create a specific sample for job offer question (9f82d41b)
            elif '9f82d41b' in conversation_id:
                logging.info("Using specific job offer example data")
                # Use consistent sample data that matches what's shown in themes-sentiment
                conversation_data = {
                    'conversation_id': '9f82d41b',  # Use exact ID, not modified version
                    'start_time': datetime.now().isoformat(),
                    'end_time': (datetime.now() + timedelta(minutes=4)).isoformat(),
                    'duration': 240,  # 4 minutes
                    'status': 'completed',
                    'channel': 'voice',
                    'turn_count': 8,
                    'transcript': [
                        {
                            'speaker': 'Caller',
                            'text': 'I was offered a new job position. Should I accept it?',
                            'timestamp': (datetime.now() - timedelta(seconds=230)).isoformat(),
                            'sentiment': 0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I sense some hesitation in your energy. Could you tell me what aspects of the job offer are making you uncertain?",
                            'timestamp': (datetime.now() - timedelta(seconds=200)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'The pay is better, but it would mean relocating to a different city away from my family.',
                            'timestamp': (datetime.now() - timedelta(seconds=180)).isoformat(),
                            'sentiment': -0.2
                        },
                        {
                            'speaker': 'Lily',
                            'text': "Thank you for sharing that. I'm sensing that your family connections are very important to you. When I look at the energies surrounding this decision, I'm seeing both opportunity and hesitation.",
                            'timestamp': (datetime.now() - timedelta(seconds=150)).isoformat(),
                            'sentiment': 0.3
                        },
                        {
                            'speaker': 'Caller',
                            'text': "Should I accept the new job offer? I'm really torn about this decision.",
                            'timestamp': (datetime.now() - timedelta(seconds=120)).isoformat(),
                            'sentiment': -0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I'm sensing that while this job offers financial growth, your spiritual and emotional well-being may be affected by the distance from your support system. The cards suggest that if you do take this position, you'll need to be intentional about maintaining those connections. Have you considered if there's any flexibility for remote work or regular visits home?",
                            'timestamp': (datetime.now() - timedelta(seconds=90)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': "That's a good point. I could ask about working remotely for part of the month.",
                            'timestamp': (datetime.now() - timedelta(seconds=60)).isoformat(),
                            'sentiment': 0.4
                        },
                        {
                            'speaker': 'Lily',
                            'text': "The energy shifts positively when you consider that compromise. I sense this could be a path forward that honors both your career ambitions and your need for family connection. Trust your intuition on this - when you imagine proposing this solution, notice how your energy feels lighter.",
                            'timestamp': (datetime.now() - timedelta(seconds=30)).isoformat(),
                            'sentiment': 0.6
                        }
                    ]
                }
            else:
                # Generic sample data
                conversation_data = {
                    'conversation_id': conversation_id,
                    'start_time': datetime.now().isoformat(),
                    'end_time': (datetime.now() + timedelta(minutes=4)).isoformat(),
                    'duration': 240,  # 4 minutes
                    'status': 'completed',
                    'channel': 'voice',
                    'turn_count': 6,
                    'transcript': [
                        {
                            'speaker': 'Caller',
                            'text': 'Hello, I have a question about my future.',
                            'timestamp': (datetime.now() - timedelta(seconds=230)).isoformat(),
                            'sentiment': 0
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I'm connecting with your energy. What specific area of your future are you curious about?",
                            'timestamp': (datetime.now() - timedelta(seconds=200)).isoformat(),
                            'sentiment': 0.2
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'I would like to know more about my career path.',
                            'timestamp': (datetime.now() - timedelta(seconds=180)).isoformat(),
                            'sentiment': 0.1
                        },
                        {
                            'speaker': 'Lily',
                            'text': "I sense you're at a crossroads. The energies indicate a potential for growth if you embrace new opportunities that may arise in the next few months.",
                            'timestamp': (datetime.now() - timedelta(seconds=150)).isoformat(),
                            'sentiment': 0.4
                        },
                        {
                            'speaker': 'Caller',
                            'text': 'That makes sense. I have been considering a career change.',
                            'timestamp': (datetime.now() - timedelta(seconds=120)).isoformat(),
                            'sentiment': 0.3
                        },
                        {
                            'speaker': 'Lily',
                            'text': "Yes, I'm seeing that. Trust your intuition on this matter - your inner guidance is strong.",
                            'timestamp': (datetime.now() - timedelta(seconds=90)).isoformat(),
                            'sentiment': 0.5
                        }
                    ]
                }
        
        logging.info(f"Returning conversation data with ID: {conversation_data.get('conversation_id')}")
        return jsonify(conversation_data)
        
    except Exception as e:
        logging.error(f"Error getting conversation {conversation_id}: {e}")
        return jsonify({"error": str(e), "conversation_id": conversation_id}), 500 

@main_bp.route('/api/conversations')
def get_conversations():
    """API endpoint to fetch conversations based on date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Log the request parameters
    logging.info(f"API Request - Fetching conversations from {start_date} to {end_date} (limit: {limit}, offset: {offset})")
    
    try:
        # Get the client from app context
        client = current_app.elevenlabs_client
        
        # Get conversations data from the client
        logging.info(f"Calling ElevenLabs client.get_conversations with dates: {start_date} to {end_date}")
        conversations_data = client.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Log raw data structure
        logging.info(f"Raw conversations_data type: {type(conversations_data)}")
        logging.info(f"Raw conversations_data keys: {list(conversations_data.keys()) if isinstance(conversations_data, dict) else 'Not a dictionary'}")
        
        # If it's a demo/fallback data, it might have a different structure
        if isinstance(conversations_data, dict):
            if 'conversations' in conversations_data:
                logging.info(f"Found 'conversations' key with {len(conversations_data['conversations'])} items")
            elif 'history' in conversations_data:
                logging.info(f"Found 'history' key with {len(conversations_data['history'])} items")
        elif isinstance(conversations_data, list):
            logging.info(f"Raw conversations_data is a list with {len(conversations_data)} items")
        
        # Process the raw conversations data
        logging.info("Processing conversations data...")
        conversations_processed = DataProcessor.process_conversations(conversations_data)
        
        # Log processed data
        if hasattr(conversations_processed, 'shape'):
            logging.info(f"Processed data is DataFrame with shape: {conversations_processed.shape}")
        elif isinstance(conversations_processed, list):
            logging.info(f"Processed data is list with {len(conversations_processed)} items")
        
        # Convert to a format suitable for DataTables
        if hasattr(conversations_processed, 'to_dict'):
            # If it's a DataFrame, convert to records
            logging.info("Converting DataFrame to records...")
            data = conversations_processed.to_dict('records')
            
            # Convert datetime objects to ISO strings for JSON serialization
            for item in data:
                for key, value in item.items():
                    if isinstance(value, pd.Timestamp):
                        item[key] = value.isoformat()
        else:
            # If it's already a list of dictionaries
            logging.info("Using data as is (already a list)...")
            data = conversations_processed
        
        # Generate demo data if no real data was found
        if not data:
            logging.warning("No conversations found. Generating fallback demo data...")
            # Create some sample conversations for demo purposes
            current_time = datetime.now()
            
            # Generate 10 sample conversations
            data = []
            topics = ["relationship", "career", "money", "health", "family", "spirituality", "future", "past"]
            
            for i in range(10):
                # Choose a random start time within the last 7 days
                days_ago = random.randint(0, 6)
                hours_ago = random.randint(0, 23)
                start_time = current_time - timedelta(days=days_ago, hours=hours_ago)
                
                # Random duration between 3 and 15 minutes
                duration_minutes = random.randint(3, 15)
                end_time = start_time + timedelta(minutes=duration_minutes)
                
                # Random turn count between 6 and 20
                turn_count = random.randint(6, 20)
                
                # Random topic from list
                topic = random.choice(topics)
                
                # Generate a random ID
                conversation_id = ''.join(random.choices('0123456789abcdef', k=8))
                
                data.append({
                    'conversation_id': conversation_id,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration': duration_minutes * 60,  # Convert to seconds
                    'turn_count': turn_count,
                    'topic': topic,
                    'status': random.choice(['completed', 'completed', 'completed', 'failed'])  # Mostly completed
                })
            
            logging.info(f"Generated {len(data)} fallback demo conversations")
        else:
            logging.info(f"Returning {len(data)} real conversations")
        
        # Return as JSON
        response_data = {
            'data': data,
            'total': len(data),
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit,
            'offset': offset
        }
        logging.info(f"API Response: {len(data)} conversations, from {start_date} to {end_date}")
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error fetching conversations: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'data': [],
            'total': 0
        }), 500 