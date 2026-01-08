"""
Embedding Service
Generates and manages vector embeddings for semantic memory search
"""

from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session

from database_models import MemoryEmbedding, SemanticMemory
import uuid


class EmbeddingService:
    """
    Service for generating and managing vector embeddings
    
    Supports multiple embedding providers:
    - OpenAI (text-embedding-3-small, text-embedding-3-large)
    - Local models (future)
    """
    
    def __init__(self, db: Session, provider: str = "openai", model: str = "text-embedding-3-small"):
        """
        Initialize embedding service
        
        Args:
            db: Database session
            provider: Embedding provider (openai, local)
            model: Model name
        """
        self.db = db
        self.provider = provider
        self.model = model
        self.dimension = self._get_dimension(model)
        
        # Initialize provider client
        if provider == "openai":
            self._init_openai()
    
    def _get_dimension(self, model: str) -> int:
        """Get embedding dimension for model"""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(model, 1536)
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        if self.provider == "openai":
            return self._generate_openai_embedding(text)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate OpenAI embedding: {str(e)}")
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        if self.provider == "openai":
            return self._generate_openai_batch_embeddings(texts)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _generate_openai_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings using OpenAI API"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise RuntimeError(f"Failed to generate OpenAI batch embeddings: {str(e)}")
    
    def store_embedding(
        self,
        semantic_memory_id: str,
        embedding_vector: List[float]
    ) -> MemoryEmbedding:
        """
        Store embedding in database
        
        Args:
            semantic_memory_id: ID of semantic memory
            embedding_vector: Embedding vector
        
        Returns:
            Created embedding record
        """
        # Check if embedding already exists
        existing = self.db.query(MemoryEmbedding).filter(
            MemoryEmbedding.semantic_memory_id == semantic_memory_id,
            MemoryEmbedding.embedding_model == self.model
        ).first()
        
        if existing:
            # Update existing embedding
            existing.embedding_vector = json.dumps(embedding_vector)
            existing.dimension = len(embedding_vector)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new embedding
        embedding = MemoryEmbedding(
            id=str(uuid.uuid4()),
            semantic_memory_id=semantic_memory_id,
            embedding_model=self.model,
            embedding_vector=json.dumps(embedding_vector),
            dimension=len(embedding_vector),
            created_at=datetime.utcnow()
        )
        
        self.db.add(embedding)
        self.db.commit()
        self.db.refresh(embedding)
        
        return embedding
    
    def get_embedding(
        self,
        semantic_memory_id: str
    ) -> Optional[List[float]]:
        """
        Get embedding for semantic memory
        
        Args:
            semantic_memory_id: ID of semantic memory
        
        Returns:
            Embedding vector or None
        """
        embedding = self.db.query(MemoryEmbedding).filter(
            MemoryEmbedding.semantic_memory_id == semantic_memory_id,
            MemoryEmbedding.embedding_model == self.model
        ).first()
        
        if not embedding:
            return None
        
        return json.loads(embedding.embedding_vector)
    
    def embed_semantic_memory(
        self,
        semantic_memory_id: str,
        force_regenerate: bool = False
    ) -> MemoryEmbedding:
        """
        Generate and store embedding for semantic memory
        
        Args:
            semantic_memory_id: ID of semantic memory
            force_regenerate: Force regeneration even if exists
        
        Returns:
            Embedding record
        """
        # Check if embedding exists
        if not force_regenerate:
            existing = self.db.query(MemoryEmbedding).filter(
                MemoryEmbedding.semantic_memory_id == semantic_memory_id,
                MemoryEmbedding.embedding_model == self.model
            ).first()
            
            if existing:
                return existing
        
        # Get semantic memory
        memory = self.db.query(SemanticMemory).filter(
            SemanticMemory.id == semantic_memory_id
        ).first()
        
        if not memory:
            raise ValueError(f"Semantic memory not found: {semantic_memory_id}")
        
        # Generate embedding from embedding_text
        if not memory.embedding_text:
            raise ValueError(f"No embedding_text for memory: {semantic_memory_id}")
        
        embedding_vector = self.generate_embedding(memory.embedding_text)
        
        # Store embedding
        return self.store_embedding(semantic_memory_id, embedding_vector)
    
    def embed_all_semantic_memories(
        self,
        user_id: Optional[str] = None,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate embeddings for all semantic memories
        
        Args:
            user_id: Optional filter by user
            force_regenerate: Force regeneration even if exists
        
        Returns:
            Summary of embedding generation
        """
        # Get semantic memories
        query = self.db.query(SemanticMemory)
        if user_id:
            query = query.filter(SemanticMemory.user_id == user_id)
        
        memories = query.all()
        
        total = len(memories)
        generated = 0
        skipped = 0
        errors = 0
        
        for memory in memories:
            try:
                # Check if embedding exists
                if not force_regenerate:
                    existing = self.db.query(MemoryEmbedding).filter(
                        MemoryEmbedding.semantic_memory_id == memory.id,
                        MemoryEmbedding.embedding_model == self.model
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                
                # Generate embedding
                if memory.embedding_text:
                    self.embed_semantic_memory(memory.id, force_regenerate)
                    generated += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"Error embedding memory {memory.id}: {str(e)}")
        
        return {
            'total_memories': total,
            'generated': generated,
            'skipped': skipped,
            'errors': errors,
            'model': self.model
        }
    
    def cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Similarity score (0-1)
        """
        import math
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        # Cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def search_similar_memories(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using semantic search
        
        Args:
            query_text: Query text
            user_id: Optional filter by user
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of similar memories with scores
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query_text)
        
        # Get all embeddings
        query = self.db.query(MemoryEmbedding).filter(
            MemoryEmbedding.embedding_model == self.model
        )
        
        embeddings = query.all()
        
        # Calculate similarities
        results = []
        for embedding in embeddings:
            # Get semantic memory
            memory = self.db.query(SemanticMemory).filter(
                SemanticMemory.id == embedding.semantic_memory_id
            ).first()
            
            if not memory:
                continue
            
            # Filter by user if specified
            if user_id and memory.user_id != user_id:
                continue
            
            # Calculate similarity
            memory_embedding = json.loads(embedding.embedding_vector)
            similarity = self.cosine_similarity(query_embedding, memory_embedding)
            
            if similarity >= min_similarity:
                results.append({
                    'memory_id': memory.id,
                    'similarity': similarity,
                    'content': memory.content,
                    'category': memory.memory_category,
                    'usage_count': memory.usage_count,
                    'success_rate': memory.success_rate,
                    'embedding_text': memory.embedding_text
                })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Return top k
        return results[:top_k]
    
    def delete_embedding(self, semantic_memory_id: str) -> bool:
        """
        Delete embedding for semantic memory
        
        Args:
            semantic_memory_id: ID of semantic memory
        
        Returns:
            True if deleted, False if not found
        """
        embedding = self.db.query(MemoryEmbedding).filter(
            MemoryEmbedding.semantic_memory_id == semantic_memory_id,
            MemoryEmbedding.embedding_model == self.model
        ).first()
        
        if not embedding:
            return False
        
        self.db.delete(embedding)
        self.db.commit()
        
        return True