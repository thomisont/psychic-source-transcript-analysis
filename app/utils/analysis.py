import pandas as pd
import numpy as np
from textblob import TextBlob
import re
from collections import Counter

class ConversationAnalyzer:
    @staticmethod
    def analyze_sentiment(transcript):
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
            
            if turn.get('speaker') == 'User':
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
        stop_words = {"i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", 
                     "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
                     "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", 
                     "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
                     "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
                     "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
                     "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", 
                     "at", "by", "for", "with", "about", "against", "between", "into", "through", 
                     "during", "before", "after", "above", "below", "to", "from", "up", "down", 
                     "in", "out", "on", "off", "over", "under", "again", "further", "then", 
                     "once", "here", "there", "when", "where", "why", "how", "all", "any", 
                     "both", "each", "few", "more", "most", "other", "some", "such", "no", 
                     "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", 
                     "t", "can", "will", "just", "don't", "should", "now"}
                     
        words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
        words = [word for word in words if word not in stop_words]
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Return top N topics
        return word_counts.most_common(top_n)
        
    @staticmethod
    def analyze_conversation_metrics(conversations_df):
        """
        Calculate metrics across multiple conversations
        
        Args:
            conversations_df (DataFrame): DataFrame of conversations
            
        Returns:
            dict: Various conversation metrics
        """
        if conversations_df.empty:
            return {}
            
        # Basic statistics
        metrics = {
            'total_conversations': len(conversations_df),
            'avg_duration': conversations_df['duration'].mean() if 'duration' in conversations_df else None,
            'max_duration': conversations_df['duration'].max() if 'duration' in conversations_df else None,
            'min_duration': conversations_df['duration'].min() if 'duration' in conversations_df else None,
            'avg_turns': conversations_df['turn_count'].mean() if 'turn_count' in conversations_df else None,
        }
        
        # Add time-based analytics if timestamps are available
        if 'start_time' in conversations_df:
            conversations_df['hour'] = conversations_df['start_time'].dt.hour
            conversations_df['day_of_week'] = conversations_df['start_time'].dt.dayofweek
            
            # Count by hour
            hour_counts = conversations_df.groupby('hour').size()
            metrics['hourly_distribution'] = hour_counts.to_dict()
            
            # Count by day of week
            day_counts = conversations_df.groupby('day_of_week').size()
            metrics['day_of_week_distribution'] = day_counts.to_dict()
            
        return metrics 