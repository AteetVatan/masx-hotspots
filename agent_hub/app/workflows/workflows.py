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
Workflow factory functions for MASX-HOTSPOTS Agentic AI System.
Provides factory functions to create different types of workflows:
- Daily workflow for regular intelligence gathering
- Detection workflow for anomaly handling
- Trigger workflow for iterative refinement

Usage: from app.workflows.workflows import create_daily_workflow
    workflow = create_daily_workflow(config)
    result = workflow.run()
"""

from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

from ..core.state import MASXState, WorkflowState
from ..core.exceptions import WorkflowException, ConfigurationException
from ..config.settings import get_settings
from ..config.logging_config import get_workflow_logger


def create_daily_workflow(config: Optional[Dict[str, Any]] = None) -> StateGraph:
    """
    Create the main daily workflow for intelligence gathering.
    This workflow implements the core MASX pipeline:
    1. Domain classification
    2. Query planning
    3. Data fetching (parallel)
    4. Merge and deduplication
    5. Language processing
    6. Entity extraction
    7. Event analysis
    8. Fact checking
    9. Validation
    10. Memory storage

    Args:
        config: Optional workflow configuration

    Returns:
        StateGraph: Configured daily workflow
    """
    logger = get_workflow_logger("DailyWorkflow")
    settings = get_settings()

    # Validate configuration
    config = config or {}
    _validate_workflow_config(config, "daily")

    # Create workflow graph
    workflow = StateGraph(MASXState)

    # Add workflow steps
    workflow.add_node("initialize", _initialize_daily_workflow)
    workflow.add_node("classify_domain", _classify_domain_step)
    workflow.add_node("plan_queries", _plan_queries_step)
    workflow.add_node("fetch_data", _fetch_data_step)
    workflow.add_node("merge_data", _merge_data_step)
    workflow.add_node("process_language", _process_language_step)
    workflow.add_node("extract_entities", _extract_entities_step)
    workflow.add_node("analyze_events", _analyze_events_step)
    workflow.add_node("check_facts", _check_facts_step)
    workflow.add_node("validate_output", _validate_output_step)
    workflow.add_node("store_memory", _store_memory_step)
    workflow.add_node("finalize", _finalize_workflow)

    # Define workflow edges
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "classify_domain")
    workflow.add_edge("classify_domain", "plan_queries")
    workflow.add_edge("plan_queries", "fetch_data")
    workflow.add_edge("fetch_data", "merge_data")
    workflow.add_edge("merge_data", "process_language")
    workflow.add_edge("process_language", "extract_entities")
    workflow.add_edge("extract_entities", "analyze_events")
    workflow.add_edge("analyze_events", "check_facts")
    workflow.add_edge("check_facts", "validate_output")
    workflow.add_edge("validate_output", "store_memory")
    workflow.add_edge("store_memory", "finalize")
    workflow.add_edge("finalize", "end")

    logger.info("Daily workflow created successfully")
    return workflow


def create_detection_workflow(config: Optional[Dict[str, Any]] = None) -> StateGraph:
    """
    Create detection workflow for anomaly handling.

    This workflow handles:
    1. Anomaly detection
    2. Anomaly classification
    3. Resolution planning
    4. Result visualization

    Args:
        config: Optional workflow configuration

    Returns:
        StateGraph: Configured detection workflow
    """
    logger = get_workflow_logger("DetectionWorkflow")

    # Validate configuration
    config = config or {}
    _validate_workflow_config(config, "detection")

    # Create workflow graph
    workflow = StateGraph(MASXState)

    # Add workflow steps
    workflow.add_node("detect_anomaly", _detect_anomaly_step)
    workflow.add_node("classify_anomaly", _classify_anomaly_step)
    workflow.add_node("plan_resolution", _plan_resolution_step)
    workflow.add_node("execute_resolution", _execute_resolution_step)
    workflow.add_node("visualize_result", _visualize_result_step)

    # Define workflow edges
    workflow.set_entry_point("detect_anomaly")
    workflow.add_edge("detect_anomaly", "classify_anomaly")
    workflow.add_edge("classify_anomaly", "plan_resolution")
    workflow.add_edge("plan_resolution", "execute_resolution")
    workflow.add_edge("execute_resolution", "visualize_result")
    workflow.add_edge("visualize_result", "end")

    logger.info("Detection workflow created successfully")
    return workflow


def create_trigger_workflow(config: Optional[Dict[str, Any]] = None) -> StateGraph:
    """
    Create trigger workflow for iterative refinement.
    This workflow handles:
    1. Trigger detection
    2. Task delegation
    3. Result collection
    4. Plan updates
    5. Conditional re-execution

    Args: config: Optional workflow configuration
    Returns: StateGraph: Configured trigger workflow
    """
    logger = get_workflow_logger("TriggerWorkflow")

    # Validate configuration
    config = config or {}
    _validate_workflow_config(config, "trigger")

    # Create workflow graph
    workflow = StateGraph(MASXState)

    # Add workflow steps
    workflow.add_node("detect_trigger", _detect_trigger_step)
    workflow.add_node("delegate_tasks", _delegate_tasks_step)
    workflow.add_node("collect_results", _collect_results_step)
    workflow.add_node("update_plan", _update_plan_step)
    workflow.add_node("re_execute", _re_execute_step)

    # Define workflow edges with conditional logic
    workflow.set_entry_point("detect_trigger")
    workflow.add_edge("detect_trigger", "delegate_tasks")
    workflow.add_edge("delegate_tasks", "collect_results")
    workflow.add_edge("collect_results", "update_plan")
    workflow.add_conditional_edges(
        "update_plan",
        _should_continue_execution,
        {"continue": "re_execute", "complete": "end"},
    )
    workflow.add_edge("re_execute", "delegate_tasks")

    logger.info("Trigger workflow created successfully")
    return workflow


def _validate_workflow_config(config: Dict[str, Any], workflow_type: str):
    """
    Validate workflow configuration.

    Args:
        config: Configuration dictionary
        workflow_type: Type of workflow being validated

    Raises:
        ConfigurationException: If configuration is invalid
    """
    required_fields = {
        "daily": ["max_retries", "timeout"],
        "detection": ["sensitivity_threshold", "max_iterations"],
        "trigger": ["max_iterations", "convergence_threshold"],
    }

    if workflow_type not in required_fields:
        raise ConfigurationException(f"Unknown workflow type: {workflow_type}")

    missing_fields = []
    for field in required_fields[workflow_type]:
        if field not in config:
            missing_fields.append(field)

    if missing_fields:
        raise ConfigurationException(
            f"Missing required configuration fields for {workflow_type} workflow: {missing_fields}"
        )


# Daily workflow step implementations
def _initialize_daily_workflow(state: MASXState) -> MASXState:
    """Initialize daily workflow state."""
    logger = get_workflow_logger("DailyWorkflow")

    # Initialize workflow state
    state.workflow = WorkflowState(
        workflow_type="daily",
        current_step="initialize",
        steps=["initialize", "classify_domain", "plan_queries", "fetch_data"],
    )

    logger.info("Daily workflow initialized", run_id=state.workflow_id[0])
    return state


def _classify_domain_step(state: MASXState) -> MASXState:
    """Execute domain classification step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the DomainClassifier agent
        # For now, just update the state
        state.workflow.current_step = "classify_domain"
        state.metadata["domains"] = ["Geopolitical", "Economic"]

        logger.info("Domain classification completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Domain classification failed: {str(e)}")
        logger.error(f"Domain classification error: {e}", run_id=state.workflow_id[0])

    return state


def _plan_queries_step(state: MASXState) -> MASXState:
    """Execute query planning step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the QueryPlanner agent
        state.workflow.current_step = "plan_queries"
        state.metadata["queries"] = ["geopolitical news", "economic events"]

        logger.info("Query planning completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Query planning failed: {str(e)}")
        logger.error(f"Query planning error: {e}", run_id=state.workflow_id[0])

    return state


def _fetch_data_step(state: MASXState) -> MASXState:
    """Execute data fetching step with parallel execution."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would run NewsFetcher and EventFetcher in parallel
        state.workflow.current_step = "fetch_data"
        state.metadata["fetched_data"] = {
            "news": ["article1", "article2"],
            "events": ["event1", "event2"],
        }

        logger.info("Data fetching completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Data fetching failed: {str(e)}")
        logger.error(f"Data fetching error: {e}", run_id=state.workflow_id[0])

    return state


def _merge_data_step(state: MASXState) -> MASXState:
    """Execute data merge and deduplication step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the MergeDeduplicator agent
        state.workflow.current_step = "merge_data"
        state.metadata["merged_data"] = ["article1", "article2", "event1"]

        logger.info("Data merge completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Data merge failed: {str(e)}")
        logger.error(f"Data merge error: {e}", run_id=state.workflow_id[0])

    return state


def _process_language_step(state: MASXState) -> MASXState:
    """Execute language processing step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call LanguageResolver and Translator agents
        state.workflow.current_step = "process_language"
        state.metadata["processed_data"] = [
            "translated_article1",
            "translated_article2",
        ]

        logger.info("Language processing completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Language processing failed: {str(e)}")
        logger.error(f"Language processing error: {e}", run_id=state.workflow_id[0])

    return state


def _extract_entities_step(state: MASXState) -> MASXState:
    """Execute entity extraction step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the EntityExtractor agent
        state.workflow.current_step = "extract_entities"
        state.metadata["entities"] = {
            "people": ["John Doe", "Jane Smith"],
            "organizations": ["UN", "NATO"],
            "locations": ["Washington", "Moscow"],
        }

        logger.info("Entity extraction completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Entity extraction failed: {str(e)}")
        logger.error(f"Entity extraction error: {e}", run_id=state.workflow_id[0])

    return state


def _analyze_events_step(state: MASXState) -> MASXState:
    """Execute event analysis step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the EventAnalyzer agent
        state.workflow.current_step = "analyze_events"
        state.metadata["hotspots"] = [
            {"title": "Crisis in Region X", "articles": ["article1", "article2"]},
            {"title": "Economic Summit", "articles": ["article3"]},
        ]

        logger.info("Event analysis completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Event analysis failed: {str(e)}")
        logger.error(f"Event analysis error: {e}", run_id=state.workflow_id[0])

    return state


def _check_facts_step(state: MASXState) -> MASXState:
    """Execute fact checking step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the FactChecker agent
        state.workflow.current_step = "check_facts"
        state.metadata["verified_hotspots"] = state.metadata.get("hotspots", [])

        logger.info("Fact checking completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Fact checking failed: {str(e)}")
        logger.error(f"Fact checking error: {e}", run_id=state.workflow_id[0])

    return state


def _validate_output_step(state: MASXState) -> MASXState:
    """Execute output validation step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the Validator agent
        state.workflow.current_step = "validate_output"
        state.metadata["validation_passed"] = True

        logger.info("Output validation completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Output validation failed: {str(e)}")
        logger.error(f"Output validation error: {e}", run_id=state.workflow_id[0])

    return state


def _store_memory_step(state: MASXState) -> MASXState:
    """Execute memory storage step."""
    logger = get_workflow_logger("DailyWorkflow")

    try:
        # This would call the MemoryManager agent
        state.workflow.current_step = "store_memory"
        state.metadata["stored_to_memory"] = True

        logger.info("Memory storage completed", run_id=state.workflow_id[0])

    except Exception as e:
        state.errors.append(f"Memory storage failed: {str(e)}")
        logger.error(f"Memory storage error: {e}", run_id=state.workflow_id[0])

    return state


def _finalize_workflow(state: MASXState) -> MASXState:
    """Finalize daily workflow execution."""
    logger = get_workflow_logger("DailyWorkflow")

    state.workflow.current_step = "finalize"
    state.workflow.completed = True

    if state.errors:
        state.workflow.failed = True
        logger.error(
            f"Daily workflow completed with errors: {state.errors}",
            run_id=state.workflow_id[0],
        )
    else:
        logger.info(
            "Daily workflow completed successfully", run_id=state.workflow_id[0]
        )

    return state


# Detection workflow step implementations
def _detect_anomaly_step(state: MASXState) -> MASXState:
    """Detect anomalies in the workflow."""
    logger = get_workflow_logger("DetectionWorkflow")

    state.workflow.current_step = "detect_anomaly"
    state.metadata["anomalies_detected"] = []

    logger.info("Anomaly detection completed", run_id=state.workflow_id[0])
    return state


def _classify_anomaly_step(state: MASXState) -> MASXState:
    """Classify detected anomalies."""
    logger = get_workflow_logger("DetectionWorkflow")

    state.workflow.current_step = "classify_anomaly"
    state.metadata["anomaly_classifications"] = []

    logger.info("Anomaly classification completed", run_id=state.workflow_id[0])
    return state


def _plan_resolution_step(state: MASXState) -> MASXState:
    """Plan resolution for anomalies."""
    logger = get_workflow_logger("DetectionWorkflow")

    state.workflow.current_step = "plan_resolution"
    state.metadata["resolution_plan"] = {}

    logger.info("Resolution planning completed", run_id=state.workflow_id[0])
    return state


def _execute_resolution_step(state: MASXState) -> MASXState:
    """Execute anomaly resolution."""
    logger = get_workflow_logger("DetectionWorkflow")

    state.workflow.current_step = "execute_resolution"
    state.metadata["resolution_executed"] = True

    logger.info("Resolution execution completed", run_id=state.workflow_id[0])
    return state


def _visualize_result_step(state: MASXState) -> MASXState:
    """Visualize detection results."""
    logger = get_workflow_logger("DetectionWorkflow")

    state.workflow.current_step = "visualize_result"
    state.workflow.completed = True

    logger.info("Result visualization completed", run_id=state.workflow_id[0])
    return state


# Trigger workflow step implementations
def _detect_trigger_step(state: MASXState) -> MASXState:
    """Detect workflow triggers."""
    logger = get_workflow_logger("TriggerWorkflow")

    state.workflow.current_step = "detect_trigger"
    state.metadata["trigger_detected"] = True

    logger.info("Trigger detection completed", run_id=state.workflow_id[0])
    return state


def _delegate_tasks_step(state: MASXState) -> MASXState:
    """Delegate tasks to agents."""
    logger = get_workflow_logger("TriggerWorkflow")

    state.workflow.current_step = "delegate_tasks"
    state.metadata["tasks_delegated"] = True

    logger.info("Task delegation completed", run_id=state.workflow_id[0])
    return state


def _collect_results_step(state: MASXState) -> MASXState:
    """Collect results from agents."""
    logger = get_workflow_logger("TriggerWorkflow")

    state.workflow.current_step = "collect_results"
    state.metadata["results_collected"] = True

    logger.info("Result collection completed", run_id=state.workflow_id[0])
    return state


def _update_plan_step(state: MASXState) -> MASXState:
    """Update execution plan."""
    logger = get_workflow_logger("TriggerWorkflow")

    state.workflow.current_step = "update_plan"
    state.metadata["plan_updated"] = True

    logger.info("Plan update completed", run_id=state.workflow_id[0])
    return state


def _re_execute_step(state: MASXState) -> MASXState:
    """Re-execute workflow steps."""
    logger = get_workflow_logger("TriggerWorkflow")

    state.workflow.current_step = "re_execute"
    state.metadata["re_execution_count"] = (
        state.metadata.get("re_execution_count", 0) + 1
    )

    logger.info("Re-execution completed", run_id=state.workflow_id[0])
    return state


def _should_continue_execution(state: MASXState) -> str:
    """
    Determine if workflow should continue execution.

    Args:
        state: Current workflow state

    Returns:
        str: "continue" or "complete"
    """
    max_iterations = state.metadata.get("max_iterations", 3)
    current_iterations = state.metadata.get("re_execution_count", 0)

    if current_iterations < max_iterations:
        return "continue"
    else:
        return "complete"
