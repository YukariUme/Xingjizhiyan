"""轻量声明式工作流引擎。"""

from app.services.workflow.base import (
    WorkflowDefinition,
    WorkflowStep,
    evaluate_condition,
)
from app.services.workflow.definitions import WORKFLOWS, get_workflow_definition
from app.services.workflow.service import WorkflowService

__all__ = [
    "WorkflowDefinition",
    "WorkflowStep",
    "evaluate_condition",
    "WORKFLOWS",
    "get_workflow_definition",
    "WorkflowService",
]

