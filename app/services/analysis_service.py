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
import openai # Added for query embedding

# Import the conversation service we need
from app.services.supabase_conversation_service import SupabaseConversationService

# --- Helper function for OpenAI Embedding ---
# Re-defined here, consider moving to a shared util later
def _get_openai_embedding(text, client, model="text-embedding-3-small"):
    if not client or not text:
        logging.debug("AnalysisService: Skipping embedding generation - no client or text.")
        return None
    try:
        response = client.embeddings.create(model=model, input=text)
        if response.data and len(response.data) > 0:
            logging.debug(f"AnalysisService: Successfully generated embedding for query snippet '{str(text)[:50]}...'.")
            return response.data[0].embedding
        else:
            logging.error("AnalysisService: OpenAI embedding response format unexpected or empty.")
            return None
    except Exception as e:
        logging.error(f"AnalysisService: Failed to get embedding from OpenAI for query snippet '{str(text)[:50]}...': {e}")
        return None
# --- End Helper Function ---

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
            
            # >>> Check for successful OpenAI client init within analyzer <<<
            # Use the analyzer's own 'use_llm' flag which indicates successful init
            if not self.lightweight_mode and (not hasattr(self.analyzer, 'use_llm') or not self.analyzer.use_llm):
                logging.warning("ConversationAnalyzer indicates LLM is not usable (failed init or no key). Service limited.")
                # Keep the analyzer instance, but recognize its LLM capabilities are off
                # self.analyzer = None # Don't set to None, let it use fallback methods if needed
                
        except Exception as e:
            logging.error(f"Error initializing ConversationAnalyzer in AnalysisService: {e}", exc_info=True)
            self.analyzer = None # Set to None if the whole class init fails
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
                logging.warning(f"Service error getting transcript for conversation {conv_id}: {e}\nTrace: {error_trace}")
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
        Fetches conversations for the date range and performs full analysis using RAG,
        returning a structure suitable for the themes/sentiment page.

        Handles caching:
            - Uses Flask-Caching with a FileSystemCache.
            - Cache key is based on start/end dates.
            - Default timeout is 3600 seconds (1 hour).
            - Returns cached result immediately if available.
        """
        start_time = time.time()
        logging.info(f"Starting RAG-based full themes & sentiment analysis for {start_date} to {end_date}")

        # Define cache key based on dates
        cache_key = f'themes_sentiment_rag_{start_date}_{end_date}' # Updated key prefix

        # Try fetching from cache first
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logging.info(f"Returning cached RAG themes/sentiment data for {start_date}-{end_date}")
                # Add model name check like before, but maybe from a central place later
                if 'analysis_status' not in cached_result:
                     cached_result['analysis_status'] = {}
                if 'model_name' not in cached_result['analysis_status']:
                    # Assume consistent model for RAG for now
                    cached_result['analysis_status']['model_name'] = getattr(self.analyzer, 'model_name', 'N/A') if self.analyzer else 'N/A'
                return cached_result

        # --- RAG-based Analysis ---
        analysis_result = {}
        error_occurred = False
        error_message = "Analysis failed"
        model_name_used = getattr(self.analyzer, 'model_name', 'N/A') if self.analyzer else 'N/A'
        # Need total count for metadata - fetch this separately now
        total_conversations_in_range = 0
        try:
            # --- Log the dates being passed --- 
            logging.info(f"RAG Analysis: Fetching count for date range: START='{start_date}', END='{end_date}'")
            # --- End Log ---
            count_result = self.conversation_service.get_conversation_count(start_date=start_date, end_date=end_date)
            # Correctly assign the integer result
            total_conversations_in_range = count_result
            logging.info(f"Total conversations found in range: {total_conversations_in_range}")
        except Exception as count_err:
             logging.error(f"Error fetching conversation count: {count_err}", exc_info=True)
             error_occurred = True
             error_message = f"Failed to get conversation count: {str(count_err)}"
             total_conversations_in_range = 0 # Set to 0 on error

        if not self.analyzer or not self.conversation_service:
             logging.error("AnalysisService prerequisites (analyzer or conversation_service) not met for RAG analysis.")
             error_occurred = True
             error_message = "Analysis prerequisites not met."
             # Use the empty result helper, ensuring total_count is passed
             analysis_result = self.analyzer._empty_analysis_result(start_date, end_date, error_message, total_conversations_in_range) if self.analyzer else {}

        if not error_occurred:
            try:
                logging.info("Performing RAG analysis for each section...")

                # Placeholder calls to internal RAG methods
                sentiment_overview = self._get_rag_sentiment_overview(start_date, end_date)
                top_themes = self._get_rag_top_themes(start_date, end_date)
                sentiment_trends = self._get_rag_sentiment_trends(start_date, end_date)
                # theme_sentiment_correlation depends on top_themes
                theme_sentiment_correlation = self._get_rag_theme_sentiment_correlation(start_date, end_date, top_themes.get('themes', []))
                categorized_quotes = self._get_rag_categorized_quotes(start_date, end_date)

                # Basic error checking for each part (can be more robust)
                if any(part is None or 'error' in part for part in [sentiment_overview, top_themes, sentiment_trends, theme_sentiment_correlation, categorized_quotes]):
                     logging.error("Error occurred in one or more RAG analysis sub-tasks.")
                     # Find the first error message if possible
                     first_error = next((part.get('error', 'Unknown error') for part in [sentiment_overview, top_themes, sentiment_trends, theme_sentiment_correlation, categorized_quotes] if part and 'error' in part), 'Error in RAG sub-task')
                     raise ValueError(first_error)


                # --- Assemble Final Result ---
                analysis_result = {
                    "metadata": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "total_conversations_in_range": total_conversations_in_range
                    },
                    "sentiment_overview": sentiment_overview,
                    "top_themes": top_themes,
                    "sentiment_trends": sentiment_trends,
                    "theme_sentiment_correlation": theme_sentiment_correlation,
                    "categorized_quotes": categorized_quotes,
                    "analysis_status": {
                        "mode": "RAG",
                        "message": "Analysis complete using RAG.",
                        "model_name": model_name_used # Store the model name used
                    }
                }
                logging.info("Successfully assembled results from RAG analysis sub-tasks.")

            except Exception as e:
                logging.error(f"Error during RAG analysis orchestration: {e}", exc_info=True)
                error_occurred = True
                error_message = f"RAG Analysis Error: {str(e)}"
                # Populate with empty structure on error
                analysis_result = self.analyzer._empty_analysis_result(start_date, end_date, error_message, total_conversations_in_range) if self.analyzer else {}


        # --- Original Data Fetching & Analysis (Commented Out) ---
        # try:
        #     logging.info(f"Fetching conversations via service for {start_date} to {end_date}")
        #     fetch_result = self.conversation_service.get_conversations(
        #         start_date=start_date,
        #         end_date=end_date,
        #         limit=10000 # Or adjust as needed
        #     )
        #     conversations = fetch_result.get('conversations', [])
        #     original_total_count = fetch_result.get('total_count', len(conversations))
        #     logging.info(f"Fetched {len(conversations)} conversations (out of {original_total_count} total) for analysis.")
        #
        # except Exception as e:
        #     logging.error(f"Error fetching conversation data via service: {e}", exc_info=True)
        #     # Return the standard empty structure on fetch error
        #     return self.analyzer._empty_analysis_result(start_date, end_date, f"Data Fetch Error: {str(e)}", 0) if self.analyzer else {"error": "Data Fetch Error and Analyzer unavailable"}
        #
        # # --- Analysis ---
        # if not self.analyzer:
        #     logging.error("ConversationAnalyzer not initialized, cannot perform analysis.")
        #     # Return the standard empty structure
        #     return self.analyzer._empty_analysis_result(start_date, end_date, "Analyzer Not Available", original_total_count)
        #
        # try:
        #     # The analyzer's unified method now returns the full structure including model name
        #     # This is the main analysis call, potentially long-running if not cached.
        #     analysis_result = self.analyzer.unified_llm_analysis(conversations, start_date, end_date, original_total_count)
        #     logging.info(f"Received analysis results from ConversationAnalyzer.")
        #
        #     # Error check (unified_llm_analysis returns {'error':...} on failure)
        #     if 'error' in analysis_result:
        #          logging.error(f"Analysis returned an error: {analysis_result.get('details', analysis_result['error'])}")
        #          # Return the error structure (which includes status) from the analyzer
        #          return analysis_result
        #
        # except Exception as e:
        #     logging.error(f"Unexpected error calling unified LLM analysis: {e}", exc_info=True)
        #     # Return the standard empty structure on unexpected error
        #     return self.analyzer._empty_analysis_result(start_date, end_date, f"Unexpected Analysis Error: {str(e)}", original_total_count)
        # --- End Commented Out Section ---

        # Cache the successful RAG result (or the error structure if generated above)
        if self.cache and not error_occurred: # Only cache successful RAG results
            cache_timeout = 3600
            self.cache.set(cache_key, analysis_result, timeout=cache_timeout)
            logging.info(f"Cached RAG themes/sentiment data for {start_date}-{end_date} with timeout {cache_timeout}s")
        elif error_occurred:
            logging.warning(f"RAG analysis failed for {start_date}-{end_date}. Returning error structure. Not caching.")
            # Ensure the returned structure indicates error
            if 'analysis_status' not in analysis_result:
                 analysis_result['analysis_status'] = {}
            analysis_result['analysis_status']['mode'] = "Error"
            analysis_result['analysis_status']['message'] = error_message
            analysis_result['analysis_status']['model_name'] = model_name_used # Keep model name if known

        end_time = time.time()
        logging.info(f"Completed RAG-based full themes & sentiment analysis attempt in {end_time - start_time:.2f} seconds. Status: {'Success' if not error_occurred else 'Failed'}")
        return analysis_result


    # --- Placeholder RAG methods to be implemented ---
    def _get_rag_sentiment_overview(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting sentiment overview (using full transcripts) for {start_date} to {end_date}")
        internal_query = "Overall sentiment and tone of conversations between psychic Lily and callers."

        expected_structure = {
            "overall_sentiment_label": "string (Positive/Neutral/Negative)",
            "sentiment_distribution": {"very_positive": "int", "positive": "int", "neutral": "int", "negative": "int", "very_negative": "int"},
            "caller_average_sentiment": "float (-1 to 1)",
            "agent_average_sentiment": "float (-1 to 1)"
        }

        # --- CONTEXT CONFIGURATION (Apply similar pattern) ---
        SEARCH_LIMIT = 15 
        CONTEXT_TRANSCRIPT_LIMIT = 10 # Limit transcripts used for this specific analysis
        MAX_CONTEXT_CHARS = 60000 
        # --- END CONFIGURATION ---
        
        try:
            # --- Prerequisites ---
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
                logging.error("RAG Sentiment Overview: OpenAI client not available.")
                return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized:
                logging.error("RAG Sentiment Overview: Conversation service not available.")
                return {'error': 'Conversation service unavailable'}

            openai_client = self.analyzer.openai_client

            # --- 1. Get Query Embedding ---
            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding:
                return {'error': 'Failed to get embedding for internal sentiment query'}

            # --- 2. Vector Search (Get Candidate IDs) ---
            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding,
                start_date=start_date,
                end_date=end_date,
                limit=SEARCH_LIMIT,
                similarity_threshold=threshold
            )

            if not similar_conversations_info:
                logging.warning(f"RAG Sentiment Overview: No relevant conversations found via vector search (limit={SEARCH_LIMIT}, threshold={threshold}). Returning default structure.")
                return {
                    "overall_sentiment_label": "Neutral",
                    "sentiment_distribution": {"very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0},
                    "caller_average_sentiment": 0.0,
                    "agent_average_sentiment": 0.0
                }

            logging.info(f"RAG Sentiment Overview: Found {len(similar_conversations_info)} candidate conversations via vector search.")

            # --- 3. Prepare FULL TRANSCRIPT Context --- 
            context = "\n\n---Retrieved Conversation Transcripts for Sentiment Analysis:---"
            context_char_count = 0
            conversations_used_count = 0
            ids_to_fetch = [conv.get('external_id') for conv in similar_conversations_info[:CONTEXT_TRANSCRIPT_LIMIT] if conv.get('external_id')]

            logging.info(f"RAG Sentiment Overview: Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")
            
            for external_id in ids_to_fetch:
                if context_char_count >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Sentiment Overview: Reached context character limit ({MAX_CONTEXT_CHARS}). Using {conversations_used_count} transcripts.")
                    break
                    
                details = self.conversation_service.get_conversation_details(external_id)
                if not details or not details.get('transcript'):
                    logging.warning(f"RAG Sentiment Overview: Could not fetch details or transcript for {external_id}. Skipping.")
                    continue
                    
                transcript_text = "\n"
                for msg in details.get('transcript', []):
                    speaker = msg.get('role', 'unknown').capitalize()
                    content = msg.get('content', '')
                    transcript_text += f"{speaker}: {content}\n"
                
                if context_char_count + len(transcript_text) >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Sentiment Overview: Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                    break 
                    
                context += f"\n--- Conversation {external_id} ---\n{transcript_text}--- End Conversation {external_id} ---"
                context_char_count += len(transcript_text)
                conversations_used_count += 1
                
            if conversations_used_count == 0:
                 logging.error("RAG Sentiment Overview: Failed to build any context from transcripts. Aborting.")
                 # Return default neutral structure if context fails
                 return {
                    "overall_sentiment_label": "Neutral",
                    "sentiment_distribution": {"very_positive": 0, "positive": 0, "neutral": 0, "negative": 0, "very_negative": 0},
                    "caller_average_sentiment": 0.0,
                    "agent_average_sentiment": 0.0
                 }
                 
            logging.info(f"RAG Sentiment Overview: Built context using {conversations_used_count} full transcripts (~{context_char_count} chars).")

            # --- 4. Construct LLM Prompt ---
            system_prompt = (
                 f"You are an expert conversation analyst. Analyze the provided FULL CONVERSATION TRANSCRIPTS (between psychic Lily and callers) "
                 f"to determine the overall sentiment overview for the period {start_date} to {end_date}. "
                 f"Focus *only* on the provided transcripts. Calculate aggregate sentiment metrics. "
                 f"Return ONLY a valid JSON object with the following structure and data types:\n"
                 f"```json\n{json.dumps(expected_structure, indent=2)}\n```"
                 f"Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts:\n{context}"

            # --- 5. Call LLM --- 
            logging.info(f"RAG Sentiment Overview (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # Low temp for factual extraction
                max_tokens=500 # Usually enough for this structure
            )

            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Sentiment Overview (Full Transcript): Received response from LLM.")

            # --- 6. Parse & Validate ---
            try:
                parsed_output = json.loads(llm_output_raw)
                # Add basic validation if needed (e.g., check keys)
                if not all(k in parsed_output for k in expected_structure.keys()):
                     logging.error(f"RAG Sentiment Overview (Full Transcript): LLM JSON missing expected keys. Got: {parsed_output.keys()}")
                     raise ValueError("LLM JSON structure mismatch")
                logging.info("RAG Sentiment Overview (Full Transcript): Successfully parsed LLM response.")
                return parsed_output
            except json.JSONDecodeError as e:
                 logging.error(f"RAG Sentiment Overview (Full Transcript): Failed to parse LLM JSON response: {e}")
                 logging.error(f"Raw response: {llm_output_raw}")
                 return {'error': f'Failed to parse LLM JSON for sentiment overview: {e}'}
            except ValueError as e:
                 logging.error(f"RAG Sentiment Overview (Full Transcript): LLM JSON validation failed: {e}")
                 return {'error': f'LLM JSON validation failed for sentiment overview: {e}'}

        except Exception as e:
            logging.error(f"RAG Sentiment Overview (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in sentiment overview: {str(e)}'}

    def _get_rag_top_themes(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting top themes (using full transcripts) for {start_date} to {end_date}")
        internal_query = "What are the main topics, subjects, or themes discussed in these conversations between psychic Lily and callers?"

        expected_structure = {
            "themes": [{"theme": "string", "count": "int"}] # List of theme objects, max 10, sorted by count desc
        }

        # --- CONTEXT CONFIGURATION ---
        # How many similar conversations to retrieve based on transcript embedding
        SEARCH_LIMIT = 20 
        # How many of the retrieved conversations' full transcripts to actually use for context
        # Adjust based on typical transcript length and token limits
        CONTEXT_TRANSCRIPT_LIMIT = 10 
        # Max estimated characters for combined transcript context (adjust based on model)
        MAX_CONTEXT_CHARS = 60000 # ~15k tokens estimate
        # --- END CONFIGURATION ---
        
        try:
            # --- Prerequisites ---
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
                logging.error("RAG Top Themes: OpenAI client not available.")
                return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized:
                logging.error("RAG Top Themes: Conversation service not available.")
                return {'error': 'Conversation service unavailable'}

            openai_client = self.analyzer.openai_client

            # --- 1. Get Query Embedding ---
            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding:
                return {'error': 'Failed to get embedding for internal themes query'}

            # --- 2. Vector Search (Get Candidate Conversation IDs) ---
            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding,
                start_date=start_date,
                end_date=end_date,
                limit=SEARCH_LIMIT,
                similarity_threshold=threshold
            )

            if not similar_conversations_info:
                logging.warning(f"RAG Top Themes: No relevant conversations found via vector search (limit={SEARCH_LIMIT}, threshold={threshold}). Returning empty list.")
                return {"themes": []} # Return structure with empty list

            logging.info(f"RAG Top Themes: Found {len(similar_conversations_info)} candidate conversations via vector search.")

            # --- 3. Prepare FULL TRANSCRIPT Context ---
            context = "\n\n---Retrieved Conversation Transcripts for Theme Analysis:---"
            context_char_count = 0
            conversations_used_count = 0
            
            # Limit the number of full transcripts we fetch/use
            ids_to_fetch = [conv.get('external_id') for conv in similar_conversations_info[:CONTEXT_TRANSCRIPT_LIMIT] if conv.get('external_id')] 
            
            logging.info(f"RAG Top Themes: Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")
            
            for external_id in ids_to_fetch:
                if context_char_count >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Top Themes: Reached context character limit ({MAX_CONTEXT_CHARS}). Using {conversations_used_count} transcripts.")
                    break
                    
                # Fetch full details including messages
                # NOTE: This is iterative and potentially slow. Consider batch fetching later.
                details = self.conversation_service.get_conversation_details(external_id)
                
                if not details or not details.get('transcript'):
                    logging.warning(f"RAG Top Themes: Could not fetch details or transcript for {external_id}. Skipping.")
                    continue
                    
                transcript_text = "\n"
                for msg in details.get('transcript', []):
                    speaker = msg.get('role', 'unknown').capitalize()
                    content = msg.get('content', '')
                    transcript_text += f"{speaker}: {content}\n"
                
                # Check if adding this transcript exceeds the limit
                if context_char_count + len(transcript_text) >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Top Themes: Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                    break # Stop adding transcripts
                    
                # Add transcript to context
                context += f"\n--- Conversation {external_id} ---\n{transcript_text}--- End Conversation {external_id} ---"
                context_char_count += len(transcript_text)
                conversations_used_count += 1
                
            if conversations_used_count == 0:
                 logging.error("RAG Top Themes: Failed to build any context from transcripts. Aborting.")
                 return {"themes": []} # Cannot proceed without context
                 
            logging.info(f"RAG Top Themes: Built context using {conversations_used_count} full transcripts (~{context_char_count} chars).")

            # --- 4. Construct LLM Prompt ---
            system_prompt = (
                 f"You are an expert conversation analyst. Analyze the provided FULL CONVERSATION TRANSCRIPTS (between psychic Lily and callers) "
                 f"from the period {start_date} to {end_date}. "
                 f"Identify the top 10 most frequently discussed themes or topics based *only* on these transcripts. Estimate the count (number of conversations mentioning the theme) for each theme. "
                 f"Return ONLY a valid JSON object with the following structure:\n"
                 f"```json\n{{\"themes\": [{{\"theme\": \"string\", \"count\": int}}, ...]}}\n```"
                 f"The list should be sorted in descending order by count. Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts:\n{context}"

            # --- 5. Call LLM ---
            logging.info(f"RAG Top Themes (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=800 # Allow more tokens for theme lists
            )

            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Top Themes (Full Transcript): Received response from LLM.")

            # --- 6. Parse & Validate (Logic remains the same) ---
            try:
                parsed_output = json.loads(llm_output_raw)
                # Basic validation
                if 'themes' not in parsed_output or not isinstance(parsed_output['themes'], list):
                     logging.error(f"RAG Top Themes (Full Transcript): LLM JSON missing 'themes' list. Got: {parsed_output}")
                     raise ValueError("LLM JSON structure mismatch (missing themes list)")
                # Optional: Check structure of items within the list
                for item in parsed_output['themes']:
                     if not isinstance(item, dict) or 'theme' not in item or 'count' not in item:
                          logging.warning(f"RAG Top Themes (Full Transcript): Invalid item in themes list: {item}")
                          # Decide whether to raise error or filter out invalid items
                          raise ValueError("Invalid item structure in themes list")

                logging.info("RAG Top Themes (Full Transcript): Successfully parsed LLM response.")
                return parsed_output # Should be dict like {"themes": [...]} 
            except json.JSONDecodeError as e:
                 logging.error(f"RAG Top Themes (Full Transcript): Failed to parse LLM JSON response: {e}")
                 logging.error(f"Raw response: {llm_output_raw}")
                 return {'error': f'Failed to parse LLM JSON for top themes: {e}'}
            except ValueError as e:
                 logging.error(f"RAG Top Themes (Full Transcript): LLM JSON validation failed: {e}")
                 return {'error': f'LLM JSON validation failed for top themes: {e}'}

        except Exception as e:
            logging.error(f"RAG Top Themes (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in top themes: {str(e)}'}

    def _get_rag_sentiment_trends(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting sentiment trends (using full transcripts) for {start_date} to {end_date}")
        internal_query = f"Analyze the sentiment progression day-by-day between {start_date} and {end_date} based on conversations between psychic Lily and callers."

        expected_structure = {
            "labels": ["YYYY-MM-DD"], # List of dates with activity
            "average_sentiment_scores": ["float (-1 to 1)"] # Corresponding daily average sentiment
        }

        # --- CONTEXT CONFIGURATION --- 
        # Might need more transcripts for trend estimation
        SEARCH_LIMIT = 30 
        CONTEXT_TRANSCRIPT_LIMIT = 15
        MAX_CONTEXT_CHARS = 80000 # Increase context slightly for trends
        # --- END CONFIGURATION ---
        
        try:
            # --- Prerequisites ---
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
                logging.error("RAG Sentiment Trends: OpenAI client not available.")
                return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized:
                logging.error("RAG Sentiment Trends: Conversation service not available.")
                return {'error': 'Conversation service unavailable'}

            openai_client = self.analyzer.openai_client

            # --- 1. Get Query Embedding ---
            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding:
                return {'error': 'Failed to get embedding for internal trends query'}

            # --- 2. Vector Search (Get Candidate IDs) ---
            threshold = 0.35 # Keep threshold consistent for now
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding,
                start_date=start_date,
                end_date=end_date,
                limit=SEARCH_LIMIT,
                similarity_threshold=threshold
            )

            if not similar_conversations_info:
                logging.warning(f"RAG Sentiment Trends: No relevant conversations found via vector search (limit={SEARCH_LIMIT}, threshold={threshold}). Returning empty structure.")
                return {"labels": [], "average_sentiment_scores": []} # Return structure with empty lists

            logging.info(f"RAG Sentiment Trends: Found {len(similar_conversations_info)} candidate conversations via vector search.")

            # --- 3. Prepare FULL TRANSCRIPT Context --- 
            context = "\n\n---Retrieved Conversation Transcripts for Trend Analysis:---"
            context_char_count = 0
            conversations_used_count = 0
            ids_to_fetch = [conv.get('external_id') for conv in similar_conversations_info[:CONTEXT_TRANSCRIPT_LIMIT] if conv.get('external_id')]
            
            logging.info(f"RAG Sentiment Trends: Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")
            
            for external_id in ids_to_fetch:
                if context_char_count >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Sentiment Trends: Reached context character limit ({MAX_CONTEXT_CHARS}). Using {conversations_used_count} transcripts.")
                    break
                    
                details = self.conversation_service.get_conversation_details(external_id)
                if not details or not details.get('transcript'):
                    logging.warning(f"RAG Sentiment Trends: Could not fetch details or transcript for {external_id}. Skipping.")
                    continue
                    
                transcript_text = "\n"
                # Prepend date to help LLM
                date_str = "Unknown Date"
                created_at = details.get('start_time') # Use start_time from details
                if created_at:
                    try:
                         date_str = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                         pass 
                transcript_text += f"Date: {date_str}\n"
                
                for msg in details.get('transcript', []):
                    speaker = msg.get('role', 'unknown').capitalize()
                    content = msg.get('content', '')
                    transcript_text += f"{speaker}: {content}\n"
                
                if context_char_count + len(transcript_text) >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Sentiment Trends: Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                    break 
                    
                context += f"\n--- Conversation {external_id} ---\n{transcript_text}--- End Conversation {external_id} ---"
                context_char_count += len(transcript_text)
                conversations_used_count += 1
                
            if conversations_used_count == 0:
                 logging.error("RAG Sentiment Trends: Failed to build any context from transcripts. Aborting.")
                 return {"labels": [], "average_sentiment_scores": []}
                 
            logging.info(f"RAG Sentiment Trends: Built context using {conversations_used_count} full transcripts (~{context_char_count} chars).")

            # --- 4. Construct LLM Prompt ---
            system_prompt = (
                 f"You are an expert conversation analyst. Based *only* on the provided sample of FULL CONVERSATION TRANSCRIPTS "
                 f"(between psychic Lily and callers) from the period {start_date} to {end_date}, estimate the daily average sentiment trend. "
                 f"Infer the trend from the content and associated dates of the transcripts. "
                 f"Return ONLY a valid JSON object with the following structure, including only dates within the range {start_date} to {end_date} that likely had conversations based on the transcripts:\n"
                 f"```json\n{{\"labels\": [\"YYYY-MM-DD\", ...], \"average_sentiment_scores\": [float, ...]}}\n```"
                 f"The lists must correspond (same length). Scores should be between -1 and 1. If no trend can be determined from the transcripts, return empty lists. Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts Sample:\n{context}"

            # --- 5. Call LLM ---
            logging.info(f"RAG Sentiment Trends (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2, # Slightly higher temp might help inference
                max_tokens=1000 # Allow space for date/score lists
            )

            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Sentiment Trends (Full Transcript): Received response from LLM.")

            # --- 6. Parse & Validate ---
            try:
                parsed_output = json.loads(llm_output_raw)
                # Basic validation
                if 'labels' not in parsed_output or 'average_sentiment_scores' not in parsed_output or \
                   not isinstance(parsed_output['labels'], list) or not isinstance(parsed_output['average_sentiment_scores'], list) or \
                   len(parsed_output['labels']) != len(parsed_output['average_sentiment_scores']):
                     logging.error(f"RAG Sentiment Trends (Full Transcript): LLM JSON invalid structure/mismatch. Got: {parsed_output}")
                     raise ValueError("LLM JSON structure mismatch for trends")

                logging.info("RAG Sentiment Trends (Full Transcript): Successfully parsed LLM response.")
                return parsed_output # Dict like {"labels": [...], "average_sentiment_scores": [...]} 
            except json.JSONDecodeError as e:
                 logging.error(f"RAG Sentiment Trends (Full Transcript): Failed to parse LLM JSON response: {e}")
                 logging.error(f"Raw response: {llm_output_raw}")
                 return {'error': f'Failed to parse LLM JSON for sentiment trends: {e}'}
            except ValueError as e:
                 logging.error(f"RAG Sentiment Trends (Full Transcript): LLM JSON validation failed: {e}")
                 return {'error': f'LLM JSON validation failed for sentiment trends: {e}'}

        except Exception as e:
            logging.error(f"RAG Sentiment Trends (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in sentiment trends: {str(e)}'}

    def _get_rag_theme_sentiment_correlation(self, start_date: str, end_date: str, top_themes: List[Dict]) -> Optional[List]:
        logging.info(f"RAG: Getting theme/sentiment correlation (using full transcripts) for {start_date} to {end_date}")
        
        # Check if we have themes to analyze
        if not top_themes:
            logging.warning("RAG Theme/Sentiment Corr: No top themes provided. Skipping correlation.")
            return [] # Return empty list as per expected structure
        
        theme_names = [t.get('theme', 'Unknown') for t in top_themes]
        internal_query = f"What is the general sentiment (Positive, Negative, Neutral, or Mixed) associated with each of these specific themes: {', '.join(theme_names)}? Base the analysis on conversations between psychic Lily and callers."

        # Structure note: Output is a LIST, not a dict containing a list.
        expected_item_structure = {"theme": "string", "mentions": "int", "sentiment_label": "string (e.g., Positive, Negative, Neutral, Mixed)"}

        # --- CONTEXT CONFIGURATION ---
        SEARCH_LIMIT = 20 
        CONTEXT_TRANSCRIPT_LIMIT = 10 
        MAX_CONTEXT_CHARS = 70000 # Allow reasonable context
        # --- END CONFIGURATION ---

        try:
            # --- Prerequisites ---
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
                logging.error("RAG Theme/Sentiment Corr: OpenAI client not available.")
                return {'error': 'OpenAI client unavailable'} # Return error dict
            if not self.conversation_service or not self.conversation_service.initialized:
                logging.error("RAG Theme/Sentiment Corr: Conversation service not available.")
                return {'error': 'Conversation service unavailable'} # Return error dict
                
            openai_client = self.analyzer.openai_client

            # --- 1. Get Query Embedding ---
            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding:
                return {'error': 'Failed to get embedding for internal correlation query'} # Error dict

            # --- 2. Vector Search (Get Candidate IDs) ---
            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding,
                start_date=start_date,
                end_date=end_date,
                limit=SEARCH_LIMIT,
                similarity_threshold=threshold
            )

            if not similar_conversations_info:
                logging.warning(f"RAG Theme/Sentiment Corr: No relevant conversations found via vector search (limit={SEARCH_LIMIT}, threshold={threshold}). Returning empty list.")
                return [] # Return empty list structure

            logging.info(f"RAG Theme/Sentiment Corr: Found {len(similar_conversations_info)} candidate conversations via vector search.")

            # --- 3. Prepare FULL TRANSCRIPT Context ---
            context = "\n\n---Retrieved Conversation Transcripts for Theme/Sentiment Correlation Analysis:---"
            context_char_count = 0
            conversations_used_count = 0
            ids_to_fetch = [conv.get('external_id') for conv in similar_conversations_info[:CONTEXT_TRANSCRIPT_LIMIT] if conv.get('external_id')]
            
            logging.info(f"RAG Theme/Sentiment Corr: Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")

            for external_id in ids_to_fetch:
                if context_char_count >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Theme/Sentiment Corr: Reached context character limit ({MAX_CONTEXT_CHARS}). Using {conversations_used_count} transcripts.")
                    break
                
                details = self.conversation_service.get_conversation_details(external_id)
                if not details or not details.get('transcript'):
                    logging.warning(f"RAG Theme/Sentiment Corr: Could not fetch details or transcript for {external_id}. Skipping.")
                    continue
                    
                transcript_text = "\n"
                for msg in details.get('transcript', []):
                    speaker = msg.get('role', 'unknown').capitalize()
                    content = msg.get('content', '')
                    transcript_text += f"{speaker}: {content}\n"
                
                if context_char_count + len(transcript_text) >= MAX_CONTEXT_CHARS:
                    logging.warning(f"RAG Theme/Sentiment Corr: Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                    break 
                    
                context += f"\n--- Conversation {external_id} ---\n{transcript_text}--- End Conversation {external_id} ---"
                context_char_count += len(transcript_text)
                conversations_used_count += 1
                
            if conversations_used_count == 0:
                 logging.error("RAG Theme/Sentiment Corr: Failed to build any context from transcripts. Aborting.")
                 return [] # Return empty list structure
                 
            logging.info(f"RAG Theme/Sentiment Corr: Built context using {conversations_used_count} full transcripts (~{context_char_count} chars).")

            # --- 4. Construct LLM Prompt ---
            themes_input_str = json.dumps(top_themes)
            system_prompt = (
                 f"You are an expert conversation analyst. Based *only* on the provided sample of FULL CONVERSATION TRANSCRIPTS "
                 f"(between psychic Lily and callers) from the period {start_date} to {end_date}, determine the general sentiment "
                 f"(Positive, Negative, Neutral, or Mixed) associated with each of the themes provided in the 'Input Themes' list below. "
                 f"Use the mention counts provided in the input list for the final output. "
                 f"Return ONLY a valid JSON list, where each item corresponds to an input theme and follows this structure:\n"
                 f"```json\n[{json.dumps(expected_item_structure, indent=2)}]\n```"
                 f"The output list should contain exactly one item for each theme in the 'Input Themes' list. Maintain the original theme names and mention counts. Do not include explanations or commentary outside the JSON list structure."
            )
            user_prompt = f"Input Themes:\n{themes_input_str}\n\nConversation Transcripts Sample:\n{context}"

            # --- 5. Call LLM ---
            logging.info(f"RAG Theme/Sentiment Corr (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o",
                response_format={"type": "json_object"}, 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000 # Allow space for the list
            )

            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Theme/Sentiment Corr (Full Transcript): Received response from LLM.")

            # --- 6. Parse & Validate ---
            try:
                logging.debug(f"RAG Theme/Sentiment Corr: Raw LLM Output:\n-------\n{llm_output_raw}\n-------")
                parsed_output = None
                try:
                    parsed_output = json.loads(llm_output_raw)
                except json.JSONDecodeError:
                    if llm_output_raw.startswith('```json') and llm_output_raw.endswith('```'):
                         llm_output_raw = llm_output_raw[7:-3].strip()
                         parsed_output = json.loads(llm_output_raw)
                    else:
                         raise

                correlation_list = []
                if isinstance(parsed_output, list):
                     correlation_list = parsed_output
                elif isinstance(parsed_output, dict) and all(k in parsed_output for k in expected_item_structure.keys()):
                     logging.warning("RAG Theme/Sentiment Corr: LLM returned a single object, wrapping it in a list.")
                     correlation_list = [parsed_output] 
                elif isinstance(parsed_output, dict) and len(parsed_output) == 1:
                     potential_list = list(parsed_output.values())[0]
                     if isinstance(potential_list, list):
                          correlation_list = potential_list
                     else:
                          raise ValueError("LLM JSON object does not contain expected list")
                else:
                     raise ValueError(f"LLM JSON is not a list or a single-key object containing a list. Structure: {type(parsed_output)}")

                validated_list = []
                if not isinstance(correlation_list, list):
                     raise ValueError("Parsed result is not a list")
                     
                for item in correlation_list:
                     if not isinstance(item, dict) or not all(k in item for k in expected_item_structure.keys()):
                          logging.warning(f"RAG Theme/Sentiment Corr (Full Transcript): Invalid item structure in list: {item}")
                          continue 
                     validated_list.append(item)
                
                if len(validated_list) != len(top_themes):
                     logging.warning(f"RAG Theme/Sentiment Corr (Full Transcript): Output list length ({len(validated_list)}) doesn't match input themes ({len(top_themes)}). LLM might have missed themes.")

                logging.info("RAG Theme/Sentiment Corr (Full Transcript): Successfully parsed LLM response.")
                return validated_list # Return the list directly
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                 logging.error(f"RAG Theme/Sentiment Corr (Full Transcript): Failed to parse/validate LLM JSON response: {e}")
                 logging.error(f"Raw response: {llm_output_raw}")
                 return {'error': f'Failed to parse/validate LLM JSON for correlation: {e}'} 

        except Exception as e:
            logging.error(f"RAG Theme/Sentiment Corr (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in theme/sentiment correlation: {str(e)}'}

    def _get_rag_categorized_quotes(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting categorized quotes (using full transcripts) for {start_date} to {end_date} [Multi-Step]")
        
        # --- Overall Structure --- 
        final_result = {
            "common_questions": [],
            "concerns_skepticism": [],
            "positive_interactions": {"count": 0, "quotes": []}
        }
        error_occurred = False
        error_messages = []

        # --- Prerequisites (Check once) ---
        if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
            logging.error("RAG Categorized Quotes: OpenAI client not available.")
            return {'error': 'OpenAI client unavailable'} # Return error dict directly
        if not self.conversation_service or not self.conversation_service.initialized:
            logging.error("RAG Categorized Quotes: Conversation service not available.")
            return {'error': 'Conversation service unavailable'} # Return error dict directly
        openai_client = self.analyzer.openai_client

        # --- STEP 1: Get Common Questions & Concerns/Skepticism --- 
        logging.info("RAG Quotes: --- Starting Step 1: Questions & Concerns ---")
        try:
            internal_query_qc = f"Identify common questions asked by callers and any concerns or skepticism expressed in conversations between psychic Lily and callers between {start_date} and {end_date}."
            expected_structure_qc = {
                "common_questions": [
                    { "category_name": "string", "count": "int", "quotes": [{ "quote_text": "string", "conversation_id": "string or null" }] } 
                ],
                "concerns_skepticism": [
                    { "category_name": "string", "count": "int", "quotes": [{ "quote_text": "string", "conversation_id": "string or null" }] } 
                ]
            }
            SEARCH_LIMIT_QC = 25
            CONTEXT_TRANSCRIPT_LIMIT_QC = 12
            MAX_CONTEXT_CHARS_QC = 70000 

            # 1a. Embedding
            query_embedding_qc = _get_openai_embedding(internal_query_qc, openai_client)
            if not query_embedding_qc:
                raise ValueError('Failed to get embedding for internal QC query')

            # 1b. Vector Search
            threshold = 0.35
            similar_conversations_info_qc = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding_qc, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT_QC, similarity_threshold=threshold
            )
            logging.info(f"RAG Quotes (QC): Found {len(similar_conversations_info_qc)} candidate conversations.")

            # 1c. Prepare Transcript Context
            context_qc, conv_id_map_qc, used_count_qc = self._build_transcript_context(
                similar_conversations_info_qc, CONTEXT_TRANSCRIPT_LIMIT_QC, MAX_CONTEXT_CHARS_QC, "QC"
            )
            if used_count_qc == 0:
                logging.warning("RAG Quotes (QC): Failed to build context. Skipping QC step.")
            else:
                # 1d. LLM Prompt
                system_prompt_qc = (
                    f"You are an expert conversation analyst. Based *only* on the provided sample of FULL CONVERSATION TRANSCRIPTS "
                    f"from {start_date} to {end_date}, identify key quotes related ONLY to common questions callers ask and concerns/skepticism they express. "
                    f"Return ONLY a valid JSON object adhering strictly to the following structure:\n"
                    f"```json\n{json.dumps(expected_structure_qc, indent=2)}\n```"
                    f"**Instructions:**\n"
                    f"- Identify up to 5 distinct categories for questions and up to 5 for concerns/skepticism.\n"
                    f"- For each category, provide up to 3 specific example quotes from the transcripts.\n"
                    f"- Use the conversation number (e.g., '1', '2', '3') provided in the context as the value for 'conversation_id'. If a quote cannot be directly attributed, use null.\n"
                    f"- Ensure 'count' reflects the number of quotes listed.\n"
                    f"- If no relevant quotes are found for a category, return an empty list for its 'quotes'.\n"
                    f"- Base analysis *strictly* on the provided transcripts.\n"
                    f"Do not include commentary outside the JSON structure."
                )
                user_prompt_qc = f"Conversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context_qc}"

                # 1e. LLM Call
                logging.info(f"RAG Quotes (QC): Sending prompt to LLM ({self.analyzer.model_name})...")
                completion_qc = openai_client.chat.completions.create(
                    model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system_prompt_qc}, {"role": "user", "content": user_prompt_qc}],
                    temperature=0.1, max_tokens=2000
                )
                llm_output_raw_qc = completion_qc.choices[0].message.content.strip()
                logging.info(f"RAG Quotes (QC): Received response from LLM.")

                # 1f. Parse & Validate
                parsed_output_qc = json.loads(llm_output_raw_qc)
                if not all(k in parsed_output_qc for k in expected_structure_qc.keys()):
                    raise ValueError("QC LLM output missing required keys")
                
                # Map IDs and update final_result
                self._map_context_ids_to_external(parsed_output_qc.get('common_questions'), conv_id_map_qc)
                self._map_context_ids_to_external(parsed_output_qc.get('concerns_skepticism'), conv_id_map_qc)
                final_result['common_questions'] = parsed_output_qc.get('common_questions', [])
                final_result['concerns_skepticism'] = parsed_output_qc.get('concerns_skepticism', [])
                logging.info("RAG Quotes (QC): Successfully processed questions and concerns.")

        except Exception as e_qc:
            logging.error(f"RAG Quotes (QC): Error during Questions/Concerns step: {e_qc}", exc_info=True)
            error_occurred = True
            error_messages.append(f"QC Step Error: {str(e_qc)}")
            # Ensure keys exist even if step failed
            final_result['common_questions'] = []
            final_result['concerns_skepticism'] = []

        # --- STEP 2: Get Positive Interactions --- 
        logging.info("RAG Quotes: --- Starting Step 2: Positive Interactions ---")
        try:
            internal_query_pos = f"Identify specific examples of positive interactions, caller satisfaction, or successful connections in conversations between psychic Lily and callers between {start_date} and {end_date}."
            expected_structure_pos = {
                "positive_interactions": {
                    "count": "int",
                    "quotes": [{ "quote_text": "string", "conversation_id": "string or null", "sentiment_score": "float" }] 
                }
            }
            SEARCH_LIMIT_POS = 20
            CONTEXT_TRANSCRIPT_LIMIT_POS = 10
            MAX_CONTEXT_CHARS_POS = 60000 

            # 2a. Embedding
            query_embedding_pos = _get_openai_embedding(internal_query_pos, openai_client)
            if not query_embedding_pos:
                raise ValueError('Failed to get embedding for internal positive query')

            # 2b. Vector Search
            similar_conversations_info_pos = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding_pos, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT_POS, similarity_threshold=0.35 # Use same threshold for now
            )
            logging.info(f"RAG Quotes (Pos): Found {len(similar_conversations_info_pos)} candidate conversations.")
            
            # 2c. Prepare Transcript Context
            context_pos, conv_id_map_pos, used_count_pos = self._build_transcript_context(
                similar_conversations_info_pos, CONTEXT_TRANSCRIPT_LIMIT_POS, MAX_CONTEXT_CHARS_POS, "Pos"
            )
            if used_count_pos == 0:
                logging.warning("RAG Quotes (Pos): Failed to build context. Skipping Positive step.")
            else:
                # 2d. LLM Prompt
                system_prompt_pos = (
                    f"You are an expert conversation analyst. Based *only* on the provided sample of FULL CONVERSATION TRANSCRIPTS "
                    f"from {start_date} to {end_date}, identify key quotes reflecting positive moments, satisfaction, or successful connections. "
                    f"Return ONLY a valid JSON object adhering strictly to the following structure:\n"
                    f"```json\n{json.dumps(expected_structure_pos, indent=2)}\n```"
                    f"**Instructions:**\n"
                    f"- Identify up to 10 quotes reflecting positive interactions.\n"
                    f"- Estimate a sentiment score (-1 to 1) for each positive quote.\n"
                    f"- Sort the quotes list by sentiment_score descending.\n"
                    f"- Use the conversation number (e.g., '1', '2', '3') provided in the context as the value for 'conversation_id'. If a quote cannot be directly attributed, use null.\n"
                    f"- Ensure the 'count' field accurately reflects the number of quotes listed.\n"
                    f"- If no positive interactions are found, return count 0 and an empty quotes list.\n"
                    f"- Base analysis *strictly* on the provided transcripts.\n"
                    f"Do not include commentary outside the JSON structure."
                )
                user_prompt_pos = f"Conversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context_pos}"

                # 2e. LLM Call
                logging.info(f"RAG Quotes (Pos): Sending prompt to LLM ({self.analyzer.model_name})...")
                completion_pos = openai_client.chat.completions.create(
                    model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system_prompt_pos}, {"role": "user", "content": user_prompt_pos}],
                    temperature=0.1, max_tokens=1500
                )
                llm_output_raw_pos = completion_pos.choices[0].message.content.strip()
                logging.info(f"RAG Quotes (Pos): Received response from LLM.")

                # 2f. Parse & Validate
                parsed_output_pos = json.loads(llm_output_raw_pos)
                if "positive_interactions" not in parsed_output_pos or not isinstance(parsed_output_pos["positive_interactions"], dict):
                    raise ValueError("Positive LLM output missing required structure")
                
                # Map IDs and update final_result
                self._map_context_ids_to_external_positive(parsed_output_pos.get('positive_interactions'), conv_id_map_pos)
                final_result['positive_interactions'] = parsed_output_pos.get('positive_interactions', {"count": 0, "quotes": []})
                logging.info("RAG Quotes (Pos): Successfully processed positive interactions.")

        except Exception as e_pos:
            logging.error(f"RAG Quotes (Pos): Error during Positive Interactions step: {e_pos}", exc_info=True)
            error_occurred = True
            error_messages.append(f"Positive Step Error: {str(e_pos)}")
            # Ensure key exists even if step failed
            final_result['positive_interactions'] = {"count": 0, "quotes": []}

        # --- Final Error Check --- 
        if error_occurred:
            logging.error(f"RAG Categorized Quotes completed with errors: {error_messages}")
            # Potentially return an error structure or the partial result with error indication
            # For now, returning the potentially partial result 
            return final_result # Or return {'error': ", ".join(error_messages)}
        
        logging.info(f"RAG Categorized Quotes: Successfully completed all steps.")
        return final_result

    # --- Helper function to build context (DRY) ---
    def _build_transcript_context(self, similar_conversations_info, transcript_limit, char_limit, step_label="Step"):
        context = f"\n\n---Retrieved Conversation Transcripts for {step_label} Analysis:---\n"
        context_char_count = 0
        conversations_used_count = 0
        conv_id_map = {}
        ids_to_fetch = [conv.get('external_id') for conv in similar_conversations_info[:transcript_limit] if conv.get('external_id')]
        
        logging.info(f"RAG Quotes ({step_label}): Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")

        for idx, external_id in enumerate(ids_to_fetch):
            current_context_index = str(idx + 1) # Use 1-based index for LLM
            conv_id_map[current_context_index] = external_id # Store mapping
            
            if context_char_count >= char_limit:
                logging.warning(f"RAG Quotes ({step_label}): Reached context character limit ({char_limit}). Using {conversations_used_count} transcripts.")
                break
            
            details = self.conversation_service.get_conversation_details(external_id)
            if not details or not details.get('transcript'):
                logging.warning(f"RAG Quotes ({step_label}): Could not fetch details or transcript for {external_id}. Skipping.")
                continue
                
            transcript_text = "\n"
            for msg in details.get('transcript', []):
                speaker = msg.get('role', 'unknown').capitalize()
                content = msg.get('content', '')
                transcript_text += f"{speaker}: {content}\n"
            
            if context_char_count + len(transcript_text) >= char_limit:
                logging.warning(f"RAG Quotes ({step_label}): Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                break 
                
            # Use the 1-based index in the context for LLM reference
            context += f"\n--- Conversation {current_context_index} (Use this number for conversation_id) ---\n{transcript_text}--- End Conversation {current_context_index} ---\n"
            context_char_count += len(transcript_text)
            conversations_used_count += 1
        
        logging.info(f"RAG Quotes ({step_label}): Built context using {conversations_used_count} full transcripts (~{context_char_count} chars).")
        return context, conv_id_map, conversations_used_count

    # --- Helper function to map IDs (DRY) ---
    def _map_context_ids_to_external(self, category_list, id_map):
        """Maps context index IDs to external IDs for common_questions/concerns_skepticism lists."""
        if not isinstance(category_list, list): return
        for category_info in category_list:
            if isinstance(category_info, dict) and 'quotes' in category_info and isinstance(category_info['quotes'], list):
                for quote in category_info['quotes']:
                    context_id = str(quote.get('conversation_id')) 
                    quote['conversation_id'] = id_map.get(context_id, None) 
    def _map_context_ids_to_external_positive(self, positive_dict, id_map):
        """Maps context index IDs to external IDs for positive_interactions quotes."""
        if not isinstance(positive_dict, dict) or 'quotes' not in positive_dict or not isinstance(positive_dict['quotes'], list): return
        for quote in positive_dict['quotes']:
             context_id = str(quote.get('conversation_id'))
             quote['conversation_id'] = id_map.get(context_id, None)

    # --- End Placeholder RAG methods ---

    # --- RAG Method for Ad-hoc Queries ---
    def process_natural_language_query(self, query: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, str]:

        # Implement the logic to process a natural language query and return the result
        # This is a placeholder and should be replaced with the actual implementation
        return {"result": "This is a placeholder implementation. Actual implementation needed."} 