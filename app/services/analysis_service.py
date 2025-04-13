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
        Fetches conversations for the date range and performs full analysis,
        returning a structure suitable for the themes/sentiment page.
        
        Handles caching: 
            - Uses Flask-Caching with a FileSystemCache.
            - Cache key is based on start/end dates.
            - Default timeout is 3600 seconds (1 hour).
            - Returns cached result immediately if available.
        """
        start_time = time.time()
        logging.info(f"Starting full themes & sentiment analysis for {start_date} to {end_date}")
        
        # Define cache key based on dates
        cache_key = f'themes_sentiment_{start_date}_{end_date}'
        
        # Try fetching from cache first
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logging.info(f"Returning cached themes/sentiment data for {start_date}-{end_date}")
                # Ensure model name is present in cached status, but don't overwrite if already there
                if 'analysis_status' not in cached_result:
                     cached_result['analysis_status'] = {}
                if 'model_name' not in cached_result['analysis_status']:
                    cached_result['analysis_status']['model_name'] = getattr(self.analyzer, 'model_name', 'N/A') if self.analyzer else 'N/A'
                return cached_result

        # --- Data Fetching using injected conversation_service ---
        try:
            logging.info(f"Fetching conversations via service for {start_date} to {end_date}")
            fetch_result = self.conversation_service.get_conversations(
                start_date=start_date, 
                end_date=end_date,   
                limit=10000 
            )
            conversations = fetch_result.get('conversations', [])
            original_total_count = fetch_result.get('total_count', len(conversations))
            logging.info(f"Fetched {len(conversations)} conversations (out of {original_total_count} total) for analysis.")
            
        except Exception as e:
            logging.error(f"Error fetching conversation data via service: {e}", exc_info=True)
            # Return the standard empty structure on fetch error
            return self.analyzer._empty_analysis_result(start_date, end_date, f"Data Fetch Error: {str(e)}", 0) if self.analyzer else {"error": "Data Fetch Error and Analyzer unavailable"}
        
        # --- Analysis ---
        if not self.analyzer:
            logging.error("ConversationAnalyzer not initialized, cannot perform analysis.")
            # Return the standard empty structure
            return self.analyzer._empty_analysis_result(start_date, end_date, "Analyzer Not Available", original_total_count)
            
        try:
            # The analyzer's unified method now returns the full structure including model name
            # This is the main analysis call, potentially long-running if not cached.
            analysis_result = self.analyzer.unified_llm_analysis(conversations, start_date, end_date, original_total_count)
            logging.info(f"Received analysis results from ConversationAnalyzer.")
            
            # Error check (unified_llm_analysis returns {'error':...} on failure)
            if 'error' in analysis_result:
                 logging.error(f"Analysis returned an error: {analysis_result.get('details', analysis_result['error'])}")
                 # Return the error structure (which includes status) from the analyzer
                 return analysis_result 

        except Exception as e:
            logging.error(f"Unexpected error calling unified LLM analysis: {e}", exc_info=True)
            # Return the standard empty structure on unexpected error
            return self.analyzer._empty_analysis_result(start_date, end_date, f"Unexpected Analysis Error: {str(e)}", original_total_count)

        # Cache the successful result
        if self.cache:
            cache_timeout = 3600 
            self.cache.set(cache_key, analysis_result, timeout=cache_timeout)
            logging.info(f"Cached themes/sentiment data for {start_date}-{end_date} with timeout {cache_timeout}s")
            
        end_time = time.time()
        logging.info(f"Successfully completed full themes & sentiment analysis in {end_time - start_time:.2f} seconds.")
        return analysis_result

    # --- RAG Method for Ad-hoc Queries ---
    def process_natural_language_query(self, query: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, str]:
        """
        Processes a natural language query using RAG against conversation summaries.

        Args:
            query: The user's natural language query.
            start_date: Optional start date string (YYYY-MM-DD).
            end_date: Optional end date string (YYYY-MM-DD).

        Returns:
            A dictionary containing the answer or an error message.
        """
        logging.info(f"Processing natural language query: '{query[:50]}...' for dates {start_date}-{end_date}")
        
        # --- Pre-requisite Checks ---
        if not self.conversation_service or not self.conversation_service.initialized:
            logging.error("Cannot process query: SupabaseConversationService not available.")
            return {'error': 'Conversation service is not available.'}
        
        if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
             logging.error("Cannot process query: OpenAI client not available via ConversationAnalyzer.")
             return {'error': 'OpenAI client is not available for analysis.'}
             
        openai_client = self.analyzer.openai_client # Use the client initialized by the analyzer

        # --- 1. Generate Query Embedding ---
        try:
            query_embedding = _get_openai_embedding(query, openai_client)
            if not query_embedding:
                logging.error("Failed to generate embedding for the query.")
                return {'error': 'Could not generate embedding for the query.'}
            # Log first few dimensions of the query embedding
            logging.info(f"Successfully generated query embedding. Start: {query_embedding[:5]}...")
        except Exception as e:
             logging.error(f"Exception during query embedding: {e}", exc_info=True)
             return {'error': 'Failed to generate query embedding.'}

        # --- 2. Find Similar Conversations ---
        try:
            limit = 10 # How many relevant summaries to fetch
            threshold = 0.35 # SET new permanent threshold based on testing
            logging.info(f"Calling find_similar_conversations with threshold={threshold}, limit={limit}") # Log params
            similar_conversations = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                similarity_threshold=threshold
            )
            
            # --- Enhanced Logging --- 
            num_found = len(similar_conversations) if similar_conversations else 0
            logging.info(f"find_similar_conversations returned {num_found} results.")
            if num_found > 0:
                 # Log details of the top match
                 top_match = similar_conversations[0]
                 logging.info(f"Top match: ID={top_match.get('id')}, ExtID={top_match.get('external_id')}, Score={top_match.get('similarity')}, Summary='{str(top_match.get('summary'))[:100]}...'")
            # --- End Enhanced Logging ---
            
            if not similar_conversations:
                logging.warning(f"No similar conversations found matching the query criteria (Threshold: {threshold}).")
                # Modified return message for user-friendliness
                return {'answer': f"Based on my analysis, I couldn't find conversations matching that specific description within the selected dates using the current similarity setting ({threshold}). You could try rephrasing your question or widening the date range."}
            
            logging.info(f"Retrieved {len(similar_conversations)} relevant conversation summaries (Threshold: {threshold}).")
        except Exception as e:
            logging.error(f"Exception during similarity search: {e}", exc_info=True)
            return {'error': 'Failed to search for similar conversations.'}

        # --- 3. Prepare Context ---
        context = "\n\n---Retrieved Conversation Summaries:---"
        for i, conv in enumerate(similar_conversations):
            context += f"\nConversation {i+1} (ID: {conv.get('external_id', 'N/A')}, Similarity: {conv.get('similarity', 0.0):.4f}):\nSummary: {conv.get('summary', '[No Summary]')}\n---"
        
        # Check context length (optional, but good practice)
        # Use tiktoken if available for accurate count, else estimate
        try:
            import tiktoken
            # Assuming gpt-4o uses cl100k_base encoding
            encoding = tiktoken.get_encoding("cl100k_base") 
            context_tokens = len(encoding.encode(context))
            logging.info(f"Prepared context with estimated {context_tokens} tokens.")
            # Add check/truncation if context_tokens exceed a threshold
        except ImportError:
            logging.warning("tiktoken not found. Cannot accurately estimate context token count.")
        except Exception as token_err:
             logging.warning(f"Error estimating token count: {token_err}")


        # --- 4. Construct LLM Prompt ---
        # Modified system prompt for Lily persona
        system_prompt = (
            f"You are Lily, an AI agent at Psychic Source. You are reporting on conversation analysis based "
            f"on transcripts of calls between yourself (as the agent) and users (Curious Callers). "
            f"Use ONLY the provided conversation summaries below to answer the user's question about these conversations. "
            f"Respond in the first person (e.g., 'I found that...', 'My analysis shows...'). "
            f"Do not make up information. If the answer isn't in the summaries, say so clearly. "
            f"Be concise and directly address the question."
        )
        
        user_prompt = f"User Question: {query}\n{context}"

        # --- 5. Call LLM for Answer Generation ---
        try:
            logging.info(f"Sending prompt to LLM ({self.analyzer.model_name or 'default'}) for final answer...")
            # Use the chat completions endpoint
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o", # Use model from analyzer or default
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2, # Lower temperature for more factual answers
                max_tokens=1000 # Adjust as needed
            )
            
            answer = completion.choices[0].message.content.strip()
            logging.info("Received answer from LLM.")
            return {'answer': answer}

        except Exception as e:
            logging.error(f"Exception during LLM call for answer generation: {e}", exc_info=True)
            return {'error': 'Failed to get answer from the analysis model.'}

    # Comment out or remove the old helper methods if they are no longer needed
    # def _calculate_sentiment_overview(self, conversations):
    #     ...

    # def _generate_sentiment_trends(self, conversations):
    #     ...

    # def analyze_themes_and_sentiment(self, start_date, end_date, max_conversations=500):
    #     ... 