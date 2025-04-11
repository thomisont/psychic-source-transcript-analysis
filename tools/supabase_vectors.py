#!/usr/bin/env python3
"""
Utility for working with Supabase and pgvector for vector similarity search.
This enables semantic search across conversation transcripts.
"""
import os
import sys
from pathlib import Path
import argparse
import logging
import time
import json
import numpy as np
from tqdm import tqdm
import openai
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the supabase_client
sys.path.append(str(Path(__file__).parent.parent))
from tools.supabase_client import SupabaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vector_embeddings.log'),
        logging.StreamHandler()
    ]
)

class SupabaseVectorStore:
    """Class for working with vector embeddings in Supabase"""
    
    def __init__(self, use_openai=True):
        """
        Initialize the vector store
        
        Args:
            use_openai: Whether to use OpenAI for embeddings (True) or local model (False)
        """
        # Load environment variables
        load_dotenv()
        
        # Initialize Supabase client
        self.supabase = SupabaseClient()
        
        # Set up embedding model
        self.use_openai = use_openai
        
        if use_openai:
            # Use OpenAI for embeddings
            self.openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found in environment variables")
            
            # Initialize OpenAI client
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            self.embedding_model = "text-embedding-3-small"
            self.embedding_dimensions = 1536  # Dimensions for text-embedding-3-small
        else:
            # Use a local model for embeddings (e.g., sentence-transformers)
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dimensions = 384  # Dimensions for all-MiniLM-L6-v2
            except ImportError:
                logging.error("sentence-transformers package not installed. Run 'pip install sentence-transformers'")
                raise
    
    def enable_vector_extension(self):
        """Enable pgvector extension in Supabase"""
        try:
            # Check if pgvector extension is already enabled
            result = self.supabase.execute_sql("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            
            if not result:
                # Enable the extension
                self.supabase.execute_sql("CREATE EXTENSION IF NOT EXISTS vector")
                logging.info("Enabled pgvector extension in Supabase")
            else:
                logging.info("pgvector extension is already enabled")
                
            return True
        except Exception as e:
            logging.error(f"Error enabling vector extension: {e}")
            return False
    
    def create_embeddings_table(self, table_name='conversation_embeddings'):
        """
        Create a table to store conversation embeddings
        
        Args:
            table_name: Name of the embeddings table
        """
        try:
            # Enable pgvector extension first
            self.enable_vector_extension()
            
            # Create the embeddings table
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                external_id VARCHAR NOT NULL,
                segment_text TEXT NOT NULL,
                embedding vector({self.embedding_dimensions}) NOT NULL,
                segment_index INTEGER NOT NULL,
                speaker VARCHAR,
                timestamp TIMESTAMP WITH TIME ZONE,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            self.supabase.execute_sql(create_table_sql)
            
            # Create indexes for better query performance
            index_conversation_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_conversation_id ON {table_name} (conversation_id);
            """
            self.supabase.execute_sql(index_conversation_sql)
            
            index_external_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_external_id ON {table_name} (external_id);
            """
            self.supabase.execute_sql(index_external_sql)
            
            # Create vector index (this is important for performance with pgvector)
            vector_index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding ON {table_name} USING ivfflat (embedding vector_l2_ops)
            WITH (lists = 100);
            """
            try:
                self.supabase.execute_sql(vector_index_sql)
            except Exception as e:
                logging.warning(f"Could not create vector index, might need more data first: {e}")
            
            logging.info(f"Created embeddings table '{table_name}'")
            return True
        except Exception as e:
            logging.error(f"Error creating embeddings table: {e}")
            return False
    
    def get_embedding(self, text):
        """
        Generate an embedding for a text string
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            numpy.ndarray: The embedding vector
        """
        if not text:
            # Return zero vector if text is empty
            return np.zeros(self.embedding_dimensions)
        
        if self.use_openai:
            # Use OpenAI API for embeddings
            try:
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
                return np.array(response.data[0].embedding)
            except Exception as e:
                logging.error(f"Error generating OpenAI embedding: {e}")
                # Return zero vector on error
                return np.zeros(self.embedding_dimensions)
        else:
            # Use local model for embeddings
            return self.model.encode([text])[0]
    
    def process_conversations(self, limit=None, table_name='conversation_embeddings', chunk_size=1000, 
                             chunk_overlap=200, batch_size=10, force_update=False):
        """
        Process conversations from the database and generate embeddings
        
        Args:
            limit: Maximum number of conversations to process
            table_name: Name of the embeddings table
            chunk_size: Maximum size of text chunks for embeddings
            chunk_overlap: Overlap between chunks
            batch_size: Number of embeddings to create in a batch
            force_update: Whether to force update existing embeddings
            
        Returns:
            int: Number of embeddings created
        """
        # Create embeddings table if it doesn't exist
        self.create_embeddings_table(table_name)
        
        # Get conversations from the database
        query = """
        SELECT c.id, c.external_id 
        FROM conversations c
        """
        
        if not force_update:
            # Only get conversations that don't have embeddings yet
            query += f"""
            WHERE NOT EXISTS (
                SELECT 1 FROM {table_name} e 
                WHERE e.conversation_id = c.id
            )
            """
        
        if limit:
            query += f" LIMIT {limit}"
            
        conversations = self.supabase.execute_sql(query)
        
        if not conversations:
            logging.info("No conversations found to process")
            return 0
        
        logging.info(f"Found {len(conversations)} conversations to process")
        
        total_embeddings = 0
        
        # Process conversations in batches
        for i in range(0, len(conversations), batch_size):
            batch = conversations[i:i+batch_size]
            batch_embeddings = []
            
            for conv in tqdm(batch, desc=f"Processing batch {i//batch_size + 1}/{(len(conversations) + batch_size - 1)//batch_size}"):
                conv_id = conv['id']
                external_id = conv['external_id']
                
                # Get messages for this conversation
                messages_query = f"""
                SELECT m.id, m.speaker, m.text, m.timestamp
                FROM messages m
                WHERE m.conversation_id = {conv_id}
                ORDER BY m.timestamp
                """
                
                messages = self.supabase.execute_sql(messages_query)
                
                if not messages:
                    logging.warning(f"No messages found for conversation {external_id}")
                    continue
                
                # Create chunks of text for this conversation
                full_text = " ".join([m['text'] for m in messages if m['text']])
                chunks = self._create_text_chunks(full_text, chunk_size, chunk_overlap)
                
                if not chunks:
                    logging.warning(f"No chunks created for conversation {external_id}")
                    continue
                
                # Create embeddings for each chunk
                for idx, chunk in enumerate(chunks):
                    # Determine which message this chunk belongs to (approximately)
                    total_length = len(full_text)
                    chunk_start = idx * (chunk_size - chunk_overlap) if idx > 0 else 0
                    chunk_end = min(chunk_start + chunk_size, total_length)
                    
                    # Find the closest message to this chunk
                    cumulative_length = 0
                    closest_message = None
                    
                    for msg in messages:
                        msg_length = len(msg['text'])
                        if cumulative_length <= chunk_start and cumulative_length + msg_length >= chunk_start:
                            closest_message = msg
                            break
                        cumulative_length += msg_length + 1  # +1 for space
                    
                    if not closest_message:
                        closest_message = messages[0]
                    
                    # Generate embedding for this chunk
                    embedding_vector = self.get_embedding(chunk)
                    
                    # Skip if embedding generation failed
                    if embedding_vector is None or (isinstance(embedding_vector, np.ndarray) and np.all(embedding_vector == 0)):
                        logging.warning(f"Failed to generate embedding for chunk {idx} of conversation {external_id}")
                        continue
                    
                    # Add to batch embeddings
                    batch_embeddings.append({
                        'conversation_id': conv_id,
                        'external_id': external_id,
                        'segment_text': chunk,
                        'embedding': embedding_vector.tolist(),
                        'segment_index': idx,
                        'speaker': closest_message['speaker'],
                        'timestamp': closest_message['timestamp'],
                        'metadata': json.dumps({
                            'message_id': closest_message['id'],
                            'chunk_size': chunk_size,
                            'chunk_overlap': chunk_overlap
                        })
                    })
            
            # Insert batch embeddings
            if batch_embeddings:
                try:
                    # We need to insert embeddings one at a time because of the vector type
                    for emb in batch_embeddings:
                        # Convert embedding to pgvector format
                        embedding_str = f"[{','.join(str(x) for x in emb['embedding'])}]"
                        
                        insert_sql = f"""
                        INSERT INTO {table_name} 
                        (conversation_id, external_id, segment_text, embedding, segment_index, speaker, timestamp, metadata)
                        VALUES 
                        ({emb['conversation_id']}, '{emb['external_id']}', '{emb['segment_text'].replace("'", "''")}', 
                         '{embedding_str}', {emb['segment_index']}, '{emb['speaker']}', 
                         '{emb['timestamp']}', '{emb['metadata']}')
                        """
                        
                        self.supabase.execute_sql(insert_sql)
                    
                    total_embeddings += len(batch_embeddings)
                    logging.info(f"Inserted {len(batch_embeddings)} embeddings from batch")
                except Exception as e:
                    logging.error(f"Error inserting embeddings batch: {e}")
            
            # Small delay to avoid overwhelming the API
            time.sleep(1)
        
        logging.info(f"Completed processing. Created {total_embeddings} embeddings.")
        return total_embeddings
    
    def _create_text_chunks(self, text, chunk_size, chunk_overlap):
        """Split text into overlapping chunks"""
        if not text:
            return []
            
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            return [text]
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:  # Avoid empty chunks
                chunks.append(chunk)
                
        return chunks
    
    def search_similar(self, query, limit=5, table_name='conversation_embeddings'):
        """
        Search for conversations similar to the query
        
        Args:
            query: Search query
            limit: Maximum number of results
            table_name: Name of the embeddings table
            
        Returns:
            list: List of similar conversations
        """
        # Generate embedding for the query
        query_embedding = self.get_embedding(query)
        
        if query_embedding is None or (isinstance(query_embedding, np.ndarray) and np.all(query_embedding == 0)):
            logging.error("Failed to generate embedding for query")
            return []
        
        # Convert embedding to pgvector format
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        
        # Search using cosine similarity
        search_sql = f"""
        SELECT 
            e.conversation_id,
            e.external_id,
            e.segment_text,
            e.segment_index,
            e.speaker,
            e.timestamp,
            1 - (e.embedding <=> '{embedding_str}') as similarity
        FROM 
            {table_name} e
        ORDER BY 
            e.embedding <=> '{embedding_str}'
        LIMIT {limit}
        """
        
        try:
            results = self.supabase.execute_sql(search_sql)
            
            if not results:
                logging.info("No similar conversations found")
                return []
                
            # Enhance results with more conversation details
            enhanced_results = []
            
            for result in results:
                # Get conversation title or other details
                conv_query = f"""
                SELECT title FROM conversations WHERE id = {result['conversation_id']}
                """
                
                conv_details = self.supabase.execute_sql(conv_query)
                
                enhanced_result = {
                    **result,
                    'title': conv_details[0]['title'] if conv_details else "Unknown",
                    'similarity_score': round(result['similarity'] * 100, 2)
                }
                
                enhanced_results.append(enhanced_result)
                
            return enhanced_results
            
        except Exception as e:
            logging.error(f"Error searching similar conversations: {e}")
            return []

def main():
    """Main function for command-line usage"""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Supabase Vector Store Utility')
    parser.add_argument('--action', choices=['create-table', 'process', 'search'], required=True,
                        help='Action to perform')
    parser.add_argument('--openai', action='store_true', default=True,
                        help='Use OpenAI for embeddings (default)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of conversations to process')
    parser.add_argument('--table', default='conversation_embeddings',
                        help='Name of the embeddings table')
    parser.add_argument('--chunk-size', type=int, default=1000,
                        help='Size of text chunks for embeddings')
    parser.add_argument('--chunk-overlap', type=int, default=200,
                        help='Overlap between chunks')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of conversations to process in each batch')
    parser.add_argument('--force-update', action='store_true',
                        help='Force update existing embeddings')
    parser.add_argument('--query', type=str,
                        help='Search query (required for search action)')
                        
    args = parser.parse_args()
    
    try:
        # Create vector store
        vector_store = SupabaseVectorStore(use_openai=args.openai)
        
        if args.action == 'create-table':
            # Create embeddings table
            success = vector_store.create_embeddings_table(table_name=args.table)
            if success:
                print(f"Successfully created embeddings table '{args.table}'")
            else:
                print(f"Failed to create embeddings table '{args.table}'")
                
        elif args.action == 'process':
            # Process conversations
            embeddings_count = vector_store.process_conversations(
                limit=args.limit,
                table_name=args.table,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                batch_size=args.batch_size,
                force_update=args.force_update
            )
            print(f"Created {embeddings_count} embeddings")
            
        elif args.action == 'search':
            # Search for similar conversations
            if not args.query:
                print("Error: --query parameter is required for search action")
                return 1
                
            results = vector_store.search_similar(
                query=args.query,
                limit=args.limit or 5,
                table_name=args.table
            )
            
            if results:
                print(f"Found {len(results)} similar conversations:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. Conversation: {result['external_id']} (Similarity: {result['similarity_score']}%)")
                    print(f"   Title: {result['title']}")
                    print(f"   Speaker: {result['speaker']}")
                    print(f"   Text: {result['segment_text'][:100]}...")
            else:
                print("No similar conversations found")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 