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
# from app.models import Conversation, Message # Removed top-level import
import json
import os
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
import openai # Added for query embedding

# Import the conversation service we need
from app.services.supabase_conversation_service import SupabaseConversationService

# --- Helper function for OpenAI Embedding ---
# Re-defined here, consider moving to a shared util later
def _get_openai_embedding(text, client, model="text-embedding-3-large"):
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
    
    def _get_model_classes(self):
        """Helper to defer import of model classes."""
        from app.models import Conversation, Message
        return Conversation, Message
    
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
        """
        logging.warning("get_categorized_themes is DEPRECATED and effectively a no-op. RAG analysis should be used instead.")
        # Entire original body of this method commented out for future reference if needed,
        # but considered deprecated.
        # 
        # logging.warning("get_categorized_themes called - this method might be deprecated in favor of RAG analysis.")
        # logging.info(f"AnalysisService: Getting categorized themes (start: {start_date}, end: {end_date})")
        # 
        # # ... (rest of the keyword/pattern logic remains unchanged for now) ...
        # # --- Define Categories and their Keywords/Patterns ---
        # common_question_keywords = {
        #     'Love & Relationships': ['love', 'relationship', 'boyfriend', 'girlfriend', 'partner', 'marriage', 'divorce',
        #                           'dating', 'ex', 'husband', 'wife', 'breakup', 'soulmate', 'twin flame', 'romance', 
        #                           'romantic', 'affair', 'crush', 'connection'],
        #     'Career & Finances': ['job', 'career', 'money', 'work', 'business', 'financial', 'finance', 'salary', 'promotion',
        #                    'interview', 'application', 'boss', 'workplace', 'income', 'debt', 'investment', 'retirement',
        #                    'savings', 'profession', 'opportunity', 'success'],
        #     'Family & Children': ['family', 'mother', 'father', 'sister', 'brother', 'daughter', 'son', 'parent', 'child',
        #              'grandparent', 'relative', 'sibling', 'aunt', 'uncle', 'cousin', 'in-law', 'adoption',
        #              'pregnant', 'pregnancy', 'baby', 'children'],
        #     'Future Predictions': ['future', 'prediction', 'happen', 'will i', 'going to', 'forecast', 'destiny', 'fate',
        #               'path', 'timeline', 'when will', 'outcome', 'result', 'eventually', 'someday'],
        #     'Psychic Source Services': [
        #         'number', 'phone', 'toll-free', 'international', 'website', 'app', 'account', 'login', 'membership',
        #         'credit', 'subscription', 'sign up', 'register', 'access',
        #         'price', 'cost', 'fee', 'charge', 'minute', 'package', 'special', 'discount', 'offer', 'promotion',
        #         'how long', 'duration', 'schedule', 'appointment', 'booking', 'available', 'time slot', 'reservation',
        #         'reader', 'advisor', 'psychic', 'specialist', 'recommend', 'suggestion', 'best for', 'top', 'profile',
        #         'extension', 'review', 'rating', 'feedback', 'experienced', 'popular', 'good at', 'specialized',
        #         'problem', 'issue', 'error', 'trouble', 'help', 'assist', 'support', 'connect', 'payment', 'receipt',
        #         'transaction', 'refund', 'credit card', 'billing', 'statement', 'email', 'contact us'
        #     ],
        #     'Spiritual & Metaphysical Concepts': ['spirit', 'energy', 'aura', 'chakra', 'meditation', 'vibration', 'frequency',
        #                          'cleansing', 'sage', 'crystal', 'ritual', 'blessing', 'prayer', 'guardian angel',
        #                          'spirit guide', 'intuition', 'empath', 'clairvoyant', 'psychic ability', 'universe',
        #                          'manifestation', 'law of attraction', 'karma', 'past life', 'reincarnation', 'soul'],
        #     'Health & Wellness': ['health', 'wellness', 'medical', 'doctor', 'therapy', 'healing', 'illness', 'disease',
        #                       'condition', 'symptom', 'diagnosis', 'recovery', 'treatment', 'medicine', 'surgery',
        #                       'mental health', 'depression', 'anxiety', 'stress', 'sleep', 'diet', 'exercise', 'pain',
        #                       'addiction', 'weight', 'nutrition', 'wellbeing']
        # }
        # concerns_keywords = {
        #      'General Concerns': ['worry', 'worried', 'concern', 'concerned', 'anxious', 'nervous', 'afraid', 'scared', 'confused',
        #                       'unsure', 'doubt', 'hesitant', 'problem', 'issue', 'difficult', 'hard', 'stuck', 'lost', 'overwhelmed'],
        #      'Doubts about Readings': ['really work', 'accurate', 'true', 'possible', 'skeptical', 'believe', 'proof',
        #                           'evidence', 'real', 'genuine', 'how do you know', 'sure about this', 'convinced', 'skepticism'],
        #      'Skepticism about Process': ['scam', 'fraud', 'trick', 'fake', 'rip off', 'waste of money', 'fortune teller', 'cold reading',
        #                              'general', 'vague', 'barnum', 'expensive', 'worth it', 'make this up', 'not sure']
        # }
        # 
        # # --- Fetch Snippets for Each Category --- 
        # common_questions_results = []
        # try:
        #     all_q_keywords = [kw for sublist in common_question_keywords.values() for kw in sublist]
        #     q_patterns = ['%?%'] 
        #     logging.info(f"Fetching common question snippets...")
        #     question_snippets = current_app.conversation_service.get_relevant_message_snippets(
        #         start_date=start_date, end_date=end_date, keywords=all_q_keywords, 
        #         patterns=q_patterns, speaker_filter=['user'], limit_per_conv=3
        #     )
        #     logging.info(f"Found {len(question_snippets)} raw question snippets.")
        #     
        #     categorized_questions = {cat_name: [] for cat_name in common_question_keywords.keys()}
        #     other_questions = []
        #     for snippet in question_snippets:
        #         text = snippet['text'].lower()
        #         categorized = False
        #         for cat_name, keywords in common_question_keywords.items():
        #             if any(word.lower() in text for word in keywords):
        #                  categorized_questions[cat_name].append(snippet)
        #                  categorized = True; break
        #         if not categorized and '?' in text: other_questions.append(snippet)
        #     if other_questions: categorized_questions['Other Questions'] = other_questions
        #     for cat_name, snippets in categorized_questions.items():
        #         if snippets: common_questions_results.append({'category': cat_name, 'count': len(snippets), 'examples': snippets})
        #     common_questions_results = sorted(common_questions_results, key=lambda x: x['count'], reverse=True)
        # except Exception as e:
        #      logging.error(f"Error processing common questions: {e}", exc_info=True)
        #      common_questions_results = []
        #      
        # concerns_skepticism_results = []
        # try:
        #     all_c_keywords = [kw for sublist in concerns_keywords.values() for kw in sublist]
        #     logging.info(f"Fetching concern/skepticism snippets...")
        #     concern_snippets = current_app.conversation_service.get_relevant_message_snippets(
        #          start_date=start_date, end_date=end_date, keywords=all_c_keywords,
        #          patterns=None, speaker_filter=['user'], limit_per_conv=3
        #     )
        #     logging.info(f"Found {len(concern_snippets)} raw concern snippets.")
        #     categorized_concerns = {cat_name: [] for cat_name in concerns_keywords.keys()}
        #     for snippet in concern_snippets:
        #          text = snippet['text'].lower()
        #          for cat_name, keywords in concerns_keywords.items():
        #              if any(word.lower() in text for word in keywords):
        #                   categorized_concerns[cat_name].append(snippet); break
        #     for cat_name, snippets in categorized_concerns.items():
        #         if snippets: concerns_skepticism_results.append({'category': cat_name, 'count': len(snippets), 'examples': snippets})
        #     concerns_skepticism_results = sorted(concerns_skepticism_results, key=lambda x: x['count'], reverse=True)
        # except Exception as e:
        #      logging.error(f"Error processing concerns/skepticism: {e}", exc_info=True)
        #      concerns_skepticism_results = []
        # 
        # final_result = {'common_questions': common_questions_results, 'concerns_skepticism': concerns_skepticism_results, 'other_analysis': {}}
        # logging.info(f"AnalysisService: Finished getting categorized themes. Found {len(common_questions_results)} question categories and {len(concerns_skepticism_results)} concern categories.")
        # return final_result
        pass # Method is deprecated
        return {'common_questions': [], 'concerns_skepticism': [], 'other_analysis': {}} # Return empty structure
    
    def get_transcripts_for_conversations(self, conversation_ids):
        """
        Efficiently fetch transcripts for multiple conversation external IDs.
        
        Args:
            conversation_ids: List of conversation EXTERNAL IDs (strings).
            
        Returns:
            dict: Mapping of external_id to full conversation data with transcript.
        """
        if not conversation_ids:
            logging.warning("get_transcripts_for_conversations called with empty ID list.")
            return {}
            
        logging.info(f"Fetching transcripts for {len(conversation_ids)} conversations (using external IDs)")
        
        result = {}
        successful_fetches = 0
        errors = []
        
        # Ensure conversation_service is available
        if not hasattr(current_app, 'conversation_service') or not current_app.conversation_service:
            logging.error("Conversation service not available on current_app context.")
            return {'error': "Conversation service unavailable"}

        for conv_id in conversation_ids:
            if not conv_id or not isinstance(conv_id, str):
                logging.warning(f"Skipping invalid conversation ID: {conv_id}")
                continue
                
            try:
                logging.debug(f"[AnalysisService] Getting details for external ID: '{conv_id}'")
                # Call service method with the external ID (string)
                conv_data = current_app.conversation_service.get_conversation_details(conv_id)
                logging.debug(f"[AnalysisService] Call finished for ID: '{conv_id}'. Result type: {type(conv_data)}")
                
                if conv_data and 'transcript' in conv_data and conv_data.get('transcript'):
                    result[conv_id] = conv_data # Use external ID as key
                    successful_fetches += 1
                    logging.debug(f"Successfully retrieved transcript for conversation {conv_id}")
                elif conv_data and 'error' in conv_data:
                     logging.warning(f"Service error getting transcript for conversation {conv_id}: {conv_data['error']}")
                     errors.append({'conversation_id': conv_id, 'error': conv_data['error']})
                else:
                    logging.warning(f"No transcript data found or returned for conversation {conv_id}")
                    errors.append({'conversation_id': conv_id, 'error': 'Not found or no transcript'})

            except Exception as e:
                error_trace = traceback.format_exc() 
                logging.warning(f"Service error getting transcript for conversation {conv_id}: {e}\nTrace: {error_trace}")
                errors.append({'conversation_id': conv_id, 'error': str(e)})
                continue # Continue to the next conversation ID
                
        logging.info(f"Finished fetching transcripts. Successfully retrieved {successful_fetches}/{len(conversation_ids)}.")
        if errors:
            logging.warning(f"Errors occurred during transcript fetching: {errors}")
        return result # Return the dictionary mapping external_id -> details
        
    def _extract_themes(self, df):
        """
        DEPRECATED? Extract themes/topics from conversations and their associated sentiment.
        This likely needs refactoring or removal if RAG analysis replaces it.
        """
        logging.warning("_extract_themes is DEPRECATED and effectively a no-op. RAG analysis should be used instead.")
        # Entire original body of this method commented out for future reference if needed,
        # but considered deprecated.
        #
        # Conversation, Message = self._get_model_classes() # This line was added in a previous step
        # logging.warning("_extract_themes called - this method might be deprecated or need refactoring.")
        # try:
        #     # ... (Existing logic, may need review) ...
        #     logging.info(f"Starting theme extraction from {len(df)} conversations")
        #     if 'conversation_id' not in df.columns: return {'top_themes': [], 'sentiment_by_theme': []}
        #     conversation_ids = df['conversation_id'].unique().tolist() # Assumes these are EXTERNAL IDs now?
        #     conversation_map = self.get_transcripts_for_conversations(conversation_ids) # Pass external IDs
        #     conversations_with_transcripts = list(conversation_map.values())
        #     if not conversations_with_transcripts: return {'top_themes': [], 'sentiment_by_theme': []}
        #     
        #     # Assuming analyzer methods can handle the structure from get_transcripts_for_conversations
        #     logging.info("Using unified_theme_sentiment_analysis for more accurate results")
        #     unified_results = self.analyzer.unified_theme_sentiment_analysis(conversations_with_transcripts)
        #     top_themes = unified_results.get('themes', [])
        #     sentiment_by_theme = unified_results.get('correlations', [])
        #     
        #     logging.info("Calling extract_common_questions with conversation transcripts")
        #     common_questions = self.analyzer.extract_common_questions(conversations_with_transcripts)
        #     logging.info("Calling extract_concerns_and_skepticism with conversation transcripts")
        #     concerns_skepticism = self.analyzer.extract_concerns_and_skepticism(conversations_with_transcripts)
        #     logging.info("Calling extract_positive_interactions with conversation transcripts")
        #     positive_interactions = self.analyzer.extract_positive_interactions(conversations_with_transcripts)
        #
        #     return {
        #         'top_themes': top_themes, 'sentiment_by_theme': sentiment_by_theme,
        #         'common_questions': common_questions, 'concerns_skepticism': concerns_skepticism,
        #         'positive_interactions': positive_interactions
        #     }
        # except Exception as e:
        #     logging.error(f"Error extracting themes: {e}", exc_info=True)
        #     return {'top_themes': [], 'sentiment_by_theme': [], 'common_questions': [], 'concerns_skepticism': [], 'positive_interactions': []}
        pass # Method is deprecated
        return {
            'top_themes': [], 'sentiment_by_theme': [], 
            'common_questions': [], 'concerns_skepticism': [], 
            'positive_interactions': []
        } # Return empty structure
    
    # --- NEW Method for Comprehensive Analysis --- 
    def get_full_themes_sentiment_analysis(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetches conversations for the date range and performs full analysis using RAG,
        returning a structure suitable for the themes/sentiment page.
        Handles caching.
        """
        start_time = time.time()
        logging.info(f"Starting RAG-based full themes & sentiment analysis for {start_date} to {end_date}")
        cache_key = f'themes_sentiment_rag_{start_date}_{end_date}'

        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logging.info(f"Returning cached RAG themes/sentiment data for {start_date}-{end_date}")
                if 'analysis_status' not in cached_result: cached_result['analysis_status'] = {}
                if 'model_name' not in cached_result['analysis_status']:
                    cached_result['analysis_status']['model_name'] = getattr(self.analyzer, 'model_name', 'N/A') if self.analyzer else 'N/A'
                return cached_result

        analysis_result = {}
        error_occurred = False
        error_message = "Analysis failed"
        model_name_used = getattr(self.analyzer, 'model_name', 'N/A') if self.analyzer else 'N/A'
        total_conversations_in_range = 0

        try:
            logging.info(f"RAG Analysis: Fetching count for date range: START='{start_date}', END='{end_date}'")
            count_result = self.conversation_service.get_conversation_count(start_date=start_date, end_date=end_date)
            total_conversations_in_range = count_result
            logging.info(f"Total conversations found in range: {total_conversations_in_range}")
        except Exception as count_err:
             logging.error(f"Error fetching conversation count: {count_err}", exc_info=True)
             error_occurred = True
             error_message = f"Failed to get conversation count: {str(count_err)}"
             total_conversations_in_range = 0

        if not self.analyzer or not self.conversation_service:
             logging.error("AnalysisService prerequisites not met for RAG analysis.")
             error_occurred = True
             error_message = "Analysis prerequisites not met."
             analysis_result = self.analyzer._empty_analysis_result(start_date, end_date, error_message, total_conversations_in_range) if self.analyzer else {}

        if not error_occurred:
            try:
                logging.info("Performing RAG analysis for each section...")
                sentiment_overview = self._get_rag_sentiment_overview(start_date, end_date)
                top_themes = self._get_rag_top_themes(start_date, end_date)
                sentiment_trends = self._get_rag_sentiment_trends(start_date, end_date)
                # --- TEMPORARILY BYPASS THEME CORRELATION ---
                # theme_sentiment_correlation = self._get_rag_theme_sentiment_correlation(start_date, end_date, top_themes.get('themes', []) if top_themes else [])
                theme_sentiment_correlation = [] # Assign default empty list
                logging.warning("Temporarily bypassing _get_rag_theme_sentiment_correlation due to LLM parsing issues.")
                # --- END BYPASS ---
                categorized_quotes = self._get_rag_categorized_quotes(start_date, end_date)

                # Check for errors in sub-tasks
                sub_tasks = {
                    "Sentiment Overview": sentiment_overview, 
                    "Top Themes": top_themes, 
                    "Sentiment Trends": sentiment_trends, 
                    # "Theme Correlation": theme_sentiment_correlation, # Ignore bypassed task in error check
                    "Categorized Quotes": categorized_quotes
                }
                errors_found = []
                for task_name, result_data in sub_tasks.items():
                     # Adjusted check to handle potential None returns correctly
                     if isinstance(result_data, dict) and 'error' in result_data:
                          errors_found.append(f"{task_name}: {result_data['error']}")
                     elif result_data is None:
                          errors_found.append(f"{task_name}: Returned None unexpectedly")
                          
                if errors_found:
                     logging.error(f"Errors occurred in RAG analysis sub-tasks: {errors_found}")
                     raise ValueError(f"Error in RAG sub-task(s): {'; '.join(errors_found)}")

                # Assemble Final Result (ensure all keys are present, even if data is empty/None)
                analysis_result = {
                    "metadata": {"start_date": start_date, "end_date": end_date, "total_conversations_in_range": total_conversations_in_range},
                    "sentiment_overview": sentiment_overview if isinstance(sentiment_overview, dict) else {}, # Default to empty dict
                    "top_themes": top_themes if isinstance(top_themes, dict) else {"themes": []}, # Default structure
                    "sentiment_trends": sentiment_trends if isinstance(sentiment_trends, dict) else {"labels": [], "average_sentiment_scores": []}, # Default structure
                    "theme_sentiment_correlation": theme_sentiment_correlation if isinstance(theme_sentiment_correlation, list) else [], # Default to empty list
                    "categorized_quotes": categorized_quotes if isinstance(categorized_quotes, dict) else {"common_questions": [], "concerns_skepticism": [], "positive_interactions": {"count": 0, "quotes": []}}, # Default structure
                    "analysis_status": {"mode": "RAG", "message": "Analysis complete using RAG.", "model_name": model_name_used}
                }
                logging.info("Successfully assembled results from RAG analysis sub-tasks.")

            except Exception as e:
                logging.error(f"Error during RAG analysis orchestration: {e}", exc_info=True)
                error_occurred = True
                error_message = f"RAG Analysis Error: {str(e)}"
                # Use the empty result helper if available
                analysis_result = self.analyzer._empty_analysis_result(start_date, end_date, error_message, total_conversations_in_range) if hasattr(self.analyzer, '_empty_analysis_result') else {}

        # Cache successful RAG results
        if self.cache and not error_occurred:
            cache_timeout = 3600
            self.cache.set(cache_key, analysis_result, timeout=cache_timeout)
            logging.info(f"Cached RAG themes/sentiment data for {start_date}-{end_date} with timeout {cache_timeout}s")
        elif error_occurred:
            logging.warning(f"RAG analysis failed for {start_date}-{end_date}. Returning error structure. Not caching.")
            # Ensure the returned structure indicates error
            if 'analysis_status' not in analysis_result: analysis_result['analysis_status'] = {}
            analysis_result['analysis_status']['mode'] = "Error"
            analysis_result['analysis_status']['message'] = error_message
            analysis_result['analysis_status']['model_name'] = model_name_used

        end_time = time.time()
        logging.info(f"Completed RAG-based full themes & sentiment analysis attempt in {end_time - start_time:.2f} seconds. Status: {'Success' if not error_occurred else 'Failed'}")
        return analysis_result

    # --- Helper to parse LLM JSON robustly ---
    def _parse_llm_json(self, llm_output_raw: str, step_label: str) -> Optional[Union[Dict, List]]:
        """Attempts to parse JSON from LLM output, handling markdown code blocks."""
        try:
            # Strip whitespace first
            content = llm_output_raw.strip()
            # Handle potential markdown code blocks
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()
            elif content.startswith('```') and content.endswith('```'):
                 content = content[3:-3].strip() # Handle cases without 'json' marker
                 
            parsed = json.loads(content)
            logging.info(f"RAG Quotes ({step_label}): Successfully parsed JSON.")
            return parsed
        except json.JSONDecodeError as e:
            logging.error(f"RAG Quotes ({step_label}): Failed to parse LLM JSON response: {e}")
            logging.debug(f"Raw response: {llm_output_raw}")
            # Optionally, try more lenient parsing or return None/error
            return None # Indicate parsing failure

    # --- RAG Sub-Methods ---
    def _get_rag_sentiment_overview(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting sentiment overview (using full transcripts) for {start_date} to {end_date}")
        internal_query = "Overall sentiment and tone of conversations between psychic Lily and callers."
        expected_structure = {
            "overall_sentiment_label": "string (Positive/Neutral/Negative)",
            "sentiment_distribution": {"very_positive": "int", "positive": "int", "neutral": "int", "negative": "int", "very_negative": "int"},
            "caller_average_sentiment": "float (-1 to 1)",
            "agent_average_sentiment": "float (-1 to 1)"
        }
        default_empty_result = {
            "overall_sentiment_label": "Neutral", "sentiment_distribution": {},
            "caller_average_sentiment": 0, "agent_average_sentiment": 0
        }
        SEARCH_LIMIT, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS = 15, 10, 60000 
        
        try:
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client: return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized: return {'error': 'Conversation service unavailable'}
            openai_client = self.analyzer.openai_client

            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding: return {'error': 'Failed to get embedding for internal sentiment query'}

            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT, similarity_threshold=threshold
            )
            
            # --- CORRECTED ACCESS PATTERN --- 
            if 'error' in similar_conversations_info:
                logging.error(f"RAG Sentiment Overview: Error finding similar conversations: {similar_conversations_info['error']}")
                return {'error': similar_conversations_info['error']}
            candidate_conversations = similar_conversations_info.get('conversations', [])
            logging.info(f"RAG Sentiment Overview: Found {len(candidate_conversations)} candidate conversations via vector search.")
            # --- END CORRECTION ---

            if not candidate_conversations:
                logging.warning("RAG Sentiment Overview: No relevant conversations found via vector search. Returning default structure.")
                return default_empty_result

            # --- Fetch Full Transcripts & Build Context ---
            context, conv_id_map, conversations_used_count = self._build_transcript_context(
                 candidate_conversations, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS, "Sentiment Overview"
            )
            if conversations_used_count == 0:
                 logging.error("RAG Sentiment Overview: Failed to build any context from transcripts. Aborting.")
                 return default_empty_result
                 
            logging.info(f"RAG Sentiment Overview: Built context using {conversations_used_count} full transcripts (~{len(context)} chars).")

            # --- LLM Prompt & Call ---
            system_prompt = (
                 f"You are an expert conversation analyst. Analyze the provided FULL CONVERSATION TRANSCRIPTS (between psychic Lily and callers) "
                 f"to determine the overall sentiment overview for the period {start_date} to {end_date}. "
                 f"Focus *only* on the provided transcripts. Calculate aggregate sentiment metrics. "
                 f"Return ONLY a valid JSON object with the following structure and data types:\n"
                 f"```json\n{json.dumps(expected_structure, indent=2)}\n```"
                 f"Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context}"
            logging.info(f"RAG Sentiment Overview (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=500
            )
            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Sentiment Overview (Full Transcript): Received response from LLM.")

            # --- Parse & Validate ---
            parsed_output = self._parse_llm_json(llm_output_raw, "Sentiment Overview")
            if parsed_output is None: return {'error': 'Failed to parse LLM JSON for sentiment overview'}
            if not all(k in parsed_output for k in expected_structure.keys()):
                 logging.error(f"RAG Sentiment Overview (Full Transcript): LLM JSON missing expected keys. Got: {parsed_output.keys()}")
                 return {'error': 'LLM JSON structure mismatch for sentiment overview'}
                 
            logging.info("RAG Sentiment Overview (Full Transcript): Successfully parsed LLM response.")
            return parsed_output

        except Exception as e:
            logging.error(f"RAG Sentiment Overview (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in sentiment overview: {str(e)}'}

    def _get_rag_top_themes(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting top themes (using full transcripts) for {start_date} to {end_date}")
        internal_query = "What are the main topics, subjects, or themes discussed in these conversations between psychic Lily and callers?"
        expected_structure = {"themes": [{"theme": "string", "count": "int"}]}
        default_empty_result = {"themes": []}
        SEARCH_LIMIT, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS = 20, 10, 60000 
        
        try:
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client: return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized: return {'error': 'Conversation service unavailable'}
            openai_client = self.analyzer.openai_client

            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding: return {'error': 'Failed to get embedding for internal themes query'}

            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT, similarity_threshold=threshold
            )

            # --- CORRECTED ACCESS PATTERN --- 
            if 'error' in similar_conversations_info:
                logging.error(f"RAG Top Themes: Error finding similar conversations: {similar_conversations_info['error']}")
                return {'error': similar_conversations_info['error']}
            candidate_conversations = similar_conversations_info.get('conversations', [])
            logging.info(f"RAG Top Themes: Found {len(candidate_conversations)} candidate conversations via vector search.")
            # --- END CORRECTION --- 

            if not candidate_conversations:
                logging.warning(f"RAG Top Themes: No relevant conversations found via vector search. Returning empty list.")
                return default_empty_result

            # --- Fetch Full Transcripts & Build Context ---
            context, conv_id_map, conversations_used_count = self._build_transcript_context(
                 candidate_conversations, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS, "Top Themes"
            )
            if conversations_used_count == 0:
                 logging.error("RAG Top Themes: Failed to build any context from transcripts. Aborting.")
                 return default_empty_result
                 
            logging.info(f"RAG Top Themes: Built context using {conversations_used_count} full transcripts (~{len(context)} chars).")

            # --- LLM Prompt & Call ---
            system_prompt = (
                 f"You are an expert conversation analyst. Analyze the provided FULL CONVERSATION TRANSCRIPTS (between psychic Lily and callers) "
                 f"from the period {start_date} to {end_date}. "
                 f"Identify the top 10 most frequently discussed themes or topics based *only* on these transcripts. Estimate the count (number of conversations mentioning the theme) for each theme. "
                 f"Return ONLY a valid JSON object with the following structure:\n"
                 f"```json\n{{\"themes\": [{{\"theme\": \"string\", \"count\": int}}, ...]}}\n```"
                 f"The list should be sorted in descending order by count. Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context}"
            logging.info(f"RAG Top Themes (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=800
            )
            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Top Themes (Full Transcript): Received response from LLM.")

            # --- Parse & Validate ---
            parsed_output = self._parse_llm_json(llm_output_raw, "Top Themes")
            if parsed_output is None: return {'error': 'Failed to parse LLM JSON for top themes'}
            if 'themes' not in parsed_output or not isinstance(parsed_output['themes'], list):
                 logging.error(f"RAG Top Themes (Full Transcript): LLM JSON missing 'themes' list. Got: {parsed_output}")
                 return {'error': "LLM JSON structure mismatch (missing themes list)"}
            # Optional: Validate items in the list
            for item in parsed_output['themes']:
                 if not isinstance(item, dict) or 'theme' not in item or 'count' not in item:
                      logging.warning(f"RAG Top Themes (Full Transcript): Invalid item in themes list: {item}")
                      return {'error': "Invalid item structure in themes list"}

            logging.info("RAG Top Themes (Full Transcript): Successfully parsed LLM response.")
            return parsed_output

        except Exception as e:
            logging.error(f"RAG Top Themes (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in top themes: {str(e)}'}

    def _get_rag_sentiment_trends(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting sentiment trends (using full transcripts) for {start_date} to {end_date}")
        internal_query = f"Analyze the sentiment progression day-by-day between {start_date} and {end_date} based on conversations between psychic Lily and callers."
        expected_structure = {"labels": ["YYYY-MM-DD"], "average_sentiment_scores": ["float (-1 to 1)"]}
        default_empty_result = {"labels": [], "average_sentiment_scores": []}
        SEARCH_LIMIT, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS = 30, 15, 80000 
        
        try:
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client: return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized: return {'error': 'Conversation service unavailable'}
            openai_client = self.analyzer.openai_client

            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding: return {'error': 'Failed to get embedding for internal trends query'}

            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT, similarity_threshold=threshold
            )

            # --- CORRECTED ACCESS PATTERN --- 
            if 'error' in similar_conversations_info:
                logging.error(f"RAG Sentiment Trends: Error finding similar conversations: {similar_conversations_info['error']}")
                return {'error': similar_conversations_info['error']}
            candidate_conversations = similar_conversations_info.get('conversations', [])
            logging.info(f"RAG Sentiment Trends: Found {len(candidate_conversations)} candidate conversations via vector search.")
            # --- END CORRECTION --- 

            if not candidate_conversations:
                logging.warning(f"RAG Sentiment Trends: No relevant conversations found via vector search. Returning empty structure.")
                return default_empty_result

            # --- Fetch Full Transcripts & Build Context ---
            context, conv_id_map, conversations_used_count = self._build_transcript_context(
                 candidate_conversations, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS, "Sentiment Trends"
            )
            if conversations_used_count == 0:
                 logging.error("RAG Sentiment Trends: Failed to build any context from transcripts. Aborting.")
                 return default_empty_result
                 
            logging.info(f"RAG Sentiment Trends: Built context using {conversations_used_count} full transcripts (~{len(context)} chars).")

            # --- LLM Prompt & Call ---
            system_prompt = (
                 f"You are an expert conversation analyst. Based *only* on the provided sample of FULL CONVERSATION TRANSCRIPTS "
                 f"(between psychic Lily and callers) from the period {start_date} to {end_date}, estimate the daily average sentiment trend. "
                 f"Infer the trend from the content and associated dates (included in context) of the transcripts. "
                 f"Return ONLY a valid JSON object with the following structure, including only dates within the range {start_date} to {end_date} that likely had conversations based on the transcripts:\n"
                 f"```json\n{{\"labels\": [\"YYYY-MM-DD\", ...], \"average_sentiment_scores\": [float, ...]}}\n```"
                 f"The lists must correspond (same length). Scores should be between -1 and 1. If no trend can be determined from the transcripts, return empty lists. Do not include explanations or commentary outside the JSON structure."
            )
            user_prompt = f"Conversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context}"
            logging.info(f"RAG Sentiment Trends (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.2, max_tokens=1000
            )
            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Sentiment Trends (Full Transcript): Received response from LLM.")

            # --- Parse & Validate ---
            parsed_output = self._parse_llm_json(llm_output_raw, "Sentiment Trends")
            if parsed_output is None: return {'error': 'Failed to parse LLM JSON for sentiment trends'}
            if 'labels' not in parsed_output or 'average_sentiment_scores' not in parsed_output or \
               not isinstance(parsed_output['labels'], list) or not isinstance(parsed_output['average_sentiment_scores'], list) or \
               len(parsed_output['labels']) != len(parsed_output['average_sentiment_scores']):
                 logging.error(f"RAG Sentiment Trends (Full Transcript): LLM JSON invalid structure/mismatch. Got: {parsed_output}")
                 return {'error': "LLM JSON structure mismatch for trends"}

            logging.info("RAG Sentiment Trends (Full Transcript): Successfully parsed LLM response.")
            return parsed_output

        except Exception as e:
            logging.error(f"RAG Sentiment Trends (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in sentiment trends: {str(e)}'}

    def _get_rag_theme_sentiment_correlation(self, start_date: str, end_date: str, top_themes: List[Dict]) -> Optional[Union[List, Dict]]: # Return list on success, dict on error
        logging.info(f"RAG: Getting theme/sentiment correlation (using full transcripts) for {start_date} to {end_date}")
        
        if not top_themes:
            logging.warning("RAG Theme/Sentiment Corr: No top themes provided. Skipping correlation.")
            return [] 
        
        theme_names = [t.get('theme', 'Unknown') for t in top_themes]
        internal_query = f"What is the general sentiment (Positive, Negative, Neutral, or Mixed) associated with each of these specific themes: {', '.join(theme_names)}? Base the analysis on conversations between psychic Lily and callers."
        expected_item_structure = {"theme": "string", "mentions": "int", "sentiment_label": "string (e.g., Positive, Negative, Neutral, Mixed)"}
        SEARCH_LIMIT, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS = 20, 10, 70000 

        try:
            if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client: return {'error': 'OpenAI client unavailable'}
            if not self.conversation_service or not self.conversation_service.initialized: return {'error': 'Conversation service unavailable'}
            openai_client = self.analyzer.openai_client

            query_embedding = _get_openai_embedding(internal_query, openai_client)
            if not query_embedding: return {'error': 'Failed to get embedding for internal correlation query'}

            threshold = 0.35
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT, similarity_threshold=threshold
            )

            # --- CORRECTED ACCESS PATTERN --- 
            if 'error' in similar_conversations_info:
                logging.error(f"RAG Theme/Sentiment Corr: Error finding similar conversations: {similar_conversations_info['error']}")
                return {'error': similar_conversations_info['error']}
            candidate_conversations = similar_conversations_info.get('conversations', [])
            logging.info(f"RAG Theme/Sentiment Corr: Found {len(candidate_conversations)} candidate conversations via vector search.")
            # --- END CORRECTION --- 

            if not candidate_conversations:
                logging.warning("RAG Theme/Sentiment Corr: No similar conversations found.")
                return [] # Return empty list as expected

            # --- Fetch Full Transcripts & Build Context ---
            context, conv_id_map, conversations_used_count = self._build_transcript_context(
                 candidate_conversations, CONTEXT_TRANSCRIPT_LIMIT, MAX_CONTEXT_CHARS, "Theme/Sentiment Correlation"
            )
            if conversations_used_count == 0:
                 logging.error("RAG Theme/Sentiment Corr: Failed to build any context from transcripts. Aborting.")
                 return [] 
                 
            logging.info(f"RAG Theme/Sentiment Corr: Built context using {conversations_used_count} full transcripts (~{len(context)} chars).")

            # --- LLM Prompt & Call ---
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
            user_prompt = f"Input Themes:\n{themes_input_str}\n\nConversation Transcripts Sample (Use the number like '1', '2' for conversation_id):\n{context}"
            logging.info(f"RAG Theme/Sentiment Corr (Full Transcript): Sending prompt to LLM ({self.analyzer.model_name})...")
            completion = openai_client.chat.completions.create(
                model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"}, 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1, max_tokens=1000
            )
            llm_output_raw = completion.choices[0].message.content.strip()
            logging.info("RAG Theme/Sentiment Corr (Full Transcript): Received response from LLM.")
            
            # --- RE-ADD RAW LOGGING --- 
            logging.debug(f"RAG Theme/Sentiment Corr (Full Transcript): RAW LLM Output:\n{llm_output_raw}")
            # --- END RAW LOGGING ---

            # --- Parse & Validate --- 
            parsed_output = self._parse_llm_json(llm_output_raw, "Theme/Sentiment Corr")
            if parsed_output is None: 
                 return {'error': 'Failed to parse LLM JSON for correlation'} 
            
            # --- EVEN MORE ROBUST LIST EXTRACTION --- 
            correlation_list = []
            found_list = False
            if isinstance(parsed_output, list):
                 # Case 1: LLM returned a list directly (ideal)
                 correlation_list = parsed_output
                 found_list = True
                 logging.info("RAG Theme/Sentiment Corr: LLM returned a list directly.")
            elif isinstance(parsed_output, dict):
                 # Case 2: LLM returned a dictionary. Try common key names first.
                 potential_keys = ['correlations', 'themes', 'results', 'data']
                 for key in potential_keys:
                      if key in parsed_output and isinstance(parsed_output[key], list):
                           correlation_list = parsed_output[key]
                           found_list = True
                           logging.info(f"RAG Theme/Sentiment Corr: Extracted list from dictionary key: '{key}'.")
                           break
                 # Case 3: If not found via common keys, check if ANY value is a list
                 if not found_list:
                     for value in parsed_output.values():
                         if isinstance(value, list):
                             # Assume the first list found is the one we want
                             correlation_list = value
                             found_list = True
                             logging.warning(f"RAG Theme/Sentiment Corr: Extracted list from an unexpected dictionary key.")
                             break 
                 # Case 4: Dictionary received, but no list found within it
                 if not found_list:
                    logging.error(f"RAG Theme/Sentiment Corr: LLM returned dict, but no list found as a value. Keys: {parsed_output.keys()}")
                    raise ValueError("LLM returned dictionary, but no list value found within it.")
            else:
                 # Case 5: Unexpected structure (neither list nor dict)
                 logging.error(f"RAG Theme/Sentiment Corr: LLM returned unexpected structure: {type(parsed_output)}")
                 raise ValueError(f"LLM JSON is not a list or a dictionary. Structure: {type(parsed_output)}")
            # --- END EVEN MORE ROBUST LIST EXTRACTION ---

            validated_list = []
            # Check the extracted list (should always be a list type now or error raised above)
            if not isinstance(correlation_list, list): 
                 # This check is slightly redundant now but kept as safety
                 logging.error("RAG Theme/Sentiment Corr: Internal Error - correlation_list is not a list after extraction logic.")
                 raise ValueError("Internal error: Parsed result is not a list after extraction.")
                 
            for item in correlation_list:
                 if not isinstance(item, dict) or not all(k in item for k in expected_item_structure.keys()):
                      logging.warning(f"RAG Theme/Sentiment Corr (Full Transcript): Invalid item structure in list: {item}. Skipping.")
                      continue # Skip invalid items instead of erroring out the whole request? Or keep erroring?
                      # raise ValueError("Invalid item structure in themes list") # Stricter validation
                 validated_list.append(item)
            
            if len(validated_list) != len(top_themes):
                 logging.warning(f"RAG Theme/Sentiment Corr (Full Transcript): Output list length ({len(validated_list)}) doesn't match input themes ({len(top_themes)}). This might be acceptable if LLM couldn't correlate all themes.")

            logging.info("RAG Theme/Sentiment Corr (Full Transcript): Successfully processed LLM response.") # Changed log message
            return validated_list

        except Exception as e:
            logging.error(f"RAG Theme/Sentiment Corr (Full Transcript): Unexpected error: {e}", exc_info=True)
            return {'error': f'Unexpected error in theme/sentiment correlation: {str(e)}'}

    def _get_rag_categorized_quotes(self, start_date: str, end_date: str) -> Optional[Dict]:
        logging.info(f"RAG: Getting categorized quotes (using full transcripts) for {start_date} to {end_date} [Multi-Step]")
        final_result = {"common_questions": [], "concerns_skepticism": [], "positive_interactions": {"count": 0, "quotes": []}}
        error_occurred = False
        error_messages = []

        if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client: return {'error': 'OpenAI client unavailable'}
        if not self.conversation_service or not self.conversation_service.initialized: return {'error': 'Conversation service unavailable'}
        openai_client = self.analyzer.openai_client

        # --- STEP 1: Get Common Questions & Concerns/Skepticism --- 
        logging.info("RAG Quotes: --- Starting Step 1: Questions & Concerns ---")
        try:
            internal_query_qc = f"Identify common questions asked by callers and any concerns or skepticism expressed in conversations between psychic Lily and callers between {start_date} and {end_date}."
            expected_structure_qc = {
                "common_questions": [{"category_name": "string", "count": "int", "quotes": [{"quote_text": "string", "conversation_id": "string or null"}]}],
                "concerns_skepticism": [{"category_name": "string", "count": "int", "quotes": [{"quote_text": "string", "conversation_id": "string or null"}]}]
            }
            SEARCH_LIMIT_QC, CONTEXT_TRANSCRIPT_LIMIT_QC, MAX_CONTEXT_CHARS_QC = 25, 12, 70000 
            threshold = 0.35

            query_embedding_qc = _get_openai_embedding(internal_query_qc, openai_client)
            if not query_embedding_qc: raise ValueError('Failed to get embedding for internal QC query')

            similar_conversations_qc = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding_qc, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT_QC, similarity_threshold=threshold
            )

            # --- CORRECTED ACCESS PATTERN (QC) --- 
            if 'error' in similar_conversations_qc:
                logging.error(f"RAG Quotes (QC): Error finding similar conversations: {similar_conversations_qc['error']}")
                raise ValueError(f"QC Step Error: {similar_conversations_qc['error']}")
            candidate_conversations_qc = similar_conversations_qc.get('conversations', [])
            logging.info(f"RAG Quotes (QC): Found {len(candidate_conversations_qc)} candidate conversations.")
            # --- END CORRECTION (QC) ---

            if candidate_conversations_qc:
                context_qc, conv_id_map_qc, used_count_qc = self._build_transcript_context(
                    candidate_conversations_qc, CONTEXT_TRANSCRIPT_LIMIT_QC, MAX_CONTEXT_CHARS_QC, "QC"
                )
                if used_count_qc == 0:
                    logging.warning("RAG Quotes (QC): Failed to build context. Skipping QC step.")
                    final_result['common_questions'], final_result['concerns_skepticism'] = [], []
                else:
                    # --- LLM Prompt & Call for QC ---
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
                    logging.info(f"RAG Quotes (QC): Sending prompt to LLM ({self.analyzer.model_name})...")
                    completion_qc = openai_client.chat.completions.create(
                        model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                        messages=[{"role": "system", "content": system_prompt_qc}, {"role": "user", "content": user_prompt_qc}],
                        temperature=0.1, max_tokens=2000
                    )
                    llm_output_raw_qc = completion_qc.choices[0].message.content.strip()
                    logging.info(f"RAG Quotes (QC): Received response from LLM.")
                    
                    parsed_output_qc = self._parse_llm_json(llm_output_raw_qc, "QC")
                    if not parsed_output_qc or not all(k in parsed_output_qc for k in expected_structure_qc.keys()):
                        raise ValueError("QC LLM output missing required keys or failed parsing")
                    
                    self._map_context_ids_to_external(parsed_output_qc.get('common_questions'), conv_id_map_qc)
                    self._map_context_ids_to_external(parsed_output_qc.get('concerns_skepticism'), conv_id_map_qc)
                    final_result['common_questions'] = parsed_output_qc.get('common_questions', [])
                    final_result['concerns_skepticism'] = parsed_output_qc.get('concerns_skepticism', [])
                    logging.info("RAG Quotes (QC): Successfully processed questions and concerns.")
            else:
                logging.warning("RAG Quotes (QC): No candidates, skipping context build and LLM call.")
                final_result['common_questions'], final_result['concerns_skepticism'] = [], []
        except Exception as e_qc:
            logging.error(f"RAG Quotes (QC): Error during Questions/Concerns step: {e_qc}", exc_info=True)
            error_occurred = True
            error_messages.append(f"QC Step Error: {str(e_qc)}")
            final_result['common_questions'], final_result['concerns_skepticism'] = [], []

        # --- STEP 2: Get Positive Interactions --- 
        logging.info("RAG Quotes: --- Starting Step 2: Positive Interactions ---")
        try:
            internal_query_pos = f"Identify specific examples of positive interactions, caller satisfaction, or successful connections in conversations between psychic Lily and callers between {start_date} and {end_date}."
            expected_structure_pos = {"positive_interactions": {"count": "int", "quotes": [{"quote_text": "string", "conversation_id": "string or null", "sentiment_score": "float"}]}}
            SEARCH_LIMIT_POS, CONTEXT_TRANSCRIPT_LIMIT_POS, MAX_CONTEXT_CHARS_POS = 20, 10, 60000 
            threshold_pos = 0.35

            query_embedding_pos = _get_openai_embedding(internal_query_pos, openai_client)
            if not query_embedding_pos: raise ValueError('Failed to get embedding for internal positive query')

            similar_conversations_pos = self.conversation_service.find_similar_conversations(
                query_vector=query_embedding_pos, start_date=start_date, end_date=end_date,
                limit=SEARCH_LIMIT_POS, similarity_threshold=threshold_pos
            )

            # --- CORRECTED ACCESS PATTERN (Pos) ---
            if 'error' in similar_conversations_pos:
                logging.error(f"RAG Quotes (Pos): Error finding similar conversations: {similar_conversations_pos['error']}")
                raise ValueError(f"Positive Step Error: {similar_conversations_pos['error']}")
            candidate_conversations_pos = similar_conversations_pos.get('conversations', [])
            logging.info(f"RAG Quotes (Pos): Found {len(candidate_conversations_pos)} candidate conversations.")
            # --- END CORRECTION (Pos) ---

            if candidate_conversations_pos:
                context_pos, conv_id_map_pos, used_count_pos = self._build_transcript_context(
                    candidate_conversations_pos, CONTEXT_TRANSCRIPT_LIMIT_POS, MAX_CONTEXT_CHARS_POS, "Pos"
                )
                if used_count_pos == 0:
                    logging.warning("RAG Quotes (Pos): Failed to build context. Skipping Positive step.")
                    final_result['positive_interactions'] = {"count": 0, "quotes": []}
                else:
                    # --- LLM Prompt & Call for Positive --- 
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
                    logging.info(f"RAG Quotes (Pos): Sending prompt to LLM ({self.analyzer.model_name})...")
                    completion_pos = openai_client.chat.completions.create(
                        model=self.analyzer.model_name or "gpt-4o", response_format={"type": "json_object"},
                        messages=[{"role": "system", "content": system_prompt_pos}, {"role": "user", "content": user_prompt_pos}],
                        temperature=0.1, max_tokens=1500
                    )
                    llm_output_raw_pos = completion_pos.choices[0].message.content.strip()
                    logging.info(f"RAG Quotes (Pos): Received response from LLM.")
                    
                    parsed_output_pos = self._parse_llm_json(llm_output_raw_pos, "Positive")
                    if not parsed_output_pos or "positive_interactions" not in parsed_output_pos or not isinstance(parsed_output_pos["positive_interactions"], dict):
                        raise ValueError("Positive LLM output missing required structure or failed parsing")
                    
                    self._map_context_ids_to_external_positive(parsed_output_pos.get('positive_interactions'), conv_id_map_pos)
                    final_result['positive_interactions'] = parsed_output_pos.get('positive_interactions', {"count": 0, "quotes": []})
                    logging.info("RAG Quotes (Pos): Successfully processed positive interactions.")
            else:
                logging.warning("RAG Quotes (Pos): No candidates, skipping context build and LLM call.")
                final_result['positive_interactions'] = {"count": 0, "quotes": []}
        except Exception as e_pos:
            logging.error(f"RAG Quotes (Pos): Error during Positive Interactions step: {e_pos}", exc_info=True)
            error_occurred = True
            error_messages.append(f"Positive Step Error: {str(e_pos)}")
            final_result['positive_interactions'] = {"count": 0, "quotes": []}

        # --- Final Error Check --- 
        if error_occurred:
            logging.error(f"RAG Categorized Quotes completed with errors: {error_messages}")
            # Return the partial result but indicate error status in the main return dict
            return {'error': ", ".join(error_messages)}
        
        logging.info(f"RAG Categorized Quotes: Successfully completed all steps.")
        return final_result

    # --- Helper function to build context (DRY) ---
    def _build_transcript_context(self, candidate_conversations, transcript_limit, char_limit, step_label="Step"):
        """Builds context string from full transcripts and maps context index to external ID."""
        context = f"\n\n---Retrieved Conversation Transcripts for {step_label} Analysis:---\n"
        context_char_count = 0
        conversations_used_count = 0
        conv_id_map = {} # Maps context index ('1', '2'...) to external_id
        
        # Ensure we only process up to the transcript_limit
        ids_to_fetch = [conv.get('external_id') for conv in candidate_conversations[:transcript_limit] if conv.get('external_id')]
        
        logging.info(f"RAG Quotes ({step_label}): Attempting to fetch full transcripts for {len(ids_to_fetch)} conversations.")

        for idx, external_id in enumerate(ids_to_fetch):
            current_context_index = str(idx + 1) # Use 1-based index for LLM reference
            
            if context_char_count >= char_limit:
                logging.warning(f"RAG Quotes ({step_label}): Reached context character limit ({char_limit}). Using {conversations_used_count} transcripts.")
                break
            
            # Fetch full details (assumes this method exists and works)
            details = self.conversation_service.get_conversation_details(external_id)
            if not details or not details.get('transcript'):
                logging.warning(f"RAG Quotes ({step_label}): Could not fetch details or transcript for {external_id}. Skipping.")
                continue
                
            transcript_text = "\n"
            # Include date if available in details
            date_str = "Unknown Date"
            created_at = details.get('start_time') 
            if created_at:
                try: date_str = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                except: pass 
            transcript_text += f"Date: {date_str}\n"

            for msg in details.get('transcript', []):
                speaker = msg.get('role', 'unknown').capitalize()
                content = msg.get('content', '')
                transcript_text += f"{speaker}: {content}\n"
            
            # Check limit before adding
            if context_char_count + len(transcript_text) > char_limit and conversations_used_count > 0: # Allow at least one transcript even if long
                logging.warning(f"RAG Quotes ({step_label}): Adding transcript for {external_id} would exceed context limit. Stopping context build.")
                break 
                
            # Add transcript to context using the context index
            context += f"\n--- Conversation {current_context_index} (Use this number for conversation_id) ---\n{transcript_text}--- End Conversation {current_context_index} ---\n"
            context_char_count += len(transcript_text)
            conversations_used_count += 1
            conv_id_map[current_context_index] = external_id # Store mapping
        
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

    # --- RAG Method for Ad-hoc Queries ---
    def process_natural_language_query(self, query: str, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, str]:
        """
        Processes a natural language query using RAG.

        1. Generates embedding for the user query.
        2. Finds similar conversations in Supabase (using vector search + date filter).
        3. Retrieves summaries/context for those conversations.
        4. Constructs a prompt for the LLM including the query and context.
        5. Calls the LLM (GPT-4o) via ConversationAnalyzer.
        6. Returns the LLM's answer or an error dictionary.
        """
        logging.info(f"RAG Query: Processing query='{query[:50]}...', start='{start_date}', end='{end_date}'")
        start_rag_time = time.time()

        # --- Prerequisites Check ---
        if not self.analyzer or not hasattr(self.analyzer, 'openai_client') or not self.analyzer.openai_client:
            logging.error("RAG Query: OpenAI client not available in analyzer.")
            return {'error': 'RAG Query Error: LLM client unavailable.'}
        if not self.conversation_service or not self.conversation_service.initialized:
            logging.error("RAG Query: Conversation service not available.")
            return {'error': 'RAG Query Error: Conversation service unavailable.'}
        
        openai_client = self.analyzer.openai_client
        
        # --- 1. Generate Query Embedding ---
        query_vector = _get_openai_embedding(query, openai_client)
        if not query_vector:
            logging.error("RAG Query: Failed to generate embedding for the query.")
            return {'error': 'RAG Query Error: Could not generate query embedding.'}
        
        # --- 2. Find Similar Conversations ---
        try:
            logging.info("RAG Query: Finding similar conversations...")
            # Use lowered threshold for broader results
            similar_conversations_info = self.conversation_service.find_similar_conversations(
                query_vector=query_vector,
                start_date=start_date,
                end_date=end_date,
                limit=5, # Limit context for ad-hoc query
                similarity_threshold=0.35 # Using lowered threshold
            )

            if 'error' in similar_conversations_info:
                logging.error(f"RAG Query: Error finding similar conversations: {similar_conversations_info['error']}")
                return {'error': f"RAG Query Error: {similar_conversations_info['error']}"}
            
            # CORRECTED: Access the list correctly
            candidate_conversations = similar_conversations_info.get('conversations', [])
            logging.info(f"RAG Query: Found {len(candidate_conversations)} potentially relevant conversations.")

            if not candidate_conversations:
                logging.warning("RAG Query: No similar conversations found.")
                return {'answer': "I couldn't find any conversations matching your query in the selected date range. Please try rephrasing or broadening your search."}

        except Exception as e:
            logging.error(f"RAG Query: Exception during conversation similarity search: {e}", exc_info=True)
            return {'error': 'RAG Query Error: Failed during similarity search.'}
            
        # --- 3. Construct Context String (Using Summaries) ---
        context_str = ""
        missing_external_id = False
        # CORRECTED: Iterate over the correct list
        for conv in candidate_conversations: 
            if 'external_id' not in conv or not conv['external_id']:
                missing_external_id = True
                logging.warning(f"RAG Query: Conversation {conv.get('id')} is missing external_id. Context linking may fail.")
                context_str += f"Conversation Context:\n{conv.get('summary', 'Summary not available.')}\n\n"
            else:
                context_str += f"Conversation (ID: {conv['external_id']}):\n{conv.get('summary', 'Summary not available.')}\n\n"
                
        if missing_external_id: logging.warning("RAG Query: One or more conversations lacked an external_id for context building.")
        if not context_str: 
             logging.warning("RAG Query: Context string is empty despite finding conversations.")
             return {'answer': "I found some relevant conversations, but had trouble preparing the context for analysis. Please try again."}

        # --- 4. Construct LLM Prompt ---
        system_prompt = f"""
        You are Lily, a helpful AI assistant analyzing conversation transcripts between a psychic advisor (also named Lily) and a caller ('Curious Caller' or 'User').
        You are responding to a user's query about these conversations.
        Use the provided conversation CONTEXT (SUMMARIES) below to answer the user's query accurately and concisely.
        Focus *only* on the information present in the provided context snippets. Do not invent details.
        If the context doesn't contain the answer, state that clearly.
        **When referencing specific conversations from the context provided, please use the format (ID: <external_id>).**

        <Conversation Context>
        {context_str}
        </Conversation Context>
        """
        user_prompt = f"User Query: {query}"

        # --- 5. Call LLM ---
        try:
            logging.info("RAG Query: Calling LLM...")
            response = self.analyzer.openai_client.chat.completions.create(
                model=self.analyzer.model_name, 
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            )
            
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content
                llm_response = {'content': answer}
            else:
                logging.error("RAG Query: OpenAI response format unexpected or empty choices.")
                llm_response = {'error': 'Invalid response format from LLM'}
            
            if 'error' in llm_response:
                 error_detail = llm_response.get('error')
                 logging.error(f"RAG Query: LLM call failed: {error_detail}")
                 return {'error': f'RAG Query Error: Failed to get analysis from LLM ({error_detail})'}

            answer = llm_response.get('content', 'Sorry, I could not process your query.')
            logging.info(f"RAG Query: Received LLM answer: '{answer[:100]}...'")
            
            end_rag_time = time.time()
            logging.info(f"RAG Query: Completed successfully in {end_rag_time - start_rag_time:.2f} seconds.")
            return {'answer': answer}

        except Exception as e:
             logging.error(f"RAG Query: Exception during LLM call: {e}", exc_info=True)
             return {'error': 'RAG Query Error: Unexpected error during LLM analysis.'}