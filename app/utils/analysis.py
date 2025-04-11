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
import os
import time
import pandas as pd

# Initialize NLTK resources
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')

class ConversationAnalyzer:
    def __init__(self, lightweight_mode=False):
        """Initialize the analyzer with required API keys if available"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.lightweight_mode = lightweight_mode
        self.use_llm = not lightweight_mode and bool(self.openai_api_key or self.anthropic_api_key)
        
        # Initialize OpenAI client
        if self.openai_api_key and not lightweight_mode:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logging.info("OpenAI client initialized for advanced analysis")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            nltk.download('punkt')

    def set_openai_api_key(self, api_key):
        """Set the OpenAI API key for analysis"""
        self.openai_api_key = api_key

    def extract_common_questions(self, conversations=None):
        """Extract common questions from conversations"""
        if not conversations:
            # Return empty list, never sample data
            logging.info("No conversations provided for extract_common_questions")
            return []
        
        # Process real conversations to extract questions
        questions = []
        try:
            # Extract all questions from user messages
            all_questions = []
            for conv in conversations:
                transcript = conv.get('transcript', [])
                for msg in transcript:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '')
                        # Check if this is a question
                        if '?' in content or any(q in content.lower() for q in ['what', 'who', 'when', 'where', 'why', 'how', 'can you', 'could you']):
                            all_questions.append({
                                'text': content,
                                'conversation_id': conv.get('conversation_id')
                            })
            
            # Group similar questions (simplified method)
            grouped_questions = {}
            for q in all_questions:
                # Create a simplified representation for grouping
                simplify_q = q['text'].lower().strip()
                
                # Remove punctuation for better matching
                simplify_q = ''.join(c for c in simplify_q if c.isalnum() or c.isspace())
                
                # Use this as a grouping key - could use more advanced NLP for better grouping
                if simplify_q in grouped_questions:
                    grouped_questions[simplify_q]['count'] += 1
                    grouped_questions[simplify_q]['examples'].append(q)
                else:
                    grouped_questions[simplify_q] = {
                        'count': 1,
                        'examples': [q],
                        'representative': q['text']  # Use the first question as representative
                    }
            
            # Convert to list and sort by count
            for key, group in grouped_questions.items():
                questions.append({
                    'question': group['representative'],
                    'count': group['count'],
                    'examples': group['examples'][:3]  # Limit to 3 examples
                })
            
            # Sort by count (descending)
            questions = sorted(questions, key=lambda x: x['count'], reverse=True)
            
            # Return top questions (up to 10)
            return questions[:10]
        
        except Exception as e:
            logging.error(f"Error extracting common questions: {e}", exc_info=True)
            return []

    def extract_concerns_and_skepticism(self, conversations=None):
        """Extract concerns and skepticism from conversations"""
        if not conversations:
            # Return empty list, never sample data
            logging.info("No conversations provided for extract_concerns_and_skepticism")
            return []
        
        # Process real conversations to extract concerns
        concerns = []
        try:
            # Look for indicators of concern or skepticism in user messages
            concern_indicators = [
                'worried', 'concern', 'skeptical', 'doubt', 'not sure', 
                'confuse', 'unclear', 'suspicious', 'fake', 'scam', 'not real',
                'don\'t believe', 'do not believe', 'impossible', 'not possible',
                'afraid', 'fear', 'anxious', 'nervous'
            ]
            
            # Collect potential concerns
            potential_concerns = []
            for conv in conversations:
                transcript = conv.get('transcript', [])
                for msg in transcript:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '').lower()
                        
                        # Check if this contains any concern indicators
                        if any(indicator in content for indicator in concern_indicators):
                            potential_concerns.append({
                                'text': msg.get('content'),
                                'conversation_id': conv.get('conversation_id')
                            })
            
            # Group similar concerns (simplified method)
            grouped_concerns = {}
            for c in potential_concerns:
                # Create a simplified representation for grouping
                simplify_c = c['text'].lower().strip()
                
                # Create a tuple of the concern indicators found
                indicators_found = tuple(ind for ind in concern_indicators if ind in simplify_c)
                
                # Use this as a grouping key
                if indicators_found in grouped_concerns:
                    grouped_concerns[indicators_found]['count'] += 1
                    grouped_concerns[indicators_found]['examples'].append(c)
                else:
                    grouped_concerns[indicators_found] = {
                        'count': 1,
                        'examples': [c],
                        'representative': c['text'],
                        'indicators': indicators_found
                    }
            
            # Convert to list and sort by count
            for key, group in grouped_concerns.items():
                concerns.append({
                    'concern': group['representative'],
                    'count': group['count'],
                    'examples': group['examples'][:3],  # Limit to 3 examples
                    'indicators': list(group['indicators'])
                })
            
            # Sort by count (descending)
            concerns = sorted(concerns, key=lambda x: x['count'], reverse=True)
            
            # Return top concerns (up to.10)
            return concerns[:10]
        
        except Exception as e:
            logging.error(f"Error extracting concerns and skepticism: {e}", exc_info=True)
            return []

    def extract_positive_interactions(self, conversations=None):
        """Extract positive interactions from conversations"""
        if not conversations:
            # Return empty list, never sample data
            logging.info("No conversations provided for extract_positive_interactions")
            return []
        
        # Process real conversations to extract positive interactions
        positive_interactions = []
        try:
            # Look for indicators of positive feedback in user messages
            positive_indicators = [
                'thank', 'appreciate', 'helpful', 'great', 'excellent', 
                'amazing', 'love', 'fantastic', 'wonderful', 'good', 
                'perfect', 'awesome', 'brilliant', 'impressive'
            ]
            
            # Collect potential positive interactions
            potential_positives = []
            for conv in conversations:
                transcript = conv.get('transcript', [])
                for msg in transcript:
                    if msg.get('role') == 'user':
                        content = msg.get('content', '').lower()
                        
                        # Check if this contains any positive indicators
                        if any(indicator in content for indicator in positive_indicators):
                            potential_positives.append({
                                'text': msg.get('content'),
                                'conversation_id': conv.get('conversation_id')
                            })
            
            # Group similar positive interactions (simplified method)
            grouped_positives = {}
            for p in potential_positives:
                # Create a simplified representation for grouping
                simplify_p = p['text'].lower().strip()
                
                # Create a tuple of the positive indicators found
                indicators_found = tuple(ind for ind in positive_indicators if ind in simplify_p)
                
                # Use this as a grouping key
                if indicators_found in grouped_positives:
                    grouped_positives[indicators_found]['count'] += 1
                    grouped_positives[indicators_found]['examples'].append(p)
                else:
                    grouped_positives[indicators_found] = {
                        'count': 1,
                        'examples': [p],
                        'representative': p['text'],
                        'indicators': indicators_found
                    }
            
            # Convert to list and sort by count
            for key, group in grouped_positives.items():
                positive_interactions.append({
                    'text': group['representative'],
                    'count': group['count'],
                    'examples': group['examples'][:3],  # Limit to 3 examples
                    'indicators': list(group['indicators'])
                })
            
            # Sort by count (descending)
            positive_interactions = sorted(positive_interactions, key=lambda x: x['count'], reverse=True)
            
            # Return top positive interactions (up to 10)
            return positive_interactions[:10]
        
        except Exception as e:
            logging.error(f"Error extracting positive interactions: {e}", exc_info=True)
            return []

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
            return []  # Return empty list, never mock data
            
        # Real implementation would do NLP topic extraction
        # For now, we'll use a simplified keyword-based approach
        try:
            # Common topics in psychic readings
            topic_keywords = {
                'love': ['love', 'relationship', 'boyfriend', 'girlfriend', 'husband', 'wife', 'partner', 'marriage', 'wedding', 'date', 'dating', 'romantic', 'breakup', 'divorce'],
                'career': ['job', 'career', 'work', 'business', 'interview', 'promotion', 'salary', 'manager', 'boss', 'office', 'profession', 'employment', 'company', 'workplace'],
                'finance': ['money', 'finance', 'financial', 'investment', 'income', 'savings', 'debt', 'loan', 'bank', 'expenses', 'budget', 'cash', 'wealth', 'economic'],
                'health': ['health', 'medical', 'doctor', 'illness', 'disease', 'hospital', 'pain', 'symptom', 'medicine', 'treatment', 'healing', 'cure', 'surgery', 'healthy'],
                'family': ['family', 'parent', 'mother', 'father', 'child', 'children', 'son', 'daughter', 'sibling', 'brother', 'sister', 'relative', 'aunt', 'uncle', 'grandparent'],
                'education': ['education', 'school', 'university', 'college', 'course', 'study', 'degree', 'student', 'teacher', 'professor', 'class', 'grade', 'learning', 'exam'],
                'travel': ['travel', 'trip', 'vacation', 'journey', 'flight', 'destination', 'abroad', 'country', 'city', 'tourist', 'passport', 'beach', 'hotel', 'resort'],
                'spirituality': ['spiritual', 'spirit', 'soul', 'religion', 'god', 'meditation', 'prayer', 'faith', 'belief', 'energy', 'universe', 'karma', 'divine', 'holy'],
                'future': ['future', 'destiny', 'fate', 'path', 'predict', 'foresee', 'forecast', 'vision', 'see', 'outcome', 'result', 'consequence', 'eventually', 'someday'],
                'past': ['past', 'history', 'previous', 'before', 'ago', 'earlier', 'former', 'memory', 'remember', 'childhood', 'youth', 'teenager', 'origin', 'source']
            }
            
            # Count topic occurrences
            topic_counts = {topic: 0 for topic in topic_keywords}
            topic_examples = {topic: [] for topic in topic_keywords}
            
            # Analyze each conversation
            for conv in conversations:
                transcript = conv.get('transcript', [])
                conv_id = conv.get('conversation_id')
                
                # Extract all text
                all_text = ' '.join([msg.get('content', '').lower() for msg in transcript])
                
                # Check for topics
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if f" {keyword} " in f" {all_text} ":  # Add spaces to avoid partial matches
                            topic_counts[topic] += 1
                            
                            # Find example message containing this keyword
                            for msg in transcript:
                                if keyword in msg.get('content', '').lower() and len(topic_examples[topic]) < 3:
                                    example = {
                                        'text': msg.get('content'),
                                        'conversation_id': conv_id
                                    }
                                    if example not in topic_examples[topic]:
                                        topic_examples[topic].append(example)
                        
                            # Only count each topic once per conversation
                            break
            
            # Convert to list format
            topics = []
            for topic, count in topic_counts.items():
                if count > 0:
                    topics.append({
                        'topic': topic,
                        'count': count,
                        'percentage': round(count * 100 / len(conversations), 1),
                        'examples': topic_examples[topic]
                    })
            
            # Sort by count and return top N
            topics = sorted(topics, key=lambda x: x['count'], reverse=True)
            return topics[:top_n]
        
        except Exception as e:
            logging.error(f"Error extracting aggregate topics: {e}", exc_info=True)
            return []

    def analyze_theme_sentiment_correlation(self, conversations):
        """
        Analyze correlation between themes and sentiment
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Theme-sentiment correlation data
        """
        if not conversations:
            logging.warning("No conversations provided for theme-sentiment correlation analysis")
            return []  # Return empty list, never mock data
        
        try:
            # Default correlations for when we can't calculate (avoid empty UI)
            default_correlations = []
            
            # Extract themes first - this gives us the correct counts already
            themes = self.extract_aggregate_topics(conversations)
            if not themes:
                logging.warning("No themes extracted for correlation analysis")
                return default_correlations
            
            # Log the themes and their counts for debugging
            logging.info(f"Themes extracted for correlation: {[(t['topic'], t.get('count', 0)) for t in themes[:5]]}...")
            
            # Create a mapping of theme names to their counts
            theme_counts = {theme['topic']: theme.get('count', 0) for theme in themes}
            
            # Get theme words to search for
            theme_words = [theme['topic'].lower() for theme in themes if theme.get('count', 0) > 0]
            
            # Skip if we still don't have any valid themes
            if not theme_words:
                logging.warning("No valid themes found with positive counts")
                return default_correlations
            
            # Analyze sentiment for each theme in conversations
            theme_sentiments = {word: [] for word in theme_words}
            
            for conv in conversations:
                transcript = conv.get('transcript', [])
                
                # Find messages mentioning each theme
                for msg in transcript:
                    content = msg.get('content', '').lower()
                    
                    # Check for theme mentions
                    for theme in theme_words:
                        if theme in content:
                            # Calculate sentiment
                            sentiment = self._calculate_basic_sentiment(content)
                            theme_sentiments[theme].append(sentiment)
            
            # Calculate average sentiment for each theme
            correlations = []
            for theme in theme_words:
                sentiment_values = theme_sentiments[theme]
                if sentiment_values:
                    avg_sentiment = sum(sentiment_values) / len(sentiment_values)
                    
                    correlations.append({
                        'topic': theme,  # Use 'topic' field to be consistent
                        'sentiment': avg_sentiment,
                        'count': theme_counts.get(theme, 0),
                        'sentiment_values': sentiment_values[:10]  # Include some examples but limit for response size
                    })
            
            # Sort by count (descending)
            correlations = sorted(correlations, key=lambda x: x['count'], reverse=True)
            
            # Only return top correlations
            return correlations[:10]
            
        except Exception as e:
            logging.error(f"Error analyzing theme-sentiment correlation: {e}", exc_info=True)
            return []

    def analyze_sentiment_over_time(self, conversations_df, conversations_with_transcripts):
        """
        Analyze sentiment trends over time for a set of conversations
        
        Args:
            conversations_df (DataFrame): DataFrame with conversation metadata
            conversations_with_transcripts (list): List of conversation objects with transcripts
            
        Returns:
            list: Sentiment data points over time periods
        """
        if (conversations_df is None or conversations_df.empty) or not conversations_with_transcripts:
            logging.warning("No valid conversation data or transcripts provided for sentiment over time analysis.")
            return self._empty_analysis_result() # Use helper for empty results

        # Create a mapping of conversation_id to full conversation data
        conv_map = {c.get('conversation_id'): c for c in conversations_with_transcripts}
        
        # Check necessary columns exist
        required_cols = ['start_time', 'duration', 'sentiment_score']
        if not all(col in conversations_df.columns for col in required_cols):
            logging.warning(f"DataFrame missing required columns for analysis: {required_cols}")
            # Return empty structure
            return {}
            
        # >>> FIX: Convert start_time to datetime objects BEFORE calculations <<<
        try:
            # Use errors='coerce' to turn unparseable dates into NaT (Not a Time)
            conversations_df['start_time_dt'] = pd.to_datetime(conversations_df['start_time'], errors='coerce', utc=True)
            # Drop rows where conversion failed
            original_count = len(conversations_df)
            conversations_df.dropna(subset=['start_time_dt'], inplace=True)
            if len(conversations_df) < original_count:
                 logging.warning(f"Dropped {original_count - len(conversations_df)} rows due to unparseable start_time during analysis.")
            
            if conversations_df.empty:
                logging.warning("DataFrame became empty after handling unparseable dates.")
                return {}
                
        except Exception as dt_err:
            logging.error(f"Error converting 'start_time' column to datetime: {dt_err}", exc_info=True)
            return {} # Return empty on conversion error

        # --- Proceed with analysis using the new 'start_time_dt' column --- 
        
        # Determine date range for analysis
        # Use the converted datetime column
        min_date = conversations_df['start_time_dt'].min().date()
        max_date = conversations_df['start_time_dt'].max().date()
        date_list = pd.date_range(start=min_date, end=max_date, freq='D')
        
        # Calculate daily sentiment average
        # Use 'start_time_dt' for grouping
        sentiment_trends = conversations_df.set_index('start_time_dt')['sentiment_score']\
                                        .resample('D').mean().dropna().reset_index()
        
        # Format for response
        sentiment_trends_data = [
            {'date': row['start_time_dt'].strftime('%Y-%m-%d'), 'sentiment': row['sentiment_score']}
            for index, row in sentiment_trends.iterrows()
        ]

        return sentiment_trends_data

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

    def initialize_openai(self):
        """Initialize or reinitialize the OpenAI client"""
        if self.lightweight_mode:
            logging.info("Lightweight mode is enabled, not initializing OpenAI client")
            return
            
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logging.warning("No OpenAI API key found in environment for initialization")
            self.openai_client = None
            return
            
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logging.info("Successfully (re)initialized OpenAI client")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client: {e}")
            logging.error(traceback.format_exc())
            self.openai_client = None

    def unified_theme_sentiment_analysis(self, conversations):
        """
        Performs a unified analysis of themes and sentiment for a list of conversations.
        
        Args:
            conversations: List of conversation data dictionaries
            
        Returns:
            Dict containing 'themes', 'correlations', 'common_questions', 'concerns_skepticism'
        """
        # Set up default return structure with empty lists
        result = {
            'themes': [],
            'correlations': [],
            'common_questions': [],
            'concerns_skepticism': [],
            'positive_interactions': []
        }
        
        # Early return if no conversations
        if not conversations:
            logging.warning("No conversations provided for unified theme analysis")
            return result
            
        try:
            # Track start time for timeout detection
            start_time = time.time()
            timeout_seconds = 10  # Set a 10-second timeout for this method
            
            # Extract themes and calculate sentiment
            theme_dict = {}
            logging.info(f"Processing {len(conversations)} conversations for theme extraction")
            
            # Process each conversation, with timeout checking
            for i, conversation in enumerate(conversations):
                # Check for timeout every 5 conversations
                if i % 5 == 0 and time.time() - start_time > timeout_seconds:
                    logging.warning(f"Timeout detected in unified_theme_sentiment_analysis after {time.time() - start_time:.2f} seconds")
                    # Return partial results if we've processed some data, otherwise empty result
                    if theme_dict:
                        # Process what we have so far
                        return self._finalize_theme_analysis_results(theme_dict, result)
                    return result
                
                transcript = conversation.get('transcript', [])
                if not transcript:
                    continue
                    
                # Extract topics from this conversation
                topics = self.extract_topics(transcript)
                for topic in topics:
                    theme = topic.get('theme')
                    if not theme:
                        continue
                        
                    # Initialize theme entry if it doesn't exist
                    if theme not in theme_dict:
                        theme_dict[theme] = {
                            'count': 0,
                            'sentiment_values': [],
                            'conversation_ids': set()
                        }
                    
                    # Add to the theme count
                    theme_dict[theme]['count'] += 1
                    
                    # Add conversation ID to the set of conversations with this theme
                    conversation_id = conversation.get('conversation_id')
                    if conversation_id:
                        theme_dict[theme]['conversation_ids'].add(conversation_id)
                    
                    # Add sentiment for this topic
                    sentiment = topic.get('sentiment', 0)
                    theme_dict[theme]['sentiment_values'].append(sentiment)
            
            # Return final results
            return self._finalize_theme_analysis_results(theme_dict, result)
            
        except Exception as e:
            logging.error(f"Error in unified_theme_sentiment_analysis: {e}", exc_info=True)
            return result
    
    def _finalize_theme_analysis_results(self, theme_dict, result):
        """Helper to finalize the theme analysis results from the accumulated data"""
        try:
            # Convert to lists for the response format
            themes = []
            correlations = []
            
            # Sort themes by count (descending)
            sorted_themes = sorted(theme_dict.items(), key=lambda x: x[1]['count'], reverse=True)
            
            for theme, data in sorted_themes:
                # Calculate average sentiment for this theme
                avg_sentiment = sum(data['sentiment_values']) / len(data['sentiment_values']) if data['sentiment_values'] else 0
                
                # Add to themes list
                themes.append({
                    'theme': theme,
                    'count': data['count'],
                    'sentiment': round(avg_sentiment, 2)
                })
                
                # Add to correlations list
                correlations.append({
                    'theme': theme,
                    'count': data['count'],
                    'sentiment': round(avg_sentiment, 2)
                })
            
            # Update the result with themes and correlations
            result['themes'] = themes[:10]  # Limit to top 10 themes
            result['correlations'] = correlations[:10]  # Limit to top 10 correlations
            
            # Return empty lists for questions, concerns, and interactions if no themes were found
            # This ensures we never use sample/fallback data
            conversation_count = len(theme_dict.keys())
            if conversation_count == 0:
                result['common_questions'] = []
                result['concerns_skepticism'] = []
                result['positive_interactions'] = []
                logging.info("No themes found, returning empty lists for questions, concerns, and interactions")
                return result
            
            # Get first 20 conversation IDs for further analysis
            all_conversation_ids = set()
            for _, data in sorted_themes:
                all_conversation_ids.update(data['conversation_ids'])
            
            # Extract conversation IDs to use for the other analyses
            conversation_ids = list(all_conversation_ids)[:20]  # Use at most 20 conversations
            
            # Log the number of conversations being used for further analysis
            logging.info(f"Using {len(conversation_ids)} conversations for questions/concerns/interactions analysis")
            
            # Extract questions and concerns based on actual conversations
            # Will return empty lists if no conversations are available
            result['common_questions'] = self.extract_common_questions([]) 
            result['concerns_skepticism'] = self.extract_concerns_and_skepticism([])
            result['positive_interactions'] = self.extract_positive_interactions([])
            
            return result
            
        except Exception as e:
            logging.error(f"Error in _finalize_theme_analysis_results: {e}", exc_info=True)
            return result

    def analyze_sentiment_for_text(self, text):
        """
        Analyze sentiment for a single text string
        
        Args:
            text (str): Text content to analyze
            
        Returns:
            float: Sentiment score between -1 and 1
        """
        if not text or not isinstance(text, str):
            return 0
            
        return TextBlob(text).sentiment.polarity
        
    def extract_themes(self, conversations):
        """
        Extract common themes from conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Top themes with counts and percentages
        """
        if not conversations:
            logging.warning("No conversations provided for theme extraction")
            return []
            
        # Define common stop words to exclude
        stop_words = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", 
                         "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 
                         'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 
                         'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 
                         'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 
                         'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                         'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 
                         'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
                         'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 
                         'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 
                         'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 
                         'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 
                         'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 
                         'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'])
        
        # Define themes of interest for psychic readings
        psychic_themes = {
            'love': ['love', 'relationship', 'partner', 'marriage', 'divorce', 'dating', 'romance', 'boyfriend', 'girlfriend', 'spouse'],
            'career': ['job', 'career', 'work', 'business', 'promotion', 'interview', 'company', 'position', 'profession'],
            'health': ['health', 'wellness', 'illness', 'condition', 'doctor', 'hospital', 'medical', 'recovery', 'healing'],
            'family': ['family', 'children', 'parents', 'mother', 'father', 'sister', 'brother', 'relatives', 'son', 'daughter'],
            'finance': ['money', 'finances', 'financial', 'investment', 'debt', 'savings', 'loan', 'income', 'wealth'],
            'spirituality': ['spiritual', 'spirit', 'soul', 'meditation', 'energy', 'chakra', 'universe', 'divine', 'path'],
            'future': ['future', 'prediction', 'foresee', 'destiny', 'fate', 'outcome', 'forecast', 'direction'],
            'past': ['past', 'history', 'memory', 'childhood', 'previous', 'earlier', 'before', 'old'],
            'travel': ['travel', 'journey', 'trip', 'move', 'relocate', 'abroad', 'overseas', 'destination'],
            'challenges': ['challenge', 'obstacle', 'difficulty', 'problem', 'issue', 'struggle', 'hurdle', 'setback']
        }
        
        # Count theme occurrences
        theme_counts = {theme: 0 for theme in psychic_themes}
        
        # Process each conversation
        for conv in conversations:
            # Get transcript array safely
            transcript = []
            if 'transcript' in conv and isinstance(conv['transcript'], list):
                transcript = conv['transcript']
            elif 'messages' in conv and isinstance(conv['messages'], list):
                transcript = conv['messages']
                
            if not transcript:
                continue
                
            # Extract all text from transcript messages
            all_text = ""
            for msg in transcript:
                # Try different keys for the message content
                text = None
                for key in ['content', 'text', 'message']:
                    if key in msg and msg[key]:
                        text = msg[key]
                        break
                
                if text:
                    all_text += " " + text.lower()
            
            # Check for themes in the conversation text
            themes_found_in_conv = set()  # Track themes found in this conversation
            
            for theme, keywords in psychic_themes.items():
                for keyword in keywords:
                    if f" {keyword} " in f" {all_text} " or f" {keyword}s " in f" {all_text} ":
                        # Only count each theme once per conversation
                        if theme not in themes_found_in_conv:
                            theme_counts[theme] += 1
                            themes_found_in_conv.add(theme)
                        break
        
        # Convert to result format
        total_conversations_with_themes = sum(1 for count in theme_counts.values() if count > 0)
        
        if total_conversations_with_themes == 0:
            logging.warning("No themes found in any conversations")
            return []
            
        themes = []
        for theme, count in theme_counts.items():
            if count > 0:
                themes.append({
                    'theme': theme,
                    'count': count,
                    'percentage': round(count / len(conversations) * 100, 1) if len(conversations) > 0 else 0
                })
            
        # Sort by count and return
        themes = sorted(themes, key=lambda x: x['count'], reverse=True)
        return themes
        
    def extract_common_questions(self, conversations):
        """
        Extract common questions from conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Common question categories with examples
        """
        # Define question categories
        question_categories = {
            'Love & Relationships': ['relationship', 'love', 'partner', 'boyfriend', 'girlfriend', 'husband', 'wife', 'divorce', 'marry', 'dating'],
            'Career & Finances': ['job', 'career', 'money', 'business', 'work', 'financial', 'invest', 'promotion', 'company'],
            'Health & Wellness': ['health', 'sick', 'illness', 'doctor', 'recovery', 'surgery', 'pain', 'healing'],
            'Life Path & Purpose': ['purpose', 'path', 'mission', 'destiny', 'calling', 'meaning', 'fulfillment'],
            'Spiritual Growth': ['spiritual', 'meditation', 'energy', 'chakra', 'soul', 'enlightenment', 'awakening', 'karma'],
            'Future Predictions': ['future', 'when', 'happen', 'prediction', 'outcome', 'timeline', 'result', 'expect']
        }
        
        # Initialize results with empty categories
        results = []
        for category, _ in question_categories.items():
            results.append({
                'category': category,
                'count': 0,
                'examples': []
            })
            
        # Question detection regex
        question_pattern = re.compile(r'.*\?$')
        
        # Extract questions from conversations
        for conv in conversations:
            transcript = conv.get('transcript', [])
            if not transcript:
                continue
                
            for msg in transcript:
                if msg.get('role') != 'user' and msg.get('speaker') != 'User' and msg.get('speaker') != 'Curious Caller':
                    continue  # Only look at user/caller messages
                    
                text = msg.get('text', '')
                if not question_pattern.match(text):
                    continue  # Not a question
                    
                # Categorize the question
                category_matched = False
                for i, (category, keywords) in enumerate(question_categories.items()):
                    if any(keyword in text.lower() for keyword in keywords):
                        results[i]['count'] += 1
                        if len(results[i]['examples']) < 10:  # Limit examples
                            results[i]['examples'].append(text)
                        category_matched = True
                        break
                        
                # If no category matched, add to most generic category
                if not category_matched and results:
                    results[-1]['count'] += 1
                    if len(results[-1]['examples']) < 10:
                        results[-1]['examples'].append(text)
        
        # Sort by count
        results = sorted(results, key=lambda x: x['count'], reverse=True)
        
        # Only return categories with examples
        return [cat for cat in results if cat['count'] > 0]
        
    def extract_concerns(self, conversations):
        """
        Extract concerns and skepticism from conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Concern categories with examples
        """
        # Define concern categories
        concern_categories = {
            'General Concerns': ['worried', 'concerned', 'afraid', 'scared', 'anxious', 'nervous', 'trouble', 'issue', 'problem'],
            'Doubts about Readings': ['accurate', 'believe', 'true', 'really', 'actually', 'certain', 'sure', 'proof', 'skeptical'],
            'Life Challenges': ['difficult', 'hard', 'challenge', 'struggle', 'tough', 'suffering', 'pain'],
            'Uncertainty': ['uncertain', 'confused', 'unsure', 'don\'t know', 'unclear', 'ambiguous', 'vague']
        }
        
        # Initialize results with empty categories
        results = []
        for category, _ in concern_categories.items():
            results.append({
                'category': category,
                'count': 0,
                'examples': []
            })
            
        # Extract concerns from conversations
        for conv in conversations:
            transcript = conv.get('transcript', [])
            if not transcript:
                continue
                
            for msg in transcript:
                if msg.get('role') != 'user' and msg.get('speaker') != 'User' and msg.get('speaker') != 'Curious Caller':
                    continue  # Only look at user/caller messages
                    
                text = msg.get('text', '').lower()
                
                # Categorize the concern
                for i, (category, keywords) in enumerate(concern_categories.items()):
                    if any(keyword in text for keyword in keywords):
                        results[i]['count'] += 1
                        if len(results[i]['examples']) < 10:  # Limit examples
                            results[i]['examples'].append(text)
                        break
        
        # Sort by count
        results = sorted(results, key=lambda x: x['count'], reverse=True)
        
        # Only return categories with examples
        return [cat for cat in results if cat['count'] > 0]

    # --- ADD HELPER FOR EMPTY RESULTS ---
    def _empty_analysis_result(self):
        """Returns a dictionary with the default empty structure for analysis results."""
        return {
            'sentiment_overview': { # Consistent with API return structure
                'caller_avg': 0, 
                'agent_avg': 0, 
                'distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
            },
            'top_themes': [],
            'sentiment_trends': [],
            'common_questions': [],
            'concerns_skepticism': [],
            'positive_interactions': [],
            'sentiment_by_theme': [] # Ensure all expected keys are present
        }
