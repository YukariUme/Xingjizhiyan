#!/usr/bin/env bash
# 预拉取 Docker 判题镜像，避免首次提交时等待（云服务器需能访问 Docker Hub）
set -euo pipefail

docker pull python:3.11-slim
docker pull gcc:13
docker pull eclipse-temurin:17-jdk

echo "判题镜像就绪。"
