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
from openai import OpenAI, RateLimitError, APIError
import tiktoken

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
        # Anthropic key is no longer used in this version
        # self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.lightweight_mode = lightweight_mode
        self.use_llm = not lightweight_mode and bool(self.openai_api_key)
        self.openai_client = None
        self.tokenizer = None # For estimating token counts
        # Define the primary OpenAI model to be used for analysis
        self.model_name = "gpt-4o" 
        
        # Initialize OpenAI client and tokenizer
        if self.openai_api_key and not lightweight_mode:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                self.tokenizer = tiktoken.get_encoding("cl100k_base") # Common encoder for gpt-3.5/4
                logging.info("OpenAI client and tokenizer initialized for advanced analysis")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client or tokenizer: {e}")
                self.openai_client = None
                self.tokenizer = None
                self.use_llm = False # Force disable LLM if init fails
            
        # Initialize NLTK resources if needed
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            try:
                nltk.download('stopwords', quiet=True)
                nltk.download('punkt', quiet=True)
            except Exception as e:
                 logging.error(f"Failed to download NLTK data: {e}")

    def set_openai_api_key(self, api_key):
        """Set the OpenAI API key and re-initialize the client"""
        self.openai_api_key = api_key
        self.use_llm = not self.lightweight_mode and bool(self.openai_api_key)
        if self.openai_api_key and not self.lightweight_mode:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                logging.info("OpenAI client and tokenizer re-initialized with new key")
            except Exception as e:
                logging.error(f"Failed to re-initialize OpenAI client or tokenizer: {e}")
                self.openai_client = None
                self.tokenizer = None
        else:
             self.openai_client = None
             self.tokenizer = None

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
        Analyzes sentiment trends over time from conversation data.
        This is a placeholder and will likely be replaced by LLM-driven analysis.
        """
        # ... (Keep existing implementation for now, or replace with LLM logic later) ...
        # For now, return structure matching expected output if possible
        if conversations_df is None or conversations_df.empty:
             return {'labels': [], 'average_sentiment_scores': []}

        # Assuming conversations_df has 'date' and 'sentiment_score' columns
        # Group by date and calculate average sentiment
        try:
            # Ensure 'date' is datetime
            conversations_df['date'] = pd.to_datetime(conversations_df['date'])
            sentiment_trends = conversations_df.groupby(conversations_df['date'].dt.date)['sentiment_score'].mean().reset_index()
            sentiment_trends = sentiment_trends.sort_values(by='date')

            labels = sentiment_trends['date'].dt.strftime('%Y-%m-%d').tolist()
            scores = sentiment_trends['sentiment_score'].round(2).tolist()
            return {'labels': labels, 'average_sentiment_scores': scores}
        except Exception as e:
             logging.error(f"Error calculating sentiment trends: {e}")
             return {'labels': [], 'average_sentiment_scores': []}

    def analyze_aggregate_sentiment(self, conversations):
        """
        Analyzes aggregate sentiment scores from conversation data.
        This is a placeholder and will likely be replaced by LLM-driven analysis.
        """
        # ... (Keep existing implementation for now, or replace with LLM logic later) ...
        # For now, return structure matching expected output if possible
        caller_sentiments = []
        agent_sentiments = []
        all_sentiments = []

        for conv in conversations:
            transcript = conv.get('transcript', [])
            for msg in transcript:
                try:
                    sentiment = TextBlob(msg.get('content', '')).sentiment.polarity
                    all_sentiments.append(sentiment)
                    if msg.get('role') == 'user':
                        caller_sentiments.append(sentiment)
                    elif msg.get('role') == 'agent':
                        agent_sentiments.append(sentiment)
                except Exception:
                    continue # Skip messages that fail sentiment analysis

        # Calculate averages, handling empty lists
        avg_caller = sum(caller_sentiments) / len(caller_sentiments) if caller_sentiments else 0
        avg_agent = sum(agent_sentiments) / len(agent_sentiments) if agent_sentiments else 0
        avg_overall = sum(all_sentiments) / len(all_sentiments) if all_sentiments else 0

        # Determine overall label based on average score
        if avg_overall > 0.2:
            overall_label = "Positive"
        elif avg_overall < -0.2:
            overall_label = "Negative"
        else:
            overall_label = "Neutral"

        # Basic distribution (can be enhanced)
        distribution = {
            "very_positive": sum(1 for s in all_sentiments if s > 0.6),
            "positive": sum(1 for s in all_sentiments if 0.2 < s <= 0.6),
            "neutral": sum(1 for s in all_sentiments if -0.2 <= s <= 0.2),
            "negative": sum(1 for s in all_sentiments if -0.6 <= s < -0.2),
            "very_negative": sum(1 for s in all_sentiments if s < -0.6)
        }
        
        return {
            "overall_sentiment_label": overall_label,
            "sentiment_distribution": distribution,
            "caller_average_sentiment": round(avg_caller, 2),
            "agent_average_sentiment": round(avg_agent, 2)
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

    # ==========================================================================
    # NEW Unified LLM Analysis Method
    # ==========================================================================
    def unified_llm_analysis(self, conversations, start_date_iso, end_date_iso, original_total_count=None):
        """
        Performs a comprehensive analysis using a single OpenAI API call.
        This is designed to get all required data for the Themes & Sentiment page.

        Args:
            conversations: List of conversation data dictionaries (including transcript).
            start_date_iso: ISO format start date of the analysis period.
            end_date_iso: ISO format end date of the analysis period.
            original_total_count: The total number of conversations found in the date range
                                  before applying limits for LLM input.

        Returns:
            Dict containing the full analysis results structured as defined previously,
            or a dictionary with an 'error' key if analysis fails.
        """
        if not self.use_llm or not self.openai_client or not self.tokenizer:
            logging.warning("LLM analysis skipped: OpenAI client not available or lightweight mode enabled.")
            # Pass the original count if available
            result = self._empty_analysis_result(start_date_iso, end_date_iso, "LLM Not Available", original_total_count)
            result['analysis_status']['model_name'] = "N/A"
            return result

        if not conversations:
            logging.warning("No conversations provided for unified LLM analysis.")
             # Pass the original count if available
            result = self._empty_analysis_result(start_date_iso, end_date_iso, "No Conversations", original_total_count)
            result['analysis_status']['model_name'] = "N/A"
            return result

        # --- 1. Prepare Input Data for LLM ---
        # Note: _prepare_llm_input now returns the prepared data and the count *actually processed*
        prepared_input_result = self._prepare_llm_input(conversations)
        if not prepared_input_result:
             # Pass the original count if available
             result = self._empty_analysis_result(start_date_iso, end_date_iso, "Input Preparation Failed", original_total_count)
             result['analysis_status']['model_name'] = "N/A"
             return result

        analysis_input = prepared_input_result["input_data"]
        processed_count = prepared_input_result["processed_count"]

        # --- 2. Construct the Prompt ---
        # Pass the *original* total count to the prompt builder
        prompt = self._build_llm_prompt(analysis_input, start_date_iso, end_date_iso, original_total_count)

        # --- 3. Call OpenAI API ---
        try:
            logging.info(f"Calling OpenAI API ({self.model_name}) for unified analysis ({processed_count} conversations processed)...")
            response = self.openai_client.chat.completions.create(
                model=self.model_name, # Use the configured model name
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert conversation analyst specializing in psychic readings. Analyze the provided conversation data and return the results strictly in the requested JSON format. Be thorough and accurate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2, 
                max_tokens=4096 
            )
            logging.info("Received response from OpenAI API.")

            llm_output_raw = response.choices[0].message.content

            # --- 4. Parse and Validate LLM Response ---
            # Pass the model name used so it can be included in the final result's status.
            analysis_result = self._parse_and_validate_llm_output(
                llm_output_raw, 
                start_date_iso, 
                end_date_iso, 
                original_total_count, 
                self.model_name 
            )
            return analysis_result

        except RateLimitError as rle:
            logging.error(f"OpenAI Rate Limit Error: {rle}")
            # Use empty result structure for consistency
            result = self._empty_analysis_result(start_date_iso, end_date_iso, f"Rate Limit Error: {str(rle)}", original_total_count)
            result['error'] = "Rate limit exceeded. Please try again later." # Add specific error key
            return result
        except APIError as apie:
             logging.error(f"OpenAI API Error: {apie}")
             result = self._empty_analysis_result(start_date_iso, end_date_iso, f"OpenAI API Error: {str(apie)}", original_total_count)
             result['error'] = "An error occurred with the OpenAI API." # Add specific error key
             return result
        except Exception as e:
            logging.error(f"Error during unified LLM analysis: {e}", exc_info=True)
            result = self._empty_analysis_result(start_date_iso, end_date_iso, f"Unexpected Analysis Error: {str(e)}", original_total_count)
            result['error'] = "An unexpected error occurred during analysis." # Add specific error key
            return result

    def _prepare_llm_input(self, conversations):
        """Prepares a simplified data structure for the LLM prompt, handling potential size limits.
           Returns a dict: {"input_data": {...}, "processed_count": int} or None on failure.
        """
        input_data_list = []
        MAX_INPUT_TOKENS = 100000 # Leave ~30k tokens for prompt and response for a 131k model
        estimated_tokens = 0
        processed_count = 0

        if not self.tokenizer:
            logging.warning("Tokenizer not available, cannot estimate token count accurately. Proceeding without check.")
            max_conversations_for_llm = 100
            conversations_to_process = conversations[:max_conversations_for_llm]
            logging.warning(f"Processing max {max_conversations_for_llm} conversations due to missing tokenizer.")
        else:
            conversations_to_process = []
            for conv in conversations:
                transcript_text = ""
                for msg in conv.get('transcript', []):
                    speaker = "Caller" if msg.get('role') == 'user' else "Psychic"
                    transcript_text += f"{speaker}: {msg.get('content', '')}\\n"

                # Estimate tokens for this conversation (simple approach)
                conv_data_for_estimation = {
                    "conversation_id": conv.get("external_id", conv.get("id")),
                    "timestamp": conv.get("created_at", "").isoformat() if conv.get("created_at") else "N/A",
                    "transcript_summary": transcript_text.strip()
                }
                current_conv_tokens = len(self.tokenizer.encode(json.dumps(conv_data_for_estimation)))

                if estimated_tokens + current_conv_tokens < MAX_INPUT_TOKENS:
                    estimated_tokens += current_conv_tokens
                    conversations_to_process.append(conv)
                else:
                    logging.warning(f"Approaching token limit... Stopping addition of conversations.")
                    logging.warning(f"Processing {len(conversations_to_process)} conversations out of {len(conversations)} provided.")
                    break
            
            if not conversations_to_process:
                 logging.error("No conversations fit within the token limit.")
                 return None

        # Now build the final input data list
        for conv in conversations_to_process:
            transcript_text = ""
            for msg in conv.get('transcript', []):
                speaker = "Caller" if msg.get('role') == 'user' else "Psychic"
                transcript_text += f"{speaker}: {msg.get('content', '')}\\n"

            input_data_list.append({
                "conversation_id": conv.get("external_id", conv.get("id")), 
                "timestamp": conv.get("created_at", "").isoformat() if conv.get("created_at") else "N/A",
                "transcript_summary": transcript_text.strip() 
            })
        
        processed_count = len(input_data_list)
        logging.info(f"Prepared LLM input with {processed_count} conversations, estimated tokens: {estimated_tokens}")
        # Return both the input for the prompt and the count processed
        return {"input_data": {"conversations": input_data_list}, "processed_count": processed_count}

    def _build_llm_prompt(self, analysis_input, start_date_iso, end_date_iso, total_conversations_in_range):
        """Constructs the detailed prompt for the OpenAI API, including the original total count."""
        # Use the provided total_conversations_in_range in the metadata description
        # Ensure total_conversations_in_range is an int or default to 0
        total_count_int = total_conversations_in_range if isinstance(total_conversations_in_range, int) else 0

        # Escape literal curly braces for f-string by doubling them {{ }}
        output_json_structure = f"""
        {{
          "metadata": {{
            "start_date": "{start_date_iso}",
            "end_date": "{end_date_iso}",
            "total_conversations_in_range": {total_count_int} // Total conversations FOUND in this date range (before token limits)
          }},
          "sentiment_overview": {{
            "overall_sentiment_label": "string (Positive/Neutral/Negative)",
            "sentiment_distribution": {{ "very_positive": int, "positive": int, "neutral": int, "negative": int, "very_negative": int }},
            "caller_average_sentiment": float, // Scale -1 to 1
            "agent_average_sentiment": float // Scale -1 to 1
          }},
          "top_themes": {{
            "themes": [{{ "theme": "string", "count": int }}] // Sorted descending by count, max 10
          }},
          "sentiment_trends": {{ // Analyze daily average sentiment across the period
            "labels": ["YYYY-MM-DD", ...], // Dates within the range with conversations
            "average_sentiment_scores": [float, ...] // Corresponding avg sentiment scores (-1 to 1)
          }},
          "theme_sentiment_correlation": [
            {{ "theme": "string", "mentions": int, "sentiment_label": "string (e.g., Positive, Slightly Negative)" }} // Match top_themes, sorted
          ]}},
          "categorized_quotes": {{
            "common_questions": [
              {{ "category_name": "string", "count": int, "quotes": [{{ "quote_text": "string", "conversation_id": "string" }}] }} // Max 3 quotes per category example
            ],
            "concerns_skepticism": [
              {{ "category_name": "string", "count": int, "quotes": [{{ "quote_text": "string", "conversation_id": "string" }}] }} // Max 3 quotes per category example
            ],
            "positive_interactions": {{
              "count": int,
              "quotes": [{{ "quote_text": "string", "conversation_id": "string", "sentiment_score": float }}] // Sorted by score, max 10 examples
            }}
          }},
          "analysis_status": {{ // Added for clarity
              "mode": "Full",
              "message": "Analysis complete using LLM."
          }}
        }}
        """

        prompt = f"""
        Analyze the following psychic reading conversation data covering the period from {start_date_iso} to {end_date_iso}.
        A total of {total_count_int} conversations were found in this date range, but only a subset might be included below due to processing limits.
        Analyze *only* the conversations provided in the Input Data section below.

        Input Data:
        ```json
        {json.dumps(analysis_input, indent=2)}
        ```

        **Analysis Tasks & Output Format:**
        
        Based *only* on the provided conversation data below, perform the following analysis and return the results *strictly* in the following JSON format. Do NOT include explanations or commentary outside the JSON structure.
        Crucially, the `metadata.total_conversations_in_range` field in your output JSON MUST be exactly {total_count_int}.
        All other analysis (sentiment, themes, quotes, etc.) must be based *only* on the conversations present in the Input Data.

        **Required JSON Output Structure:**
        ```json
        {output_json_structure}
        ```

        **Detailed Instructions:**
        1.  **metadata:** Fill with the provided date range and ensure `total_conversations_in_range` is exactly {total_count_int}.
        2.  **sentiment_overview:** Calculate based *only* on messages in the Input Data.
        3.  **top_themes:** Identify themes based *only* on conversations in the Input Data.
        4.  **sentiment_trends:** Calculate daily averages based *only* on messages in the Input Data for dates within the requested range.
        5.  **theme_sentiment_correlation:** Correlate themes found in the Input Data.
        6.  **categorized_quotes:** Extract quotes *only* from conversations present in the Input Data.

        Ensure the output is a single, valid JSON object adhering exactly to the structure specified.
        """
        return prompt.strip()

    def _parse_and_validate_llm_output(self, llm_output_raw, start_date_iso, end_date_iso, original_total_count, model_name="N/A"):
        """
        Parses the LLM JSON output, validates structure, and enriches metadata.
        Includes adding the provided `model_name` to the `analysis_status`.
        """
        try:
            logging.debug(f"Raw LLM Output:\n{llm_output_raw[:500]}...")
            parsed_output = json.loads(llm_output_raw)
            logging.info("Successfully parsed LLM JSON response.")

            # --- Basic Structure Validation ---
            required_top_keys = ["metadata", "sentiment_overview", "top_themes", "sentiment_trends", 
                               "theme_sentiment_correlation", "categorized_quotes", "analysis_status"]
            if not all(key in parsed_output for key in required_top_keys):
                logging.error(f"LLM output missing required top-level keys. Found: {list(parsed_output.keys())}")
                raise ValueError("LLM output structure validation failed (top keys)")
            
            # --- Enrich/Validate Metadata ---
            # Ensure the LLM used the provided total count
            if 'metadata' not in parsed_output or not isinstance(parsed_output['metadata'], dict):
                 parsed_output['metadata'] = {}
                 
            parsed_output['metadata']['start_date'] = start_date_iso
            parsed_output['metadata']['end_date'] = end_date_iso
            parsed_output['metadata']['total_conversations_in_range'] = original_total_count if original_total_count is not None else 0
            
            # --- Enrich/Validate Analysis Status ---
            if 'analysis_status' not in parsed_output or not isinstance(parsed_output['analysis_status'], dict):
                 parsed_output['analysis_status'] = {}
                 
            parsed_output['analysis_status']['mode'] = "Full"
            parsed_output['analysis_status']['message'] = "Analysis complete using LLM."
            # Ensure the model name used for the analysis is included in the status
            parsed_output['analysis_status']['model_name'] = model_name 

            # --- Add deeper validation here if needed (e.g., check types, list lengths) ---
            # Example: Validate top_themes format
            if not isinstance(parsed_output.get('top_themes', {}).get('themes', []), list):
                 logging.warning("LLM output for top_themes.themes is not a list. Attempting recovery or defaulting.")
                 # Attempt recovery or set a default empty list
                 parsed_output['top_themes'] = {"themes": []}
                 
            # Add more validation checks for other sections...
            
            logging.info("Successfully parsed and validated LLM response structure.")
            return parsed_output

        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to parse LLM JSON response: {json_err}")
            logging.error(f"Problematic JSON string (first 500 chars): {llm_output_raw[:500]}")
            raise ValueError(f"Invalid JSON format received from LLM: {json_err}")
        except ValueError as val_err:
             # Re-raise validation errors
             raise val_err
        except Exception as e:
            logging.error(f"Unexpected error parsing/validating LLM output: {e}", exc_info=True)
            raise ValueError(f"Unexpected error processing LLM output: {str(e)}")

    def _empty_analysis_result(self, start_date_iso, end_date_iso, status_message="No Data", total_conversations=0):
        """Generates a default empty analysis result structure."""
        return {
            "metadata": {
                "start_date": start_date_iso,
                "end_date": end_date_iso,
                "total_conversations_in_range": total_conversations if total_conversations is not None else 0
            },
            "sentiment_overview": None,
            "top_themes": None,
            "sentiment_trends": None,
            "theme_sentiment_correlation": None,
            "categorized_quotes": None,
            "analysis_status": {
                "mode": "Unavailable" if status_message != "LLM Not Available" else "Lightweight",
                "message": status_message,
                "model_name": "N/A" # Default model name for empty/error results
            }
        }
