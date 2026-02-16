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
Base agent classes and interfaces for MASX-HOTSPOTS Agentic AI System.
Defines the foundational agent architecture including:
- BaseAgent: Abstract base class for all agents
- AgentResult: Standardized result structure for agent outputs
- Common functionality: logging, error handling, timing, state management

Usage:from app.agents.base import BaseAgent, AgentResult
    class MyAgent(BaseAgent):
        def execute(self, input_data: dict) -> AgentResult:
            # Agent implementation
            pass
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger, log_agent_action
from ..core.utils import measure_execution_time


class AgentResult(BaseModel):
    """
    Standardized result structure for agent outputs.
    Ensures consistent data format across all agents.
    """

    success: bool = Field(..., description="Whether the agent execution was successful")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Output data from the agent"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the execution"
    )
    execution_time: Optional[float] = Field(
        default=None, description="Execution time in seconds"
    )


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the MASX system.
    Provides common functionality including:
    - Standardized execution interface
    - Logging and error handling
    - State management integration
    - Performance monitoring
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize the base agent.
        Args:
            name: Unique name for this agent
            description: Human-readable description of the agent's purpose
        """
        self.name = name
        self.description = description
        self.logger = get_agent_logger(name)
        self._state: Optional[AgentState] = None

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main logic.
        Args: input_data: Input data for the agent
        Returns: AgentResult: Standardized result from the agent execution
        This method must be implemented by all concrete agent classes.
        """
        pass

    def run(
        self, input_data: Dict[str, Any], workflow_id: Optional[str] = None
    ) -> AgentResult:
        """
        Run the agent with full logging, error handling, and state management.
        Args: input_data: Input data for the agent
            workflow_id: Optional run ID for tracking
        Returns: AgentResult: Result from agent execution
        """
        # Initialize agent state
        self._state = AgentState(
            name=self.name,
            status="running",
            input=input_data,
            start_time=datetime.utcnow(),
        )

        # Log start of execution
        log_agent_action(
            self.logger,
            self.name,
            "start_execution",
            parameters=input_data,
            workflow_id=workflow_id,
        )

        try:
            # Execute agent logic with timing
            with measure_execution_time(f"{self.name}_execution"):
                result = self.execute(input_data)

            # Update state with success
            self._state.status = "success" if result.success else "failed"
            self._state.output = result.data
            self._state.error = result.error
            self._state.end_time = datetime.utcnow()

            # Log completion
            log_agent_action(
                self.logger,
                self.name,
                "complete_execution",
                result={
                    "success": result.success,
                    "execution_time": result.execution_time,
                },
                workflow_id=workflow_id,
            )

            return result

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error in {self.name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # Update state with failure
            self._state.status = "failed"
            self._state.error = error_msg
            self._state.end_time = datetime.utcnow()

            # Log error
            log_agent_action(
                self.logger,
                self.name,
                "execution_failed",
                error=error_msg,
                workflow_id=workflow_id,
            )

            # Return error result
            return AgentResult(
                success=False,
                error=error_msg,
                metadata={"exception_type": type(e).__name__},
            )

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for the agent.
        Args: input_data: Input data to validate
        Returns: bool: True if input is valid
        Override this method in subclasses to add specific validation logic.
        """
        return isinstance(input_data, dict)

    def preprocess_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess input data before execution.
        Args: input_data: Raw input data
        Returns: Dict[str, Any]: Preprocessed input data
        Override this method in subclasses to add preprocessing logic.
        """
        return input_data

    def postprocess_output(self, result: AgentResult) -> AgentResult:
        """
        Postprocess output data after execution.
        Args: result: Raw result from execution
        Returns: AgentResult: Postprocessed result
        Override this method in subclasses to add postprocessing logic.
        """
        return result

    @property
    def state(self) -> Optional[AgentState]:
        """Get the current state of the agent."""
        return self._state

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities and metadata.
        Returns: Dict[str, Any]: Agent capabilities information
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__,
            "abstract": False,
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        return self.__str__()
