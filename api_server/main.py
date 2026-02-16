# ┌───────────────────────────────────────────────────────────────┐
# │  Copyright (c) 2025 Ateet Vatan Bahmani                       │
# │  Project: MASX AI – Strategic Agentic AI System               │
# │  All rights reserved.                                         │
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
Main application entry point for MASX-HOTSPOTS (MASX) Agentic AI System.

This module provides the FastAPI application server with:
- Health check endpoints
- Workflow management
- Data retrieval and analytics
- Service monitoring
- Interactive API documentation

Usage:
    python -m src.main
    uvicorn src.main:app --host 0.0.0.0 --port 8000
"""

import os
import uvicorn
from app.api import create_app
from app.config.settings import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app" if settings.api_reload else app,
        host=settings.api_host or "0.0.0.0",
        port=port,
        reload=settings.api_reload or False,
        log_level=settings.log_level.lower() if settings.log_level else "info",
    )
