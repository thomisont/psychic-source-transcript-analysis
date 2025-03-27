"""
Analysis service for handling conversation analysis operations.
"""
import logging
import traceback
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from app.utils.analysis import ConversationAnalyzer
from flask import current_app

class AnalysisService:
    """Service for handling conversation analysis operations."""
    
    def __init__(self, lightweight_mode=False):
        """Initialize the analysis service."""
        self.analyzer = ConversationAnalyzer(lightweight_mode=lightweight_mode)
        logging.info(f"Analysis service initialized with lightweight_mode={lightweight_mode}")
    
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
        """
        Analyze conversations over time to identify trends in sentiment and topics.
        
        Args:
            conversations: List of conversation data or DataFrame
            timeframe: Aggregation timeframe (day, week, month)
            
        Returns:
            dict: Analysis results including sentiment over time and topics
        """
        try:
            logging.info(f"Starting analyze_conversations_over_time with {len(conversations) if isinstance(conversations, list) else 'DataFrame'} conversations")
            import pandas as pd
            
            # Ensure conversations is a DataFrame
            if not isinstance(conversations, pd.DataFrame):
                if isinstance(conversations, list):
                    if not conversations:
                        logging.warning("Empty conversations list provided for analysis")
                        return {
                            'sentiment_over_time': [],
                            'top_themes': [],
                            'sentiment_by_theme': [],
                            'common_questions': [],
                            'concerns_skepticism': [],
                            'positive_interactions': []
                        }
                    df = pd.DataFrame(conversations)
                    logging.info(f"Converted list to DataFrame with {len(df)} rows and columns: {df.columns.tolist()}")
                else:
                    logging.error(f"Unsupported data type for conversations: {type(conversations)}")
                    return {
                        'sentiment_over_time': [],
                        'top_themes': [],
                        'sentiment_by_theme': [],
                        'common_questions': [],
                        'concerns_skepticism': [],
                        'positive_interactions': []
                    }
            else:
                df = conversations
                
            # Handle empty DataFrame
            if df.empty:
                logging.warning("Empty DataFrame provided for analysis")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': [],
                    'common_questions': [],
                    'concerns_skepticism': [],
                    'positive_interactions': []
                }
                
            # Ensure start_time is a datetime
            if 'start_time' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['start_time']):
                    df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
                    df = df.dropna(subset=['start_time'])
                    logging.info(f"Converted start_time to datetime, now have {len(df)} valid rows")
            else:
                logging.warning("No start_time column in conversations data for time-based analysis")
                logging.info(f"Available columns: {df.columns.tolist()}")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': [],
                    'common_questions': [],
                    'concerns_skepticism': [],
                    'positive_interactions': []
                }
                
            # If we have no data after cleaning, return empty results
            if df.empty:
                logging.warning("No valid conversations after date parsing")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': [],
                    'common_questions': [],
                    'concerns_skepticism': [],
                    'positive_interactions': []
                }
            
            # Aggregate by timeframe
            if timeframe == 'week':
                df['period'] = df['start_time'].dt.isocalendar().week.astype(str) + '-' + df['start_time'].dt.isocalendar().year.astype(str)
                logging.info(f"Aggregating by week, created {df['period'].nunique()} unique periods")
            elif timeframe == 'month':
                df['period'] = df['start_time'].dt.strftime('%Y-%m')
                logging.info(f"Aggregating by month, created {df['period'].nunique()} unique periods")
            else:  # day
                df['period'] = df['start_time'].dt.strftime('%Y-%m-%d')
                logging.info(f"Aggregating by day, created {df['period'].nunique()} unique periods")
                
            # Log conversation IDs for debugging
            logging.info(f"Conversation IDs in analysis: {df['conversation_id'].tolist()[:5]}...")
            
            # Calculate sentiment over time
            sentiment_over_time = []
            
            # Check if sentiment data is available
            if 'sentiment' in df.columns:
                # Group by period and calculate average sentiment
                period_sentiment = df.groupby('period')['sentiment'].mean().reset_index()
                sentiment_over_time = [
                    {
                        'period': row['period'],
                        'sentiment': float(row['sentiment'])  # Convert to native Python type
                    }
                    for _, row in period_sentiment.iterrows()
                ]
            else:
                logging.warning("No sentiment column in conversations data, calculating from transcripts...")
                
                # Get transcripts for each conversation
                conversations_with_transcripts = []
                for idx, row in df.iterrows():
                    conv_id = row.get('conversation_id')
                    if not conv_id:
                        continue
                    
                    # Get period for this conversation    
                    period = row.get('period', None)
                    if not period:
                        continue
                        
                    # Get full conversation data with transcript
                    try:
                        conv_data = current_app.conversation_service.get_conversation_details(conv_id)
                        if conv_data and 'transcript' in conv_data and conv_data['transcript']:
                            # Add period to conversation data
                            conv_data['period'] = period
                            conversations_with_transcripts.append(conv_data)
                    except Exception as e:
                        logging.warning(f"Error getting transcript for conversation {conv_id}: {e}")
                
                # Group conversations by period
                period_groups = {}
                for conv in conversations_with_transcripts:
                    period = conv.get('period')
                    if not period:
                        continue
                        
                    if period not in period_groups:
                        period_groups[period] = []
                    
                    period_groups[period].append(conv)
                
                # Calculate average sentiment for each period
                for period, convs in period_groups.items():
                    # Skip if no conversations in this period
                    if not convs:
                        continue
                        
                    # Calculate sentiment for each conversation
                    period_sentiments = []
                    for conv in convs:
                        transcript = conv.get('transcript', [])
                        if not transcript:
                            continue
                            
                        # Analyze sentiment for this conversation
                        sentiment_data = self.analyzer.analyze_sentiment(transcript)
                        if sentiment_data:
                            period_sentiments.append(sentiment_data.get('overall', 0))
                    
                    # Calculate average sentiment for this period
                    if period_sentiments:
                        avg_sentiment = sum(period_sentiments) / len(period_sentiments)
                        sentiment_over_time.append({
                            'period': period,
                            'sentiment': float(avg_sentiment)
                        })
                
                logging.info(f"Calculated sentiment for {len(sentiment_over_time)} periods from transcripts")
            
            # Extract and analyze themes/topics
            themes_analysis = self._extract_themes(df)
            
            return {
                'sentiment_over_time': sentiment_over_time,
                'top_themes': themes_analysis.get('top_themes', []),
                'sentiment_by_theme': themes_analysis.get('sentiment_by_theme', []),
                'common_questions': themes_analysis.get('common_questions', []),
                'concerns_skepticism': themes_analysis.get('concerns_skepticism', []),
                'positive_interactions': themes_analysis.get('positive_interactions', [])
            }
            
        except Exception as e:
            logging.error(f"Error in analyze_conversations_over_time: {e}")
            logging.error(traceback.format_exc())
            
            # Return empty results on error
            return {
                'sentiment_over_time': [],
                'top_themes': [],
                'sentiment_by_theme': [],
                'common_questions': [],
                'concerns_skepticism': [],
                'positive_interactions': []
            }
    
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
        for conv_id in conversation_ids:
            if not conv_id:
                continue
                
            try:
                conv_data = current_app.conversation_service.get_conversation_details(conv_id)
                
                if conv_data and 'transcript' in conv_data and conv_data['transcript']:
                    result[conv_id] = conv_data
                    logging.info(f"Successfully retrieved transcript for conversation {conv_id}")
                else:
                    logging.warning(f"No transcript found for conversation {conv_id}")
            except Exception as e:
                logging.error(f"Error fetching transcript for conversation {conv_id}: {e}")
                logging.error(traceback.format_exc())
                
        logging.info(f"Successfully retrieved {len(result)}/{len(conversation_ids)} conversation transcripts")
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
            
            # Fetch all conversation data in a single batch for efficiency
            conversation_map = self.get_transcripts_for_conversations(conversation_ids)
            conversations_with_transcripts = list(conversation_map.values())
            
            logging.info(f"Found {len(conversations_with_transcripts)} conversations with transcripts")
            
            if not conversations_with_transcripts:
                logging.warning("No conversations with transcripts found")
                return {
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
            
            # Extract themes using the conversation analyzer
            logging.info("Calling extract_aggregate_topics with conversation transcripts")
            top_themes = self.analyzer.extract_aggregate_topics(conversations_with_transcripts)
            logging.info(f"Extracted {len(top_themes)} themes")
            
            # Extract sentiment by theme correlation
            logging.info("Calling analyze_theme_sentiment_correlation with conversation transcripts")
            sentiment_by_theme = self.analyzer.analyze_theme_sentiment_correlation(conversations_with_transcripts)
            logging.info(f"Extracted {len(sentiment_by_theme)} theme-sentiment correlations")
            
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
            
            # Log the results
            logging.info(f"Extracted {len(top_themes)} themes, {len(sentiment_by_theme)} theme-sentiment correlations, " +
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