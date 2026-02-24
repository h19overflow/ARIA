"""Build Cycle Error Classifier — classifies execution errors for routing."""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, ClassifiedError
from src.agentic_system.build_cycle.schemas.execution import ClassifiedErrorOutput
from src.agentic_system.build_cycle.prompts.error_classifier import (
    ERROR_CLASSIFIER_SYSTEM_PROMPT,
)


_agent = BaseAgent[ClassifiedErrorOutput](
    prompt=ERROR_CLASSIFIER_SYSTEM_PROMPT,
    schema=ClassifiedErrorOutput,
    name="ErrorClassifier",
)


async def error_classifier_node(state: ARIAState) -> dict:
    """Classify execution error into routing category."""
    exec_result = state["execution_result"]
    error_data = exec_result.get("error") or {}

    prompt = f"Execution error:\n{json.dumps(error_data, indent=2)}"
    messages = [HumanMessage(content=prompt)]

    result: ClassifiedErrorOutput = await _agent.invoke(messages)

    classified: ClassifiedError = {
        "type": result.error_type,
        "node_name": result.node_name,
        "message": result.message,
        "description": result.description,
        "line_number": result.line_number,
        "stack": None,
    }

    return {
        "classified_error": classified,
        "messages": [HumanMessage(
            content=f"[Classifier] Error type: {result.error_type} in node '{result.node_name}'"
        )],
    }
