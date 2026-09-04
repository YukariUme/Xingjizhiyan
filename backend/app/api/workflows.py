"""工作流路由：定义列表、运行、运行记录、审批。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.database import get_db
from app.models import User
from app.services.workflow.service import WorkflowService

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _step_out(step) -> dict:
    return {
        "id": step.id,
        "step_id": step.step_id,
        "label": step.label,
        "status": step.status,
        "input": step.input_json,
        "output": step.output_json,
        "error": step.error,
        "started_at": step.started_at.isoformat(),
        "finished_at": step.finished_at.isoformat() if step.finished_at else None,
    }


def _run_out(run) -> dict:
    return {
        "id": run.id,
        "definition_id": run.definition_id,
        "name": run.name,
        "status": run.status,
        "owner_id": run.owner_id,
        "input": run.input_json,
        "output": run.output_json,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "steps": [_step_out(s) for s in run.steps],
    }


@router.get("")
def list_workflows(user: User = Depends(get_current_user)) -> list[dict]:
    return WorkflowService.list_definitions()


@router.post("/{definition_id}/run")
def run_workflow(
    definition_id: str,
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """运行一个工作流，返回执行记录（含每步状态与输出）。"""
    try:
        run = WorkflowService.run(db, definition_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if run.status == "failed":
        raise HTTPException(status_code=500, detail=run.error)
    return _run_out(run)


@router.get("/runs")
def list_runs(
    definition_id: str | None = None,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    runs = WorkflowService.list_runs(db, definition_id=definition_id, limit=limit)
    return [_run_out(run) for run in runs]


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    run = WorkflowService.get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="运行记录不存在")
    return _run_out(run)


@router.post("/runs/{run_id}/approve")
def approve_run(
    run_id: int,
    data: dict,
    user: User = Depends(require_roles("teacher")),
    db: Session = Depends(get_db),
) -> dict:
    """通过人工审批节点（仅教师），继续执行剩余步骤。"""
    try:
        run = WorkflowService.approve(db, run_id, user, data.get("decision") or data)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run.status == "failed":
        raise HTTPException(status_code=500, detail=run.error)
    return _run_out(run)

