"""
Unit tests for the AnalysisService.
"""
import unittest
from unittest.mock import Mock, patch
from app.services.analysis_service import AnalysisService

class TestAnalysisService(unittest.TestCase):
    """Test cases for the AnalysisService."""
    
    def setUp(self):
        """Set up test fixtures before each test method is run."""
        self.service = AnalysisService()
        # Mock the ConversationAnalyzer
        self.service.analyzer = Mock()
    
    def test_analyze_conversation_calls_analyzer_methods(self):
        """Test that analyze_conversation calls the analyzer methods with correct parameters."""
        # Arrange
        conversation_data = {
            'conversation_id': 'test123',
            'transcript': [
                {'speaker': 'Caller', 'text': 'Hello'},
                {'speaker': 'Agent', 'text': 'Hi there'}
            ]
        }
        self.service.analyzer.analyze_sentiment.return_value = {'overall': 0.5}
        self.service.analyzer.extract_topics.return_value = ['greeting']
        self.service.analyzer.analyze_conversation_flow.return_value = {'turns': 2}
        
        # Act
        result = self.service.analyze_conversation(conversation_data)
        
        # Assert
        self.service.analyzer.analyze_sentiment.assert_called_once_with(conversation_data['transcript'])
        self.service.analyzer.extract_topics.assert_called_once_with(conversation_data['transcript'])
        self.service.analyzer.analyze_conversation_flow.assert_called_once_with(conversation_data['transcript'])
        self.assertEqual(result['conversation_id'], 'test123')
        self.assertEqual(result['sentiment'], {'overall': 0.5})
        self.assertEqual(result['topics'], ['greeting'])
        self.assertEqual(result['flow'], {'turns': 2})
    
    def test_analyze_conversation_handles_empty_data(self):
        """Test that analyze_conversation handles empty conversation data."""
        # Act
        result = self.service.analyze_conversation({})
        
        # Assert
        self.assertEqual(result, {})
        self.service.analyzer.analyze_sentiment.assert_not_called()
    
    def test_analyze_conversations_over_time_calls_analyzer_methods(self):
        """Test that analyze_conversations_over_time calls the analyzer methods with correct parameters."""
        # Arrange
        conversations = [
            {
                'conversation_id': 'test123',
                'start_time': '2025-01-01T10:00:00',
                'transcript': [{'speaker': 'Caller', 'text': 'Hello'}]
            },
            {
                'conversation_id': 'test456',
                'start_time': '2025-01-02T10:00:00',
                'transcript': [{'speaker': 'Caller', 'text': 'Hi'}]
            }
        ]
        self.service.analyzer.aggregate_sentiment_by_timeframe.return_value = {'2025-01-01': 0.5}
        self.service.analyzer.aggregate_topics_by_timeframe.return_value = {'2025-01-01': ['greeting']}
        
        # Act
        result = self.service.analyze_conversations_over_time(conversations, timeframe='day')
        
        # Assert
        self.service.analyzer.aggregate_sentiment_by_timeframe.assert_called_once_with(conversations, 'day')
        self.service.analyzer.aggregate_topics_by_timeframe.assert_called_once_with(conversations, 'day')
        self.assertEqual(result['sentiment_over_time'], {'2025-01-01': 0.5})
        self.assertEqual(result['topics_over_time'], {'2025-01-01': ['greeting']})
        self.assertEqual(result['timeframe'], 'day')
        self.assertEqual(result['conversation_count'], 2)
    
    def test_analyze_conversations_over_time_handles_empty_list(self):
        """Test that analyze_conversations_over_time handles empty conversation list."""
        # Act
        result = self.service.analyze_conversations_over_time([])
        
        # Assert
        self.assertEqual(result, {})
        self.service.analyzer.aggregate_sentiment_by_timeframe.assert_not_called()

if __name__ == '__main__':
    unittest.main() 