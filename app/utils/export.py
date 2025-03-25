import json
import pandas as pd
import csv
from io import StringIO

class DataExporter:
    @staticmethod
    def to_json(data):
        """
        Export data to JSON format
        
        Args:
            data: Data to export (dict or DataFrame)
            
        Returns:
            str: JSON string
        """
        if isinstance(data, pd.DataFrame):
            return data.to_json(orient='records', date_format='iso')
        return json.dumps(data, default=str, indent=2)
        
    @staticmethod
    def to_csv(data):
        """
        Export data to CSV format
        
        Args:
            data: Data to export (dict or DataFrame)
            
        Returns:
            str: CSV string
        """
        if isinstance(data, pd.DataFrame):
            return data.to_csv(index=False)
            
        # Handle dict data
        output = StringIO()
        if isinstance(data, dict):
            writer = csv.DictWriter(output, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                
        return output.getvalue()
        
    @staticmethod
    def to_markdown(data):
        """
        Export data to Markdown format
        
        Args:
            data: Data to export (dict, DataFrame, or conversation details)
            
        Returns:
            str: Markdown string
        """
        if isinstance(data, pd.DataFrame):
            return data.to_markdown(index=False)
            
        # Handle conversation details with transcript
        if isinstance(data, dict) and 'transcript' in data:
            md_output = f"# Conversation {data.get('conversation_id')}\n\n"
            md_output += f"**Start Time:** {data.get('start_time')}\n"
            md_output += f"**End Time:** {data.get('end_time')}\n"
            md_output += f"**Duration:** {data.get('duration')} seconds\n"
            md_output += f"**Status:** {data.get('status')}\n\n"
            
            md_output += "## Transcript\n\n"
            for turn in data.get('transcript', []):
                speaker = turn.get('speaker')
                text = turn.get('text')
                timestamp = turn.get('timestamp')
                md_output += f"**{speaker}** ({timestamp}):\n{text}\n\n"
                
            return md_output
            
        # Default to JSON representation for other types
        return f"```json\n{DataExporter.to_json(data)}\n```" 