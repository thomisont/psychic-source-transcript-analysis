from flask import Blueprint, render_template, request, jsonify, send_file, current_app, redirect, flash
from datetime import datetime, timedelta
import io
import json
from app.api.data_processor import DataProcessor
from app.utils.export import DataExporter
from app.utils.analysis import ConversationAnalyzer
import logging

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
    
    return render_template('data_selection.html', 
                          start_date="",
                          end_date=end_date)

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