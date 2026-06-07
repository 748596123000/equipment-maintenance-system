#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 升级版启动脚本
# 版本: v2.0 (2026-06-04)
#
# 功能:
#   - 依赖检测（PyMuPDF / ChromaDB / numpy / sqlite-fts5）
#   - 自动从 HTTP 拉取 update-v*.tar.gz
#   - 自动备份旧代码（app.backup.<时间戳>）
#   - 自动部署 + 错误回滚
#   - 智能 Nginx 部署（解决目录不一致问题）
#   - 优雅 stop（用 PID 文件，不用 pkill）
#   - 健康检查（5 秒内 /health 通）
#   - 颜色高亮 + 中文友好提示
#
# 使用:
#   ./start.sh                    # 标准启动（自动打开浏览器）
#   ./start.sh --update           # 启动前自动拉取并部署最新 update-v*.tar.gz
#   ./start.sh --http-url URL     # 指定 HTTP server 拉取 update
#   ./start.sh --skip-nginx       # 跳过 Nginx 重启
#   ./start.sh --no-color         # 禁用颜色
#   ./start.sh --no-browser       # 不自动打开浏览器
#   ./start.sh --rollback         # 回滚到上一个备份
# ============================================================

set -e

# ========== 配置区 ==========
PROJECT_DIR="/home/vmuser/knowledge-system"
VENV_DIR="$PROJECT_DIR/venv"
BACKEND_PORT=8000
NGINX_HTML_DIR="/usr/share/nginx/html"
PROJECT_DIST_DIR="$PROJECT_DIR/frontend/dist"
PID_DIR="$PROJECT_DIR/data/logs"
BACKUP_BASE_DIR="$PROJECT_DIR/.backups"

# HTTP server 拉取 update 包
HTTP_UPDATE_URL="http://10.221.100.100:8765"
UPDATE_PATTERN="update-v*.tar.gz"

# 健康检查
HEALTH_CHECK_URL="http://localhost:$BACKEND_PORT/health"
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=1

# 颜色（可通过 --no-color 禁用）
USE_COLOR=1
if [ -t 1 ]; then
    USE_COLOR=1
else
    USE_COLOR=0
fi

if [ "$USE_COLOR" = "1" ]; then
    C_RED='\033[0;31m'
    C_GREEN='\033[0;32m'
    C_YELLOW='\033[0;33m'
    C_BLUE='\033[0;34m'
    C_CYAN='\033[0;36m'
    C_BOLD='\033[1m'
    C_RESET='\033[0m'
else
    C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

# ========== 工具函数 ==========
log_info()    { echo -e "${C_BLUE}[INFO]${C_RESET}  $*"; }
log_ok()      { echo -e "${C_GREEN}[ OK ]${C_RESET}  $*"; }
log_warn()    { echo -e "${C_YELLOW}[WARN]${C_RESET}  $*"; }
log_error()   { echo -e "${C_RED}[FAIL]${C_RESET}  $*" >&2; }
log_section() { echo -e "\n${C_BOLD}${C_CYAN}== $* ==${C_RESET}"; }

die() { log_error "$*"; exit 1; }

# 时间戳
ts() { date +"%Y%m%d_%H%M%S"; }

# 确保目录存在
ensure_dir() {
    [ -d "$1" ] || mkdir -p "$1" || die "无法创建目录: $1"
}

# ========== 依赖检测 ==========
check_dependencies() {
    log_section "1/7  依赖检测"

    local has_error=0

    # 1. Python venv
    if [ -d "$VENV_DIR" ]; then
        log_ok "Python venv: $VENV_DIR"
    else
        log_error "Python venv 不存在: $VENV_DIR"
        has_error=1
    fi

    # 2. PDF 处理依赖
    if "$VENV_DIR/bin/python" -c "import pdfplumber" 2>/dev/null; then
        log_ok "PDF 解析: pdfplumber ✓"
    else
        log_error "PDF 解析: pdfplumber 缺失（pip install pdfplumber --no-index --find-links ./pip_packages）"
        has_error=1
    fi

    if "$VENV_DIR/bin/python" -c "from pdfminer.high_level import extract_text" 2>/dev/null; then
        log_ok "PDF 解析: pdfminer.six ✓"
    else
        log_warn "PDF 解析: pdfminer.six 缺失（部分功能受限）"
    fi

    if "$VENV_DIR/bin/python" -c "import fitz" 2>/dev/null; then
        log_ok "PDF 渲染: PyMuPDF ✓"
    else
        log_warn "PDF 渲染: PyMuPDF 未安装（本项目已用 pdfplumber 整页渲染绕过，不影响功能）"
    fi

    # 3. 向量检索（项目已不依赖 ChromaDB，但提醒一下）
    if "$VENV_DIR/bin/python" -c "import chromadb" 2>/dev/null; then
        log_ok "向量检索: ChromaDB ✓"
    else
        log_ok "向量检索: SQLite FTS5 + numpy（项目内置，已替代 ChromaDB）"
    fi

    # 4. SQLite FTS5
    if "$VENV_DIR/bin/python" -c "
import sqlite3
conn = sqlite3.connect(':memory:')
conn.execute('CREATE VIRTUAL TABLE t USING fts5(c)')
conn.close()
" 2>/dev/null; then
        log_ok "SQLite FTS5: 可用 ✓"
    else
        log_error "SQLite FTS5: 不可用（系统 sqlite3 需编译时启用 FTS5）"
        has_error=1
    fi

    # 5. 向量化服务（dashscope）
    if "$VENV_DIR/bin/python" -c "import dashscope" 2>/dev/null; then
        log_ok "Embedding SDK: dashscope ✓"
    else
        log_warn "Embedding SDK: dashscope 缺失（Embedding 服务不可用）"
    fi

    # 6. 视觉模型
    if "$VENV_DIR/bin/python" -c "from app.services.vision_service import get_vision_service" 2>/dev/null; then
        log_ok "视觉服务: 可用 ✓"
    else
        log_warn "视觉服务: 不可用（AI 图片分析功能受限）"
    fi

    # 7. Nginx
    if command -v nginx &> /dev/null; then
        log_ok "Nginx: $(nginx -v 2>&1 | head -1)"
    else
        log_warn "Nginx: 未安装（前端无法通过 80 端口访问）"
    fi

    if [ $has_error -eq 1 ]; then
        die "关键依赖缺失，请先解决"
    fi
}

# ========== 备份旧代码 ==========
backup_current() {
    log_section "2/7  备份当前代码"
    ensure_dir "$BACKUP_BASE_DIR"

    local backup_name="app.backup.$(ts)"
    local backup_path="$BACKUP_BASE_DIR/$backup_name"

    if [ -d "$PROJECT_DIR/app" ]; then
        cp -r "$PROJECT_DIR/app" "$backup_path"
        log_ok "已备份 app → $backup_path"

        # 写入 latest 软链接（方便回滚）
        ln -sfn "$backup_path" "$BACKUP_BASE_DIR/latest"
    else
        log_warn "app 目录不存在，跳过备份"
    fi
}

# ========== 拉取并部署 update ==========
deploy_update() {
    log_section "3/7  拉取并部署 update"

    # 1. 下载最新的 update-v*.tar.gz
    log_info "从 $HTTP_UPDATE_URL 拉取 $UPDATE_PATTERN"

    local tmp_dir=$(mktemp -d)
    local downloaded_files=()

    # 用 curl 试匹配所有 update-v*.tar.gz 文件
    if command -v wget &> /dev/null; then
        wget -q -P "$tmp_dir" "$HTTP_UPDATE_URL/$UPDATE_PATTERN" 2>/dev/null || true
    elif command -v curl &> /dev/null; then
        curl -s -o "$tmp_dir/latest.html" "$HTTP_UPDATE_URL/" 2>/dev/null || true
        # 从 HTML 解析文件名（不依赖 lynx/w3m，简单粗暴）
        grep -oE 'update-v[0-9]+\.tar\.gz' "$tmp_dir/latest.html" 2>/dev/null | sort -u | while read -r f; do
            curl -s -o "$tmp_dir/$f" "$HTTP_UPDATE_URL/$f" 2>/dev/null && echo "$tmp_dir/$f" >> "$tmp_dir/.list"
        done
    else
        log_warn "未找到 wget 或 curl，跳过自动拉取"
        rm -rf "$tmp_dir"
        return 0
    fi

    # 找到最新的 update 包
    local latest_pkg=""
    for pkg in $(ls "$tmp_dir"/update-v*.tar.gz 2>/dev/null | sort -V); do
        latest_pkg="$pkg"
    done

    if [ -z "$latest_pkg" ] || [ ! -f "$latest_pkg" ]; then
        log_warn "未找到 update-v*.tar.gz，跳过部署"
        rm -rf "$tmp_dir"
        return 0
    fi

    local pkg_name=$(basename "$latest_pkg")
    log_ok "下载完成: $pkg_name"

    # 2. 解压到临时目录
    local extract_dir="$tmp_dir/extract"
    ensure_dir "$extract_dir"
    tar -xzf "$latest_pkg" -C "$extract_dir"

    # 3. 找出包内的根目录（通常是 update-vN/）
    local src_root=$(ls -d "$extract_dir"/*/ 2>/dev/null | head -1)
    if [ -z "$src_root" ]; then
        log_warn "包内无目录结构，跳过部署"
        rm -rf "$tmp_dir"
        return 0
    fi

    # 4. 复制文件到项目（覆盖前已备份）
    log_info "部署文件到 $PROJECT_DIR/"

    # 用 rsync 如果有，否则 cp -ru
    if command -v rsync &> /dev/null; then
        rsync -a --update "$src_root"*/ "$PROJECT_DIR/"
        log_ok "rsync 部署完成"
    else
        # 遍历 src_root 下的所有文件
        find "$src_root" -type f | while read -r src_file; do
            local rel_path="${src_file#$src_root}"
            local dst_path="$PROJECT_DIR/$rel_path"
            ensure_dir "$(dirname "$dst_path")"
            cp -f "$src_file" "$dst_path"
            log_info "  + $rel_path"
        done
        log_ok "cp 部署完成"
    fi

    # 5. 清理 .pyc 缓存
    find "$PROJECT_DIR/app" -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_DIR/app" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

    rm -rf "$tmp_dir"
}

# ========== 部署前端到 Nginx ==========
deploy_frontend() {
    log_section "4/7  部署前端到 Nginx"

    if ! command -v nginx &> /dev/null; then
        log_warn "Nginx 未安装，跳过前端部署"
        return 0
    fi

    if [ ! -d "$PROJECT_DIST_DIR" ]; then
        log_warn "前端 dist 不存在: $PROJECT_DIST_DIR"
        return 0
    fi

    # 检测当前 Nginx 服务目录
    if [ -L "$NGINX_HTML_DIR" ]; then
        log_warn "Nginx html 是软链接，删除并改为普通目录（避免权限问题）"
        sudo rm -f "$NGINX_HTML_DIR"
    fi

    if [ ! -d "$NGINX_HTML_DIR" ]; then
        log_info "创建 Nginx html 目录"
        sudo mkdir -p "$NGINX_HTML_DIR"
    fi

    # 复制 dist 内容（用 /. 包含隐藏文件）
    log_info "复制 dist → $NGINX_HTML_DIR"
    sudo cp -r "$PROJECT_DIST_DIR/." "$NGINX_HTML_DIR/"

    # 设置权限
    sudo chown -R nginx:nginx "$NGINX_HTML_DIR" 2>/dev/null || true
    sudo find "$NGINX_HTML_DIR" -type f -exec chmod 644 {} \; 2>/dev/null || true
    sudo find "$NGINX_HTML_DIR" -type d -exec chmod 755 {} \; 2>/dev/null || true

    log_ok "前端部署完成"
}

# ========== 停止旧进程 ==========
stop_backend() {
    log_section "5/7  停止旧后端进程"
    ensure_dir "$PID_DIR"

    if [ -f "$PID_DIR/api.pid" ]; then
        local old_pid=$(cat "$PID_DIR/api.pid")
        if kill -0 "$old_pid" 2>/dev/null; then
            log_info "停止后端 PID: $old_pid"
            kill -TERM "$old_pid" 2>/dev/null || true
            sleep 2
            if kill -0 "$old_pid" 2>/dev/null; then
                log_warn "进程未响应 SIGTERM，发送 SIGKILL"
                kill -9 "$old_pid" 2>/dev/null || true
            fi
        else
            log_warn "PID 文件存在但进程已退出"
        fi
        rm -f "$PID_DIR/api.pid"
    else
        log_warn "未找到 PID 文件，尝试 pkill（可能误杀其他同名进程）"
        pkill -f "uvicorn app.main" 2>/dev/null || true
        sleep 2
    fi

    # 等待端口释放
    local waited=0
    while [ $waited -lt 10 ]; do
        if ! ss -tln 2>/dev/null | grep -q ":$BACKEND_PORT "; then
            break
        fi
        sleep 1
        waited=$((waited + 1))
    done
    log_ok "旧后端已停止"
}

stop_nginx() {
    if ! command -v nginx &> /dev/null; then
        return 0
    fi

    # 优雅 reload（如果有 nginx 在跑）
    if [ -f /var/run/nginx.pid ] || pgrep -x nginx > /dev/null; then
        log_info "Nginx 配置重载"
        sudo nginx -s reload 2>&1 | head -5 || true
    fi
}

# ========== 启动新后端 ==========
start_backend() {
    log_section "6/7  启动新后端"
    ensure_dir "$PID_DIR"
    ensure_dir "$PROJECT_DIR/data/logs"

    cd "$PROJECT_DIR"

    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    log_info "启动 uvicorn (端口 $BACKEND_PORT)..."

    nohup venv/bin/uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$BACKEND_PORT" \
        > "$PROJECT_DIR/data/logs/api.log" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_DIR/api.pid"
    log_ok "后端已启动 PID: $new_pid"
}

# ========== 健康检查 ==========
health_check() {
    log_section "7/7  健康检查"

    local waited=0
    while [ $waited -lt "$HEALTH_CHECK_TIMEOUT" ]; do
        if curl -sf "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log_ok "后端健康 ($HEALTH_CHECK_URL)"

            # 额外检查: 获取版本信息
            local ver_info=$(curl -s "$HEALTH_CHECK_URL" 2>/dev/null | head -c 200)
            if [ -n "$ver_info" ]; then
                log_info "响应: $ver_info"
            fi
            return 0
        fi
        sleep "$HEALTH_CHECK_INTERVAL"
        waited=$((waited + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    echo ""

    log_error "后端未在 ${HEALTH_CHECK_TIMEOUT} 秒内就绪"
    log_warn "查看日志: tail -50 $PROJECT_DIR/data/logs/api.log"
    return 1
}

# ========== 回滚 ==========
do_rollback() {
    log_section "回滚到上一个备份"

    local latest_backup="$BACKUP_BASE_DIR/latest"
    if [ ! -e "$latest_backup" ]; then
        die "未找到备份: $latest_backup"
    fi

    local backup_path=$(readlink -f "$latest_backup")
    log_info "回滚到: $backup_path"

    # 先停止当前服务
    stop_backend

    # 备份当前版本（以防回滚失败）
    if [ -d "$PROJECT_DIR/app" ]; then
        mv "$PROJECT_DIR/app" "$BACKUP_BASE_DIR/app.rollback.$(ts)"
    fi

    # 复制备份
    cp -r "$backup_path" "$PROJECT_DIR/app"

    log_ok "回滚完成，重启服务..."
    start_backend
    health_check
}

# ========== 打开浏览器 ==========
open_browser() {
    local url="$1"

    # 仅在图形会话下尝试
    if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
        log_info "无图形会话（SSH/无头），跳过自动打开浏览器"
        return 0
    fi

    log_info "自动打开浏览器: $url"

    # 优先级: xdg-open > gio open > wslview (WSL) > firefox > google-chrome > chromium
    if command -v xdg-open &> /dev/null; then
        nohup xdg-open "$url" > /dev/null 2>&1 &
        log_ok "已通过 xdg-open 打开"
    elif command -v gio &> /dev/null; then
        nohup gio open "$url" > /dev/null 2>&1 &
        log_ok "已通过 gio open 打开"
    elif command -v wslview &> /dev/null; then
        nohup wslview "$url" > /dev/null 2>&1 &
        log_ok "已通过 wslview 打开（WSL）"
    elif command -v firefox &> /dev/null; then
        nohup firefox "$url" > /dev/null 2>&1 &
        log_ok "已通过 firefox 打开"
    elif command -v google-chrome &> /dev/null; then
        nohup google-chrome "$url" > /dev/null 2>&1 &
        log_ok "已通过 google-chrome 打开"
    elif command -v chromium &> /dev/null; then
        nohup chromium "$url" > /dev/null 2>&1 &
        log_ok "已通过 chromium 打开"
    else
        log_warn "未找到可用的浏览器命令（xdg-open/firefox/chrome）"
        log_warn "请手动打开: $url"
        return 0
    fi

    # 等待 1 秒看是否能成功（不阻塞）
    sleep 1
}

# ========== 打印摘要 ==========
print_summary() {
    echo ""
    echo -e "${C_BOLD}${C_GREEN}==========================================${C_RESET}"
    echo -e "${C_BOLD}${C_GREEN}  系统启动完成${C_RESET}"
    echo -e "${C_BOLD}${C_GREEN}==========================================${C_RESET}"
    echo -e "  前端:    ${C_CYAN}http://10.221.100.33:80${C_RESET}"
    echo -e "  API:     ${C_CYAN}http://10.221.100.33:$BACKEND_PORT/docs${C_RESET}"
    echo -e "  Health:  ${C_CYAN}$HEALTH_CHECK_URL${C_RESET}"
    echo -e "  日志:    ${C_CYAN}tail -f $PROJECT_DIR/data/logs/api.log${C_RESET}"
    echo -e "${C_BOLD}${C_GREEN}==========================================${C_RESET}"
    echo ""
    echo "  停止: ./stop.sh"
    echo "  回滚: ./start.sh --rollback"
    echo ""
}

# ========== 主流程 ==========
main() {
    local do_update=0
    local do_rollback_flag=0
    local skip_nginx=0

    # 解析参数
    while [ $# -gt 0 ]; do
        case "$1" in
            --update)
                do_update=1
                shift
                ;;
            --http-url)
                HTTP_UPDATE_URL="$2"
                shift 2
                ;;
            --skip-nginx)
                skip_nginx=1
                shift
                ;;
            --no-color)
                USE_COLOR=0
                C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''; C_BOLD=''; C_RESET=''
                shift
                ;;
            --rollback)
                do_rollback_flag=1
                shift
                ;;
            --no-browser)
                no_browser=1
                shift
                ;;
            --help|-h)
                sed -n '2,25p' "$0"
                exit 0
                ;;
            *)
                log_error "未知参数: $1（使用 --help 查看用法）"
                exit 1
                ;;
        esac
    done

    # 进入项目目录
    cd "$PROJECT_DIR" || die "项目目录不存在: $PROJECT_DIR"

    # 1. 回滚模式
    if [ $do_rollback_flag -eq 1 ]; then
        do_rollback
        print_summary
        exit 0
    fi

    # 2. 依赖检测
    check_dependencies

    # 3. 备份
    backup_current

    # 4. 拉取并部署 update
    if [ $do_update -eq 1 ]; then
        deploy_update
    else
        log_info "跳过 update 拉取（使用 --update 启用）"
    fi

    # 5. 部署前端
    if [ $skip_nginx -eq 0 ]; then
        deploy_frontend
        stop_nginx
    fi

    # 6. 停止旧后端
    stop_backend

    # 7. 启动新后端
    start_backend

    # 8. 健康检查
    if ! health_check; then
        log_error "健康检查失败，尝试回滚..."
        do_rollback
        exit 1
    fi

    # 9. 摘要
    print_summary

    # 10. 自动打开浏览器
    open_browser "http://localhost:80"
}

main "$@"
