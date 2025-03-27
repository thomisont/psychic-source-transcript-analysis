"""
Unit tests for the ExportService.
"""
import unittest
from unittest.mock import Mock, patch
from io import BytesIO
from app.services.export_service import ExportService
from app.utils.export import DataExporter

class TestExportService(unittest.TestCase):
    """Test cases for the ExportService."""
    
    def setUp(self):
        """Set up test fixtures before each test method is run."""
        self.service = ExportService()
    
    @patch('app.utils.export.DataExporter.to_json')
    def test_export_data_json_format(self, mock_to_json):
        """Test that export_data formats data correctly for JSON."""
        # Arrange
        data = {'key': 'value'}
        mock_to_json.return_value = '{"key": "value"}'
        
        # Act
        buffer, mimetype = self.service.export_data(data, 'json')
        
        # Assert
        mock_to_json.assert_called_once_with(data)
        self.assertEqual(mimetype, 'application/json')
        buffer.seek(0)
        self.assertEqual(buffer.read().decode('utf-8'), '{"key": "value"}')
    
    @patch('app.utils.export.DataExporter.to_csv')
    def test_export_data_csv_format(self, mock_to_csv):
        """Test that export_data formats data correctly for CSV."""
        # Arrange
        data = [{'key': 'value'}]
        mock_to_csv.return_value = 'key\nvalue'
        
        # Act
        buffer, mimetype = self.service.export_data(data, 'csv')
        
        # Assert
        mock_to_csv.assert_called_once_with(data)
        self.assertEqual(mimetype, 'text/csv')
        buffer.seek(0)
        self.assertEqual(buffer.read().decode('utf-8'), 'key\nvalue')
    
    @patch('app.utils.export.DataExporter.to_markdown')
    def test_export_data_markdown_format(self, mock_to_markdown):
        """Test that export_data formats data correctly for Markdown."""
        # Arrange
        data = [{'key': 'value'}]
        mock_to_markdown.return_value = '# Data\n\n- key: value'
        
        # Act
        buffer, mimetype = self.service.export_data(data, 'md')
        
        # Assert
        mock_to_markdown.assert_called_once_with(data)
        self.assertEqual(mimetype, 'text/markdown')
        buffer.seek(0)
        self.assertEqual(buffer.read().decode('utf-8'), '# Data\n\n- key: value')
    
    def test_export_data_unsupported_format(self):
        """Test that export_data handles unsupported formats."""
        # Act
        buffer, mimetype = self.service.export_data({'key': 'value'}, 'unsupported')
        
        # Assert
        self.assertIsNone(buffer)
        self.assertIsNone(mimetype)
    
    def test_export_data_empty_data(self):
        """Test that export_data handles empty data."""
        # Act
        buffer, mimetype = self.service.export_data(None, 'json')
        
        # Assert
        self.assertIsNone(buffer)
        self.assertIsNone(mimetype)
    
    def test_generate_filename_conversation(self):
        """Test generate_filename for a single conversation."""
        # Act
        filename = self.service.generate_filename('conversation', 'abc123')
        
        # Assert
        self.assertEqual(filename, 'conversation_abc123')
    
    def test_generate_filename_conversations(self):
        """Test generate_filename for multiple conversations."""
        # Act
        filename = self.service.generate_filename('conversations', '2025-01-01_to_2025-01-31')
        
        # Assert
        self.assertEqual(filename, 'conversations_2025-01-01_to_2025-01-31')
    
    def test_generate_filename_default(self):
        """Test generate_filename default behavior."""
        # Act
        filename = self.service.generate_filename('unknown')
        
        # Assert
        self.assertTrue(filename.startswith('unknown_'))
        self.assertTrue(len(filename) > 8)  # Should include timestamp

if __name__ == '__main__':
    unittest.main() 