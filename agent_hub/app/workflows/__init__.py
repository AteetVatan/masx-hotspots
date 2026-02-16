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
Workflow orchestration for MASX-HOTSPOTS Agentic AI System.
This package contains LangGraph workflow definitions and orchestration logic including:
- Main orchestrator for coordinating agent execution
- Workflow definitions for different scenarios
- Parallel execution handling and state management
- Conditional logic and error recovery

Usage:    from app.workflows import MASXOrchestrator, create_daily_workflow
"""

from .orchestrator import MASXOrchestrator
from .workflows import (
    create_daily_workflow,
    create_detection_workflow,
    create_trigger_workflow,
)

__all__ = [
    "MASXOrchestrator",
    "create_daily_workflow",
    "create_detection_workflow",
    "create_trigger_workflow",
]
