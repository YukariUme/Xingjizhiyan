#!/usr/bin/env bash
# 阿里云轻量服务器（Ubuntu 22.04）初始化脚本：
# 1) 内存不足时创建 swap；2) 安装 Docker + Compose（阿里云镜像加速）；
# 3) 配置 Docker Hub 镜像加速（可选）；4) 安装常用工具。
# 用法：以 root 执行  bash deploy/setup-server.sh
set -euo pipefail

echo "==> [1/5] 更新系统包索引"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y

echo "==> [2/5] 内存不足时创建 swap（<2G 加 4G swap）"
MEM_MB=$(free -m | awk '/^Mem:/{print $2}')
if [ "$MEM_MB" -lt 2048 ] && [ ! -f /swapfile ]; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "已创建 4G swap（当前内存 ${MEM_MB}MB）"
else
  echo "内存充足或 swap 已存在，跳过"
fi

echo "==> [3/5] 安装 Docker（阿里云镜像源）"
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://mirrors.aliyun.com/docker-ce/linux/ubuntu $CODENAME stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "==> [4/5] 配置 Docker Hub 镜像加速（可选，国内拉镜像更快）"
if [ ! -f /etc/docker/daemon.json ]; then
  cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
EOF
  systemctl restart docker
  echo "已写入 /etc/docker/daemon.json（可用阿里云个人加速器地址替换）"
fi

echo "==> [5/5] 安装常用工具并验证"
apt-get install -y nano curl git htop
docker --version
docker compose version

echo ""
echo "初始化完成！下一步："
echo "  1. 把项目代码上传到服务器（scp / git clone）"
echo "  2. cp .env.cloud.example .env 并填写配置"
echo "  3. bash deploy/pull-images.sh && docker compose up -d --build"
