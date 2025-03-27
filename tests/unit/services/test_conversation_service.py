"""
Unit tests for the ConversationService.
"""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

from app.services.conversation_service import ConversationService

class TestConversationService(unittest.TestCase):
    """Test cases for the ConversationService."""
    
    def setUp(self):
        """Set up test fixtures before each test method is run."""
        self.mock_api_client = Mock()
        self.service = ConversationService(self.mock_api_client)
    
    def test_get_conversations_calls_api_client(self):
        """Test that get_conversations calls the API client with correct parameters."""
        # Arrange
        self.mock_api_client.get_conversations.return_value = {'conversations': []}
        
        # Act
        self.service.get_conversations(start_date='2025-01-01', end_date='2025-01-31', limit=50, offset=10)
        
        # Assert
        self.mock_api_client.get_conversations.assert_called_once_with(
            start_date='2025-01-01', 
            end_date='2025-01-31', 
            limit=50, 
            offset=10
        )
    
    def test_get_conversations_processes_data(self):
        """Test that get_conversations processes the data from the API client."""
        # Arrange
        mock_conversation = {
            'conversation_id': 'test123',
            'start_time': '2025-01-15T10:00:00',
            'end_time': '2025-01-15T10:15:00',
            'duration': 900,
            'turn_count': 10,
            'status': 'done'
        }
        self.mock_api_client.get_conversations.return_value = {
            'conversations': [mock_conversation]
        }
        
        # Act
        result = self.service.get_conversations()
        
        # Assert
        self.assertIn('conversations', result)
        self.assertIn('total_count', result)
        self.assertEqual(result['total_count'], 1)
    
    def test_get_conversation_details_calls_api_client(self):
        """Test that get_conversation_details calls the API client with correct parameters."""
        # Arrange
        self.mock_api_client.get_conversation_details.return_value = {}
        
        # Act
        self.service.get_conversation_details('test123')
        
        # Assert
        self.mock_api_client.get_conversation_details.assert_called_once_with('test123')
    
    def test_get_conversation_details_handles_empty_id(self):
        """Test that get_conversation_details handles empty conversation ID."""
        # Act
        result = self.service.get_conversation_details('')
        
        # Assert
        self.assertEqual(result, {})
        self.mock_api_client.get_conversation_details.assert_not_called()
    
    def test_get_conversation_details_processes_data(self):
        """Test that get_conversation_details processes the data from the API client."""
        # Arrange
        mock_details = {
            'conversation_id': 'test123',
            'transcript': [
                {'speaker': 'Caller', 'text': 'Hello'},
                {'speaker': 'Agent', 'text': 'Hi there'}
            ]
        }
        self.mock_api_client.get_conversation_details.return_value = mock_details
        
        # Act
        result = self.service.get_conversation_details('test123')
        
        # Assert
        self.assertEqual(result, mock_details)

if __name__ == '__main__':
    unittest.main() 