#!/usr/bin/env bash
# 云部署备份：PG 逻辑备份 + 知识文件归档
# 建议 crontab：0 3 * * * /path/to/jbgs/deploy/backup.sh >> /var/log/jbgs-backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p backups

echo "[backup] $STAMP 开始备份..."

# 1) PostgreSQL 逻辑备份（-F c 自定义格式，可用 pg_restore 恢复）
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-jbgs}" -d "${POSTGRES_DB:-jbgs}" -F c -f /tmp/jbgs.dump
docker compose cp db:/tmp/jbgs.dump "backups/jbgs-${STAMP}.dump"

# 2) 知识文件与嵌入缓存
tar -czf "backups/data-${STAMP}.tar.gz" \
  -C backend/data knowledge_files embeddings 2>/dev/null || true

# 3) 清理：保留最近 14 份
ls -1t backups/jbgs-*.dump 2>/dev/null | tail -n +15 | xargs -r rm -f
ls -1t backups/data-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "[backup] 完成：backups/jbgs-${STAMP}.dump"
ls -lh backups | tail -4
