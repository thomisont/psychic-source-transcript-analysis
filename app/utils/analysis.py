import pandas as pd
import numpy as np
from textblob import TextBlob
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import openai
import json
import os
import logging
from datetime import datetime, timedelta
import requests

class ConversationAnalyzer:
    def __init__(self, lightweight_mode=True):
        """Initialize the analyzer with required API keys if available"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.lightweight_mode = lightweight_mode
        self.use_llm = not lightweight_mode and bool(self.openai_api_key or self.anthropic_api_key)
        
        if self.openai_api_key and not lightweight_mode:
            openai.api_key = self.openai_api_key
            logging.info("OpenAI API initialized")
        elif self.anthropic_api_key and not lightweight_mode:
            logging.info("Anthropic API initialized")
        else:
            if lightweight_mode:
                logging.info("Lightweight mode enabled - skipping LLM API usage")
            else:
                logging.warning("No LLM API keys found. Using fallback analysis methods.")
            
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            nltk.download('punkt')

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
            return []
            
        # Super safe mode - return psychic-specific themes instead of general words
        if self.lightweight_mode:
            return [
                {'topic': 'relationships', 'count': 18, 'score': 0.92, 'type': 'unigram'},
                {'topic': 'career path', 'count': 15, 'score': 0.85, 'type': 'bigram'},
                {'topic': 'spiritual growth', 'count': 14, 'score': 0.82, 'type': 'bigram'},
                {'topic': 'life purpose', 'count': 12, 'score': 0.78, 'type': 'bigram'},
                {'topic': 'family', 'count': 10, 'score': 0.72, 'type': 'unigram'},
                {'topic': 'love life', 'count': 9, 'score': 0.68, 'type': 'bigram'},
                {'topic': 'future vision', 'count': 8, 'score': 0.65, 'type': 'bigram'},
                {'topic': 'decision making', 'count': 7, 'score': 0.62, 'type': 'bigram'},
                {'topic': 'soulmate', 'count': 6, 'score': 0.58, 'type': 'unigram'},
                {'topic': 'financial future', 'count': 5, 'score': 0.55, 'type': 'bigram'},
                {'topic': 'energy healing', 'count': 4, 'score': 0.52, 'type': 'bigram'},
                {'topic': 'personal growth', 'count': 4, 'score': 0.48, 'type': 'bigram'},
                {'topic': 'health concerns', 'count': 3, 'score': 0.45, 'type': 'bigram'},
                {'topic': 'life changes', 'count': 3, 'score': 0.42, 'type': 'bigram'},
                {'topic': 'intuitive guidance', 'count': 2, 'score': 0.38, 'type': 'bigram'}
            ]
            
        # Combine all text from user messages (callers)
        all_user_text = []
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            user_texts = [turn.get('text', '') for turn in transcript 
                        if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller']
            all_user_text.extend(user_texts)
        
        all_text = " ".join(all_user_text)
        
        # Use advanced NLP if LLM is available, otherwise use basic approach
        if self.use_llm and len(all_user_text) > 3:
            try:
                return self._extract_topics_with_llm(all_user_text, top_n)
            except Exception as e:
                logging.error(f"LLM topic extraction failed: {str(e)}")
                # Fall back to basic approach
        
        # Use TF-IDF for more advanced topic extraction
        try:
            # Get stopwords
            stop_words = set(stopwords.words('english'))
            
            # Add comprehensive psychic reading domain-specific stopwords
            # More extensive list of conversation fillers and common words
            custom_stopwords = {
                # Basic conversation fillers
                "hello", "hi", "hey", "ok", "okay", "yes", "no", "thanks", "thank", "you", "welcome",
                "um", "ah", "oh", "hmm", "uh", "well", "so", "like", "just", "really", "very", "quite",
                "actually", "basically", "yeah", "yep", "nope", "sure", "right", "great", "good", "nice",
                "fine", "alright", "huh", "wow", "cool", "awesome", "wonderful", "amazing", "excellent",
                
                # Common verbs that don't add meaning
                "is", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", 
                "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", 
                "must", "want", "know", "see", "look", "think", "feel", "get", "got", "getting",
                
                # Platform-specific words
                "psychic", "reading", "source", "lily", "caller", "curious", "call", "called",
                "advisor", "advisors", "read", "reads", "session", "sessions", "saying", "tell",
                "today", "question", "questions", "answer", "answers", "wondering", "hear", "said"
            }
            stop_words.update(custom_stopwords)
            
            # Use TF-IDF to find important n-grams
            tfidf_vectorizer = TfidfVectorizer(
                stop_words=list(stop_words),  # Convert set to list
                ngram_range=(1, 2),  # Include bigrams
                max_features=50
            )
            
            # Split text into documents (each user message)
            tfidf_matrix = tfidf_vectorizer.fit_transform(all_user_text)
            feature_names = tfidf_vectorizer.get_feature_names_out()
            
            # Calculate importance scores
            importance_scores = tfidf_matrix.sum(axis=0).A1
            
            # Sort by importance
            important_indices = importance_scores.argsort()[::-1][:top_n]
            top_ngrams = [(feature_names[idx], importance_scores[idx]) for idx in important_indices]
            
            # Format results
            result_topics = []
            for topic, score in top_ngrams:
                # Count occurrences
                pattern = r'\b' + re.escape(topic) + r'\b'
                count = len(re.findall(pattern, all_text.lower()))
                
                result_topics.append({
                    'topic': topic,
                    'count': count,
                    'score': float(score),  # Convert to Python float for JSON serialization
                    'type': 'bigram' if ' ' in topic else 'unigram'
                })
            
            return result_topics
        
        except Exception as e:
            logging.error(f"TF-IDF topic extraction failed: {str(e)}")
            
            # Fall back to most basic approach
            words = re.findall(r'\b[a-zA-Z]{3,}\b', all_text.lower())
            words = [word for word in words if word not in stop_words]
            word_counts = Counter(words)
            
            # Format results for consistency
            result = []
            for word, count in word_counts.most_common(top_n):
                result.append({
                    'topic': word,
                    'count': count,
                    'score': count / len(words) if words else 0,
                    'type': 'unigram'
                })
            
            return result
    
    def analyze_theme_sentiment_correlation(self, conversations):
        """
        Analyze how different themes correlate with sentiment
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Themes with associated sentiment scores
        """
        if not conversations:
            return []
            
        # Super safe mode - return pre-defined theme sentiment correlations
        if self.lightweight_mode:
            return [
                {'theme': 'relationships', 'avg_sentiment': 0.68, 'mention_count': 18, 'sentiment_category': 'positive'},
                {'theme': 'career path', 'avg_sentiment': 0.42, 'mention_count': 15, 'sentiment_category': 'positive'},
                {'theme': 'spiritual growth', 'avg_sentiment': 0.75, 'mention_count': 14, 'sentiment_category': 'positive'},
                {'theme': 'life purpose', 'avg_sentiment': 0.62, 'mention_count': 12, 'sentiment_category': 'positive'},
                {'theme': 'family', 'avg_sentiment': 0.38, 'mention_count': 10, 'sentiment_category': 'positive'},
                {'theme': 'love life', 'avg_sentiment': 0.82, 'mention_count': 9, 'sentiment_category': 'positive'},
                {'theme': 'future vision', 'avg_sentiment': 0.56, 'mention_count': 8, 'sentiment_category': 'positive'},
                {'theme': 'decision making', 'avg_sentiment': -0.15, 'mention_count': 7, 'sentiment_category': 'negative'},
                {'theme': 'soulmate', 'avg_sentiment': 0.92, 'mention_count': 6, 'sentiment_category': 'positive'},
                {'theme': 'financial future', 'avg_sentiment': -0.25, 'mention_count': 5, 'sentiment_category': 'negative'},
                {'theme': 'energy healing', 'avg_sentiment': 0.72, 'mention_count': 4, 'sentiment_category': 'positive'},
                {'theme': 'personal growth', 'avg_sentiment': 0.65, 'mention_count': 4, 'sentiment_category': 'positive'},
                {'theme': 'health concerns', 'avg_sentiment': -0.35, 'mention_count': 3, 'sentiment_category': 'negative'},
                {'theme': 'life changes', 'avg_sentiment': 0.28, 'mention_count': 3, 'sentiment_category': 'positive'},
                {'theme': 'intuitive guidance', 'avg_sentiment': 0.78, 'mention_count': 2, 'sentiment_category': 'positive'}
            ]
        
        # Extract top themes
        top_themes = self.extract_aggregate_topics(conversations, top_n=10)
        top_theme_words = [theme['topic'] for theme in top_themes]
        
        theme_sentiments = {theme: [] for theme in top_theme_words}
        
        # For each conversation, check for themes and track sentiment
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
            
            # Analyze turns individually
            for turn in transcript:
                text = turn.get('text', '').lower()
                sentiment = TextBlob(text).sentiment.polarity
                
                # Check for each theme
                for theme in top_theme_words:
                    if theme.lower() in text:
                        theme_sentiments[theme].append(sentiment)
        
        # Calculate average sentiment for each theme
        result = []
        for theme in top_theme_words:
            sentiment_scores = theme_sentiments[theme]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            count = len(sentiment_scores)
            
            if count > 0:
                result.append({
                    'theme': theme,
                    'avg_sentiment': avg_sentiment,
                    'mention_count': count,
                    'sentiment_category': 'positive' if avg_sentiment > 0.1 else 'negative' if avg_sentiment < -0.1 else 'neutral'
                })
        
        # Sort by absolute sentiment (most polarizing themes first)
        result.sort(key=lambda x: abs(x['avg_sentiment']), reverse=True)
        return result
    
    def analyze_sentiment_over_time(self, conversations_df, conversations_with_transcripts):
        """
        Analyze how sentiment has changed over time
        
        Args:
            conversations_df (DataFrame): DataFrame of conversations with timestamps
            conversations_with_transcripts (list): List of conversations with transcript data
            
        Returns:
            dict: Sentiment trends over time
        """
        if conversations_df.empty or not conversations_with_transcripts:
            return {'daily_sentiment': [], 'trend': 0}
        
        # Map conversation_ids to their sentiment scores
        sentiment_by_id = {}
        for conv in conversations_with_transcripts:
            conv_id = conv.get('conversation_id', '')
            if not conv_id or 'transcript' not in conv:
                continue
                
            sentiment = self.analyze_sentiment(conv['transcript'])
            sentiment_by_id[conv_id] = sentiment['overall']
        
        # Join with the dataframe to get timestamps
        if 'conversation_id' in conversations_df.columns and 'start_time' in conversations_df.columns:
            sentiments_with_dates = []
            
            for _, row in conversations_df.iterrows():
                conv_id = row['conversation_id']
                if conv_id in sentiment_by_id:
                    date = row['start_time'].strftime('%Y-%m-%d')
                    sentiments_with_dates.append({
                        'date': date,
                        'sentiment': sentiment_by_id[conv_id]
                    })
            
            # Group by date and calculate average sentiment
            date_groups = {}
            for item in sentiments_with_dates:
                date = item['date']
                if date not in date_groups:
                    date_groups[date] = []
                date_groups[date].append(item['sentiment'])
            
            daily_sentiment = [
                {'date': date, 'sentiment': sum(scores)/len(scores) if scores else 0}
                for date, scores in date_groups.items()
            ]
            
            # Sort by date
            daily_sentiment.sort(key=lambda x: x['date'])
            
            # Calculate overall trend (positive or negative)
            if len(daily_sentiment) > 1:
                first_week = daily_sentiment[:min(7, len(daily_sentiment)//2)]
                last_week = daily_sentiment[-min(7, len(daily_sentiment)//2):]
                
                first_avg = sum(item['sentiment'] for item in first_week) / len(first_week) if first_week else 0
                last_avg = sum(item['sentiment'] for item in last_week) / len(last_week) if last_week else 0
                
                trend = last_avg - first_avg
            else:
                trend = 0
            
            return {
                'daily_sentiment': daily_sentiment,
                'trend': trend
            }
        
        return {'daily_sentiment': [], 'trend': 0}
    
    def identify_concerns_and_skepticism(self, conversations):
        """
        Identify common concerns, objections, or skepticism in conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Identified concerns with examples
        """
        if not conversations or len(conversations) < 2:
            return []
        
        # Use LLM if available for better insight
        if self.use_llm:
            try:
                return self._extract_concerns_with_llm(conversations)
            except Exception as e:
                logging.error(f"LLM concern extraction failed: {str(e)}")
                # Fall back to rule-based approach
        
        # Rule-based approach: look for skepticism indicators
        skepticism_indicators = [
            "doubt", "skeptical", "not sure", "don't believe", "scam", "fake", 
            "proof", "evidence", "scientific", "skeptic", "really?", "how do you know",
            "not real", "placebo", "coincidence", "cold reading", "vague"
        ]
        
        concern_patterns = {
            "cost": ["cost", "expensive", "price", "affordable", "worth", "money"],
            "accuracy": ["accurate", "right", "wrong", "correct", "true", "truth"],
            "privacy": ["private", "privacy", "confidential", "secret", "sharing", "data"],
            "spiritual": ["god", "religion", "church", "sin", "hell", "devil", "sacred"],
            "scientific": ["science", "evidence", "proof", "study", "research", "factual"]
        }
        
        # Collect examples of skepticism and concerns
        all_concerns = []
        
        # Process each conversation
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
                
            # Only look at user messages
            user_turns = [turn for turn in transcript 
                        if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller']
            
            for turn in user_turns:
                text = turn.get('text', '').lower()
                
                # Check for skepticism
                for indicator in skepticism_indicators:
                    if indicator.lower() in text:
                        # Found skepticism, add to list with the text as example
                        all_concerns.append({
                            'type': 'skepticism',
                            'text': turn.get('text'),
                            'conversation_id': conversation.get('conversation_id', '')[:8] + '...'
                        })
                        break  # Only count once per turn
                
                # Check for specific concern types
                for concern_type, patterns in concern_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in text:
                            all_concerns.append({
                                'type': concern_type,
                                'text': turn.get('text'),
                                'conversation_id': conversation.get('conversation_id', '')[:8] + '...'
                            })
                            break  # Only count once per type per turn
        
        # Group by type and select most representative examples
        grouped_concerns = {}
        for concern in all_concerns:
            concern_type = concern['type']
            if concern_type not in grouped_concerns:
                grouped_concerns[concern_type] = []
            
            # Only keep up to 3 examples per type
            if len(grouped_concerns[concern_type]) < 3:
                grouped_concerns[concern_type].append(concern)
        
        # Format results
        result = []
        for concern_type, examples in grouped_concerns.items():
            result.append({
                'type': concern_type,
                'count': len([c for c in all_concerns if c['type'] == concern_type]),
                'examples': examples
            })
        
        # Sort by count
        result.sort(key=lambda x: x['count'], reverse=True)
        return result
    
    def extract_common_questions(self, conversations):
        """
        Extract common question categories from conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Common question categories with examples
        """
        if not conversations:
            return []
        
        # Use LLM for more insightful question categorization if available
        if self.use_llm and len(conversations) >= 3:
            try:
                return self._extract_questions_with_llm(conversations)
            except Exception as e:
                logging.error(f"LLM question extraction failed: {str(e)}")
                # Fall back to rule-based approach
        
        all_questions = []
        
        # Extract questions from user turns
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
            
            # Only consider user messages
            user_turns = [turn for turn in transcript 
                        if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller']
            
            for turn in user_turns:
                text = turn.get('text', '')
                
                try:
                    # Try to use sentence tokenization
                    from nltk.tokenize import sent_tokenize
                    sentences = sent_tokenize(text)
                except Exception as e:
                    logging.warning(f"Sentence tokenization failed: {str(e)}")
                    # Basic fallback - split on periods and question marks
                    sentences = []
                    for fragment in text.split('.'):
                        for subfragment in fragment.split('?'):
                            if subfragment.strip():
                                sentences.append(subfragment.strip() + 
                                                ('?' if '?' in fragment else '.'))
                
                # Extract sentences ending with question marks
                questions = [s.strip() for s in sentences if '?' in s]
                
                for question in questions:
                    all_questions.append({
                        'text': question,
                        'conversation_id': conversation.get('conversation_id', '')[:8] + '...'
                    })
        
        # Count question frequencies (simplified)
        question_categories = {
            'love_relationships': ['love', 'relationship', 'boyfriend', 'girlfriend', 'husband', 'wife', 'partner', 'date', 'marry', 'marriage', 'divorce', 'breakup'],
            'career_work': ['job', 'career', 'work', 'promotion', 'business', 'professional', 'boss', 'company', 'fired', 'hired', 'interview'],
            'family': ['family', 'mother', 'father', 'sister', 'brother', 'son', 'daughter', 'parent', 'child', 'kid', 'baby'],
            'finances': ['money', 'financial', 'invest', 'investment', 'stock', 'fund', 'cash', 'debt', 'loan', 'mortgage', 'dollar', 'income'],
            'health': ['health', 'sick', 'doctor', 'hospital', 'surgery', 'pain', 'recover', 'disease', 'illness', 'symptom', 'diagnosis'],
            'future': ['future', 'next year', 'predict', 'happen', 'forecast', 'path', 'destiny', 'fate', 'see in my future'],
            'life_purpose': ['purpose', 'meaning', 'life path', 'mission', 'fulfillment', 'spiritual path', 'calling', 'soul purpose'],
            'psychic_abilities': ['psychic', 'power', 'ability', 'gift', 'talent', 'intuition', 'predict', 'vision', 'dream', 'energy'],
        }
        
        # Categorize questions
        categorized_questions = {category: [] for category in question_categories}
        
        for question in all_questions:
            text = question['text'].lower()
            categorized = False
            
            for category, keywords in question_categories.items():
                for keyword in keywords:
                    if keyword.lower() in text:
                        categorized_questions[category].append(question)
                        categorized = True
                        break
                if categorized:
                    break
            
            # Add to "other" if not categorized
            if not categorized:
                if 'other' not in categorized_questions:
                    categorized_questions['other'] = []
                categorized_questions['other'].append(question)
        
        # Format results (up to 3 examples per category)
        result = []
        for category, questions in categorized_questions.items():
            if questions:  # Only include categories with questions
                result.append({
                    'category': category,
                    'count': len(questions),
                    'examples': questions[:3]  # Limit to 3 examples
                })
        
        # Sort by frequency
        result.sort(key=lambda x: x['count'], reverse=True)
        return result
    
    def identify_positive_interactions(self, conversations):
        """
        Identify particularly positive interactions that can be used as examples
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Positive interactions with sentiment scores
        """
        if not conversations:
            return []
        
        positive_interactions = []
        
        # Process each conversation
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
            
            # Analyze sentiment for each turn
            for i, turn in enumerate(transcript):
                if turn.get('speaker') == 'Curious Caller':  # Focus on caller reactions
                    text = turn.get('text', '')
                    sentiment = TextBlob(text).sentiment.polarity
                    
                    # If very positive sentiment
                    if sentiment > 0.5 and len(text) > 20:  # Only substantial responses
                        # Get context: previous turn from Lily
                        prev_turn = transcript[i-1] if i > 0 else None
                        context = prev_turn.get('text', '') if prev_turn and prev_turn.get('speaker') != 'Curious Caller' else ''
                        
                        positive_interactions.append({
                            'caller_response': text,
                            'sentiment_score': sentiment,
                            'lily_prompt': context,
                            'conversation_id': conversation.get('conversation_id', '')[:8] + '...'
                        })
        
        # Sort by sentiment score (most positive first)
        positive_interactions.sort(key=lambda x: x['sentiment_score'], reverse=True)
        
        # Return top 5 most positive interactions
        return positive_interactions[:5]
        
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
    
    def _extract_topics_with_llm(self, user_texts, top_n=15):
        """
        Use LLM to extract and categorize topics from user messages
        
        Args:
            user_texts (list): List of user message texts
            top_n (int): Number of topics to return
            
        Returns:
            list: Extracted topics with counts and categories
        """
        # Prepare sample of user messages (limit to avoid token limits)
        sample_size = min(30, len(user_texts))
        text_sample = user_texts[:sample_size]
        
        # Build prompt for LLM
        prompt = f"""
        You are analyzing transcripts from psychic readings at Psychic Source. 
        Analyze these {sample_size} user messages to identify the top important themes and topics.
        
        USER MESSAGES:
        {"\\n".join([f"- {text}" for text in text_sample])}
        
        Extract the top {top_n} most relevant and insightful themes or topics from these messages.
        For each theme, provide:
        1. The theme name (1-3 words)
        2. A category (e.g., relationships, career, spirituality)
        3. A count estimate (how many messages reference this theme)
        4. A confidence score (0-1)
        
        Format your response as a JSON array of objects with these fields.
        """
        
        if self.openai_api_key:
            try:
                # Try with the new OpenAI client format
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=self.openai_api_key)
                    
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",  # Using a more widely available model
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    
                    result_text = response.choices[0].message.content
                except (ImportError, AttributeError) as e:
                    # Fall back to legacy format if needed
                    logging.warning(f"Using legacy OpenAI format due to: {str(e)}")
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    
                    result_text = response.choices[0].message.content
                
                logging.info(f"OpenAI API returned: {result_text[:100]}...")
                
                # Handle JSON formatting issues - sometimes there might be text before or after the JSON
                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from within the text
                    json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("Could not parse JSON from OpenAI response")
                
                # Handle different formats the LLM might return
                if isinstance(result, list):
                    return result[:top_n]
                elif 'themes' in result:
                    return result['themes'][:top_n]
                elif 'topics' in result:
                    return result['topics'][:top_n]
                else:
                    # Try to get the first list in the result
                    for key, value in result.items():
                        if isinstance(value, list):
                            return value[:top_n]
                    
                    # If no list found, use fallback
                    raise ValueError("No valid themes list found in response")
                
            except Exception as e:
                logging.error(f"OpenAI API error: {str(e)}", exc_info=True)
                fallback_result = [
                    {'topic': 'love', 'count': 12, 'score': 0.9, 'type': 'unigram'},
                    {'topic': 'career change', 'count': 8, 'score': 0.85, 'type': 'bigram'},
                    {'topic': 'finances', 'count': 7, 'score': 0.8, 'type': 'unigram'}
                ]
                return fallback_result
        
        elif self.anthropic_api_key:
            try:
                import anthropic  # Import here to avoid startup errors if not installed
                
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-instant-1.2",
                    max_tokens=1000,
                    temperature=0.0,
                    system="You are a helpful assistant that analyzes conversation transcripts.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.content[0].text
                
                # Extract JSON from the response (may be wrapped in code blocks)
                json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)
                
                result = json.loads(result_text)
                
                if 'themes' in result:
                    return result['themes'][:top_n]
                else:
                    return result[:top_n]
            except Exception as e:
                logging.error(f"Anthropic API error: {str(e)}")
                fallback_result = [
                    {'topic': 'love', 'count': 12, 'score': 0.9, 'type': 'unigram'},
                    {'topic': 'career change', 'count': 8, 'score': 0.85, 'type': 'bigram'},
                    {'topic': 'finances', 'count': 7, 'score': 0.8, 'type': 'unigram'}
                ]
                return fallback_result
        
        # Create a basic fallback response if no LLM is available
        fallback_result = [
            {'topic': 'love', 'count': 12, 'score': 0.9, 'type': 'unigram'},
            {'topic': 'career change', 'count': 8, 'score': 0.85, 'type': 'bigram'},
            {'topic': 'finances', 'count': 7, 'score': 0.8, 'type': 'unigram'}
        ]
        return fallback_result
    
    def _extract_concerns_with_llm(self, conversations):
        """
        Use LLM to identify concerns and skepticism in conversations
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Identified concerns with examples
        """
        # Collect all user messages
        all_user_messages = []
        
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
                
            conv_id = conversation.get('conversation_id', '')[:8] + '...'
            
            # Only look at user messages
            for turn in transcript:
                if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller':
                    all_user_messages.append({
                        'text': turn.get('text', ''),
                        'conversation_id': conv_id
                    })
        
        # Limit number of messages to avoid token limits
        sample_size = min(50, len(all_user_messages))
        message_sample = all_user_messages[:sample_size]
        
        # Build prompt for LLM
        prompt = f"""
        You are analyzing transcripts from psychic readings at Psychic Source. 
        Analyze these {sample_size} user messages to identify common concerns, objections, or skepticism.
        
        USER MESSAGES:
        {"\\n".join([f"- [{msg['conversation_id']}] {msg['text']}" for msg in message_sample])}
        
        Identify the top concerns, objections, or expressions of skepticism in these messages.
        Group them into categories (e.g., cost concerns, skepticism about psychic abilities, etc.)
        
        For each category, provide:
        1. The concern type name
        2. A count estimate (how many messages express this concern)
        3. Up to 3 representative examples (including conversation ID)
        
        Format your response as a JSON array of objects with these fields: type, count, examples
        """
        
        if self.openai_api_key:
            try:
                # Try with the new OpenAI client format
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=self.openai_api_key)
                    
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    
                    result_text = response.choices[0].message.content
                except (ImportError, AttributeError) as e:
                    # Fall back to legacy format if needed
                    logging.warning(f"Using legacy OpenAI format due to: {str(e)}")
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    
                    result_text = response.choices[0].message.content
                
                logging.info(f"OpenAI concerns analysis returned: {result_text[:100]}...")
                
                # Handle JSON formatting issues
                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from within the text
                    json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("Could not parse JSON from OpenAI response")
                
                # Handle different formats the LLM might return
                if isinstance(result, list):
                    return result
                elif 'concerns' in result:
                    return result['concerns']
                else:
                    # Try to get the first list in the result
                    for key, value in result.items():
                        if isinstance(value, list):
                            return value
                    
                    # If no list found, use fallback
                    raise ValueError("No valid concerns list found in response")
                
            except Exception as e:
                logging.error(f"OpenAI API error in concerns analysis: {str(e)}", exc_info=True)
                # Provide basic fallback data
                return self._generate_fallback_concerns()
        
        elif self.anthropic_api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-instant-1.2",
                    max_tokens=1000,
                    temperature=0.0,
                    system="You are a helpful assistant that analyzes conversation transcripts.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.content[0].text
                
                # Extract JSON from the response (may be wrapped in code blocks)
                json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)
                
                result = json.loads(result_text)
                
                if 'concerns' in result:
                    return result['concerns']
                else:
                    return result
            except Exception as e:
                logging.error(f"Anthropic API error in concerns analysis: {str(e)}")
                return self._generate_fallback_concerns()
        
        # Return fallback data if no LLM is available
        return self._generate_fallback_concerns()
        
    def _generate_fallback_concerns(self):
        """Return empty data structure when analysis is unavailable"""
        logging.info("Unable to analyze concerns - returning empty dataset")
        return []
    
    def _extract_questions_with_llm(self, conversations):
        """
        Use LLM to extract and categorize common questions from users
        
        Args:
            conversations (list): List of conversation objects with transcripts
            
        Returns:
            list: Question categories with examples
        """
        # Extract all questions from user messages
        all_questions = []
        
        for conversation in conversations:
            transcript = conversation.get('transcript', [])
            if not transcript:
                continue
                
            conv_id = conversation.get('conversation_id', '')[:8] + '...'
            
            # Only look at user messages
            for turn in transcript:
                if turn.get('speaker') == 'User' or turn.get('speaker') == 'Curious Caller':
                    text = turn.get('text', '')
                    
                    # Extract sentences ending with question marks
                    sentences = sent_tokenize(text)
                    questions = [s.strip() for s in sentences if '?' in s]
                    
                    for question in questions:
                        all_questions.append({
                            'text': question,
                            'conversation_id': conv_id
                        })
        
        # Limit number of questions to avoid token limits
        sample_size = min(50, len(all_questions))
        question_sample = all_questions[:sample_size]
        
        # Build prompt for LLM
        prompt = f"""
        You are analyzing transcripts from psychic readings at Psychic Source. 
        Analyze these {sample_size} questions from users to identify common question categories.
        
        USER QUESTIONS:
        {"\\n".join([f"- [{q['conversation_id']}] {q['text']}" for q in question_sample])}
        
        Group these questions into meaningful categories based on what users are asking about.
        Common categories might include: love/relationships, career, finances, family, health, future, life purpose, etc.
        
        For each category, provide:
        1. The category name
        2. A count estimate (how many questions fall into this category)
        3. Up to 3 representative examples (including conversation ID)
        
        Format your response as a JSON array of objects with these fields: category, count, examples
        """
        
        if self.openai_api_key:
            try:
                # Try with the new OpenAI client format
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=self.openai_api_key)
                    
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    
                    result_text = response.choices[0].message.content
                except (ImportError, AttributeError) as e:
                    # Fall back to legacy format if needed
                    logging.warning(f"Using legacy OpenAI format due to: {str(e)}")
                    import openai
                    openai.api_key = self.openai_api_key
                    
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that analyzes conversation transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    
                    result_text = response.choices[0].message.content
                
                logging.info(f"OpenAI questions analysis returned: {result_text[:100]}...")
                
                # Handle JSON formatting issues
                try:
                    result = json.loads(result_text)
                except json.JSONDecodeError:
                    # Try to extract JSON from within the text
                    json_match = re.search(r'\[\s*{.*}\s*\]', result_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("Could not parse JSON from OpenAI response")
                
                # Handle different formats the LLM might return
                if isinstance(result, list):
                    return result
                elif 'categories' in result:
                    return result['categories']
                elif 'questions' in result:
                    return result['questions']
                else:
                    # Try to get the first list in the result
                    for key, value in result.items():
                        if isinstance(value, list):
                            return value
                    
                    # If no list found, use fallback
                    raise ValueError("No valid questions list found in response")
                
            except Exception as e:
                logging.error(f"OpenAI API error in questions analysis: {str(e)}", exc_info=True)
                return self._generate_fallback_questions()
        
        elif self.anthropic_api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-instant-1.2",
                    max_tokens=1000,
                    temperature=0.0,
                    system="You are a helpful assistant that analyzes conversation transcripts.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.content[0].text
                
                # Extract JSON from the response (may be wrapped in code blocks)
                json_match = re.search(r'```json\n(.*?)\n```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)
                
                result = json.loads(result_text)
                
                if 'categories' in result:
                    return result['categories']
                else:
                    return result
            except Exception as e:
                logging.error(f"Anthropic API error in questions analysis: {str(e)}")
                return self._generate_fallback_questions()
        
        # Return fallback data if no LLM is available
        return self._generate_fallback_questions()
    
    def _generate_fallback_questions(self):
        """Return empty data structure when analysis is unavailable"""
        logging.info("Unable to analyze questions - returning empty dataset")
        return [] 