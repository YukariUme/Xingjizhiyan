"""工作流定义模型与安全条件求值。"""

import ast
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """单个工作流步骤。

    type: tool（调用工具）| branch（条件分支）| approval（人工审批节点）
    params 支持 {context_key} 占位符，执行时用上下文值替换。
    """

    id: str
    label: str
    type: str = "tool"
    tool: str = ""
    params: dict = field(default_factory=dict)
    next: str = ""
    condition: str = ""
    next_yes: str = ""
    next_no: str = ""
    approval_role: str = "teacher"


@dataclass
class WorkflowDefinition:
    """工作流定义：id + 名称 + 步骤列表。"""

    id: str
    name: str
    description: str
    steps: list[WorkflowStep]

    def step_map(self) -> dict[str, WorkflowStep]:
        return {step.id: step for step in self.steps}


def evaluate_condition(expression: str, context: dict) -> bool:
    """在受限命名空间中安全求值条件表达式（仅允许 context 与基础运算）。"""
    if not expression:
        return True
    tree = ast.parse(expression, mode="eval")
    allowed = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Name,
               ast.Load, ast.Constant, ast.Attribute, ast.Subscript, ast.List, ast.Tuple,
               ast.Dict, ast.Starred, ast.Call, ast.keyword, ast.And, ast.Or, ast.Not,
               ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
               ast.Slice, ast.IfExp, ast.Index)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"条件中包含不允许的语法：{type(node).__name__}")
    env: dict = {"context": context, "len": len, "str": str, "int": int, "float": float, "any": any, "all": all}
    return bool(eval(compile(tree, "<condition>", "eval"), {"__builtins__": {}}, env))

