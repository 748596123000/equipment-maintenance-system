#!/bin/bash
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/backup_${TIMESTAMP}"

mkdir -p "${BACKUP_PATH}"

echo "开始备份..."
echo "备份时间: $(date)"

command -v sqlite3 >/dev/null 2>&1 || { echo "错误: sqlite3 未安装"; exit 1; }

if [ -f "data/app.db" ]; then
    sqlite3 data/app.db ".backup '${BACKUP_PATH}/app.db'"
    echo "✓ SQLite数据库备份完成"
fi

if [ -d "data/chroma_db" ]; then
    cp -r data/chroma_db "${BACKUP_PATH}/"
    echo "✓ ChromaDB向量数据库备份完成"
fi

if [ -d "data/uploads" ]; then
    cp -r data/uploads "${BACKUP_PATH}/"
    echo "✓ 上传文件备份完成"
fi

tar -czf "${BACKUP_PATH}.tar.gz" -C "${BACKUP_DIR}" "backup_${TIMESTAMP}"
rm -rf "${BACKUP_PATH}"

# 验证备份完整性
if tar -tzf "${BACKUP_PATH}.tar.gz" > /dev/null 2>&1; then
    echo "✓ 备份验证通过"
else
    echo "✗ 备份验证失败!"
    exit 1
fi

echo "备份完成: ${BACKUP_PATH}.tar.gz"

KEEP_COUNT=7
ls -t "${BACKUP_DIR}"/backup_*.tar.gz | tail -n +$((KEEP_COUNT + 1)) | xargs -r rm
echo "已清理，仅保留最近${KEEP_COUNT}个备份"
