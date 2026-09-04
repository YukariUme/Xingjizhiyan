# Docker 沙箱判题

## 为什么用 Docker
本地裸跑学生代码等于把不可信代码放进业务进程的权限边界内（可读 `.env`、可联网、
可删文件）。Docker 一次性容器把每次提交放进隔离沙箱：

| 维度 | Docker 沙箱（当前默认） | 本地裸跑（开发用，已不默认） |
| --- | --- | --- |
| 网络 | `--network none` 断网，数据传不出去 | 有网 |
| 文件系统 | `--read-only`，根文件系统只读，只能写 /sandbox、/tmp | 可读写整个磁盘 |
| 内存 | `--memory` 硬限制，超限内核 OOM 杀 | psutil 统计（软限制） |
| CPU | `--cpus` 配额 + 墙钟 timeout | 墙钟 timeout |
| 进程数 | `--pids-limit` | 无限制 |
| 残留 | `--rm` 自动删除 | 临时目录手动清理 |

## 判题流程
```
学生提交 → workdir（backend/data/judge_work/<uuid>）
  ├─ solution.py / solution.c / solution.cpp / Main.java
  ├─ case_1.in / case_1.out ...（测试点）
  ├─ runner.sh（容器内 bash runner：编译 → 逐测试点运行 → results.txt）
  └─ docker run --rm --network none --read-only --memory --cpus --pids-limit
             -v workdir:/sandbox <语言镜像> bash /sandbox/runner.sh ...
→ 解析 results.txt → AC/WA/TLE/MLE/RE/CE
```

## 配置（`.env`，已默认启用）
```dotenv
JUDGE_PROVIDER=docker
JUDGE_DOCKER_IMAGE_PYTHON=python:3.11-slim
JUDGE_DOCKER_IMAGE_C=gcc:13
JUDGE_DOCKER_IMAGE_CPP=gcc:13
JUDGE_DOCKER_IMAGE_JAVA=eclipse-temurin:17-jdk
JUDGE_DOCKER_CPUS=1.0
JUDGE_DOCKER_PIDS_LIMIT=64
JUDGE_DOCKER_GLOBAL_TIMEOUT_S=300
```

## 本机启用步骤（Windows）
1. 安装 **Docker Desktop for Windows**（https://www.docker.com/products/docker-desktop/），
   打开后等待引擎启动（`docker info` 不报错）；
2. 拉取语言镜像（首次判题会自动拉取，也可手动）：
   ```powershell
   docker pull python:3.11-slim
   docker pull gcc:13
   docker pull eclipse-temurin:17-jdk
   ```
3. 无需改代码，`JUDGE_PROVIDER=docker` 已生效；提交编程题即走沙箱判题。

> Docker 未安装/未启动时，提交会返回明确提示（internal_error），不会悄悄降级为本地裸跑。

## 测试
`tests/test_judge_docker.py`：结果解析/判定纯逻辑始终运行；Docker 端到端（AC/WA）
在检测到 Docker 时自动运行，否则跳过。
