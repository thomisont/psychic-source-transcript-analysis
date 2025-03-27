"""
Analysis service for handling conversation analysis operations.
"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from app.utils.analysis import ConversationAnalyzer

class AnalysisService:
    """Service for handling conversation analysis operations."""
    
    def __init__(self):
        """Initialize the analysis service."""
        self.analyzer = ConversationAnalyzer()
    
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
            import pandas as pd
            
            # Ensure conversations is a DataFrame
            if not isinstance(conversations, pd.DataFrame):
                if isinstance(conversations, list):
                    if not conversations:
                        logging.warning("Empty conversations list provided for analysis")
                        return {
                            'sentiment_over_time': [],
                            'top_themes': [],
                            'sentiment_by_theme': []
                        }
                    df = pd.DataFrame(conversations)
                else:
                    logging.error(f"Unsupported data type for conversations: {type(conversations)}")
                    return {
                        'sentiment_over_time': [],
                        'top_themes': [],
                        'sentiment_by_theme': []
                    }
            else:
                df = conversations
                
            # Handle empty DataFrame
            if df.empty:
                logging.warning("Empty DataFrame provided for analysis")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
                
            # Ensure start_time is a datetime
            if 'start_time' in df.columns:
                if not pd.api.types.is_datetime64_any_dtype(df['start_time']):
                    df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
                    df = df.dropna(subset=['start_time'])
            else:
                logging.warning("No start_time column in conversations data for time-based analysis")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
                
            # If we have no data after cleaning, return empty results
            if df.empty:
                logging.warning("No valid conversations after date parsing")
                return {
                    'sentiment_over_time': [],
                    'top_themes': [],
                    'sentiment_by_theme': []
                }
            
            # Aggregate by timeframe
            if timeframe == 'week':
                df['period'] = df['start_time'].dt.isocalendar().week.astype(str) + '-' + df['start_time'].dt.isocalendar().year.astype(str)
            elif timeframe == 'month':
                df['period'] = df['start_time'].dt.strftime('%Y-%m')
            else:  # day
                df['period'] = df['start_time'].dt.strftime('%Y-%m-%d')
            
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
                logging.warning("No sentiment column in conversations data")
            
            # Extract and analyze themes/topics
            themes_analysis = self._extract_themes(df)
            
            return {
                'sentiment_over_time': sentiment_over_time,
                'top_themes': themes_analysis.get('top_themes', []),
                'sentiment_by_theme': themes_analysis.get('sentiment_by_theme', [])
            }
            
        except Exception as e:
            logging.error(f"Error in analyze_conversations_over_time: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
            # Return empty results on error
            return {
                'sentiment_over_time': [],
                'top_themes': [],
                'sentiment_by_theme': []
            }
    
    def _extract_themes(self, df):
        """
        Extract themes/topics from conversations and their associated sentiment.
        
        Args:
            df: DataFrame of conversations
            
        Returns:
            dict: Top themes and sentiment by theme
        """
        try:
            # If there are no common themes available and no NLP capabilities,
            # return empty data rather than generating fake/random themes
            logging.info("No theme extraction capability available, returning empty themes data")
            
            return {
                'top_themes': [],
                'sentiment_by_theme': []
            }
            
        except Exception as e:
            logging.error(f"Error extracting themes: {e}")
            # Return empty results on error
            return {
                'top_themes': [],
                'sentiment_by_theme': []
            } 