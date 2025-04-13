import os
import openai
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file.")
    exit()

# Initialize client
client = openai.OpenAI(api_key=api_key)

# The query text
query_text = "provocative" # Simple, concrete query

try:
    # Generate embedding
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query_text
    )

    # Extract the vector
    if response.data and len(response.data) > 0:
        embedding_vector = response.data[0].embedding
        # Print the vector in a format easy to copy into SQL
        print("\n--- Embedding Vector ---")
        # Format as a PostgreSQL array literal string
        vector_string = "[" + ",".join(map(str, embedding_vector)) + "]"
        print(vector_string)
        print(f"\n(Generated embedding for: '{query_text}')")
    else:
        print("Error: Unexpected response format from OpenAI.")

except Exception as e:
    print(f"An error occurred: {e}")
