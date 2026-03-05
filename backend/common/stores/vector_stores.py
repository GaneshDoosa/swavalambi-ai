"""
vector_stores.py — Concrete implementations of vector store providers.
"""

import logging
from typing import List, Dict, Any
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

# Optional imports - only needed for specific store implementations
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    # Silently skip - OpenSearch is optional


class OpenSearchServerlessStore(VectorStore):
    """OpenSearch Serverless vector store."""
    
    def __init__(self, endpoint: str, region: str = "us-east-1"):
        import boto3
        from requests_aws4auth import AWS4Auth
        
        self.endpoint = endpoint
        self.region = region
        
        # Setup AWS auth
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            "aoss",
            session_token=credentials.token
        )
        
        self.client = OpenSearch(
            hosts=[{"host": endpoint.replace("https://", "").replace("http://", ""), "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
    
    def create_index(self, index_name: str, dimension: int) -> None:
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    }
                }
            }
        }
        
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=index_body)
            logger.info(f"Created OpenSearch index: {index_name}")
        else:
            logger.info(f"Index {index_name} already exists")
    
    def index_document(self, index_name: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        doc = {**metadata, "embedding": embedding}
        self.client.index(index=index_name, id=doc_id, body=doc)
    
    def search(self, index_name: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        search_body = {
            "size": limit,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": limit
                    }
                }
            }
        }
        
        response = self.client.search(index=index_name, body=search_body)
        
        results = []
        for hit in response["hits"]["hits"]:
            result = hit["_source"]
            result["vector_score"] = hit["_score"]
            results.append(result)
        
        return results
    
    def delete_index(self, index_name: str) -> None:
        if self.client.indices.exists(index=index_name):
            self.client.indices.delete(index=index_name)
            logger.info(f"Deleted index: {index_name}")
    
    def get_store_name(self) -> str:
        return "OpenSearchServerless"


class OpenSearchLocalStore(VectorStore):
    """Local OpenSearch installation vector store."""
    
    def __init__(self, host: str = "localhost", port: int = 9200, username: str = "admin", password: str = "admin"):
        self.host = host
        self.port = port
        
        self.client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=(username, password),
            use_ssl=False,
            verify_certs=False,
            timeout=30
        )
    
    def create_index(self, index_name: str, dimension: int) -> None:
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    }
                }
            }
        }
        
        if not self.client.indices.exists(index=index_name):
            self.client.indices.create(index=index_name, body=index_body)
            logger.info(f"Created OpenSearch index: {index_name}")
        else:
            logger.info(f"Index {index_name} already exists")
    
    def index_document(self, index_name: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        doc = {**metadata, "embedding": embedding}
        self.client.index(index=index_name, id=doc_id, body=doc)
    
    def search(self, index_name: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        search_body = {
            "size": limit,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": limit
                    }
                }
            }
        }
        
        response = self.client.search(index=index_name, body=search_body)
        
        results = []
        for hit in response["hits"]["hits"]:
            result = hit["_source"]
            result["vector_score"] = hit["_score"]
            results.append(result)
        
        return results
    
    def delete_index(self, index_name: str) -> None:
        if self.client.indices.exists(index=index_name):
            self.client.indices.delete(index=index_name)
            logger.info(f"Deleted index: {index_name}")
    
    def get_store_name(self) -> str:
        return "OpenSearchLocal"


class PostgresPgVectorStore(VectorStore):
    """PostgreSQL with pgvector extension."""
    
    def __init__(self, connection_string: str):
        try:
            import psycopg2
            from pgvector.psycopg2 import register_vector
            self.conn = psycopg2.connect(connection_string)
            register_vector(self.conn)
        except ImportError:
            raise ImportError("psycopg2 and pgvector required. Install: pip install psycopg2-binary pgvector")
    
    def create_index(self, index_name: str, dimension: int) -> None:
        with self.conn.cursor() as cur:
            # Create extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {index_name} (
                    id TEXT PRIMARY KEY,
                    embedding vector({dimension}),
                    metadata JSONB
                )
            """)
            
            # Create index
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}_embedding_idx 
                ON {index_name} USING ivfflat (embedding vector_cosine_ops)
            """)
            
            self.conn.commit()
            logger.info(f"Created pgvector table: {index_name}")
    
    def index_document(self, index_name: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        import json
        with self.conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {index_name} (id, embedding, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata
            """, (doc_id, embedding, json.dumps(metadata)))
            self.conn.commit()
    
    def search(self, index_name: str, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        import numpy as np
        with self.conn.cursor() as cur:
            # Convert list to numpy array for pgvector
            query_vec = np.array(query_embedding)
            
            # Get all columns except embedding
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name != 'embedding' AND column_name != 'created_at'
            """, (index_name,))
            columns = [row[0] for row in cur.fetchall()]
            columns_str = ', '.join(columns)
            
            cur.execute(f"""
                SELECT {columns_str}, 1 - (embedding <=> %s) as score
                FROM {index_name}
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (query_vec, query_vec, limit))
            
            results = []
            for row in cur.fetchall():
                result = {}
                for i, col in enumerate(columns):
                    result[col] = row[i]
                result["vector_score"] = float(row[-1])
                results.append(result)
            
            return results
    
    def delete_index(self, index_name: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {index_name}")
            self.conn.commit()
            logger.info(f"Deleted table: {index_name}")
    
    def get_store_name(self) -> str:
        return "PostgresPgVector"
