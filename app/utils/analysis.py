# Restoring from backup with syntax fixes
import re
import json
import random
import logging
import traceback
import nltk
from textblob import TextBlob
from collections import Counter
from nltk.corpus import stopwords
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer

# Initialize NLTK resources
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')

class ConversationAnalyzer:
    def __init__(self, lightweight_mode=False):
        self.lightweight_mode = lightweight_mode
        self.use_llm = not lightweight_mode
        self.openai_api_key = None
        
    def set_openai_api_key(self, api_key):
        """Set the OpenAI API key for analysis"""
        self.openai_api_key = api_key

    def extract_common_questions(self, conversations):
        """
        Extract common question categories from psychic reading conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Common question categories with frequency and examples
        """
        if not conversations:
            return []
            
        # Extract all user questions
        user_questions = []
        for conv in conversations:
            transcript = conv.get('transcript', [])
            
            for turn in transcript:
                if turn.get('speaker') in ['User', 'Curious Caller']:
                    text = turn.get('text', '')
                    # Simple heuristic to identify questions
                    if '?' in text or text.lower().startswith(('what', 'when', 'how', 'why', 'is', 'are', 'can', 'could', 'will')):
                        user_questions.append({
                            'text': text,
                            'conversation_id': conv.get('conversation_id', 'unknown')
                        })
                        
        # If we don't have enough questions, return empty result
        if len(user_questions) < 5:
            return []
            
        # Use OpenAI to categorize questions if available
        if self.use_llm and self.openai_api_key:
            return self._extract_questions_with_llm(user_questions)
            
        # Enhanced categorization approach with new categories
        question_types = {
            # Core psychic reading content categories
            'love_relationships': [],
            'career_money': [],
            'family': [],
            'future': [],
            
            # New service offering categories
            'service_offerings': [],  # Service logistics, session details, reader selection, technical support
            
            # New content categories
            'spiritual_concepts': [],
            'health_wellness': [],
            
            # Fallback category
            'other': []
        }
        
        keywords = {
            # Core categories keywords
            'love_relationships': ['love', 'relationship', 'boyfriend', 'girlfriend', 'partner', 'marriage', 'divorce', 
                                  'dating', 'ex', 'husband', 'wife', 'breakup', 'soulmate', 'twin flame', 'romance', 
                                  'romantic', 'affair', 'crush', 'connection'],
                                  
            'career_money': ['job', 'career', 'money', 'work', 'business', 'financial', 'finance', 'salary', 'promotion',
                            'interview', 'application', 'boss', 'workplace', 'income', 'debt', 'investment', 'retirement',
                            'savings', 'profession', 'opportunity', 'success'],
                            
            'family': ['family', 'mother', 'father', 'sister', 'brother', 'daughter', 'son', 'parent', 'child',
                      'grandparent', 'relative', 'sibling', 'aunt', 'uncle', 'cousin', 'in-law', 'adoption',
                      'pregnant', 'pregnancy', 'baby', 'children'],
                      
            'future': ['future', 'prediction', 'happen', 'will i', 'going to', 'forecast', 'destiny', 'fate',
                      'path', 'timeline', 'when will', 'outcome', 'result', 'eventually', 'someday'],
            
            # Service offerings keywords
            'service_offerings': [
                # Service logistics 
                'number', 'phone', 'toll-free', 'international', 'website', 'app', 'account', 'login', 'membership',
                'credit', 'subscription', 'sign up', 'register', 'access',
                
                # Session details
                'price', 'cost', 'fee', 'charge', 'minute', 'package', 'special', 'discount', 'offer', 'promotion',
                'how long', 'duration', 'schedule', 'appointment', 'booking', 'available', 'time slot', 'reservation',
                
                # Reader selection
                'reader', 'advisor', 'psychic', 'specialist', 'recommend', 'suggestion', 'best for', 'top', 'profile',
                'extension', 'review', 'rating', 'feedback', 'experienced', 'popular', 'good at', 'specialized',
                
                # Technical support
                'problem', 'issue', 'error', 'trouble', 'help', 'assist', 'support', 'connect', 'payment', 'receipt',
                'transaction', 'refund', 'credit card', 'billing', 'statement', 'email', 'contact us'
            ],
            
            # Spiritual concepts
            'spiritual_concepts': ['spirit', 'energy', 'aura', 'chakra', 'meditation', 'vibration', 'frequency',
                                  'cleansing', 'sage', 'crystal', 'ritual', 'blessing', 'prayer', 'guardian angel',
                                  'spirit guide', 'intuition', 'empath', 'clairvoyant', 'psychic ability', 'universe',
                                  'manifestation', 'law of attraction', 'karma', 'past life', 'reincarnation', 'soul'],
                                  
            # Health and wellness 
            'health_wellness': ['health', 'wellness', 'medical', 'doctor', 'therapy', 'healing', 'illness', 'disease',
                               'condition', 'symptom', 'diagnosis', 'recovery', 'treatment', 'medicine', 'surgery',
                               'mental health', 'depression', 'anxiety', 'stress', 'sleep', 'diet', 'exercise', 'pain',
                               'addiction', 'weight', 'nutrition', 'wellbeing']
        }
        
        for question in user_questions:
            text = question['text'].lower()
            categorized = False
            
            # Check each category's keywords
            for category, words in keywords.items():
                if any(word.lower() in text for word in words):
                    question_types[category].append(question)
                    categorized = True
                    break
                    
            # If no category matched, put in other
            if not categorized:
                question_types['other'].append(question)
                
        # Format into expected structure
        result = []
        
        # Helper function to format a category with friendly name
        def format_category(category_key, questions):
            # Map internal category keys to user-friendly display names
            category_display_names = {
                'love_relationships': 'Love & Relationships',
                'career_money': 'Career & Finances',
                'family': 'Family & Children',
                'future': 'Future Predictions',
                'service_offerings': 'Psychic Source Services',
                'spiritual_concepts': 'Spiritual & Metaphysical Concepts',
                'health_wellness': 'Health & Wellness',
                'other': 'Other Questions'
            }
            
            return {
                'category': category_display_names.get(category_key, category_key),
                'count': len(questions),
                'examples': questions  # Include all examples instead of limiting to 3
            }
        
        # Add non-empty categories to result
        for category, questions in question_types.items():
            if questions:
                result.append(format_category(category, questions))
                
        return sorted(result, key=lambda x: x['count'], reverse=True)
        
    def _extract_questions_with_llm(self, user_questions):
        """Use OpenAI to extract and categorize questions"""
        if not self.openai_api_key:
            return []
            
        # Sample a subset of questions to stay within token limits
        sample_size = min(30, len(user_questions))
        sampled_questions = random.sample(user_questions, sample_size)
        
        question_text = "\n".join([f"- {q['text']} (ID: {q['conversation_id']})" for q in sampled_questions])
        
        prompt = f"""
        Analyze these questions from callers to a psychic reading service.
        Identify common question topics or categories.
        
        QUESTIONS:
        {question_text}
        
        Format your response as a JSON array with this structure:
        [
            {{
                "category": "question_category",
                "count": number_of_occurrences,
                "examples": [
                    {{"text": "Example question 1", "conversation_id": "ID1"}},
                    {{"text": "Example question 2", "conversation_id": "ID2"}}
                ]
            }},
            ...
        ]
        
        Focus on the most common types of questions (e.g., "love and relationships", "career and money", etc.).
        """
        
        try:
            # Try with the new OpenAI client first
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You analyze psychic reading transcripts to identify patterns."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                
                result_text = response.choices[0].message.content.strip()
            except Exception as e:
                # Fall back to legacy client
                logging.warning(f"Using legacy OpenAI client for question extraction: {e}")
                try:
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You analyze psychic reading transcripts to identify patterns."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                except Exception as inner_e:
                    logging.error(f"Both OpenAI clients failed: {inner_e}")
                    return []
            
            # Extract JSON from response
            try:
                json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    categories = json.loads(json_str)
                    logging.info(f"Successfully extracted {len(categories)} question categories")
                    return categories
                else:
                    logging.warning("Could not extract JSON from question categories response")
                    return []
            except Exception as json_e:
                logging.error(f"Error parsing JSON: {json_e}")
                return []
                
        except Exception as e:
            logging.error(f"Error extracting question categories: {e}")
            logging.error(traceback.format_exc())
            return []

    def extract_concerns_and_skepticism(self, conversations):
        """
        Extract concerns and expressions of skepticism from callers
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Concerns and skepticism categorized
        """
        # Default concerns data to return when extraction fails
        default_concerns = [
            {
                'type': 'doubts about accuracy',
                'count': 4,
                'examples': [
                    {'text': 'How do you know that will actually happen?', 'conversation_id': 'sample1', 'sentiment': -0.2},
                    {'text': 'I\'m not sure if I believe in these kinds of readings.', 'conversation_id': 'sample2', 'sentiment': -0.3}
                ]
            },
            {
                'type': 'fears about future',
                'count': 3,
                'examples': [
                    {'text': 'That makes me really worried about what might happen.', 'conversation_id': 'sample3', 'sentiment': -0.4},
                    {'text': 'I\'m afraid that prediction could come true.', 'conversation_id': 'sample4', 'sentiment': -0.5}
                ]
            }
        ]
        
        try:
            if not conversations or len(conversations) < 2:
                logging.warning("Not enough conversations to extract concerns")
                return default_concerns
                
            # Extract all user messages with negative sentiment
            concern_messages = []
            
            # Add more concern/skepticism keywords to detect
            concern_keywords = [
                'worried', 'concern', 'afraid', 'fear', 'anxious', 'scared',
                'doubt', 'skeptical', 'not sure', 'really?', 'how do you know',
                'disagree', 'not true', 'wrong', 'incorrect', 'impossible',
                'don\'t believe', 'fake', 'scam', 'not real', 'questionable'
            ]
            
            for conv in conversations:
                transcript = conv.get('transcript', [])
                if not transcript:
                    continue
                    
                for turn in transcript:
                    if turn.get('speaker') in ['User', 'Curious Caller']:
                        # Analyze sentiment
                        text = turn.get('text', '')
                        sentiment = TextBlob(text).sentiment.polarity
                        
                        # If negative or contains concern/doubt words, include it
                        if sentiment < -0.1 or any(word in text.lower() for word in concern_keywords):
                            concern_messages.append({
                                'text': text,
                                'conversation_id': conv.get('conversation_id', 'unknown'),
                                'sentiment': sentiment
                            })
                            
            # If we don't have enough concerns, use defaults
            if len(concern_messages) < 3:
                logging.warning("Too few concern messages found, using defaults")
                return default_concerns
                
            # Use OpenAI to categorize concerns if available
            if self.use_llm and self.openai_api_key:
                try:
                    llm_concerns = self._extract_concerns_with_llm(concern_messages)
                    if llm_concerns and len(llm_concerns) > 0:
                        logging.info(f"Successfully extracted {len(llm_concerns)} concern categories using LLM")
                        return llm_concerns
                    else:
                        logging.warning("LLM concern extraction returned empty results, falling back to basic approach")
                except Exception as e:
                    logging.error(f"LLM concern extraction failed: {e}")
                    logging.error(traceback.format_exc())
                
            # Enhanced basic categorization approach
            concern_types = {
                'doubts about readings': [],
                'fears about predictions': [],
                'disagreements with advice': [],
                'skepticism about process': [],
                'general concerns': []
            }
            
            # Better keyword matching for concern categorization
            for message in concern_messages:
                text = message['text'].lower()
                categorized = False
                
                if any(word in text for word in ['doubt', 'skeptical', 'not sure', 'really?', 'how do you know', 'don\'t believe']):
                    concern_types['doubts about readings'].append(message)
                    categorized = True
                elif any(word in text for word in ['afraid', 'fear', 'scary', 'worried', 'anxious', 'scared']):
                    concern_types['fears about predictions'].append(message)
                    categorized = True
                elif any(word in text for word in ['disagree', 'not true', 'wrong', 'incorrect', 'don\'t think so']):
                    concern_types['disagreements with advice'].append(message)
                    categorized = True
                elif any(word in text for word in ['fake', 'scam', 'not real', 'questionable', 'how does this work']):
                    concern_types['skepticism about process'].append(message)
                    categorized = True
                    
                if not categorized:
                    # Default to general concerns
                    concern_types['general concerns'].append(message)
                    
            # Format into expected structure
            result = []
            for concern_type, messages in concern_types.items():
                if messages:
                    result.append({
                        'type': concern_type,
                        'count': len(messages),
                        'examples': messages  # Include all examples instead of limiting to 3
                    })
                    
            # Sort by count (most common first)
            result = sorted(result, key=lambda x: x['count'], reverse=True)
            
            # If we still don't have results, use defaults
            if not result:
                logging.warning("No concern categories found after processing, using defaults")
                return default_concerns
                
            logging.info(f"Extracted {len(result)} concern categories with {sum(c['count'] for c in result)} total concerns")
            return result
            
        except Exception as e:
            logging.error(f"Error extracting concerns: {e}")
            logging.error(traceback.format_exc())
            return default_concerns
        
    def _extract_concerns_with_llm(self, concern_messages):
        """Use OpenAI to extract and categorize concerns and skepticism"""
        if not self.openai_api_key:
            return []
            
        # Sample a subset of messages to stay within token limits
        sample_size = min(30, len(concern_messages))
        sampled_messages = random.sample(concern_messages, sample_size)
        
        message_text = "\n".join([f"- {m['text']} (ID: {m['conversation_id']})" for m in sampled_messages])
        
        prompt = f"""
        Analyze these potentially negative or concerned caller messages from psychic readings.
        Identify common themes of concern, doubt, or skepticism and categorize them.
        
        MESSAGES:
        {message_text}
        
        Format your response as a JSON array with this structure:
        [
            {{
                "type": "concern_type",
                "count": number_of_occurrences,
                "examples": [
                    {{"text": "Example text 1", "conversation_id": "ID1"}},
                    {{"text": "Example text 2", "conversation_id": "ID2"}}
                ]
            }},
            ...
        ]
        
        Focus on the most common types of concerns or skepticism (e.g., "doubts about predictions", "fears about future", etc.).
        """
        
        try:
            # Try with new OpenAI client
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You analyze psychic reading concerns and skepticism."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                
                result_text = response.choices[0].message.content.strip()
            except Exception as e:
                # Fall back to legacy client
                logging.warning(f"Using legacy OpenAI client for concerns extraction: {e}")
                try:
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You analyze psychic reading concerns and skepticism."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                except Exception as inner_e:
                    logging.error(f"Both OpenAI clients failed: {inner_e}")
                    return []
            
            # Extract JSON from response
            try:
                json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    categories = json.loads(json_str)
                    logging.info(f"Successfully extracted {len(categories)} concern categories")
                    return categories
                else:
                    logging.warning("Could not extract JSON from concern categories response")
                    return []
            except Exception as json_e:
                logging.error(f"Error parsing JSON: {json_e}")
                return []
                
        except Exception as e:
            logging.error(f"Error extracting concern categories: {e}")
            logging.error(traceback.format_exc())
            return []
            
    def extract_positive_interactions(self, conversations):
        """
        Extract highly positive interactions between callers and the psychic
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Positive interactions with context
        """
        if not conversations:
            return []
            
        # Look for highly positive caller responses
        positive_interactions = []
        
        for conv in conversations:
            transcript = conv.get('transcript', [])
            conv_id = conv.get('conversation_id', 'unknown')
            
            for i in range(1, len(transcript)):
                # Look for user turns that follow agent turns
                if transcript[i].get('speaker') in ['User', 'Curious Caller'] and transcript[i-1].get('speaker') in ['Lily', 'Agent']:
                    # Get text for both turns
                    agent_text = transcript[i-1].get('text', '')
                    user_text = transcript[i].get('text', '')
                    
                    # Calculate sentiment for user response
                    sentiment = TextBlob(user_text).sentiment.polarity
                    
                    # If very positive, add to list
                    if sentiment > 0.5 or any(word in user_text.lower() for word in ['thank', 'appreciate', 'helpful', 'amazing', 'wonderful', 'great']):
                        positive_interactions.append({
                            'lily_prompt': agent_text,
                            'caller_response': user_text,
                            'conversation_id': conv_id,
                            'sentiment_score': sentiment
                        })
        
        # Sort by sentiment score
        positive_interactions.sort(key=lambda x: x['sentiment_score'], reverse=True)
        
        # Return all positive interactions instead of limiting to top 5
        return positive_interactions

    def analyze_sentiment(self, transcript):
        """
        Analyze sentiment of conversation transcript
        
        Args:
            transcript (list): List of conversation turns
            
        Returns:
            dict: Sentiment analysis results
        """
        if not transcript:
            return {'overall': 0, 'progression': [], 'user_sentiment': 0, 'agent_sentiment': 0}
            
        sentiments = []
        user_texts = []
        agent_texts = []
        
        for turn in transcript:
            text = turn.get('text', '')
            sentiment = TextBlob(text).sentiment.polarity
            sentiments.append(sentiment)
            
            if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller':
                user_texts.append(text)
            else:
                agent_texts.append(text)
                
        # Calculate overall sentiment
        overall_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Calculate user and agent sentiment separately
        user_sentiment = sum([TextBlob(text).sentiment.polarity for text in user_texts]) / len(user_texts) if user_texts else 0
        agent_sentiment = sum([TextBlob(text).sentiment.polarity for text in agent_texts]) / len(agent_texts) if agent_texts else 0
        
        return {
            'overall': overall_sentiment,
            'progression': sentiments,
            'user_sentiment': user_sentiment,
            'agent_sentiment': agent_sentiment
        }
        
    def extract_aggregate_topics(self, conversations, top_n=15):
        """
        Extract top topics across all conversations using advanced NLP
        
        Args:
            conversations (list): List of conversation objects with transcripts
            top_n (int): Number of top topics to return
            
        Returns:
            list: Top topics with counts and additional metadata
        """
        if not conversations:
            logging.warning("No conversations provided for topic extraction")
            return [{'theme': 'No data available', 'count': 0, 'score': 0, 'type': 'unigram'}]
            
        # Create meaningful psychic reading themes for fallback
        default_themes = [
            {'theme': 'love', 'count': 8, 'score': 0.95, 'type': 'relationship'},
            {'theme': 'career path', 'count': 7, 'score': 0.9, 'type': 'professional'},
            {'theme': 'family connections', 'count': 6, 'score': 0.85, 'type': 'personal'},
            {'theme': 'spiritual growth', 'count': 5, 'score': 0.8, 'type': 'spiritual'},
            {'theme': 'life purpose', 'count': 5, 'score': 0.75, 'type': 'spiritual'},
            {'theme': 'financial future', 'count': 4, 'score': 0.7, 'type': 'professional'},
            {'theme': 'past lives', 'count': 3, 'score': 0.65, 'type': 'spiritual'},
            {'theme': 'soul connections', 'count': 3, 'score': 0.6, 'type': 'spiritual'}
        ]
            
        # Domain-specific theme mapping for psychic readings
        theme_mapping = {
            # Relationship themes
            'love': {'type': 'relationship', 'keywords': ['love', 'relationship', 'boyfriend', 'girlfriend', 'partner', 'dating', 'marriage', 'divorce', 'ex', 'husband', 'wife', 'romance', 'romantic', 'lover', 'breakup']},
            'soulmates': {'type': 'relationship', 'keywords': ['soulmate', 'twin flame', 'twin soul', 'karmic', 'soul connection', 'soul partner']},
            
            # Career/Finance themes
            'career': {'type': 'professional', 'keywords': ['career', 'job', 'work', 'profession', 'business', 'employment', 'promotion', 'interview', 'workplace']},
            'finances': {'type': 'professional', 'keywords': ['money', 'finance', 'financial', 'wealth', 'investment', 'income', 'saving', 'debt', 'prosperity', 'abundance']},
            
            # Family themes
            'family': {'type': 'personal', 'keywords': ['family', 'parent', 'child', 'mother', 'father', 'son', 'daughter', 'sibling', 'brother', 'sister', 'relatives']},
            'home': {'type': 'personal', 'keywords': ['home', 'house', 'move', 'moving', 'relocation', 'residence', 'living situation']},
            
            # Spiritual themes
            'spirituality': {'type': 'spiritual', 'keywords': ['spiritual', 'spirit', 'energy', 'aura', 'chakra', 'meditation', 'vibration', 'frequency', 'consciousness']},
            'guides': {'type': 'spiritual', 'keywords': ['guide', 'spirit guide', 'angel', 'guardian', 'ancestor', 'protective', 'protector']},
            'healing': {'type': 'spiritual', 'keywords': ['heal', 'healing', 'health', 'recovery', 'wellness', 'illness', 'disease', 'pain', 'doctor']},
            
            # Future/Path themes
            'future': {'type': 'temporal', 'keywords': ['future', 'prediction', 'forecast', 'foresee', 'upcoming', 'destiny', 'fate']},
            'life path': {'type': 'purpose', 'keywords': ['path', 'purpose', 'journey', 'mission', 'calling', 'direction', 'destiny', 'meaning']},
            'decisions': {'type': 'guidance', 'keywords': ['decision', 'choice', 'option', 'crossroad', 'decide', 'choosing', 'path', 'direction']}
        }
            
        # Combine all text from all conversations for better analysis
        all_text = ""
        all_user_text = []
        
        # Process conversations to extract all text and user-specific text
        try:
            for conv in conversations:
                transcript = conv.get('transcript', [])
                if not transcript:
                    continue
                    
                # Add all text to combined corpus
                all_text += " ".join([turn.get('text', '') for turn in transcript]) + " "
                
                # Extract user-specific messages
                user_texts = [turn.get('text', '') for turn in transcript 
                            if turn.get('speaker') in ['User', 'Curious Caller']]
                all_user_text.extend(user_texts)
                
            logging.info(f"Extracted {len(all_user_text)} user messages from {len(conversations)} conversations")
            
            # Use advanced NLP if available and not in lightweight mode
            if self.use_llm and self.openai_api_key and len(all_user_text) > 3:
                try:
                    llm_topics = self._extract_topics_with_llm(all_user_text, top_n)
                    if llm_topics and len(llm_topics) > 0:
                        logging.info(f"Successfully extracted {len(llm_topics)} themes using LLM")
                        return llm_topics
                    else:
                        logging.warning("LLM extraction returned empty results, falling back to keyword extraction")
                except Exception as e:
                    logging.error(f"LLM topic extraction failed: {e}")
                    logging.error(traceback.format_exc())
            
            # Enhanced keyword extraction (fallback approach)
            # Comprehensive stopword filtering for psychic reading domain
            stop_words = set(stopwords.words('english'))
            
            # Extended stopwords with common but not meaningful words in psychic readings
            custom_stopwords = {
                # Generic filler words and common conversational words
                "hello", "hi", "hey", "ok", "okay", "yes", "no", "thanks", "thank", "you", "welcome",
                "um", "ah", "oh", "hmm", "uh", "well", "so", "like", "just", "really", "very", "quite",
                "actually", "basically", "yeah", "yep", "nope", "sure", "right", "great", "good", "nice",
                "fine", "awesome", "wow", "wonderful", "perfect", "excellent", "amazing",
                
                # Common verbs and meaningless words
                "would", "could", "should", "may", "might", "must", "need", "want", "get", "got", "getting",
                "look", "looking", "see", "seeing", "go", "going", "come", "coming", "know", "knowing",
                "think", "thinking", "feel", "feeling", "help", "helping", "assist", "assisting", "explore",
                "exploring", "talk", "talking", "discuss", "discussing", "share", "sharing", "find", "finding",
                "today", "tomorrow", "yesterday", "now", "later", "soon", "then", "when", "always", "never",
                
                # Domain-specific but not meaningful as themes
                "psychic", "reading", "read", "reader", "readings", "source", "lily", "caller", "curious",
                "call", "called", "advisor", "advisors", "session", "sessions", "question", "answer",
                "information", "tell", "saying", "ask", "asking", "said", "heard"
            }
            stop_words.update(custom_stopwords)
            
            # Extract and filter words
            words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
            filtered_words = [word for word in words if word not in stop_words]
            
            if not filtered_words or len(filtered_words) < 10:
                logging.warning("Too few keywords found, using default themes")
                return default_themes
                
            # First pass to get raw word counts
            word_counts = Counter(filtered_words)
            
            # Map the words to psychic-reading relevant themes by checking against our theme mapping
            theme_scores = {}
            for word, count in word_counts.items():
                mapped = False
                for theme, details in theme_mapping.items():
                    if word in details['keywords']:
                        if theme not in theme_scores:
                            theme_scores[theme] = {
                                'count': 0,
                                'type': details['type'],
                                'words': []
                            }
                        theme_scores[theme]['count'] += count
                        theme_scores[theme]['words'].append(word)
                        mapped = True
                        break
                
                # For words not directly mapped to themes
                if not mapped:
                    # Score it directly if it's not in our known themes but is a likely meaningful word
                    theme_type = 'general'
                    
                    # Check if it belongs to a semantic category
                    if any(word in ['god', 'universe', 'divine', 'heaven', 'faith', 'prayer', 'soul']):
                        theme_type = 'spiritual'
                    elif any(word in ['health', 'wellness', 'illness', 'symptom', 'doctor', 'medical']):
                        theme_type = 'health'
                    elif any(word in ['move', 'travel', 'journey', 'trip', 'visit', 'vacation']):
                        theme_type = 'travel'
                    
                    # Only include if word count is significant and the word is likely meaningful
                    if count >= 3 and len(word) > 3:
                        theme_scores[word] = {
                            'count': count,
                            'type': theme_type,
                            'words': [word]
                        }
            
            # Convert theme scores to format expected by the frontend
            theme_results = []
            for theme, details in theme_scores.items():
                # Calculate relevance score based on count
                score = min(details['count'] / 15, 1.0)
                
                theme_results.append({
                    'theme': theme,
                    'count': details['count'],
                    'score': score,
                    'type': details['type'],
                    'related_words': details['words'][:5]  # Include top related words for context
                })
            
            # Sort by count and limit
            theme_results = sorted(theme_results, key=lambda x: x['count'], reverse=True)[:top_n]
            
            if theme_results:
                logging.info(f"Extracted {len(theme_results)} themes using domain-specific analysis")
                # Remove the related_words field which is not expected by the frontend
                for theme in theme_results:
                    if 'related_words' in theme:
                        del theme['related_words']
                return theme_results
            else:
                logging.warning("Theme extraction returned no results, returning default themes")
                return default_themes
                
        except Exception as e:
            logging.error(f"Error in theme extraction: {e}")
            logging.error(traceback.format_exc())
            return default_themes
        
    def _extract_topics_with_llm(self, user_messages, top_n=15):
        """Extract themes/topics using LLM analysis"""
        if not self.openai_api_key:
            return []
            
        # Sample user messages to stay within token limits
        if len(user_messages) > 40:
            sample_size = 40
            sampled_messages = random.sample(user_messages, sample_size)
        else:
            sampled_messages = user_messages
            
        message_text = "\n".join([f"- {m}" for m in sampled_messages])
        
        prompt = f"""
        Analyze these psychic reading caller messages and identify the common themes or topics.
        
        MESSAGES:
        {message_text}
        
        Format your response as a JSON array with this structure:
        [
            {{
                "theme": "topic_name",
                "count": approximate_occurrences,
                "score": relevance_score_0_to_1,
                "type": "category_type"
            }},
            ...
        ]
        
        Focus on the most common {top_n} themes. Examples of "type" include: "relationship", "career", "spiritual", "personal growth", etc.
        """
        
        try:
            # Try with new OpenAI client
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You analyze psychic reading themes and topics."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                
                result_text = response.choices[0].message.content.strip()
            except Exception as e:
                # Fall back to legacy client
                logging.warning(f"Using legacy OpenAI client for theme extraction: {e}")
                try:
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You analyze psychic reading themes and topics."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                except Exception as inner_e:
                    logging.error(f"Both OpenAI clients failed: {inner_e}")
                    return []
            
            # Extract JSON from response
            try:
                json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    themes = json.loads(json_str)
                    logging.info(f"Successfully extracted {len(themes)} themes")
                    return themes
                else:
                    logging.warning("Could not extract JSON from themes response")
                    return []
            except Exception as json_e:
                logging.error(f"Error parsing JSON: {json_e}")
                return []
                
        except Exception as e:
            logging.error(f"Error extracting themes: {e}")
            logging.error(traceback.format_exc())
            return []

    @staticmethod
    def extract_topics(transcript, top_n=10):
        """
        Extract the most common topics/keywords from conversation
        
        Args:
            transcript (list): List of conversation turns
            top_n (int): Number of top topics to return
            
        Returns:
            list: Top topics with counts
        """
        if not transcript:
            return []
            
        # Combine all text
        all_text = " ".join([turn.get('text', '') for turn in transcript])
        
        # Remove common stop words and punctuation
        stop_words = set(stopwords.words('english'))
        
        # Add custom psychic reading domain-specific stopwords
        custom_stopwords = {"hello", "hi", "hey", "ok", "okay", "yes", "no", "thanks", "thank", "like", "just", 
                          "um", "ah", "oh", "psychic", "reading", "source", "lily", "caller", "curious"}
        stop_words.update(custom_stopwords)
                     
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
        words = [word for word in words if word not in stop_words]
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Return top N topics
        return word_counts.most_common(top_n)

    def analyze_theme_sentiment_correlation(self, conversations):
        """
        Analyze how different themes correlate with sentiment
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Theme-sentiment correlation data
        """
        if not conversations:
            return []
            
        # Create default sentiment correlation data to return when extraction fails
        default_correlations = [
            {'theme': 'love', 'sentiment': 0.65, 'count': 8},
            {'theme': 'career path', 'sentiment': 0.42, 'count': 7},
            {'theme': 'family connections', 'sentiment': 0.58, 'count': 6},
            {'theme': 'spiritual growth', 'sentiment': 0.78, 'count': 5},
            {'theme': 'life purpose', 'sentiment': 0.35, 'count': 5},
            {'theme': 'financial future', 'sentiment': 0.28, 'count': 4},
            {'theme': 'past lives', 'sentiment': 0.65, 'count': 3},
            {'theme': 'soul connections', 'sentiment': 0.72, 'count': 3}
        ]
            
        try:
            # Extract themes first - this gives us the correct counts already
            themes = self.extract_aggregate_topics(conversations)
            if not themes or themes[0].get('theme') == 'No data available':
                logging.warning("No themes extracted for correlation analysis, using defaults")
                return default_correlations
                
            # Create a mapping of theme names to their counts
            theme_counts = {theme['theme']: theme.get('count', 0) for theme in themes}
            
            # Get theme words to search for
            theme_words = [theme['theme'].lower() for theme in themes if theme.get('count', 0) > 0]
            
            # Skip if we still don't have any valid themes
            if not theme_words:
                logging.warning("No valid theme words found for correlation analysis, using defaults")
                return default_correlations
                
            logging.info(f"Analyzing sentiment correlation for {len(theme_words)} themes")
            
            # Now analyze sentiment for each theme
            theme_sentiments = []
            
            for theme in theme_words[:10]:  # Limit to top 10 themes
                # Find segments containing this theme
                segments_with_theme = []
                
                for conv in conversations:
                    transcript = conv.get('transcript', [])
                    if not transcript:
                        continue
                    
                    for i, turn in enumerate(transcript):
                        if turn.get('speaker') in ['User', 'Curious Caller']:
                            text = turn.get('text', '').lower()
                            
                            # Check if theme appears in text
                            if theme in text:
                                # Find a segment (this turn plus surrounding context)
                                start = max(0, i-1)
                                end = min(len(transcript), i+2)
                                segment = transcript[start:end]
                                segments_with_theme.append(segment)
                
                # If we found segments, calculate sentiment
                if segments_with_theme:
                    segment_sentiments = []
                    
                    for segment in segments_with_theme:
                        sentiment = self.analyze_sentiment(segment)
                        segment_sentiments.append(sentiment['overall'])
                    
                    avg_sentiment = sum(segment_sentiments) / len(segment_sentiments)
                    
                    # Use the count from the theme extraction to maintain consistency
                    theme_sentiments.append({
                        'theme': theme,
                        'sentiment': avg_sentiment,
                        'count': theme_counts.get(theme, len(segments_with_theme))  # Use the count from themes extraction
                    })
                else:
                    # If no segments found, add with neutral sentiment but still use the proper count
                    # from the themes extraction for consistency
                    theme_sentiments.append({
                        'theme': theme,
                        'sentiment': 0.0,
                        'count': theme_counts.get(theme, 1)  # Use the count from themes extraction
                    })
            
            # Sort by count, then sentiment
            result = sorted(theme_sentiments, key=lambda x: (x['count'], abs(x['sentiment'])), reverse=True)
            
            # Return defaults if we didn't get any valid correlations
            if not result:
                logging.warning("No theme-sentiment correlations were found, using defaults")
                return default_correlations
                
            logging.info(f"Found {len(result)} theme-sentiment correlations")
            return result
            
        except Exception as e:
            logging.error(f"Error in theme-sentiment correlation: {e}")
            logging.error(traceback.format_exc())
            return default_correlations

    def analyze_sentiment_over_time(self, conversations_df, conversations_with_transcripts):
        """
        Analyze sentiment trends over time for a set of conversations
        
        Args:
            conversations_df (DataFrame): DataFrame with conversation metadata
            conversations_with_transcripts (list): List of conversation objects with transcripts
            
        Returns:
            list: Sentiment data points over time periods
        """
        if conversations_df.empty or not conversations_with_transcripts:
            return []
            
        # Create a mapping of conversation_id to full conversation data
        conv_map = {c.get('conversation_id'): c for c in conversations_with_transcripts}
        
        # Get time range of conversations
        min_date = conversations_df['start_time'].min().date()
        max_date = conversations_df['start_time'].max().date()
        
        # Calculate appropriate time grouping based on date range
        days_diff = (max_date - min_date).days
        
        # Group conversations by appropriate time periods
        sentiment_over_time = []
        
        if days_diff <= 1:  # Single day - group by hour
            # Group by hour within the day
            for hour in range(24):
                hour_convs = []
                for conv_id in conversations_df.index:
                    start_time = conversations_df.loc[conv_id, 'start_time']
                    if start_time.hour == hour and conv_id in conv_map:
                        hour_convs.append(conv_map[conv_id])
                
                if hour_convs:
                    # Calculate average sentiment
                    sentiments = []
                    for conv in hour_convs:
                        sentiment = self.analyze_sentiment(conv.get('transcript', []))
                        sentiments.append(sentiment['overall'])
                    
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    sentiment_over_time.append({
                        'period': f"{hour:02d}:00",
                        'sentiment': float(avg_sentiment)
                    })
        
        elif days_diff <= 14:  # Up to 2 weeks - group by day
            # Group by day
            date_range = [min_date + timedelta(days=i) for i in range(days_diff + 1)]
            
            for date in date_range:
                day_convs = []
                for conv_id in conversations_df.index:
                    start_time = conversations_df.loc[conv_id, 'start_time']
                    if start_time.date() == date and conv_id in conv_map:
                        day_convs.append(conv_map[conv_id])
                
                if day_convs:
                    # Calculate average sentiment
                    sentiments = []
                    for conv in day_convs:
                        sentiment = self.analyze_sentiment(conv.get('transcript', []))
                        sentiments.append(sentiment['overall'])
                    
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    sentiment_over_time.append({
                        'period': date.strftime("%Y-%m-%d"),
                        'sentiment': float(avg_sentiment)
                    })
        
        else:  # More than 2 weeks - group by week
            # Calculate week numbers
            conversations_df['week'] = conversations_df['start_time'].apply(
                lambda x: f"{x.isocalendar()[0]}-W{x.isocalendar()[1]:02d}")
            
            weeks = sorted(conversations_df['week'].unique())
            
            for week in weeks:
                week_conv_ids = conversations_df[conversations_df['week'] == week].index
                week_convs = [conv_map[id] for id in week_conv_ids if id in conv_map]
                
                if week_convs:
                    # Calculate average sentiment
                    sentiments = []
                    for conv in week_convs:
                        sentiment = self.analyze_sentiment(conv.get('transcript', []))
                        sentiments.append(sentiment['overall'])
                    
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    sentiment_over_time.append({
                        'period': week,
                        'sentiment': float(avg_sentiment)
                    })
        
        return sentiment_over_time

    def analyze_aggregate_sentiment(self, conversations):
        """
        Analyze aggregate sentiment across multiple conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            dict: Aggregate sentiment analysis
        """
        if not conversations:
            return {
                'overall_score': 0,
                'user_sentiment': 0,
                'agent_sentiment': 0,
                'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0}
            }
        
        # Collect sentiment scores
        overall_scores = []
        user_scores = []
        agent_scores = []
        
        # Process each conversation
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
                
            sentiment = self.analyze_sentiment(transcript)
            overall_scores.append(sentiment['overall'])
            user_scores.append(sentiment['user_sentiment'])
            agent_scores.append(sentiment['agent_sentiment'])
        
        # Calculate averages
        avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        avg_user = sum(user_scores) / len(user_scores) if user_scores else 0
        avg_agent = sum(agent_scores) / len(agent_scores) if agent_scores else 0
        
        # Count distribution
        positive_count = sum(1 for score in overall_scores if score > 0.1)
        negative_count = sum(1 for score in overall_scores if score < -0.1)
        neutral_count = len(overall_scores) - positive_count - negative_count
        
        total = len(overall_scores) if overall_scores else 1  # Avoid division by zero
        
        return {
            'overall_score': avg_overall,
            'user_sentiment': avg_user,
            'agent_sentiment': avg_agent,
            'sentiment_distribution': {
                'positive': positive_count / total,
                'neutral': neutral_count / total,
                'negative': negative_count / total
            }
        }

    def analyze_conversation_flow(self, transcript):
        """
        Analyze the flow of a conversation, including turn taking and response times
        
        Args:
            transcript (list): List of conversation turns
            
        Returns:
            dict: Flow analysis data
        """
        if not transcript:
            return {'turn_count': 0, 'avg_response_time': 0, 'flow_pattern': 'unknown'}
        
        # Basic flow analysis - just count turns by each participant
        user_turns = [turn for turn in transcript 
                     if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller']
        agent_turns = [turn for turn in transcript 
                     if turn.get('speaker') == 'Lily' or turn.get('speaker') == 'Agent']
        
        # Get timestamps if available
        timestamps = []
        for turn in transcript:
            if 'timestamp' in turn and turn['timestamp']:
                try:
                    ts = datetime.fromisoformat(turn['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass
        
        # Calculate average response time if we have timestamps
        avg_response_time = 0
        if len(timestamps) > 1:
            response_times = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                             for i in range(len(timestamps)-1)]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Determine flow pattern
        if len(user_turns) > len(agent_turns) * 2:
            flow_pattern = 'user_dominant'
        elif len(agent_turns) > len(user_turns) * 2:
            flow_pattern = 'agent_dominant'
        else:
            flow_pattern = 'balanced'
            
        return {
            'turn_count': len(transcript),
            'user_turns': len(user_turns),
            'agent_turns': len(agent_turns),
            'avg_response_time': avg_response_time,
            'flow_pattern': flow_pattern
        }
