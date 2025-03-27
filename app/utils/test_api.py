"""
Utility for testing the ElevenLabs API integration.
"""
import logging
import os
import json
from dotenv import load_dotenv
from app.api.elevenlabs_client import ElevenLabsClient

class APITester:
    """Utility class for testing API integration with ElevenLabs."""
    
    def __init__(self):
        """Initialize the API tester."""
        # Load environment variables
        load_dotenv()
        
        # Get API credentials
        self.api_key = os.getenv('ELEVENLABS_API_KEY', '')
        self.agent_id = os.getenv('ELEVENLABS_AGENT_ID', '')
        self.api_url = os.getenv('ELEVENLABS_API_URL', 'https://api.elevenlabs.io')
        
        # Initialize the client
        self.client = ElevenLabsClient(
            api_key=self.api_key,
            agent_id=self.agent_id,
            api_url=self.api_url
        )
    
    def test_connection(self):
        """Test basic API connectivity."""
        logging.info("Testing ElevenLabs API connection...")
        result = self.client.test_connection()
        
        if result:
            logging.info("✓ API connection successful")
        else:
            logging.error("✗ API connection failed")
            
        return result
    
    def test_get_conversations(self):
        """Test retrieving conversations."""
        logging.info("Testing get_conversations API...")
        conversations = self.client.get_conversations(limit=5)
        
        if isinstance(conversations, dict) and 'conversations' in conversations:
            count = len(conversations['conversations'])
            logging.info(f"✓ Retrieved {count} conversations")
            return True
        else:
            logging.error(f"✗ Failed to retrieve conversations. Got: {type(conversations)}")
            if isinstance(conversations, dict):
                logging.error(f"Keys: {list(conversations.keys())}")
            return False
    
    def test_get_conversation_details(self, conversation_id=None):
        """
        Test retrieving a specific conversation's details.
        
        Args:
            conversation_id: Optional ID to test with. If None, will try to get one from get_conversations.
        """
        # If no conversation_id provided, try to get one
        if not conversation_id:
            conversations = self.client.get_conversations(limit=1)
            if isinstance(conversations, dict) and 'conversations' in conversations and conversations['conversations']:
                first_conv = conversations['conversations'][0]
                conversation_id = first_conv.get('conversation_id', first_conv.get('id'))
                logging.info(f"Using conversation ID: {conversation_id}")
            else:
                logging.error("No conversations available to test get_conversation_details")
                return False
        
        logging.info(f"Testing get_conversation_details API for ID: {conversation_id}...")
        details = self.client.get_conversation_details(conversation_id)
        
        if details and isinstance(details, dict):
            logging.info(f"✓ Retrieved conversation details for {conversation_id}")
            # Check if transcript is available
            if 'transcript' in details and details['transcript']:
                logging.info(f"✓ Conversation has transcript with {len(details['transcript'])} turns")
            else:
                logging.warning("✗ No transcript available in conversation details")
            return True
        else:
            logging.error(f"✗ Failed to retrieve conversation details. Got: {type(details)}")
            return False
    
    def run_all_tests(self):
        """Run all API tests and return a summary."""
        results = {
            'connection': self.test_connection(),
            'get_conversations': self.test_get_conversations(),
            'get_conversation_details': self.test_get_conversation_details()
        }
        
        # Overall result
        success = all(results.values())
        
        summary = {
            'success': success,
            'results': results,
            'message': "All API tests passed!" if success else "Some API tests failed."
        }
        
        logging.info(f"API Test Summary: {summary['message']}")
        return summary


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    tester = APITester()
    results = tester.run_all_tests()
    
    # Print results in a readable format
    print("\n==== API TEST RESULTS ====")
    print(f"Overall: {'✓ SUCCESS' if results['success'] else '✗ FAILED'}")
    print("\nDetailed Results:")
    for test, result in results['results'].items():
        print(f"  {test}: {'✓ PASSED' if result else '✗ FAILED'}")
    print("\n==========================\n") 