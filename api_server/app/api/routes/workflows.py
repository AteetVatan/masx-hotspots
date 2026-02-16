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
Workflow management endpoints for MASX-HOTSPOTS Agentic AI System.

Provides endpoints for:
- Workflow execution
- Workflow status monitoring
- Workflow history
- Workflow configuration
"""
# import asyncio
# import threading
# from typing import Dict, Any, Optional, List
# from fastapi import APIRouter, HTTPException, BackgroundTasks
# from pydantic import BaseModel

# from ...config.logging_config import get_api_logger
# from ...workflows import MASXOrchestrator
# from ...core.state import MASXState

# router = APIRouter()
# logger = get_api_logger("WorkflowRoutes")


# class WorkflowRequest(BaseModel):
#     """Workflow execution request model."""

#     workflow_type: str = "daily"
#     input_data: Optional[Dict[str, Any]] = None


# class WorkflowResponse(BaseModel):
#     """Workflow execution response model."""

#     workflow_id: str
#     status: str
#     workflow_type: str
#     execution_time: float
#     result: Optional[Dict[str, Any]] = None
#     error: Optional[str] = None


# class WorkflowStatus(BaseModel):
#     """Workflow status model."""

#     workflow_id: str
#     status: str
#     current_step: str
#     completed_steps: List[str]
#     total_steps: int
#     progress: float
#     start_time: str
#     estimated_completion: Optional[str] = None


# @router.post("/execute", response_model=WorkflowResponse)
# async def execute_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
#     """
#     Execute a workflow.

#     Args:
#         request: Workflow execution request
#         background_tasks: FastAPI background tasks

#     Returns:
#         WorkflowResponse: Workflow execution response
#     """
#     logger.info(f"Workflow execution requested: {request.workflow_type}")

#     try:
#         orchestrator = MASXOrchestrator()

#         # Execute workflow
#         result = orchestrator.run_workflow(
#             workflow_type=request.workflow_type, input_data=request.input_data
#         )

#         workflow_id = result.workflow_id[0]
#         response = WorkflowResponse(
#             workflow_id=workflow_id,
#             status="completed" if result.workflow.completed else "failed",
#             workflow_type=request.workflow_type,
#             execution_time=result.workflow.execution_time or 0.0,
#             result=(
#                 {
#                     "hotspots_count": len(result.metadata.get("hotspots", [])),
#                     "articles_count": len(result.metadata.get("articles", [])),
#                     "domains": result.metadata.get("domains", []),
#                     "errors": [str(e) for e in result.errors],
#                 }
#                 if result.workflow.completed
#                 else None
#             ),
#             error="; ".join([str(e) for e in result.errors]) if result.errors else None,
#         )

#         logger.info(f"Workflow execution completed: {workflow_id}")
#         return response

#     except Exception as e:
#         logger.error(f"Workflow execution failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Workflow execution failed: {str(e)}"
#         )


# @router.post("/execute/daily")
# async def execute_daily_workflow(request: Optional[WorkflowRequest] = None):
#     """
#     Execute the daily workflow as a completely detached background thread.
#     """
#     try:

#         def _run_in_background(req_data: Optional[Dict]):
#             try:

#                 async def runner():
#                     orchestrator = MASXOrchestrator()
#                     orchestrator.run_daily_workflow(input_data=req_data)

#                 # ✅ Manually set event loop in thread
#                 loop = asyncio.new_event_loop()
#                 asyncio.set_event_loop(loop)
#                 loop.run_until_complete(runner())
#                 loop.close()
#             except Exception as e:
#                 logger.error(f"[MASX] Background workflow failed: {e}", exc_info=True)

#         input_data = request.input_data if request else None
#         threading.Thread(
#             target=_run_in_background, args=(input_data,), daemon=True
#         ).start()

#         return WorkflowResponse(
#             workflow_id="",
#             status="started",
#             workflow_type="daily",
#             execution_time=0.0,
#             result={
#                 "message": "Daily workflow started independently – check status endpoint for progress"
#             },
#         )

#     except Exception as e:
#         logger.error(f"Daily workflow execution failed: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=500, detail=f"Daily workflow execution failed: {str(e)}"
#         )


# @router.post("/execute/detection")
# async def execute_detection_workflow(request: Optional[WorkflowRequest] = None):
#     """
#     Execute the detection workflow.

#     Args:
#         request: Optional workflow request with input data

#     Returns:
#         WorkflowResponse: Workflow execution response
#     """
#     logger.info("Detection workflow execution requested")

#     try:
#         orchestrator = MASXOrchestrator()

#         input_data = request.input_data if request else None
#         result = orchestrator.run_detection_workflow(input_data=input_data)

#         workflow_id = result.workflow_id[0]
#         response = WorkflowResponse(
#             workflow_id=workflow_id,
#             status="completed" if result.workflow.completed else "failed",
#             workflow_type="detection",
#             execution_time=result.workflow.execution_time or 0.0,
#             result=(
#                 {
#                     "anomalies_detected": len(result.metadata.get("anomalies", [])),
#                     "confidence_score": result.metadata.get("confidence_score", 0.0),
#                     "errors": [str(e) for e in result.errors],
#                 }
#                 if result.workflow.completed
#                 else None
#             ),
#             error="; ".join([str(e) for e in result.errors]) if result.errors else None,
#         )

#         logger.info(f"Detection workflow execution completed: {workflow_id}")
#         return response

#     except Exception as e:
#         logger.error(f"Detection workflow execution failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Detection workflow execution failed: {str(e)}"
#         )


# @router.get("/status/{workflow_id}", response_model=WorkflowStatus)
# async def get_workflow_status(workflow_id: str):
#     """
#     Get workflow execution status.

#     Args:
#         workflow_id: Workflow run ID

#     Returns:
#         WorkflowStatus: Workflow status information
#     """
#     logger.info(f"Workflow status requested: {workflow_id}")

#     try:
#         # This would typically query a database or cache for workflow status
#         # get the workflow status from the orchestrator
#         orchestrator = MASXOrchestrator()
#         status = orchestrator.get_workflow_status(workflow_id)

#         # For now, return a mock status
#         status = WorkflowStatus(
#             workflow_id=workflow_id,
#             status="completed",
#             current_step="completed",
#             completed_steps=[
#                 "initialize",
#                 "classify_domain",
#                 "plan_queries",
#                 "fetch_data",
#                 "process_data",
#             ],
#             total_steps=5,
#             progress=100.0,
#             start_time=__import__("datetime").datetime.utcnow().isoformat(),
#             estimated_completion=__import__("datetime").datetime.utcnow().isoformat(),
#         )

#         logger.info(f"Workflow status retrieved: {workflow_id}")
#         return status

#     except Exception as e:
#         logger.error(f"Workflow status retrieval failed: {e}")
#         raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


# @router.get("/history")
# async def get_workflow_history(
#     limit: int = 10, offset: int = 0, workflow_type: Optional[str] = None
# ):
#     """
#     Get workflow execution history.

#     Args:
#         limit: Maximum number of workflows to return
#         offset: Number of workflows to skip
#         workflow_type: Filter by workflow type

#     Returns:
#         List of workflow execution records
#     """
#     logger.info("Workflow history requested")

#     try:
#         # This would typically query a database for workflow history
#         # For now, return mock data
#         history = [
#             {
#                 "workflow_id": f"run_{i}",
#                 "workflow_type": "daily",
#                 "status": "completed",
#                 "start_time": __import__("datetime").datetime.utcnow().isoformat(),
#                 "execution_time": 120.5,
#                 "hotspots_count": 5,
#                 "articles_count": 25,
#             }
#             for i in range(1, limit + 1)
#         ]

#         logger.info(f"Workflow history retrieved: {len(history)} records")
#         return {
#             "workflows": history,
#             "total": len(history),
#             "limit": limit,
#             "offset": offset,
#         }

#     except Exception as e:
#         logger.error(f"Workflow history retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Workflow history retrieval failed: {str(e)}"
#         )


# @router.get("/config")
# async def get_workflow_config():
#     """
#     Get workflow configuration.

#     Returns:
#         Workflow configuration information
#     """
#     logger.info("Workflow configuration requested")

#     try:
#         orchestrator = MASXOrchestrator()

#         config = {
#             "available_workflows": ["daily", "detection", "trigger"],
#             "agents": list(orchestrator.agents.keys()),
#             "default_workflow": "daily",
#             "max_concurrent_tasks": 10,
#             "timeout_seconds": 3600,
#             "retry_attempts": 3,
#         }

#         logger.info("Workflow configuration retrieved")
#         return config

#     except Exception as e:
#         logger.error(f"Workflow configuration retrieval failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Workflow configuration retrieval failed: {str(e)}"
#         )


# @router.delete("/cancel/{workflow_id}")
# async def cancel_workflow(workflow_id: str):
#     """
#     Cancel a running workflow.

#     Args:
#         workflow_id: Workflow run ID to cancel

#     Returns:
#         Cancellation status
#     """
#     logger.info(f"Workflow cancellation requested: {workflow_id}")

#     try:
#         # This would typically implement workflow cancellation logic
#         # For now, return success

#         logger.info(f"Workflow cancelled: {workflow_id}")
#         return {
#             "workflow_id": workflow_id,
#             "status": "cancelled",
#             "message": "Workflow cancellation requested",
#         }

#     except Exception as e:
#         logger.error(f"Workflow cancellation failed: {e}")
#         raise HTTPException(
#             status_code=500, detail=f"Workflow cancellation failed: {str(e)}"
#         )
