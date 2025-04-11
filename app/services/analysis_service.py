"""
Analysis service for handling conversation analysis operations.
"""
import logging
import traceback
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from app.utils.analysis import ConversationAnalyzer
from flask import current_app
import time
import pandas as pd
from app.extensions import db
import random
from sqlalchemy import func, distinct, text
from app.models import Conversation, Message
import json
import os
from collections import Counter, defaultdict
from sqlalchemy.orm import Session

# Import the conversation service we need
from app.services.supabase_conversation_service import SupabaseConversationService

class AnalysisService:
    """Service for handling conversation analysis operations."""
    
    def __init__(self, conversation_service: SupabaseConversationService, cache=None, lightweight_mode=False):
        """
        Initialize the analysis service.
        
        Args:
            conversation_service: An instance of SupabaseConversationService.
            cache: Cache object for storing analysis results (e.g., Flask-Cache instance)
            lightweight_mode: Whether to use lightweight analysis methods
        """
        self.conversation_service = conversation_service # Use the passed service
        self.cache = cache  # Store the passed cache object
        self.lightweight_mode = lightweight_mode
        
        try:
            # Initialize the underlying analyzer utility
            self.analyzer = ConversationAnalyzer(lightweight_mode=self.lightweight_mode)
            logging.info(f"AnalysisService initialized (Lightweight: {self.lightweight_mode})")
            
            # >>> ADD CHECK for successful OpenAI client init within analyzer <<<
            if not self.lightweight_mode and (not hasattr(self.analyzer, 'openai_client') or self.analyzer.openai_client is None):
                logging.warning("ConversationAnalyzer initialized, but its OpenAI client failed. Forcing limited mode.")
                # Set analyzer to None to indicate failure for full analysis capabilities
                self.analyzer = None 
                # Optionally, could re-init in lightweight mode: 
                # self.analyzer = ConversationAnalyzer(lightweight_mode=True)
                
        except Exception as e:
            logging.error(f"Error initializing ConversationAnalyzer in AnalysisService: {e}", exc_info=True)
            self.analyzer = None
            logging.warning(f"AnalysisService running in limited mode due to analyzer init error (Lightweight: {self.lightweight_mode})")
        
        # Removed manual cache dictionary and TTL
        logging.info(f"Analysis service initialized with lightweight_mode={lightweight_mode}. Cache object: {type(self.cache)}")
    
    def _create_safe_analyzer(self):
        """Create a placeholder analyzer with fallback methods"""
        class SafeAnalyzer:
            def analyze_sentiment(self, transcript):
                logging.warning("Using fallback analyzer for sentiment analysis")
                return {'overall': 0, 'progression': [], 'user_sentiment': 0, 'agent_sentiment': 0}
                
            def extract_topics(self, transcript):
                logging.warning("Using fallback analyzer for topic extraction")
                return []
                
            def analyze_conversation_flow(self, transcript):
                logging.warning("Using fallback analyzer for conversation flow analysis")
                return {}
                
            def extract_common_questions(self, conversations=None):
                logging.warning("Using fallback analyzer for question extraction")
                return []
                
            def extract_concerns_and_skepticism(self, conversations=None):
                logging.warning("Using fallback analyzer for concerns extraction")
                return []
                
            def extract_positive_interactions(self, conversations=None):
                logging.warning("Using fallback analyzer for positive interactions extraction")
                return []
                
            def analyze_theme_sentiment_correlation(self, conversations):
                logging.warning("Using fallback analyzer for theme-sentiment correlation")
                return []
                
            def extract_aggregate_topics(self, conversations, top_n=15):
                logging.warning("Using fallback analyzer for aggregate topics extraction")
                return []
        
        return SafeAnalyzer()
    
    def clear_cache(self):
        """Clears the cache if a cache object is configured."""
        if self.cache and hasattr(self.cache, 'clear'): # Check if cache object exists and has clear method
            try:
                self.cache.clear()
                logging.info("AnalysisService cache cleared via injected cache object.")
            except Exception as e:
                logging.error(f"Error clearing AnalysisService cache via injected object: {e}", exc_info=True)
        else:
            logging.warning("Attempted to clear cache, but no valid cache object configured for AnalysisService.")
    
    def analyze_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single conversation.
        
        Args:
            conversation_data: Conversation data to analyze
            
        Returns:
            Analysis results including sentiment, topics, etc.
        """
        if not conversation_data:
            logging.warning("No conversation data provided for analysis")
            return {}
            
        logging.info(f"Analyzing conversation {conversation_data.get('conversation_id', 'unknown')}")
        
        # Extract transcript for analysis
        transcript = conversation_data.get('transcript', [])
        
        # Perform sentiment analysis
        sentiment_data = self.analyzer.analyze_sentiment(transcript)
        
        # Extract topics
        topics_data = self.analyzer.extract_topics(transcript)
        
        # Analyze conversation flow
        flow_data = self.analyzer.analyze_conversation_flow(transcript)
        
        return {
            'conversation_id': conversation_data.get('conversation_id', 'unknown'),
            'sentiment': sentiment_data,
            'topics': topics_data,
            'flow': flow_data
        }
    
    def analyze_conversations_over_time(self, conversations, timeframe='day'):
        """Analyzes sentiment and themes over time across multiple conversations.
        Uses Flask-Caching if configured.
        """
        # Check if analyzer is available
        if not self.analyzer:
            logging.error("ConversationAnalyzer not initialized, cannot perform analysis.")
            # Return default empty structure
            return {
                'sentiment_overview': {},
                'sentiment_trends': [],
                'top_themes': [],
                'sentiment_by_theme': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': []
            }
            
        logging.info(f"Analyzing {len(conversations)} conversations for themes/sentiment (Timeframe: {timeframe})")
        
        # TODO: Implement actual Flask-Caching @cache.memoize decorator pattern here if desired.
        # Currently, no caching is applied to this method after removing manual cache.
        logging.warning("analyze_conversations_over_time is NOT currently cached.")

        # Perform the actual analysis using the analyzer utility
        try:
            if not isinstance(conversations, list):
                 logging.error(f"Invalid data type for analysis: expected list, got {type(conversations)}")
                 raise TypeError("Invalid data type for analysis")
                 
            try:
                 conversations_dataframe = pd.DataFrame(conversations)
                 logging.info(f"Converted list to DataFrame with shape: {conversations_dataframe.shape}")
            except Exception as df_err:
                 logging.error(f"Failed to create DataFrame from conversations list: {df_err}", exc_info=True)
                 raise ValueError("Could not process conversation data into DataFrame")

            analysis_result = self.analyzer.analyze_sentiment_over_time(
                conversations_df=conversations_dataframe, 
                conversations_with_transcripts=conversations
            )
            
        except AttributeError as ae:
             logging.error(f"AttributeError calling analyzer method - Expected method 'analyze_sentiment_over_time' on {type(self.analyzer)} object. Error: {ae}", exc_info=True)
             raise 
        except TypeError as te:
             logging.error(f"TypeError calling analyzer method 'analyze_sentiment_over_time'. Check arguments. Error: {te}", exc_info=True)
             raise
        except Exception as analysis_err:
             logging.error(f"Error during core analysis: {analysis_err}", exc_info=True)
             raise 

        # Removed manual cache set
        return analysis_result
    
    def get_categorized_themes(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches categorized themes (Common Questions, Concerns) based on message snippets
        within a given date range.

        Args:
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).

        Returns:
            Dictionary containing categorized results.
            Example: {
                'common_questions': [{'category': '...', 'count': ..., 'examples': [...]}, ...],
                'concerns_skepticism': [{'category': '...', 'count': ..., 'examples': [...]}, ...],
                'other_analysis': {} # Placeholder for future additions
            }
        """
        logging.info(f"AnalysisService: Getting categorized themes (start: {start_date}, end: {end_date})")
        
        # --- Define Categories and their Keywords/Patterns ---
        # Using similar structure as ConversationAnalyzer for consistency
        common_question_keywords = {
            'Love & Relationships': ['love', 'relationship', 'boyfriend', 'girlfriend', 'partner', 'marriage', 'divorce',
                                  'dating', 'ex', 'husband', 'wife', 'breakup', 'soulmate', 'twin flame', 'romance', 
                                  'romantic', 'affair', 'crush', 'connection'],
            'Career & Finances': ['job', 'career', 'money', 'work', 'business', 'financial', 'finance', 'salary', 'promotion',
                           'interview', 'application', 'boss', 'workplace', 'income', 'debt', 'investment', 'retirement',
                           'savings', 'profession', 'opportunity', 'success'],
            'Family & Children': ['family', 'mother', 'father', 'sister', 'brother', 'daughter', 'son', 'parent', 'child',
                     'grandparent', 'relative', 'sibling', 'aunt', 'uncle', 'cousin', 'in-law', 'adoption',
                     'pregnant', 'pregnancy', 'baby', 'children'],
            'Future Predictions': ['future', 'prediction', 'happen', 'will i', 'going to', 'forecast', 'destiny', 'fate',
                      'path', 'timeline', 'when will', 'outcome', 'result', 'eventually', 'someday'],
            'Psychic Source Services': [
                'number', 'phone', 'toll-free', 'international', 'website', 'app', 'account', 'login', 'membership',
                'credit', 'subscription', 'sign up', 'register', 'access',
                'price', 'cost', 'fee', 'charge', 'minute', 'package', 'special', 'discount', 'offer', 'promotion',
                'how long', 'duration', 'schedule', 'appointment', 'booking', 'available', 'time slot', 'reservation',
                'reader', 'advisor', 'psychic', 'specialist', 'recommend', 'suggestion', 'best for', 'top', 'profile',
                'extension', 'review', 'rating', 'feedback', 'experienced', 'popular', 'good at', 'specialized',
                'problem', 'issue', 'error', 'trouble', 'help', 'assist', 'support', 'connect', 'payment', 'receipt',
                'transaction', 'refund', 'credit card', 'billing', 'statement', 'email', 'contact us'
            ],
            'Spiritual & Metaphysical Concepts': ['spirit', 'energy', 'aura', 'chakra', 'meditation', 'vibration', 'frequency',
                                 'cleansing', 'sage', 'crystal', 'ritual', 'blessing', 'prayer', 'guardian angel',
                                 'spirit guide', 'intuition', 'empath', 'clairvoyant', 'psychic ability', 'universe',
                                 'manifestation', 'law of attraction', 'karma', 'past life', 'reincarnation', 'soul'],
            'Health & Wellness': ['health', 'wellness', 'medical', 'doctor', 'therapy', 'healing', 'illness', 'disease',
                              'condition', 'symptom', 'diagnosis', 'recovery', 'treatment', 'medicine', 'surgery',
                              'mental health', 'depression', 'anxiety', 'stress', 'sleep', 'diet', 'exercise', 'pain',
                              'addiction', 'weight', 'nutrition', 'wellbeing']
        }

        # Keywords/patterns for concerns and skepticism
        concerns_keywords = {
             'General Concerns': ['worry', 'worried', 'concern', 'concerned', 'anxious', 'nervous', 'afraid', 'scared', 'confused',
                              'unsure', 'doubt', 'hesitant', 'problem', 'issue', 'difficult', 'hard', 'stuck', 'lost', 'overwhelmed'],
             'Doubts about Readings': ['really work', 'accurate', 'true', 'possible', 'skeptical', 'believe', 'proof',
                                  'evidence', 'real', 'genuine', 'how do you know', 'sure about this', 'convinced', 'skepticism'],
             'Skepticism about Process': ['scam', 'fraud', 'trick', 'fake', 'rip off', 'waste of money', 'fortune teller', 'cold reading',
                                     'general', 'vague', 'barnum', 'expensive', 'worth it', 'make this up', 'not sure']
        }
        
        # Speakers to target (usually the user/caller)
        user_speakers = ['User', 'Curious Caller']
        
        # --- Fetch Snippets for Each Category --- 
        common_questions_results = []
        try:
            # Combine all keywords for common questions into one list
            all_q_keywords = [kw for sublist in common_question_keywords.values() for kw in sublist]
            # Add pattern for question mark
            q_patterns = ['%?%'] 
            
            logging.info(f"Fetching common question snippets...")
            question_snippets = current_app.conversation_service.get_relevant_message_snippets(
                start_date=start_date, end_date=end_date,
                keywords=all_q_keywords, 
                patterns=q_patterns,
                speaker_filter=['user'], # Correct speaker filter
                limit_per_conv=3 # Get a few examples per conversation
            )
            logging.info(f"Found {len(question_snippets)} raw question snippets.")
            
            # --- Post-process and categorize questions --- 
            # This simple categorization might be enough for display
            categorized_questions = {cat_name: [] for cat_name in common_question_keywords.keys()}
            other_questions = []

            for snippet in question_snippets:
                text = snippet['text'].lower()
                categorized = False
                for cat_name, keywords in common_question_keywords.items():
                    if any(word.lower() in text for word in keywords):
                         categorized_questions[cat_name].append(snippet)
                         categorized = True
                         break # Assign to first matching category
                if not categorized:
                     # Check for question mark for generic questions
                     if '?' in text:
                        other_questions.append(snippet)
                    # Else, discard snippets that don't match keywords or have ' ?'
            
            # Add the 'Other Questions' category if it has items
            if other_questions:
                 categorized_questions['Other Questions'] = other_questions
            
            # Format for response
            for cat_name, snippets in categorized_questions.items():
                if snippets:
                    common_questions_results.append({
                        'category': cat_name,
                        'count': len(snippets), # Count snippets found for this category
                        'examples': snippets # Return the actual snippets
                    })
            # Sort by count
            common_questions_results = sorted(common_questions_results, key=lambda x: x['count'], reverse=True)

        except Exception as e:
             logging.error(f"Error processing common questions: {e}", exc_info=True)
             common_questions_results = [] # Ensure it's an empty list on error
             
        concerns_skepticism_results = []
        try:
            # Combine all keywords for concerns
            all_c_keywords = [kw for sublist in concerns_keywords.values() for kw in sublist]
            logging.info(f"Fetching concern/skepticism snippets...")
            concern_snippets = current_app.conversation_service.get_relevant_message_snippets(
                 start_date=start_date, end_date=end_date,
                 keywords=all_c_keywords,
                 patterns=None, # No specific pattern needed here usually
                 speaker_filter=['user'], # Correct speaker filter
                 limit_per_conv=3
            )
            logging.info(f"Found {len(concern_snippets)} raw concern snippets.")

            # --- Post-process and categorize concerns --- 
            categorized_concerns = {cat_name: [] for cat_name in concerns_keywords.keys()}
            other_concerns = [] # Placeholder if needed

            for snippet in concern_snippets:
                 text = snippet['text'].lower()
                 categorized = False
                 for cat_name, keywords in concerns_keywords.items():
                     if any(word.lower() in text for word in keywords):
                          categorized_concerns[cat_name].append(snippet)
                          categorized = True
                          break
                 # Optionally add to an 'Other Concerns' if needed
                 # if not categorized: other_concerns.append(snippet)
            
            # Format for response
            for cat_name, snippets in categorized_concerns.items():
                if snippets:
                    concerns_skepticism_results.append({
                        'category': cat_name,
                        'count': len(snippets),
                        'examples': snippets
                    })
            # Sort by count
            concerns_skepticism_results = sorted(concerns_skepticism_results, key=lambda x: x['count'], reverse=True)

        except Exception as e:
             logging.error(f"Error processing concerns/skepticism: {e}", exc_info=True)
             concerns_skepticism_results = []
        
        # --- Assemble Final Result --- 
        final_result = {
            'common_questions': common_questions_results,
            'concerns_skepticism': concerns_skepticism_results,
            'other_analysis': {} # Placeholder
        }
        
        logging.info(f"AnalysisService: Finished getting categorized themes. Found {len(common_questions_results)} question categories and {len(concerns_skepticism_results)} concern categories.")
        return final_result
    
    def get_transcripts_for_conversations(self, conversation_ids):
        """
        Efficiently fetch transcripts for multiple conversations
        
        Args:
            conversation_ids: List of conversation IDs
            
        Returns:
            dict: Mapping of conversation_id to full conversation data with transcript
        """
        logging.info(f"Fetching transcripts for {len(conversation_ids)} conversations")
        
        result = {}
        successful_fetches = 0 # Counter for successful fetches
        errors = [] # List to store errors
        for conv_id in conversation_ids:
            # --- Add Logging --- 
            logging.info(f"Processing conv_id: {conv_id} (Type: {type(conv_id)})")
            # --- End Logging ---
            if not conv_id:
                continue
            # --- ENSURE conv_id IS STRING --- 
            conv_id_str = str(conv_id)
            try:
                # --- ADD DETAILED LOG --- 
                logging.info(f"[AnalysisService] Attempting to get details for string ID: '{conv_id_str}'")
                # Ensure conversation_service is accessed correctly via current_app
                # Pass the string version of the ID
                conv_data = current_app.conversation_service.get_conversation_details(conv_id_str)
                # --- Log after call ---
                logging.info(f"[AnalysisService] Call finished for ID: '{conv_id_str}'. Result type: {type(conv_data)}")
                
                if conv_data and 'transcript' in conv_data and conv_data.get('transcript'):
                    result[conv_id_str] = conv_data # Use string ID as key
                    successful_fetches += 1 # Increment counter
                    logging.debug(f"Successfully retrieved transcript for conversation {conv_id_str}")
                elif conv_data and 'error' in conv_data:
                     logging.warning(f"Service error getting transcript for conversation {conv_id_str}: {conv_data['error']}")
                else:
                    logging.warning(f"No transcript data found or returned for conversation {conv_id_str}")

            except Exception as e:
                # --- ADD ROLLBACK ---
                try:
                    from app.extensions import db
                    db.session.rollback()
                    logging.warning(f"Rolled back session after error getting transcript for {conv_id}")
                except Exception as rb_exc:
                     logging.error(f"Error during rollback after transcript fetch failure for {conv_id}: {rb_exc}")
                
                # Log the specific conversation ID that failed along with the error
                # Use traceback to get more context if needed
                error_trace = traceback.format_exc() 
                logging.warning(f"Service error getting transcript for conversation {conv_id}: {e}\\nTrace: {error_trace}")
                errors.append({'conversation_id': conv_id, 'error': str(e)})
                continue # Continue to the next conversation ID
                
        # Use the counter in the log message
        logging.info(f"Finished fetching transcripts. Successfully retrieved {successful_fetches}/{len(conversation_ids)}.")
        if errors:
            logging.warning(f"Errors occurred during transcript fetching: {errors}")
        return result
        
    def _extract_themes(self, df):
        """
        Extract themes/topics from conversations and their associated sentiment.
        
        Args:
            df: DataFrame of conversations
            
        Returns:
            dict: Top themes and sentiment by theme
        """
        try:
            logging.info(f"Starting theme extraction from {len(df)} conversations")
            
            # Check if we have conversation_id column - necessary for retrieving full data
            if 'conversation_id' not in df.columns:
                logging.warning("DataFrame doesn't have conversation_id column - can't fetch transcripts")
                return {
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
                
            # Get unique conversation IDs to fetch transcripts
            conversation_ids = df['conversation_id'].unique().tolist()
            logging.info(f"Found {len(conversation_ids)} unique conversation IDs")
            
            # Enhanced logging of conversation IDs
            if conversation_ids:
                logging.info(f"First few conversation IDs for theme extraction: {conversation_ids[:5]}")
                logging.info(f"Total number of unique conversation IDs: {len(set(conversation_ids))}")
            
            # Fetch all conversation data in a single batch for efficiency
            conversation_map = self.get_transcripts_for_conversations(conversation_ids)
            conversations_with_transcripts = list(conversation_map.values())
            
            # More detailed logging about transcripts
            total_turns = sum(len(conv.get('transcript', [])) for conv in conversations_with_transcripts)
            logging.info(f"Found {len(conversations_with_transcripts)} conversations with transcripts, total of {total_turns} turns")
            
            if not conversations_with_transcripts:
                logging.warning("No conversations with transcripts found")
                return {
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
            
            # Use unified theme and sentiment analysis to get consistent counts
            logging.info("Using unified_theme_sentiment_analysis for more accurate results")
            unified_results = self.analyzer.unified_theme_sentiment_analysis(conversations_with_transcripts)
            
            # Extract themes and sentiment correlations from unified results
            top_themes = unified_results.get('themes', [])
            sentiment_by_theme = unified_results.get('correlations', [])
            
            # Log results
            logging.info(f"Unified analysis extracted {len(top_themes)} themes and {len(sentiment_by_theme)} sentiment correlations")
            
            # Still get other metrics separately
            # Extract common questions
            logging.info("Calling extract_common_questions with conversation transcripts")
            common_questions = self.analyzer.extract_common_questions(conversations_with_transcripts)
            logging.info(f"Extracted {len(common_questions)} common question categories")
            
            # Extract concerns and skepticism
            logging.info("Calling extract_concerns_and_skepticism with conversation transcripts")
            concerns_skepticism = self.analyzer.extract_concerns_and_skepticism(conversations_with_transcripts)
            logging.info(f"Extracted {len(concerns_skepticism)} concern/skepticism categories")
            
            # Extract positive interactions
            logging.info("Calling extract_positive_interactions with conversation transcripts")
            positive_interactions = self.analyzer.extract_positive_interactions(conversations_with_transcripts)
            logging.info(f"Extracted {len(positive_interactions)} positive interactions")
            
            # Log the complete results
            logging.info(f"Analysis complete: {len(top_themes)} themes, {len(sentiment_by_theme)} theme-sentiment correlations, " +
                        f"{len(common_questions)} question categories, {len(concerns_skepticism)} concern categories, " +
                        f"and {len(positive_interactions)} positive interactions")
            
            return {
                'top_themes': top_themes,
                'sentiment_by_theme': sentiment_by_theme,
                'common_questions': common_questions,
                'concerns_skepticism': concerns_skepticism,
                'positive_interactions': positive_interactions
            }
            
        except Exception as e:
            logging.error(f"Error extracting themes: {e}")
            logging.error(traceback.format_exc())
            # Return empty results on error
            return {
                'top_themes': [],
                'sentiment_by_theme': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': []
            }
    
    # --- NEW Method for Comprehensive Analysis --- 
    def get_full_themes_sentiment_analysis(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Performs a comprehensive analysis including themes, sentiment, trends,
        common questions, concerns, and positive interactions for conversations
        within a specified date range. Fetches conversations directly using the conversation service.

        Args:
            start_date: Start date string (YYYY-MM-DD).
            end_date: End date string (YYYY-MM-DD).

        Returns:
            Dictionary containing the full analysis results.
        """
        logging.info(f"Starting full themes/sentiment analysis from {start_date} to {end_date}")
        
        # >>> ADD Check if analyzer is None early on <<<
        if self.analyzer is None:
            logging.error("AnalysisService cannot perform full analysis because ConversationAnalyzer is not available (failed to initialize?).")
            # Return default empty structure
            return {
                'sentiment_overview': { 'caller_avg': 0, 'agent_avg': 0, 'distribution': {'positive': 0, 'negative': 0, 'neutral': 0} },
                'top_themes': [],
                'sentiment_trends': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': []
            }

        # Define the structure for results, including keys for all expected analyses
        results = {
            'sentiment_overview': { # Placeholder for averages and ratios
                'avg_caller_sentiment': 0,
                'avg_agent_sentiment': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'neutral_ratio': 0
            },
            'top_themes': [],
            'sentiment_trends': [],
            'common_questions': [],
            'concerns_skepticism': [],
            'positive_interactions': []
            # Add other keys if more analyses are included
        }
        
        # Ensure the analyzer is available before proceeding
        if not self.analyzer:
            logging.error("Cannot perform full analysis: ConversationAnalyzer is not initialized.")
            return results # Return default empty results

        try:
            # Fetch conversations with transcripts directly using the conversation service
            # Limit to 100 conversations for performance, adjust as needed
            conversation_data = self.conversation_service.get_conversations(
                start_date=start_date, 
                end_date=end_date, 
                limit=100 # TODO: Make limit configurable?
            )
            
            conversations_with_transcripts = conversation_data.get('conversations', [])
            total_found = conversation_data.get('total_count', 0)
            
            logging.info(f"Fetched {len(conversations_with_transcripts)} conversations (out of {total_found} total) for analysis.")

            if not conversations_with_transcripts:
                logging.warning(f"No conversations with transcripts found between {start_date} and {end_date}")
                return results # Return empty results if no data
            
            # --- Start Analysis --- 
            logging.info("--- Starting analysis steps ---")
            
            # Calculate sentiment overview (uses helper method)
            sentiment_data = self._calculate_sentiment_overview(conversations_with_transcripts)
            logging.info(f"Step 1: Sentiment Overview calculated: {sentiment_data}")
            results['sentiment_overview'] = sentiment_data
            
            # Extract top themes (using ConversationAnalyzer)
            themes = self.analyzer.extract_themes(conversations_with_transcripts)
            logging.info(f"Step 2: Top Themes extracted: Count={len(themes) if themes else 0}")
            results['top_themes'] = themes[:20] if themes else []  # Limit to top 20 themes
            
            # Generate basic sentiment trends over time (uses helper method)
            trends = self._generate_sentiment_trends(conversations_with_transcripts)
            logging.info(f"Step 3: Sentiment Trends generated: Count={len(trends) if trends else 0}")
            results['sentiment_trends'] = trends
            
            # Extract common questions (using ConversationAnalyzer)
            questions = self.analyzer.extract_common_questions(conversations_with_transcripts)
            logging.info(f"Step 4: Common Questions extracted: Count={len(questions) if questions else 0}")
            results['common_questions'] = questions
            
            # Extract concerns and skepticism (using ConversationAnalyzer)
            concerns = self.analyzer.extract_concerns(conversations_with_transcripts)
            logging.info(f"Step 5: Concerns extracted: Count={len(concerns) if concerns else 0}")
            results['concerns_skepticism'] = concerns
            
            # Extract positive interactions (using ConversationAnalyzer)
            positive = self.analyzer.extract_positive_interactions(conversations_with_transcripts)
            logging.info(f"Step 6: Positive Interactions extracted: Count={len(positive) if positive else 0}")
            results['positive_interactions'] = positive
            
            logging.info("--- Finished analysis steps ---")
            
        except Exception as e:
            logging.error(f"Error during get_full_themes_sentiment_analysis: {str(e)}", exc_info=True)
            # Don't re-raise, return the partially filled results or empty structure
        
        logging.info(f"Completed full themes/sentiment analysis from {start_date} to {end_date}")
        return results
    
    def _calculate_sentiment_overview(self, conversations):
        """Helper to calculate sentiment overview statistics"""
        try:
            total_caller = 0
            total_agent = 0
            caller_count = 0
            agent_count = 0
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for conv in conversations:
                transcript = conv.get('transcript', [])
                for msg in transcript:
                    # Determine if this is a user/caller message
                    is_user = False
                    if 'role' in msg:
                        is_user = msg['role'] == 'user'
                    elif 'speaker' in msg:
                        is_user = msg['speaker'] in ['User', 'Curious Caller']
                    
                    # Get the text content from the message, flexible key lookup
                    text = None
                    for key in ['content', 'text', 'message']:
                        if key in msg and msg[key]:
                            text = msg[key]
                            break
                            
                    if not text:
                        continue
                        
                    # Use analyze_sentiment_for_text instead of analyze_sentiment for string input
                    sentiment = self.analyzer.analyze_sentiment_for_text(text)
                    
                    # Update counters based on sentiment
                    if sentiment > 0.1:
                        positive_count += 1
                    elif sentiment < -0.1:
                        negative_count += 1
                    else:
                        neutral_count += 1
                        
                    # Update speaker-specific sentiment
                    if is_user:
                        total_caller += sentiment
                        caller_count += 1
                    else:
                        total_agent += sentiment
                        agent_count += 1
            
            # Calculate averages and ratios
            total_messages = caller_count + agent_count
            if total_messages == 0:
                return {
                    'avg_caller_sentiment': 0,
                    'avg_agent_sentiment': 0,
                    'positive_ratio': 0,
                    'negative_ratio': 0,
                    'neutral_ratio': 0
                }
                
            return {
                'avg_caller_sentiment': total_caller / caller_count if caller_count > 0 else 0,
                'avg_agent_sentiment': total_agent / agent_count if agent_count > 0 else 0,
                'positive_ratio': positive_count / total_messages,
                'negative_ratio': negative_count / total_messages,
                'neutral_ratio': neutral_count / total_messages
            }
            
        except Exception as e:
            logging.error(f"Error in _calculate_sentiment_overview: {e}", exc_info=True)
            return {
                'avg_caller_sentiment': 0,
                'avg_agent_sentiment': 0,
                'positive_ratio': 0,
                'negative_ratio': 0,
                'neutral_ratio': 0
            }
        
    def _generate_sentiment_trends(self, conversations):
        """Helper to generate basic sentiment trends over time"""
        try:
            # Group conversations by day
            conversations_by_day = {}
            
            for conv in conversations:
                # Handle various date formats
                start_time = None
                if 'start_time' in conv and conv['start_time']:
                    start_time = conv['start_time']
                elif 'created_at' in conv and conv['created_at']:
                    start_time = conv['created_at']
                    
                if not start_time:
                    continue
                    
                # Convert string date to 'YYYY-MM-DD' format
                if isinstance(start_time, str):
                    if 'T' in start_time:  # ISO format
                        day = start_time.split('T')[0]
                    elif ' ' in start_time:  # Some other format with space
                        day = start_time.split(' ')[0]
                    else:
                        day = start_time[:10]  # Take first 10 chars
                else:
                    # Handle datetime object
                    day = start_time.strftime('%Y-%m-%d')
                
                if day not in conversations_by_day:
                    conversations_by_day[day] = []
                conversations_by_day[day].append(conv)
            
            # Calculate average sentiment for each day
            trends = []
            for day, convs in conversations_by_day.items():
                total_sentiment = 0
                message_count = 0
                
                for conv in convs:
                    # Get transcript safely
                    transcript = conv.get('transcript', [])
                    
                    for msg in transcript:
                        # Extract text content flexibly
                        text = None
                        for key in ['content', 'text', 'message']:
                            if key in msg and msg[key]:
                                text = msg[key]
                                break
                                
                        if text:
                            sentiment = self.analyzer.analyze_sentiment_for_text(text)
                            total_sentiment += sentiment
                            message_count += 1
                
                # Only add if we have messages
                if message_count > 0:
                    avg_sentiment = total_sentiment / message_count
                    trends.append({
                        'date': day,
                        'sentiment': float(avg_sentiment)
                    })
            
            # Sort by date
            trends.sort(key=lambda x: x['date'])
            
            return trends
            
        except Exception as e:
            logging.error(f"Error in _generate_sentiment_trends: {e}", exc_info=True)
            return []

    def analyze_themes_and_sentiment(self, start_date, end_date, max_conversations=500):
        """
        Analyze themes and sentiment across conversations within a date range.
        
        Args:
            start_date: Start date in ISO format string (e.g., "2023-10-26")
            end_date: End date in ISO format string (e.g., "2023-10-27")
            max_conversations: Maximum number of conversations to analyze (default: 500)
            
        Returns:
            Dict containing analysis results
        """
        start_time = time.time()
        
        # Removed manual cache check
        logging.warning("analyze_themes_and_sentiment is NOT currently cached.")
                
        logging.info(f"Performing themes and sentiment analysis for date range: {start_date} to {end_date}")
        
        # Use the injected conversation service directly
        try:
             conversation_ids_result = self.conversation_service.get_conversation_ids(start_date=start_date, end_date=end_date, limit=max_conversations)
             # Assuming the service returns a list of IDs directly or under a key like 'conversation_ids'
             if isinstance(conversation_ids_result, list):
                  conversation_ids = conversation_ids_result
             elif isinstance(conversation_ids_result, dict) and 'conversation_ids' in conversation_ids_result:
                  conversation_ids = conversation_ids_result['conversation_ids']
             else:
                  logging.error(f"Unexpected format from conversation_service.get_conversation_ids: {type(conversation_ids_result)}")
                  conversation_ids = []
        except Exception as e:
             logging.error(f"Error getting conversation IDs via service: {e}", exc_info=True)
             conversation_ids = []

        # Get conversations with transcripts using the injected service
        try:
             # Adapt based on the actual method name and expected return format of the injected service
             # Example: Assuming get_conversations_by_ids exists and returns {'conversations': [...]}
             conversations_result = self.conversation_service.get_conversations_by_ids(conversation_ids)
             if isinstance(conversations_result, list):
                 conversations = conversations_result
             elif isinstance(conversations_result, dict) and 'conversations' in conversations_result:
                 conversations = conversations_result['conversations']
             else:
                  logging.error(f"Unexpected format from conversation_service method for getting transcripts: {type(conversations_result)}")
                  conversations = []
        except Exception as e:
             logging.error(f"Error getting transcripts via service: {e}", exc_info=True)
             conversations = []
             
        # ... (rest of analysis logic) ...

        # Removed manual cache set
        
        logging.info(f"Completed themes and sentiment analysis in {time.time() - start_time:.2f}s")
        return analysis_results 