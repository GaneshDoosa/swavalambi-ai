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
    """PostgreSQL with pgvector extension and connection pooling."""
    
    def __init__(self, connection_string: str, min_conn: int = 2, max_conn: int = 10):
        try:
            import psycopg2
            from psycopg2 import pool
            from pgvector.psycopg2 import register_vector
            
            # Create connection pool
            self.pool = pool.ThreadedConnectionPool(
                min_conn,
                max_conn,
                connection_string
            )
            
            # Register vector type with a test connection
            conn = self.pool.getconn()
            try:
                register_vector(conn)
            finally:
                self.pool.putconn(conn)
            
            logger.info(f"PostgreSQL connection pool created: min={min_conn}, max={max_conn}")
            
        except ImportError:
            raise ImportError("psycopg2 and pgvector required. Install: pip install psycopg2-binary pgvector")
    
    def _get_connection(self):
        """Get a connection from the pool"""
        return self.pool.getconn()
    
    def _put_connection(self, conn):
        """Return a connection to the pool"""
        self.pool.putconn(conn)
    
    def create_index(self, index_name: str, dimension: int) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
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
                
                # Create HNSW index (faster than IVFFlat for approximate search)
                # m=16: number of connections per layer (higher = better recall, slower build)
                # ef_construction=64: size of dynamic candidate list (higher = better quality, slower build)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}_embedding_idx 
                    ON {index_name} USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """)
                
                conn.commit()
                logger.info(f"Created pgvector table with HNSW index: {index_name}")
        finally:
            self._put_connection(conn)
    
    def index_document(self, index_name: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        import json
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {index_name} (id, embedding, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata
                """, (doc_id, embedding, json.dumps(metadata)))
                conn.commit()
        finally:
            self._put_connection(conn)
    
    def search(self, index_name: str, query_embedding: List[float], limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        import numpy as np
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Convert list to numpy array for pgvector
                query_vec = np.array(query_embedding)
                
                # Define columns for each table (hardcoded to avoid information_schema query)
                if index_name == 'jobs':
                    columns = ['id', 'title', 'description', 'company', 'skills', 'location', 'job_type', 'vacancies', 'min_salary', 'max_salary', 'experience', 'ai_classified_job']
                elif index_name == 'schemes':
                    columns = ['id', 'name', 'ministry', 'description', 'categories', 'tags', 'state', 'level', 'url', 'ai_classified_scheme']
                elif index_name == 'upskill':
                    columns = ['id', 'name', 'description', 'provider', 'skills', 'location', 'address', 'contact', 'email', 'ai_classified_training']
                else:
                    columns = ['id']
                
                columns_str = ', '.join(columns)
                
                # Build WHERE clause for filters
                where_clauses = []
                params = [query_vec]  # First param for SELECT score calculation
                
                # Salary filter for jobs
                if filters and filters.get('min_salary') and index_name == 'jobs':
                    where_clauses.append("(max_salary >= %s OR max_salary = 0 OR max_salary IS NULL)")
                    params.append(filters['min_salary'])
                
                # Profession filter based on AI classification
                if filters and filters.get('profession'):
                    profession = filters['profession'].lower()
                    if index_name == 'jobs':
                        where_clauses.append("ai_classified_job = %s")
                        params.append(profession)
                    elif index_name == 'schemes':
                        where_clauses.append("ai_classified_scheme = %s")
                        params.append(profession)
                    elif index_name == 'upskill':
                        where_clauses.append("ai_classified_training = %s")
                        params.append(profession)
                
                where_clause = ""
                if where_clauses:
                    where_clause = "WHERE " + " AND ".join(where_clauses)
                
                # Add remaining vector params
                params.extend([query_vec, limit])  # For ORDER BY and LIMIT
                
                sql_query = f"""
                    SELECT {columns_str}, 1 - (embedding <=> %s) as score
                    FROM {index_name}
                    {where_clause}
                    ORDER BY embedding <=> %s
                    LIMIT %s
                """
                print(f"\n🔍 SQL Query: {sql_query}")
                print(f"📊 Params: filters={filters}, limit={limit}")

                cur.execute(sql_query, params)
                
                results = []
                for row in cur.fetchall():
                    result = {}
                    for i, col in enumerate(columns):
                        result[col] = row[i]
                    result["vector_score"] = float(row[-1])
                    results.append(result)
                
                return results
        finally:
            self._put_connection(conn)
    
    def delete_index(self, index_name: str) -> None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {index_name}")
                conn.commit()
                logger.info(f"Deleted table: {index_name}")
        finally:
            self._put_connection(conn)
    
    def close_pool(self):
        """Close all connections in the pool"""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")
    
    def get_store_name(self) -> str:
        return "PostgresPgVector"
