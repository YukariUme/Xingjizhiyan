/** 判题 verdict 的展示标签与徽章样式（CodeCrucible 语义）。 */

const VERDICT_LABELS: Record<string, string> = {
  accepted: "AC 通过",
  wrong_answer: "WA 答案错误",
  compile_error: "CE 编译错误",
  time_limit_exceeded: "TLE 运行超时",
  memory_limit_exceeded: "MLE 内存超限",
  runtime_error: "RE 运行错误",
  internal_error: "内部错误",
};

const VERDICT_CLASSES: Record<string, string> = {
  accepted: "green",
  compile_error: "orange",
  internal_error: "gray",
};

export function verdictLabel(verdict?: string | null): string {
  if (!verdict) return "未评测";
  return VERDICT_LABELS[verdict] ?? "未通过";
}

export function verdictClass(verdict?: string | null): string {
  if (!verdict) return "gray";
  return VERDICT_CLASSES[verdict] ?? "red";
}
