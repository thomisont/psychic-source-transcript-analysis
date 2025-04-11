import json
import logging
import re

class ConversationAnalyzer:
    def extract_categories(self, conversations, prompt_template):
        """Extract categorized items like questions, concerns with examples from conversations."""
        try:
            if not conversations:
                return []
                
            # First, build a comprehensive prompt with all conversations
            all_examples = []
            for conv in conversations:
                transcript = conv.get('transcript', [])
                messages = []
                conv_id = conv.get('conversation_id') or conv.get('id')
                
                for msg in transcript:
                    if msg.get('role') == 'user':
                        messages.append(f"Caller: {msg.get('content')}")
                    elif msg.get('role') == 'assistant':
                        messages.append(f"Lily: {msg.get('content')}")
                
                if messages:
                    all_examples.append({
                        'transcript': '\n'.join(messages),
                        'conversation_id': conv_id
                    })
            
            if not all_examples:
                return []
                
            # Build the prompt
            examples_json = json.dumps(all_examples, indent=2)
            prompt = prompt_template.replace("{{conversations}}", examples_json)
            
            # Call the LLM for categorization
            try:
                result = self._call_openai_with_retry(prompt)
                categories = json.loads(result)
                
                # Ensure each example has conversation_id
                for category in categories:
                    examples = category.get('examples', [])
                    for i, example in enumerate(examples):
                        # If example is a simple string, convert to object with conversation_id
                        if isinstance(example, str):
                            # Try to find the conversation this example came from
                            matching_id = self._find_conversation_id_for_text(example, all_examples)
                            examples[i] = {
                                'text': example,
                                'conversation_id': matching_id
                            }
                        # If example is an object but missing conversation_id
                        elif isinstance(example, dict) and not example.get('conversation_id'):
                            matching_id = self._find_conversation_id_for_text(example.get('text', ''), all_examples)
                            example['conversation_id'] = matching_id
                            
                return categories
            except Exception as e:
                logging.error(f"Error calling OpenAI for category extraction: {e}")
                return []
                
        except Exception as e:
            logging.error(f"Error in extract_categories: {e}")
            return []
            
    def _find_conversation_id_for_text(self, text, examples):
        """Find the conversation ID where a text snippet appears."""
        if not text:
            return ""
            
        # Simplify text for comparison (lowercase, strip punctuation)
        simplified_text = re.sub(r'[^\w\s]', '', text.lower())
        
        for example in examples:
            if simplified_text in re.sub(r'[^\w\s]', '', example.get('transcript', '').lower()):
                return example.get('conversation_id', '')
                
        return ""

    def unified_theme_sentiment_analysis(self, conversations):
        """
        Perform comprehensive analysis on a set of conversations, extracting themes,
        correlations, questions, and concerns in a single operation.
        
        Args:
            conversations: List of conversation objects with transcripts
            
        Returns:
            Dictionary with sections: themes, correlations, common_questions, concerns_skepticism
        """
        if not conversations:
            return {
                'themes': [],
                'correlations': [],
                'common_questions': [],
                'concerns_skepticism': []
            }
            
        try:
            # Extract themes
            themes = self.extract_themes(conversations)
            
            # Extract theme correlations (relationships between different themes)
            correlations = self.extract_theme_correlations(conversations)
            
            # Extract common questions by category
            questions_prompt = """
            You are an expert at categorizing customer questions from psychic reading transcripts.
            Analyze these psychic reading conversation transcripts and identify the common questions callers ask.
            Group the questions into 5-8 meaningful categories (like "Love & Relationships", "Career & Finances", etc.).
            
            For each category:
            1. Pick a descriptive name
            2. List 3-5 representative example questions directly from the transcripts
            3. Indicate how many conversations include questions from this category
            
            Provide your analysis in this JSON format:
            [
              {
                "category": "Category Name",
                "examples": ["Example question 1", "Example question 2"],
                "count": 5
              }
            ]
            
            Here are the conversations to analyze:
            {{conversations}}
            """
            
            common_questions = self.extract_categories(conversations, questions_prompt)
            
            # Extract concerns and skepticism by category
            concerns_prompt = """
            You are an expert at categorizing caller concerns from psychic reading transcripts.
            Analyze these psychic reading conversation transcripts and identify common concerns, doubts, and skepticism expressed by callers.
            Group these concerns into 4-6 meaningful categories (like "General Concerns", "Skepticism about Process", etc.).
            
            For each category:
            1. Pick a descriptive name
            2. List 3-5 representative examples directly from the transcripts showing actual caller concerns
            3. Indicate how many conversations include concerns from this category
            
            Provide your analysis in this JSON format:
            [
              {
                "category": "Category Name",
                "examples": ["Example concern 1", "Example concern 2"],
                "count": 5
              }
            ]
            
            Here are the conversations to analyze:
            {{conversations}}
            """
            
            concerns_skepticism = self.extract_categories(conversations, concerns_prompt)
            
            # Extract positive interactions
            positive_interactions = self.extract_positive_interactions(conversations[:30])  # Limit to first 30 conversations
            
            return {
                'themes': themes,
                'correlations': correlations,
                'common_questions': common_questions,
                'concerns_skepticism': concerns_skepticism,
                'positive_interactions': positive_interactions
            }
            
        except Exception as e:
            logging.error(f"Error in unified_theme_sentiment_analysis: {e}")
            return {
                'themes': [],
                'correlations': [],
                'common_questions': [],
                'concerns_skepticism': []
            } 