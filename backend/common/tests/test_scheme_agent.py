"""Test SchemeAgent with PostgreSQL"""
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, '/home/ashwinbiyani/Swalambi/backend')
load_dotenv('/home/ashwinbiyani/Swalambi/backend/.env')

from agents.schema.scheme_agent import SchemeAgent
from agents.schema.providers.embedding_providers import AzureOpenAIEmbeddingProvider
from agents.schema.stores.vector_stores import PostgresPgVectorStore

# Test user profile
user_profile = {
    "skill": "weaver",
    "intent": "loan",
    "skill_level": 3,
    "state": "Tamil Nadu"
}

print("Initializing SchemeAgent with Azure OpenAI + PostgreSQL...")

# Create providers explicitly
embedding_provider = AzureOpenAIEmbeddingProvider(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

vector_store = PostgresPgVectorStore(
    connection_string=os.getenv("POSTGRES_CONNECTION_STRING")
)

agent = SchemeAgent(
    embedding_provider=embedding_provider,
    vector_store=vector_store,
    index_name="schemes"
)

print(f"\nSearching schemes for: {user_profile}")
results = agent.search_schemes(user_profile, limit=5)

print(f"\nFound {len(results)} schemes:\n")
for i, scheme in enumerate(results, 1):
    print(f"{i}. {scheme.get('name', 'N/A')}")
    print(f"   Ministry: {scheme.get('ministry', 'N/A')}")
    print(f"   State: {scheme.get('state', 'N/A')}")
    print(f"   Vector Score: {scheme.get('vector_score', 0):.3f}")
    print(f"   Eligibility Score: {scheme.get('eligibility_score', 0):.3f}")
    print(f"   Final Score: {scheme.get('final_score', 0):.3f}")
    print()
