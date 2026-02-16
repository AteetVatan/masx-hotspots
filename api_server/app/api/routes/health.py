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
# Health check endpoints for MASX-HOTSPOTS Agentic AI System.

# Provides endpoints for:
# - System health status
# - Service health checks
# - Performance metrics
# - System information
# """

# from typing import Dict, Any
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel

# from ...config.logging_config import get_api_logger
# from ...services import DatabaseService, TranslationService, EmbeddingService
# from ...workflows import MASXOrchestrator

# router = APIRouter()
# logger = get_api_logger("HealthRoutes")


# class HealthResponse(BaseModel):
#     """Health check response model."""

#     status: str
#     timestamp: str
#     version: str
#     services: Dict[str, Any]
#     system_info: Dict[str, Any]


# @router.get("/", response_model=HealthResponse)
# async def health_check():
#     """
#     Overall system health check.

#     Returns:
#         HealthResponse: System health status
#     """
#     logger.info("Health check requested")

#     try:
#         # Check all services
#         services_health = {}

#         # Database health
#         try:
#             async with DatabaseService() as db:
#                 db_health = await db.health_check()
#                 services_health["database"] = db_health
#         except Exception as e:
#             services_health["database"] = {"status": "error", "error": str(e)}

#         # Translation service health
#         try:
#             async with TranslationService() as translator:
#                 trans_health = await translator.health_check()
#                 services_health["translation"] = trans_health
#         except Exception as e:
#             services_health["translation"] = {"status": "error", "error": str(e)}

#         # Embedding service health
#         try:
#             async with EmbeddingService() as embedder:
#                 embed_health = await embedder.health_check()
#                 services_health["embedding"] = embed_health
#         except Exception as e:
#             services_health["embedding"] = {"status": "error", "error": str(e)}

#         # Determine overall status
#         overall_status = "healthy"
#         for service_name, service_health in services_health.items():
#             if service_health.get("status") == "error":
#                 overall_status = "unhealthy"
#                 break

#         # System information
#         import platform
#         import psutil

#         system_info = {
#             "platform": platform.platform(),
#             "python_version": platform.python_version(),
#             "cpu_count": psutil.cpu_count(),
#             "memory_total": psutil.virtual_memory().total,
#             "memory_available": psutil.virtual_memory().available,
#             "disk_usage": psutil.disk_usage("/").percent,
#         }

#         response = HealthResponse(
#             status=overall_status,
#             timestamp=__import__("datetime").datetime.utcnow().isoformat(),
#             version="1.0.0",
#             services=services_health,
#             system_info=system_info,
#         )

#         logger.info(f"Health check completed: {overall_status}")
#         return response

#     except Exception as e:
#         logger.error(f"Health check failed: {e}")
#         raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# @router.get("/database")
# async def database_health():
#     """
#     Database service health check.

#     Returns:
#         dict: Database health status
#     """
#     logger.info("Database health check requested")

#     try:
#         async with DatabaseService() as db:
#             health_status = await db.health_check()
#             logger.info(f"Database health check completed: {health_status['status']}")
#             return health_status
#     except Exception as e:
#         logger.error(f"Database health check failed: {e}")
#         raise HTTPException(
#             status_code=503, detail=f"Database health check failed: {str(e)}"
#         )


# @router.get("/translation")
# async def translation_health():
#     """
#     Translation service health check.

#     Returns:
#         dict: Translation service health status
#     """
#     logger.info("Translation health check requested")

#     try:
#         async with TranslationService() as translator:
#             health_status = await translator.health_check()
#             logger.info(
#                 f"Translation health check completed: {health_status['status']}"
#             )
#             return health_status
#     except Exception as e:
#         logger.error(f"Translation health check failed: {e}")
#         raise HTTPException(
#             status_code=503, detail=f"Translation health check failed: {str(e)}"
#         )


# @router.get("/embedding")
# async def embedding_health():
#     """
#     Embedding service health check.

#     Returns:
#         dict: Embedding service health status
#     """
#     logger.info("Embedding health check requested")

#     try:
#         async with EmbeddingService() as embedder:
#             health_status = await embedder.health_check()
#             logger.info(f"Embedding health check completed: {health_status['status']}")
#             return health_status
#     except Exception as e:
#         logger.error(f"Embedding health check failed: {e}")
#         raise HTTPException(
#             status_code=503, detail=f"Embedding health check failed: {str(e)}"
#         )


# @router.get("/workflows")
# async def workflows_health():
#     """
#     Workflow orchestrator health check.

#     Returns:
#         dict: Workflow orchestrator health status
#     """
#     logger.info("Workflows health check requested")

#     try:
#         orchestrator = MASXOrchestrator()

#         # Check if orchestrator can be initialized
#         health_status = {
#             "status": "healthy",
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "orchestrator": {
#                 "initialized": True,
#                 "agents_loaded": len(orchestrator.agents),
#                 "agent_names": list(orchestrator.agents.keys()),
#             },
#         }

#         logger.info(f"Workflows health check completed: {health_status['status']}")
#         return health_status
#     except Exception as e:
#         logger.error(f"Workflows health check failed: {e}")
#         raise HTTPException(
#             status_code=503, detail=f"Workflows health check failed: {str(e)}"
#         )


# @router.get("/ready")
# async def readiness_check():
#     """
#     Readiness check for Kubernetes/container orchestration.

#     Returns:
#         dict: Readiness status
#     """
#     logger.info("Readiness check requested")

#     try:
#         # Check critical services
#         critical_services = ["database", "embedding"]
#         service_status = {}

#         # Database check
#         try:
#             async with DatabaseService() as db:
#                 db_health = await db.health_check()
#                 service_status["database"] = db_health["status"] == "healthy"
#         except Exception:
#             service_status["database"] = False

#         # Embedding check
#         try:
#             async with EmbeddingService() as embedder:
#                 embed_health = await embedder.health_check()
#                 service_status["embedding"] = embed_health["status"] == "healthy"
#         except Exception:
#             service_status["embedding"] = False

#         # All critical services must be healthy
#         ready = all(service_status.values())

#         response = {
#             "ready": ready,
#             "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#             "services": service_status,
#         }

#         if not ready:
#             raise HTTPException(status_code=503, detail="System not ready")

#         logger.info("Readiness check completed: ready")
#         return response

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Readiness check failed: {e}")
#         raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")


# @router.get("/live")
# async def liveness_check():
#     """
#     Liveness check for Kubernetes/container orchestration.

#     Returns:
#         dict: Liveness status
#     """
#     logger.debug("Liveness check requested")

#     return {
#         "alive": True,
#         "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
#     }


# @router.get("/metrics")
# async def system_metrics():
#     """
#     System performance metrics.

#     Returns:
#         dict: System metrics
#     """
#     logger.info("System metrics requested")

#     try:
#         import psutil
#         import time

#         # CPU metrics
#         cpu_percent = psutil.cpu_percent(interval=1)
#         cpu_count = psutil.cpu_count()

#         # Memory metrics
#         memory = psutil.virtual_memory()
#         memory_metrics = {
#             "total": memory.total,
#             "available": memory.available,
#             "used": memory.used,
#             "percent": memory.percent,
#         }

#         # Disk metrics
#         disk = psutil.disk_usage("/")
#         disk_metrics = {
#             "total": disk.total,
#             "used": disk.used,
#             "free": disk.free,
#             "percent": disk.percent,
#         }

#         # Network metrics
#         network = psutil.net_io_counters()
#         network_metrics = {
#             "bytes_sent": network.bytes_sent,
#             "bytes_recv": network.bytes_recv,
#             "packets_sent": network.packets_sent,
#             "packets_recv": network.packets_recv,
#         }

#         # Process metrics
#         process = psutil.Process()
#         process_metrics = {
#             "cpu_percent": process.cpu_percent(),
#             "memory_percent": process.memory_percent(),
#             "memory_info": {
#                 "rss": process.memory_info().rss,
#                 "vms": process.memory_info().vms,
#             },
#             "num_threads": process.num_threads(),
#             "open_files": len(process.open_files()),
#             "connections": len(process.connections()),
#         }

#         metrics = {
#             "timestamp": time.time(),
#             "cpu": {"percent": cpu_percent, "count": cpu_count},
#             "memory": memory_metrics,
#             "disk": disk_metrics,
#             "network": network_metrics,
#             "process": process_metrics,
#         }

#         logger.info("System metrics collected successfully")
#         return metrics

#     except Exception as e:
#         logger.error(f"System metrics collection failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Metrics collection failed: {str(e)}"
#         )
