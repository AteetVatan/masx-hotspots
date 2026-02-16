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
MASX-HOTSPOTS
A modular, multi-agent system for geopolitical intelligence gathering.
Powered by LangGraph, CrewAI, and AutoGen for collaborative reasoning.

Author: MASX AI Team
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "MASX AI Team"
__email__ = "ab@masxai.com"

# Import core components for easy access
from .config.settings import get_settings
from .core.state import MASXState
from .workflows.orchestrator import MASXOrchestrator

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "get_settings",
    "MASXState",
    "MASXOrchestrator",
]
