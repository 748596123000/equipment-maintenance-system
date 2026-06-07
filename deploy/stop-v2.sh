#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 升级版停止脚本
# ============================================================

set -e

PROJECT_DIR="/home/vmuser/knowledge-system"
PID_DIR="$PROJECT_DIR/data/logs"

# 颜色
if [ -t 1 ]; then
    C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[0;33m'
    C_BLUE='\033[0;34m'; C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_RESET='\033[0m'
else
    C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

log_info()  { echo -e "${C_BLUE}[INFO]${C_RESET}  $*"; }
log_ok()    { echo -e "${C_GREEN}[ OK ]${C_RESET}  $*"; }
log_warn()  { echo -e "${C_YELLOW}[WARN]${C_RESET}  $*"; }
log_error() { echo -e "${C_RED}[FAIL]${C_RESET}  $*"; }

stop_pid() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ ! -f "$pid_file" ]; then
        log_warn "未找到 PID 文件: $pid_file"
        return 0
    fi

    local pid=$(cat "$pid_file")
    if ! kill -0 "$pid" 2>/dev/null; then
        log_warn "进程 $pid 已退出，清理 PID 文件"
        rm -f "$pid_file"
        return 0
    fi

    log_info "停止 $name (PID: $pid)..."
    kill -TERM "$pid" 2>/dev/null || true

    local waited=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
        if [ $waited -ge 10 ]; then
            log_warn "进程未响应 SIGTERM，发送 SIGKILL"
            kill -9 "$pid" 2>/dev/null || true
            break
        fi
    done

    rm -f "$pid_file"
    log_ok "$name 已停止"
}

main() {
    cd "$PROJECT_DIR"

    log_info "停止后端..."
    stop_pid "api"

    log_info "停止 Nginx（如果运行中）..."
    if command -v nginx &> /dev/null && pgrep -x nginx > /dev/null; then
        sudo nginx -s stop 2>/dev/null || log_warn "Nginx 停止失败（可能已停止）"
        log_ok "Nginx 已停止"
    else
        log_info "Nginx 未运行"
    fi

    echo ""
    log_ok "所有服务已停止"
}

main "$@"
