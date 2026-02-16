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
State management models for MASX-HOTSPOTS Agentic AI System.

Defines the core state objects for orchestrating multi-agent workflows, tracking agent execution,
and maintaining workflow progress and results. All models are Pydantic-based for type safety.

Usage: from app.core.state import MASXState, AgentState, WorkflowState
These models are used throughout the orchestrator, agents, and logging/auditing subsystems.
"""

from typing import Any, Dict, List, Optional, Annotated
from datetime import datetime
import operator
from pydantic import BaseModel, Field
from .flashpoint import FlashpointDataset, FlashpointItem

# from app.core.flashpoint import FlashpointDataset, FlashpointItem


class AgentState(BaseModel):
    """
    State for an agent in the workflow.
    Tracks status, input/output, errors, and timing.
    """

    name: str = Field(..., description="Agent name")
    status: str = Field(
        "pending", description="Status: pending, running, success, failed"
    )
    input: Optional[Dict[str, Any]] = Field(
        default=None, description="Input data for the agent"
    )
    output: Optional[Dict[str, Any]] = Field(
        default=None, description="Output/result from the agent"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    start_time: Optional[datetime] = Field(
        default=None, description="Agent execution start time"
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Agent execution end time"
    )
    logs: List[Dict[str, Any]] = Field(
        default_factory=list, description="Structured logs for this agent"
    )


class WorkflowState(BaseModel):
    """
    Tracks workflow progress, steps, and results.
    """

    current_step: Optional[str] = Field(default=None, description="Current step name")
    steps: List[str] = Field(
        default_factory=list, description="Ordered list of workflow steps"
    )
    completed: bool = Field(
        default=False, description="Whether the workflow is complete"
    )
    failed: bool = Field(default=False, description="Whether the workflow failed")
    results: Optional[Dict[str, Any]] = Field(
        default=None, description="Final results of the workflow"
    )


class MASXState1(BaseModel):
    """
    Top-level state for a workflow run.
    Includes run metadata, agent states, workflow state, and errors.
    """

    workflow_id: Annotated[List[str], operator.add] = Field(default_factory=list)
    timestamp: Annotated[List[datetime], operator.add] = Field(default_factory=list)

    # put current_flashpoint and all_flashpoints in data
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data for the workflow",  # current_flashpoint and all_flashpoints
    )

    agents: Dict[str, AgentState] = Field(
        default_factory=dict, description="States for each agent by name"
    )
    workflow: WorkflowState = Field(..., description="Workflow progress and results")
    errors: List[str] = Field(
        default_factory=list, description="List of errors encountered during run"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional run metadata (config, env, etc.)"
    )


# Custom merge functions
def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


def merge_errors(a: list, b: list) -> list:
    return a + b


class MASXState(BaseModel):
    workflow_id: Annotated[List[str], operator.add] = Field(default_factory=list)
    timestamp: Annotated[List[datetime], operator.add] = Field(default_factory=list)
    agents: Annotated[Dict[str, AgentState], merge_dicts] = Field(default_factory=dict)
    workflow: Annotated[WorkflowState, lambda a, b: b]  # take latest if both update
    errors: Annotated[List[str], merge_errors] = Field(default_factory=list)
    metadata: Annotated[Dict[str, Any], merge_dicts] = Field(default_factory=dict)
    data: Annotated[Dict[str, Any], merge_dicts] = Field(default_factory=dict)
