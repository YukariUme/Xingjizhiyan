# CodeCrucible 判题接入

> 更新：判题默认已切换为 **Docker 沙箱**（`JUDGE_PROVIDER=docker`，见
> `docs/DOCKER-JUDGE.md`）。本文档保留 CodeCrucible 本地/远程接入方案，
> 作为“复用成熟判题系统”的第二选择与远程集群对接文档。

## 目标
把 CodeCrucible（`D:\MyStudy\2026Summer\NUS\codecrucible`）的判题语义接入本平台，
替换原静态 Mock 判题：真实编译 → 逐测试点运行 → 双计时 → AC/WA/TLE/MLE/RE/CE。

## 接入方式（两种模式，`JUDGE_PROVIDER=codecrucible` 已启用）

### 1. 本地模式（默认，开发/演示）
`app/services/judge/codecrucible.py` 复用 CodeCrucible judge-worker 的判题核心：
- 状态机：Queued → Compiling → Running(k/n) → AC/WA/TLE/MLE/RE/CE；
- 双计时（防作弊）：CPU 时间按限时卡（POSIX `RLIMIT_CPU`），墙钟时间在限时上加宽限
  （`JUDGE_WALL_SLACK_SECONDS`），`sleep`/阻塞 IO 也会判 TLE；
- 语言：Python / C / C++ / Java（CodeCrucible 原版只支持 python/cpp，已扩展）;
- 测试点：支持 `{input, output}` 标准输入输出（忽略行尾空白），兼容旧式 `{check, value}` 静态检查；
- 内存：psutil 实测峰值 + POSIX rlimit（尽力而为）。

> 注意：本地模式未做 nsjail 级隔离，仅限开发/演示
> （`JUDGE_ALLOW_UNSAFE_LOCAL=true`）；生产请接远程集群。

### 2. 远程模式（CodeCrucible 集群）
配置后走 submission-service HTTP API：
```dotenv
CODECRUCIBLE_BASE_URL=http://<host>:<port>
CODECRUCIBLE_AUTH_TOKEN=<JWT>          # 或 CODECRUCIBLE_JWT_SECRET=<secret> 自动签发
CODECRUCIBLE_PROBLEM_ID=<uuid>
```
流程：`POST /api/submissions` → 轮询 `GET /api/submissions/{id}` → 终态 verdict 映射。
远程模式语言受 CodeCrucible 白名单限制（python/cpp）。

## 配置
```dotenv
JUDGE_PROVIDER=codecrucible
JUDGE_TIME_LIMIT_MS=1000
JUDGE_MEMORY_LIMIT_KB=262144
JUDGE_ALLOW_UNSAFE_LOCAL=true
```

## 前端
- 教师建题：编程题支持选择语言（Python/Java/C/C++），测试点支持
  “标准输入输出”与“静态检查”两种模式（`frontend/src/pages/teacher/Assignments.tsx`）。
- 结果展示：AC/WA/CE/TLE/MLE/RE 中文徽章（`frontend/src/pages/verdict.ts`）。

## 测试
`tests/test_judge_crucible.py`：Python AC/WA/CE/TLE、静态检查兼容、C/C++/Java 编译运行、不支持语言。
端到端：`python -m scripts.e2e_judge_pg`（PG + 真实工作流 + 本地判题，AC 与 WA 均验证）。
