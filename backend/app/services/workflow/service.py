"""工作流执行器：顺序执行步骤、条件分支、人工审批节点与全量留痕。"""

import re
import traceback
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import utcnow
from app.models import User, WorkflowRun, WorkflowStepRun
from app.services.workflow.base import WorkflowDefinition, evaluate_condition
from app.services.workflow.definitions import get_workflow_definition
from app.services.workflow.tools import TOOLS


def _resolve(value, context: dict):
    """把 {a.b} / {key} 占位符与简单表达式解析为上下文值。"""
    if isinstance(value, str):
        if value.startswith("{") and value.endswith("}") and value.count("{") == 1:
            return _resolve_expr(value[1:-1], context)
        # 处理内嵌占位符，例如 "课程：{course} {topic}"
        if "{" in value:
            def replace(match: "re.Match[str]") -> str:
                return str(_resolve_expr(match.group(1), context))

            return re.sub(r"\{([^{}]+)\}", replace, value)
    return value


def _resolve_expr(expr: str, context: dict):
    # 支持 {generate.parsed}、{judge.verdict} 等点路径
    if "." in expr and expr.split(".")[0] in context:
        parts = expr.split(".")
        cur = context.get(parts[0], {})
        try:
            for part in parts[1:]:
                if isinstance(cur, dict):
                    cur = cur.get(part, {})
                elif isinstance(cur, list) and part.isdigit():
                    cur = cur[int(part)]
                else:
                    cur = getattr(cur, part, "")
            return cur
        except (KeyError, IndexError, TypeError):
            return ""
    if expr in context:
        return context.get(expr)
    try:
        return evaluate_condition(expr, context)
    except Exception:
        return ""


def _render_params(params: dict, context: dict) -> dict:
    rendered = {}
    for key, value in params.items():
        if isinstance(value, dict):
            rendered[key] = _render_params(value, context)
        elif isinstance(value, list):
            rendered[key] = [_render_params(item, context) if isinstance(item, dict) else _resolve(item, context) for item in value]
        elif isinstance(value, str):
            rendered[key] = _resolve(value, context)
        else:
            rendered[key] = value
    return rendered


def _eval_branch(condition: str, context: dict) -> bool:
    """分支条件求值：先把 {a.b} / {key} 占位符替换为字面值再安全求值。"""
    import re

    def replace(match: "re.Match[str]") -> str:
        return repr(_resolve_expr(match.group(1), context))

    resolved = re.sub(r"\{([^{}]+)\}", replace, condition)
    return evaluate_condition(resolved, context)


class WorkflowService:
    """执行并记录工作流运行。MVP 为进程内同步执行，保证演示确定性。"""

    @staticmethod
    def list_definitions() -> list[dict]:
        from app.services.workflow.definitions import WORKFLOWS

        return [
            {
                "id": definition.id,
                "name": definition.name,
                "description": definition.description,
                "steps": [
                    {
                        "id": step.id,
                        "label": step.label,
                        "type": step.type,
                        "tool": step.tool,
                    }
                    for step in definition.steps
                ],
            }
            for definition in WORKFLOWS.values()
        ]

    @staticmethod
    def run(db: Session, definition_id: str, payload: dict, user: User) -> WorkflowRun:
        definition = get_workflow_definition(definition_id)
        if not definition:
            raise ValueError(f"未定义工作流：{definition_id}")
        run = WorkflowRun(
            definition_id=definition.id,
            name=definition.name,
            status="running",
            owner_id=user.id,
            submission_id=(
                int(payload["submission_id"])
                if definition_id == "assignment_loop" and payload.get("submission_id") is not None
                else None
            ),
            input_json=payload,
            output_json={},
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            context = {"__user__": user}
            context.update(payload)
            WorkflowService._execute_steps(db, run, definition, context)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            run.status = "failed"
            run.error = f"{exc}\n{traceback.format_exc(limit=3)}"
            run.finished_at = utcnow()
            db.add(run)
            db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def _execute_steps(
        db: Session,
        run: WorkflowRun,
        definition: WorkflowDefinition,
        context: dict,
        start_step_id: str | None = None,
    ) -> None:
        step_map = definition.step_map()
        step_id = start_step_id or definition.steps[0].id
        visited: set[str] = set()
        while step_id and step_id != "done" and step_id not in visited:
            visited.add(step_id)
            step = step_map.get(step_id)
            if not step:
                break
            step_run = WorkflowStepRun(
                run_id=run.id,
                step_id=step.id,
                label=step.label,
                status="running",
                input_json={},
                output_json={},
            )
            db.add(step_run)
            db.commit()
            db.refresh(step_run)

            if step.type == "branch":
                branch = _eval_branch(step.condition, context)
                step_run.status = "success"
                step_run.output_json = {"branch": "yes" if branch else "no", "condition": step.condition}
                step_run.finished_at = utcnow()
                db.add(step_run)
                db.commit()
                step_id = step.next_yes if branch else step.next_no
                continue

            if step.type == "approval":
                step_run.status = "awaiting_approval"
                step_run.input_json = {"approval_role": step.approval_role}
                db.add(step_run)
                run.status = "awaiting_approval"
                db.add(run)
                db.commit()
                return

            # tool 步骤
            params = _render_params(step.params, context)
            tool = TOOLS.get(step.tool)
            if not tool:
                raise ValueError(f"未注册工具：{step.tool}")
            step_run.input_json = params
            db.add(step_run)
            db.commit()
            try:
                output = tool(db, context, params) or {}
                step_run.status = "success"
                step_run.output_json = output
                step_run.finished_at = utcnow()
                db.add(step_run)
                db.commit()
                context[step.id] = output
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                step_run.status = "failed"
                step_run.error = str(exc)
                step_run.finished_at = utcnow()
                db.add(step_run)
                db.commit()
                raise
            step_id = step.next

        run.status = "success"
        run.output_json = {
            key: value
            for key, value in context.items()
            if not key.startswith("__") and key not in {"source_code", "test_cases", "history"}
        }
        run.finished_at = utcnow()
        db.add(run)
        db.commit()

    @staticmethod
    def approve(db: Session, run_id: int, approver: User, data: dict) -> WorkflowRun:
        """批准人工审批节点并继续执行剩余步骤。"""
        run = db.get(WorkflowRun, run_id)
        if not run:
            raise ValueError("工作流运行不存在")
        definition = get_workflow_definition(run.definition_id)
        if not definition:
            raise ValueError("工作流定义不存在")
        pending = next((s for s in run.steps if s.status == "awaiting_approval"), None)
        if not pending:
            raise ValueError("该工作流没有待审批节点")
        if approver.role != "teacher":
            raise PermissionError("仅教师可以确认成绩")
        pending.status = "success"
        pending.output_json = {"approved_by": approver.id, "decision": data}
        pending.finished_at = utcnow()
        db.add(pending)
        db.commit()

        context = {"__user__": approver}
        context.update(run.input_json)
        # 恢复已完成步骤的输出作为上下文
        for step_run in run.steps:
            if step_run.status == "success" and step_run.output_json:
                context[step_run.step_id] = step_run.output_json
        run.status = "running"
        db.add(run)
        db.commit()
        definition_step = definition.step_map().get(pending.step_id)
        next_step_id = definition_step.next if definition_step else "done"
        WorkflowService._execute_steps(db, run, definition, context, start_step_id=next_step_id)
        db.refresh(run)
        return run

    @staticmethod
    def list_runs(db: Session, definition_id: str | None = None, limit: int = 30) -> list[WorkflowRun]:
        from sqlalchemy import select

        query = select(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(limit)
        if definition_id:
            query = select(WorkflowRun).where(
                WorkflowRun.definition_id == definition_id
            ).order_by(WorkflowRun.created_at.desc()).limit(limit)
        return list(db.scalars(query))

    @staticmethod
    def get_run(db: Session, run_id: int) -> WorkflowRun | None:
        return db.get(WorkflowRun, run_id)

    @staticmethod
    def find_run_for_submission(db: Session, submission_id: int) -> WorkflowRun | None:
        from sqlalchemy import select

        return db.scalar(
            select(WorkflowRun)
            .where(
                WorkflowRun.definition_id == "assignment_loop",
                WorkflowRun.submission_id == submission_id,
            )
            .order_by(WorkflowRun.created_at.desc())
        )
