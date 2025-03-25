from flask import Blueprint, jsonify, current_app, request
from app.api.data_processor import DataProcessor

# Create a Blueprint for the API
api = Blueprint('api', __name__)

# Move these routes from the main_bp to here
@api.route('/conversations')
def get_conversations():
    """API endpoint to get conversation data"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    try:
        # Log the requested date range
        print(f"DEBUG: API request for conversations from {start_date} to {end_date}")
        
        # Get the ElevenLabs client from the app
        client = current_app.elevenlabs_client
        
        # Get conversations from API
        conversations_data = client.get_conversations(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Process the data
        df = DataProcessor.process_conversations(conversations_data)
        
        # Additional filter to ensure dates match the requested range
        if start_date and end_date and not df.empty:
            # Convert string dates to datetime objects
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)  # End of day
            
            # Filter the DataFrame to only include records within the date range
            df = df[(df['start_time'] >= start_dt) & (df['start_time'] <= end_dt)]
            print(f"DEBUG: After date filtering, have {len(df)} conversations")
        
        # Convert to records
        records = []
        if not df.empty:
            # Serialize the DataFrame to JSON
            records = df.to_dict(orient='records')
            
            # Format dates for JSON
            for record in records:
                for key in ['start_time', 'end_time']:
                    if record.get(key) and hasattr(record[key], 'isoformat'):
                        record[key] = record[key].isoformat()
                        
        # Return as JSON
        return jsonify({
            'total': len(records),
            'data': records
        })
        
    except Exception as e:
        print(f"DEBUG: Error in get_conversations API: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@api.route('/conversations/<conversation_id>')
def get_conversation_details(conversation_id):
    """API endpoint to get details for a specific conversation"""
    try:
        # Get the ElevenLabs client from the app
        client = current_app.elevenlabs_client
        
        # Get conversation details
        conversation_data = client.get_conversation_details(conversation_id)
        
        # Process the data
        processed_data = DataProcessor.process_conversation_details(conversation_data)
        
        # Format dates for JSON
        if processed_data.get('start_time') and hasattr(processed_data['start_time'], 'isoformat'):
            processed_data['start_time'] = processed_data['start_time'].isoformat()
            
        if processed_data.get('end_time') and hasattr(processed_data['end_time'], 'isoformat'):
            processed_data['end_time'] = processed_data['end_time'].isoformat()
            
        # Format timestamps in transcript
        for message in processed_data.get('transcript', []):
            if message.get('timestamp') and hasattr(message['timestamp'], 'isoformat'):
                message['timestamp'] = message['timestamp'].isoformat()
        
        return jsonify(processed_data)
        
    except Exception as e:
        print(f"DEBUG: Error in get_conversation_details API: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
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