# # ┌───────────────────────────────────────────────────────────────┐
# # │  Copyright (c) 2025 Ateet Vatan Bahmani                      │
# # │  Project: MASX AI – Strategic Agentic AI System              │
# # │  All rights reserved.                                        │
# # └───────────────────────────────────────────────────────────────┘
# #
# # MASX AI is a proprietary software system developed and owned by Ateet Vatan Bahmani.
# # The source code, documentation, workflows, designs, and naming (including "MASX AI")
# # are protected by applicable copyright and trademark laws.
# #
# # Redistribution, modification, commercial use, or publication of any portion of this
# # project without explicit written consent is strictly prohibited.
# #
# # This project is not open-source and is intended solely for internal, research,
# # or demonstration use by the author.
# #
# # Contact: ab@masxai.com | MASXAI.com

# """
# Service management endpoints for MASX-HOTSPOTS Agentic AI System.

# Provides endpoints for:
# - Service status and configuration
# - Service health monitoring
# - Cache management
# - Service metrics
# """

# from typing import Dict, Any, Optional
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel

# from ...config.logging_config import get_api_logger
# from ...services import DatabaseService, TranslationService, EmbeddingService

# router = APIRouter()
# logger = get_api_logger("ServiceRoutes")


# class ServiceStatus(BaseModel):
#     """Service status model."""

#     name: str
#     status: str
#     version: str
#     uptime: float
#     metrics: Dict[str, Any]


# class CacheStats(BaseModel):
#     """Cache statistics model."""

#     service: str
#     cache_size: int
#     hit_rate: float
#     miss_rate: float
#     total_requests: int


# @router.get("/status")
# async def get_services_status():
#     """
#     Get status of all services.

#     Returns:
#         Dictionary with service status information
#     """
#     logger.info("Services status requested")

#     try:
#         services_status = {}

#         # Database service status
#         try:
#             async with DatabaseService() as db:
#                 db_health = await db.health_check()
#                 services_status["database"] = {
#                     "name": "Database Service",
#                     "status": db_health["status"],
#                     "version": "1.0.0",
#                     "uptime": 0.0,  # Would need to track uptime
#                     "metrics": db_health,
#                 }
#         except Exception as e:
#             services_status["database"] = {
#                 "name": "Database Service",
#                 "status": "error",
#                 "version": "1.0.0",
#                 "uptime": 0.0,
#                 "error": str(e),
#             }

#         # Translation service status
#         try:
#             async with TranslationService() as translator:
#                 trans_health = await translator.health_check()
#                 cache_stats = translator.get_cache_stats()
#                 services_status["translation"] = {
#                     "name": "Translation Service",
#                     "status": trans_health["status"],
#                     "version": "1.0.0",
#                     "uptime": 0.0,
#                     "metrics": {**trans_health, "cache_stats": cache_stats},
#                 }
#         except Exception as e:
#             services_status["translation"] = {
#                 "name": "Translation Service",
#                 "status": "error",
#                 "version": "1.0.0",
#                 "uptime": 0.0,
#                 "error": str(e),
#             }

#         # Embedding service status
#         try:
#             async with EmbeddingService() as embedder:
#                 embed_health = await embedder.health_check()
#                 cache_stats = embedder.get_cache_stats()
#                 services_status["embedding"] = {
#                     "name": "Embedding Service",
#                     "status": embed_health["status"],
#                     "version": "1.0.0",
#                     "uptime": 0.0,
#                     "metrics": {**embed_health, "cache_stats": cache_stats},
#                 }
#         except Exception as e:
#             services_status["embedding"] = {
#                 "name": "Embedding Service",
#                 "status": "error",
#                 "version": "1.0.0",
#                 "uptime": 0.0,
#                 "error": str(e),
#             }

#         logger.info("Services status retrieved successfully")
#         return {
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "services": services_status,
#         }

#     except Exception as e:
#         logger.error(f"Services status retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Services status retrieval failed: {str(e)}"
#         )


# @router.get("/database")
# async def get_database_service_info():
#     """
#     Get database service information.

#     Returns:
#         Database service information
#     """
#     logger.info("Database service info requested")

#     try:
#         async with DatabaseService() as db:
#             health_status = await db.health_check()
#             stats = await db.get_database_stats()

#             service_info = {
#                 "name": "Database Service",
#                 "version": "1.0.0",
#                 "health": health_status,
#                 "statistics": stats,
#                 "capabilities": [
#                     "CRUD operations",
#                     "Vector similarity search",
#                     "Transaction management",
#                     "Connection pooling",
#                     "Performance monitoring",
#                 ],
#             }

#             logger.info("Database service info retrieved")
#             return service_info

#     except Exception as e:
#         logger.error(f"Database service info retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Database service info retrieval failed: {str(e)}"
#         )


# @router.get("/translation")
# async def get_translation_service_info():
#     """
#     Get translation service information.

#     Returns:
#         Translation service information
#     """
#     logger.info("Translation service info requested")

#     try:
#         async with TranslationService() as translator:
#             health_status = await translator.health_check()
#             cache_stats = translator.get_cache_stats()
#             supported_languages = translator.get_supported_languages(
#                 translator.TranslationProvider.GOOGLE
#             )

#             service_info = {
#                 "name": "Translation Service",
#                 "version": "1.0.0",
#                 "health": health_status,
#                 "cache_stats": cache_stats,
#                 "supported_languages": supported_languages,
#                 "capabilities": [
#                     "Multi-language translation",
#                     "Language detection",
#                     "Batch translation",
#                     "Caching and rate limiting",
#                     "Multiple providers (Google, DeepL, Local)",
#                 ],
#             }

#             logger.info("Translation service info retrieved")
#             return service_info

#     except Exception as e:
#         logger.error(f"Translation service info retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Translation service info retrieval failed: {str(e)}",
#         )


# @router.get("/embedding")
# async def get_embedding_service_info():
#     """
#     Get embedding service information.

#     Returns:
#         Embedding service information
#     """
#     logger.info("Embedding service info requested")

#     try:
#         async with EmbeddingService() as embedder:
#             health_status = await embedder.health_check()
#             cache_stats = embedder.get_cache_stats()

#             # Get model information
#             models_info = {}
#             for model_enum in embedder.EmbeddingModel:
#                 models_info[model_enum.value] = embedder.get_model_info(model_enum)

#             service_info = {
#                 "name": "Embedding Service",
#                 "version": "1.0.0",
#                 "health": health_status,
#                 "cache_stats": cache_stats,
#                 "models": models_info,
#                 "capabilities": [
#                     "Text embedding generation",
#                     "Vector similarity calculations",
#                     "Batch processing",
#                     "Multiple models (OpenAI, Sentence Transformers)",
#                     "Clustering and similarity search",
#                 ],
#             }

#             logger.info("Embedding service info retrieved")
#             return service_info

#     except Exception as e:
#         logger.error(f"Embedding service info retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Embedding service info retrieval failed: {str(e)}"
#         )


# @router.get("/cache")
# async def get_cache_statistics():
#     """
#     Get cache statistics for all services.

#     Returns:
#         Cache statistics for all services
#     """
#     logger.info("Cache statistics requested")

#     try:
#         cache_stats = {}

#         # Translation service cache
#         try:
#             async with TranslationService() as translator:
#                 trans_cache = translator.get_cache_stats()
#                 cache_stats["translation"] = CacheStats(
#                     service="translation",
#                     cache_size=trans_cache["cache_size"],
#                     hit_rate=0.8,  # Mock data
#                     miss_rate=0.2,  # Mock data
#                     total_requests=trans_cache["cache_size"] * 5,  # Mock data
#                 )
#         except Exception as e:
#             cache_stats["translation"] = {"service": "translation", "error": str(e)}

#         # Embedding service cache
#         try:
#             async with EmbeddingService() as embedder:
#                 embed_cache = embedder.get_cache_stats()
#                 cache_stats["embedding"] = CacheStats(
#                     service="embedding",
#                     cache_size=embed_cache["cache_size"],
#                     hit_rate=0.7,  # Mock data
#                     miss_rate=0.3,  # Mock data
#                     total_requests=embed_cache["cache_size"] * 3,  # Mock data
#                 )
#         except Exception as e:
#             cache_stats["embedding"] = {"service": "embedding", "error": str(e)}

#         logger.info("Cache statistics retrieved")
#         return {
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "cache_stats": cache_stats,
#         }

#     except Exception as e:
#         logger.error(f"Cache statistics retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Cache statistics retrieval failed: {str(e)}"
#         )


# @router.delete("/cache/clear")
# async def clear_all_caches():
#     """
#     Clear all service caches.

#     Returns:
#         Cache clearing status
#     """
#     logger.info("Cache clearing requested")

#     try:
#         cleared_caches = {}

#         # Clear translation cache
#         try:
#             async with TranslationService() as translator:
#                 translator.clear_cache()
#                 cleared_caches["translation"] = "cleared"
#         except Exception as e:
#             cleared_caches["translation"] = f"error: {str(e)}"

#         # Clear embedding cache
#         try:
#             async with EmbeddingService() as embedder:
#                 embedder.clear_cache()
#                 cleared_caches["embedding"] = "cleared"
#         except Exception as e:
#             cleared_caches["embedding"] = f"error: {str(e)}"

#         logger.info("All caches cleared")
#         return {
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "status": "completed",
#             "cleared_caches": cleared_caches,
#         }

#     except Exception as e:
#         logger.error(f"Cache clearing failed: {e}")
#         raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")


# @router.delete("/cache/clear/{service}")
# async def clear_service_cache(service: str):
#     """
#     Clear cache for a specific service.

#     Args:
#         service: Service name (translation/embedding)

#     Returns:
#         Cache clearing status
#     """
#     logger.info(f"Cache clearing requested for service: {service}")

#     try:
#         if service == "translation":
#             async with TranslationService() as translator:
#                 translator.clear_cache()
#                 logger.info("Translation cache cleared")
#                 return {
#                     "service": service,
#                     "status": "cleared",
#                     "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#                 }

#         elif service == "embedding":
#             async with EmbeddingService() as embedder:
#                 embedder.clear_cache()
#                 logger.info("Embedding cache cleared")
#                 return {
#                     "service": service,
#                     "status": "cleared",
#                     "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#                 }

#         else:
#             raise HTTPException(
#                 status_code=400, detail=f"Unsupported service: {service}"
#             )

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Cache clearing failed for {service}: {e}")
#         raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")


# @router.get("/metrics")
# async def get_service_metrics():
#     """
#     Get comprehensive service metrics.

#     Returns:
#         Service metrics
#     """
#     logger.info("Service metrics requested")

#     try:
#         metrics = {
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "services": {},
#         }

#         # Database metrics
#         try:
#             async with DatabaseService() as db:
#                 db_stats = await db.get_database_stats()
#                 metrics["services"]["database"] = {
#                     "type": "database",
#                     "metrics": db_stats,
#                     "performance": {
#                         "avg_query_time": 0.05,  # Mock data
#                         "connection_pool_size": 10,
#                         "active_connections": 2,
#                     },
#                 }
#         except Exception as e:
#             metrics["services"]["database"] = {"type": "database", "error": str(e)}

#         # Translation metrics
#         try:
#             async with TranslationService() as translator:
#                 trans_cache = translator.get_cache_stats()
#                 metrics["services"]["translation"] = {
#                     "type": "translation",
#                     "cache_metrics": trans_cache,
#                     "performance": {
#                         "avg_translation_time": 0.5,  # Mock data
#                         "requests_per_minute": 120,
#                         "success_rate": 0.98,
#                     },
#                 }
#         except Exception as e:
#             metrics["services"]["translation"] = {
#                 "type": "translation",
#                 "error": str(e),
#             }

#         # Embedding metrics
#         try:
#             async with EmbeddingService() as embedder:
#                 embed_cache = embedder.get_cache_stats()
#                 metrics["services"]["embedding"] = {
#                     "type": "embedding",
#                     "cache_metrics": embed_cache,
#                     "performance": {
#                         "avg_embedding_time": 0.2,  # Mock data
#                         "requests_per_minute": 200,
#                         "success_rate": 0.99,
#                     },
#                 }
#         except Exception as e:
#             metrics["services"]["embedding"] = {"type": "embedding", "error": str(e)}

#         logger.info("Service metrics retrieved")
#         return metrics

#     except Exception as e:
#         logger.error(f"Service metrics retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Service metrics retrieval failed: {str(e)}"
#         )


# @router.post("/test")
# async def test_service(service: str, test_type: str = "health"):
#     """
#     Test a specific service.

#     Args:
#         service: Service name to test
#         test_type: Type of test to perform

#     Returns:
#         Test results
#     """
#     logger.info(f"Service test requested: {service} ({test_type})")

#     try:
#         if service == "database":
#             async with DatabaseService() as db:
#                 if test_type == "health":
#                     result = await db.health_check()
#                 elif test_type == "connection":
#                     # Test basic connection
#                     stats = await db.get_database_stats()
#                     result = {"status": "connected", "stats": stats}
#                 else:
#                     raise HTTPException(
#                         status_code=400, detail=f"Unsupported test type: {test_type}"
#                     )

#         elif service == "translation":
#             async with TranslationService() as translator:
#                 if test_type == "health":
#                     result = await translator.health_check()
#                 elif test_type == "translation":
#                     # Test basic translation
#                     test_result = await translator.translate(
#                         "Hello world", target_lang="es"
#                     )
#                     result = {
#                         "status": "success",
#                         "translation": test_result.translated_text,
#                         "confidence": test_result.confidence,
#                     }
#                 else:
#                     raise HTTPException(
#                         status_code=400, detail=f"Unsupported test type: {test_type}"
#                     )

#         elif service == "embedding":
#             async with EmbeddingService() as embedder:
#                 if test_type == "health":
#                     result = await embedder.health_check()
#                 elif test_type == "embedding":
#                     # Test basic embedding
#                     test_result = await embedder.embed_text("Hello world")
#                     result = {
#                         "status": "success",
#                         "dimensions": test_result.dimensions,
#                         "model": test_result.model.value,
#                     }
#                 else:
#                     raise HTTPException(
#                         status_code=400, detail=f"Unsupported test type: {test_type}"
#                     )

#         else:
#             raise HTTPException(
#                 status_code=400, detail=f"Unsupported service: {service}"
#             )

#         logger.info(f"Service test completed: {service}")
#         return {
#             "service": service,
#             "test_type": test_type,
#             "result": result,
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Service test failed: {e}")
#         raise HTTPException(status_code=500, detail=f"Service test failed: {str(e)}")
