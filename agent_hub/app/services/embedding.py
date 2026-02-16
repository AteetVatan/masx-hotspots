# ┌───────────────────────────────────────────────────────────────┐
# │  Copyright (c) 2025 Ateet Vatan Bahmani                      │
# │  Project: MASX AI – Strategic Agentic AI System              │
# │  All rights reserved.                                        │
# └───────────────────────────────────────────────────────────────┘
#
# MASX AI is a proprietary software system developed and owned by Ateet Vatan Bahmani.
# The source code, documentation, workflows, designs, and naming (including "MASX AI")
# are protected by applicable copyright and trademark laws.
#
# Redistribution, modification, commercial use, or publication of any portion of this
# project without explicit written consent is strictly prohibited.
#
# This project is not open-source and is intended solely for internal, research,
# or demonstration use by the author.
#
# Contact: ab@masxai.com | MASXAI.com

"""
Embedding service for MASX-HOTSPOTS Agentic AI System.

Provides vector embedding capabilities with:
- OpenAI embeddings integration
- Local embedding models (sentence-transformers)
- Vector operations and similarity calculations
- Batch processing and caching
- Performance monitoring and optimization

Usage:
    from app.services.embedding import EmbeddingService

    embedder = EmbeddingService()
    embedding = await embedder.embed_text("Hello world")
    similarity = await embedder.calculate_similarity(embedding1, embedding2)
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sentence_transformers import SentenceTransformer
import openai

from ..core.exceptions import EmbeddingException, ConfigurationException
from ..core.utils import measure_execution_time
from ..config.settings import get_settings
from ..config.logging_config import get_service_logger


class EmbeddingModel(Enum):
    """Supported embedding models."""

    OPENAI_TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"
    OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    OPENAI_TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2 = "all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_ALL_MPNET_BASE_V2 = "all-mpnet-base-v2"
    SENTENCE_TRANSFORMERS_MULTI_QA_MPNET_BASE_DOT_V1 = "multi-qa-mpnet-base-dot-v1"


@dataclass
class EmbeddingRequest:
    """Embedding request data."""

    text: str
    model: EmbeddingModel = EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002
    cache_key: Optional[str] = None

    def __post_init__(self):
        if self.cache_key is None:
            # Generate cache key from text and model
            key_data = f"{self.text}:{self.model.value}"
            self.cache_key = hashlib.md5(key_data.encode()).hexdigest()


@dataclass
class EmbeddingResult:
    """Embedding result data."""

    text: str
    embedding: List[float]
    model: EmbeddingModel
    dimensions: int
    execution_time: float = 0.0
    cached: bool = False
    token_count: Optional[int] = None


@dataclass
class SimilarityResult:
    """Similarity calculation result."""

    text1: str
    text2: str
    similarity_score: float
    method: str = "cosine"
    execution_time: float = 0.0


class EmbeddingService:
    """
    Embedding service with multiple model support.

    Features:
    - Multiple embedding models (OpenAI, Sentence Transformers)
    - Vector operations and similarity calculations
    - Batch processing for efficiency
    - Caching for performance
    - Performance monitoring and optimization
    """

    def __init__(self):
        """Initialize the embedding service."""
        self.settings = get_settings()
        self.logger = get_service_logger("EmbeddingService")
        self._cache: Dict[str, EmbeddingResult] = {}
        self._models: Dict[EmbeddingModel, Any] = {}
        self._openai_client = None

        self._initialize_models()

    def _initialize_models(self):
        """Initialize embedding models."""
        try:
            # Initialize OpenAI client
            if self.settings.openai_api_key:
                openai.api_key = self.settings.openai_api_key
                self._openai_client = openai
                self.logger.info("OpenAI client initialized")

            # Initialize local models
            if self.settings.enable_local_embeddings:
                self._initialize_local_models()

            if not self._openai_client and not self._models:
                self.logger.warning("No embedding models configured")

        except Exception as e:
            self.logger.error(f"Failed to initialize embedding models: {e}")
            raise ConfigurationException(
                f"Embedding service initialization failed: {str(e)}"
            )

    def _initialize_local_models(self):
        """Initialize local embedding models."""
        try:
            # Initialize sentence transformers models
            models_to_load = [
                EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MINILM_L6_V2,
                EmbeddingModel.SENTENCE_TRANSFORMERS_ALL_MPNET_BASE_V2,
                EmbeddingModel.SENTENCE_TRANSFORMERS_MULTI_QA_MPNET_BASE_DOT_V1,
            ]

            for model_enum in models_to_load:
                try:
                    model = SentenceTransformer(model_enum.value)
                    self._models[model_enum] = model
                    self.logger.info(f"Local model loaded: {model_enum.value}")
                except Exception as e:
                    self.logger.warning(f"Failed to load model {model_enum.value}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to initialize local models: {e}")

    async def embed_text(
        self, text: str, model: Optional[EmbeddingModel] = None, use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            model: Embedding model to use
            use_cache: Whether to use cached results

        Returns:
            EmbeddingResult: Embedding result
        """
        with measure_execution_time("embed_text"):
            try:
                # Use default model if none specified
                if model is None:
                    model = EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002

                # Create embedding request
                request = EmbeddingRequest(text=text, model=model)

                # Check cache first
                if use_cache and request.cache_key in self._cache:
                    cached_result = self._cache[request.cache_key]
                    cached_result.cached = True
                    self.logger.debug(
                        f"Embedding cache hit for key: {request.cache_key}"
                    )
                    return cached_result

                # Generate embedding
                result = await self._embed_with_model(request)

                # Cache result
                if use_cache:
                    self._cache[request.cache_key] = result

                self.logger.info(
                    f"Embedding generated: {model.value}",
                    dimensions=result.dimensions,
                    text_length=len(text),
                )

                return result

            except Exception as e:
                self.logger.error(f"Embedding generation failed: {e}")
                raise EmbeddingException(f"Embedding generation failed: {str(e)}")

    async def _embed_with_model(self, request: EmbeddingRequest) -> EmbeddingResult:
        """
        Generate embedding using specified model.

        Args:
            request: Embedding request

        Returns:
            EmbeddingResult: Embedding result
        """
        try:
            if request.model.value.startswith("text-embedding"):
                # OpenAI model
                if not self._openai_client:
                    raise EmbeddingException("OpenAI client not initialized")

                return await self._embed_with_openai(request)

            elif request.model.value.startswith(("all-", "multi-qa-")):
                # Sentence Transformers model
                if request.model not in self._models:
                    raise EmbeddingException(f"Model {request.model.value} not loaded")

                return await self._embed_with_sentence_transformers(request)

            else:
                raise EmbeddingException(f"Unsupported model: {request.model.value}")

        except Exception as e:
            raise EmbeddingException(
                f"Embedding with model {request.model.value} failed: {str(e)}"
            )

    async def _embed_with_openai(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Generate embedding using OpenAI API."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            def _openai_embed():
                response = openai.Embedding.create(
                    input=request.text, model=request.model.value
                )
                return response

            response = await loop.run_in_executor(None, _openai_embed)

            embedding = response["data"][0]["embedding"]
            token_count = response["usage"]["total_tokens"]

            return EmbeddingResult(
                text=request.text,
                embedding=embedding,
                model=request.model,
                dimensions=len(embedding),
                token_count=token_count,
            )

        except Exception as e:
            raise EmbeddingException(f"OpenAI embedding failed: {str(e)}")

    async def _embed_with_sentence_transformers(
        self, request: EmbeddingRequest
    ) -> EmbeddingResult:
        """Generate embedding using Sentence Transformers."""
        try:
            model = self._models[request.model]

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, model.encode, request.text)

            # Convert numpy array to list
            embedding_list = embedding.tolist()

            return EmbeddingResult(
                text=request.text,
                embedding=embedding_list,
                model=request.model,
                dimensions=len(embedding_list),
            )

        except Exception as e:
            raise EmbeddingException(
                f"Sentence Transformers embedding failed: {str(e)}"
            )

    async def embed_batch(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
        max_concurrent: int = 10,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts in parallel.

        Args:
            texts: List of texts to embed
            model: Embedding model to use
            max_concurrent: Maximum concurrent embeddings

        Returns:
            List of embedding results
        """
        with measure_execution_time("embed_batch"):
            try:
                semaphore = asyncio.Semaphore(max_concurrent)

                async def embed_single(text: str) -> EmbeddingResult:
                    async with semaphore:
                        return await self.embed_text(text=text, model=model)

                tasks = [embed_single(text) for text in texts]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle exceptions
                embedding_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Embedding {i} failed: {result}")
                        # Return zero vector as fallback
                        embedding_results.append(
                            EmbeddingResult(
                                text=texts[i],
                                embedding=[0.0] * 1536,  # Default dimension
                                model=model
                                or EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002,
                                dimensions=1536,
                            )
                        )
                    else:
                        embedding_results.append(result)

                self.logger.info(
                    f"Batch embedding completed: {len(embedding_results)} texts"
                )
                return embedding_results

            except Exception as e:
                self.logger.error(f"Batch embedding failed: {e}")
                raise EmbeddingException(f"Batch embedding failed: {str(e)}")

    async def calculate_similarity(
        self,
        embedding1: Union[List[float], str],
        embedding2: Union[List[float], str],
        method: str = "cosine",
    ) -> SimilarityResult:
        """
        Calculate similarity between two embeddings or texts.

        Args:
            embedding1: First embedding or text
            embedding2: Second embedding or text
            method: Similarity method ('cosine', 'euclidean', 'dot_product')

        Returns:
            SimilarityResult: Similarity calculation result
        """
        with measure_execution_time("calculate_similarity"):
            try:
                # Convert texts to embeddings if needed
                if isinstance(embedding1, str):
                    result1 = await self.embed_text(embedding1)
                    embedding1 = result1.embedding
                    text1 = embedding1
                else:
                    text1 = "embedding1"

                if isinstance(embedding2, str):
                    result2 = await self.embed_text(embedding2)
                    embedding2 = result2.embedding
                    text2 = embedding2
                else:
                    text2 = "embedding2"

                # Convert to numpy arrays
                vec1 = np.array(embedding1)
                vec2 = np.array(embedding2)

                # Calculate similarity based on method
                if method == "cosine":
                    similarity = self._cosine_similarity(vec1, vec2)
                elif method == "euclidean":
                    similarity = self._euclidean_similarity(vec1, vec2)
                elif method == "dot_product":
                    similarity = self._dot_product_similarity(vec1, vec2)
                else:
                    raise EmbeddingException(f"Unsupported similarity method: {method}")

                return SimilarityResult(
                    text1=text1, text2=text2, similarity_score=similarity, method=method
                )

            except Exception as e:
                self.logger.error(f"Similarity calculation failed: {e}")
                raise EmbeddingException(f"Similarity calculation failed: {str(e)}")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _euclidean_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate Euclidean similarity between two vectors."""
        distance = np.linalg.norm(vec1 - vec2)
        # Convert distance to similarity (1 / (1 + distance))
        return 1.0 / (1.0 + distance)

    def _dot_product_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate dot product similarity between two vectors."""
        return float(np.dot(vec1, vec2))

    async def find_most_similar(
        self,
        query_embedding: Union[List[float], str],
        candidate_embeddings: List[Union[List[float], str]],
        top_k: int = 5,
        method: str = "cosine",
    ) -> List[Tuple[int, float]]:
        """
        Find most similar embeddings to query.

        Args:
            query_embedding: Query embedding or text
            candidate_embeddings: List of candidate embeddings or texts
            top_k: Number of top results to return
            method: Similarity method

        Returns:
            List of (index, similarity_score) tuples
        """
        with measure_execution_time("find_most_similar"):
            try:
                # Convert query to embedding if needed
                if isinstance(query_embedding, str):
                    query_result = await self.embed_text(query_embedding)
                    query_embedding = query_result.embedding

                # Calculate similarities
                similarities = []
                for i, candidate in enumerate(candidate_embeddings):
                    similarity_result = await self.calculate_similarity(
                        query_embedding, candidate, method
                    )
                    similarities.append((i, similarity_result.similarity_score))

                # Sort by similarity (descending)
                similarities.sort(key=lambda x: x[1], reverse=True)

                # Return top_k results
                return similarities[:top_k]

            except Exception as e:
                self.logger.error(f"Most similar search failed: {e}")
                raise EmbeddingException(f"Most similar search failed: {str(e)}")

    async def cluster_embeddings(
        self, embeddings: List[List[float]], n_clusters: int = 5, method: str = "kmeans"
    ) -> List[int]:
        """
        Cluster embeddings using specified method.

        Args:
            embeddings: List of embeddings to cluster
            n_clusters: Number of clusters
            method: Clustering method ('kmeans', 'hierarchical')

        Returns:
            List of cluster assignments
        """
        with measure_execution_time("cluster_embeddings"):
            try:
                # Convert to numpy array
                embedding_array = np.array(embeddings)

                # Run clustering in thread pool
                loop = asyncio.get_event_loop()

                if method == "kmeans":
                    from sklearn.cluster import KMeans

                    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                    cluster_labels = await loop.run_in_executor(
                        None, kmeans.fit_predict, embedding_array
                    )

                elif method == "hierarchical":
                    from sklearn.cluster import AgglomerativeClustering

                    clustering = AgglomerativeClustering(n_clusters=n_clusters)
                    cluster_labels = await loop.run_in_executor(
                        None, clustering.fit_predict, embedding_array
                    )

                else:
                    raise EmbeddingException(f"Unsupported clustering method: {method}")

                return cluster_labels.tolist()

            except Exception as e:
                self.logger.error(f"Embedding clustering failed: {e}")
                raise EmbeddingException(f"Embedding clustering failed: {str(e)}")

    def get_model_info(self, model: EmbeddingModel) -> Dict[str, Any]:
        """
        Get information about an embedding model.

        Args:
            model: Embedding model

        Returns:
            Dictionary with model information
        """
        model_info = {
            "name": model.value,
            "type": (
                "openai"
                if model.value.startswith("text-embedding")
                else "sentence_transformers"
            ),
            "dimensions": None,
            "max_tokens": None,
            "loaded": False,
        }

        # Add model-specific information
        if model.value == "text-embedding-ada-002":
            model_info.update(
                {
                    "dimensions": 1536,
                    "max_tokens": 8191,
                    "description": "OpenAI's text-embedding-ada-002 model",
                }
            )
        elif model.value == "text-embedding-3-small":
            model_info.update(
                {
                    "dimensions": 1536,
                    "max_tokens": 8191,
                    "description": "OpenAI's text-embedding-3-small model",
                }
            )
        elif model.value == "text-embedding-3-large":
            model_info.update(
                {
                    "dimensions": 3072,
                    "max_tokens": 8191,
                    "description": "OpenAI's text-embedding-3-large model",
                }
            )
        elif model.value == "all-MiniLM-L6-v2":
            model_info.update(
                {
                    "dimensions": 384,
                    "description": "Sentence Transformers all-MiniLM-L6-v2 model",
                }
            )
        elif model.value == "all-mpnet-base-v2":
            model_info.update(
                {
                    "dimensions": 768,
                    "description": "Sentence Transformers all-mpnet-base-v2 model",
                }
            )
        elif model.value == "multi-qa-mpnet-base-dot-v1":
            model_info.update(
                {
                    "dimensions": 768,
                    "description": "Sentence Transformers multi-qa-mpnet-base-dot-v1 model",
                }
            )

        # Check if model is loaded
        if model in self._models:
            model_info["loaded"] = True
        elif model.value.startswith("text-embedding") and self._openai_client:
            model_info["loaded"] = True

        return model_info

    def clear_cache(self):
        """Clear the embedding cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Embedding cache cleared: {cache_size} entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get embedding cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "loaded_models": [model.value for model in self._models.keys()],
            "openai_available": self._openai_client is not None,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform embedding service health check.

        Returns:
            Dictionary with health check results
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "models": {},
            }

            # Check OpenAI
            if self._openai_client:
                try:
                    # Simple embedding test
                    test_result = await self.embed_text(
                        "test", model=EmbeddingModel.OPENAI_TEXT_EMBEDDING_ADA_002
                    )
                    health_status["models"]["openai"] = {
                        "status": "healthy",
                        "dimensions": test_result.dimensions,
                    }
                except Exception as e:
                    health_status["models"]["openai"] = {
                        "status": "error",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["models"]["openai"] = {"status": "not_configured"}

            # Check local models
            for model_enum, model in self._models.items():
                try:
                    # Simple embedding test
                    test_result = await self.embed_text("test", model=model_enum)
                    health_status["models"][model_enum.value] = {
                        "status": "healthy",
                        "dimensions": test_result.dimensions,
                    }
                except Exception as e:
                    health_status["models"][model_enum.value] = {
                        "status": "error",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
            }
