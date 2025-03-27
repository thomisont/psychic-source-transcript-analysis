"""
Export service for handling data export operations.
"""
import logging
import io
from typing import Dict, List, Optional, Any, Union
from app.utils.export import DataExporter
from datetime import datetime

class ExportService:
    """Service for handling data export operations."""
    
    def __init__(self):
        """Initialize the export service."""
        self.exporter = DataExporter()
    
    def export_data(self, data: Any, format: str) -> tuple:
        """
        Export data in the specified format.
        
        Args:
            data: Data to export
            format: Export format ('json', 'csv', 'md')
            
        Returns:
            Tuple of (file_content, mimetype)
        """
        if not data:
            logging.warning("No data provided for export")
            return None, None
            
        logging.info(f"Exporting data in {format} format")
        
        # Export in the requested format
        if format == 'json':
            output = DataExporter.to_json(data)
            mimetype = 'application/json'
        elif format == 'csv':
            output = DataExporter.to_csv(data)
            mimetype = 'text/csv'
        elif format == 'md':
            output = DataExporter.to_markdown(data)
            mimetype = 'text/markdown'
        else:
            logging.error(f"Unsupported export format: {format}")
            return None, None
            
        # Create in-memory file
        buffer = io.BytesIO(output.encode('utf-8'))
        buffer.seek(0)
        
        return buffer, mimetype
    
    def generate_filename(self, data_type: str, identifier: Optional[str] = None) -> str:
        """
        Generate a filename for exported data.
        
        Args:
            data_type: Type of data being exported ('conversation', 'conversations')
            identifier: Optional identifier (conversation_id, date range, etc.)
            
        Returns:
            Generated filename without extension
        """
        if data_type == 'conversation' and identifier:
            return f"conversation_{identifier}"
        elif data_type == 'conversations' and identifier:
            return f"conversations_{identifier}"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"{data_type}_{timestamp}" 