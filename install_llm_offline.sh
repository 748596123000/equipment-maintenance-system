#!/bin/bash
# ================================================================
# 离线LLM编译配置脚本
# 从主机传输的llama.cpp源码编译 → 配置模型 → 配置环境 → 重启项目
# ================================================================

set +e

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/data/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/llm_offline_$(date +%Y%m%d_%H%M%S).log"

ok() { echo -e "  ${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
fail() { echo -e "  ${RED}✗${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }
info() { echo -e "  ${BLUE}ℹ${NC} $1" | tee -a "$LOG_FILE"; }
fix() { echo -e "  ${YELLOW}↻${NC} $1" | tee -a "$LOG_FILE"; }

section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN} $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

CPU_CORES=$(nproc 2>/dev/null || echo 4)

# ================================================================
section "步骤1/6: 解压离线包"

PACKAGE=""
for p in ~/llm_offline_package.zip ~/knowledge-system/llm_offline_package.zip /tmp/llm_offline_package.zip; do
    if [ -f "$p" ]; then
        PACKAGE="$p"
        break
    fi
done

if [ -z "$PACKAGE" ]; then
    fail "未找到 llm_offline_package.zip"
    info "请将Windows主机上的 llm_offline_package.zip 传输到虚拟机 ~/ 目录"
    info "然后重新运行此脚本"
    exit 1
fi

fix "解压 $PACKAGE ..."
cd ~
unzip -o "$PACKAGE" 2>>"$LOG_FILE"
ok "解压完成"

if [ -d ~/llama.cpp-master ] && [ ! -d ~/llama.cpp ]; then
    fix "重命名 llama.cpp-master → llama.cpp ..."
    mv ~/llama.cpp-master ~/llama.cpp
fi

echo -n "  llama.cpp源码: "
if [ -d ~/llama.cpp ]; then
    ok "已解压"
else
    fail "未找到llama.cpp目录"
    exit 1
fi

echo -n "  GGUF模型: "
GGUF_MODEL=""
for d in ~/models ~/knowledge-system/models; do
    FOUND=$(find "$d" -name "*.gguf" -type f 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        GGUF_MODEL="$FOUND"
        ok "$FOUND"
        break
    fi
done
if [ -z "$GGUF_MODEL" ]; then
    warn "未找到GGUF模型文件"
fi

# ================================================================
section "步骤2/6: 编译llama.cpp"

if command -v llama-server &>/dev/null; then
    ok "llama-server已安装"
    LLAMACPP_OK=true
else
    LLAMACPP_OK=false

    if ! command -v cmake &>/dev/null || ! command -v gcc &>/dev/null; then
        fix "安装编译工具..."
        sudo yum install -y cmake gcc-c++ 2>>"$LOG_FILE"
    fi

    fix "编译llama.cpp (5-10分钟)..."
    cd ~/llama.cpp

    cmake -B build -DCMAKE_BUILD_TYPE=Release 2>>"$LOG_FILE"
    cmake --build build --config Release -j$CPU_CORES 2>>"$LOG_FILE"

    if [ -f "build/bin/llama-server" ]; then
        sudo cp build/bin/llama-server /usr/local/bin/
        sudo cp build/bin/llama-cli /usr/local/bin/ 2>/dev/null
        ok "llama.cpp编译成功(cmake)"
        LLAMACPP_OK=true
    else
        info "cmake编译失败，尝试make..."
        make -j$CPU_CORES 2>>"$LOG_FILE"
        if [ -f "llama-server" ]; then
            sudo cp llama-server /usr/local/bin/
            sudo cp llama-cli /usr/local/bin/ 2>/dev/null
            ok "llama.cpp编译成功(make)"
            LLAMACPP_OK=true
        else
            fail "llama.cpp编译失败"
            info "查看编译日志: cat $LOG_FILE"
        fi
    fi

    cd "$SCRIPT_DIR"
fi

# ================================================================
section "步骤3/6: 启动llama.cpp服务"

LLM_RUNNING=false
LLM_BACKEND=""
LLM_MODEL=""
LLM_BASE_URL=""

if $LLAMACPP_OK || command -v llama-server &>/dev/null; then
    # 停止旧的llama.cpp进程
    pkill -f "llama-server" 2>/dev/null
    sleep 2

    if [ -z "$GGUF_MODEL" ]; then
        for d in ~/models ~/knowledge-system/models /opt/models; do
            FOUND=$(find "$d" -name "*.gguf" -type f 2>/dev/null | head -1)
            if [ -n "$FOUND" ]; then
                GGUF_MODEL="$FOUND"
                break
            fi
        done
    fi

    if [ -n "$GGUF_MODEL" ]; then
        fix "启动llama.cpp服务..."
        nohup llama-server -m "$GGUF_MODEL" --host 0.0.0.0 --port 11435 -c 4096 -t $CPU_CORES \
            >> "$LOG_DIR/llama_cpp.log" 2>&1 &
        LLAMA_PID=$!
        echo "$LLAMA_PID" > "$LOG_DIR/llama_cpp.pid"

        for i in $(seq 1 60); do
            sleep 1
            if curl -sf http://localhost:11435/v1/models --connect-timeout 2 2>/dev/null | grep -q "data"; then
                LLM_RUNNING=true
                break
            fi
        done

        if $LLM_RUNNING; then
            ok "llama.cpp服务已启动 (PID: $LLAMA_PID)"
            LLM_BACKEND="openai_compatible"
            LLM_MODEL="qwen2.5-3b-instruct"
            LLM_BASE_URL="http://localhost:11435/v1"
        else
            fail "llama.cpp服务启动失败"
            info "查看日志: cat $LOG_DIR/llama_cpp.log"
            echo "最后10行日志:"
            tail -10 "$LOG_DIR/llama_cpp.log" 2>/dev/null | while read line; do echo -e "    $line"; done
        fi
    else
        fail "未找到GGUF模型文件"
    fi
else
    fail "llama.cpp未编译成功"
fi

# ================================================================
section "步骤4/6: 配置环境"

if [ -f ".env" ]; then
    info "更新.env文件..."
    if [ -n "$LLM_BACKEND" ]; then
        sed -i "s/^LLM_BACKEND=.*/LLM_BACKEND=$LLM_BACKEND/" .env
        sed -i "s/^LLM_MODEL=.*/LLM_MODEL=$LLM_MODEL/" .env
        sed -i "s|^LLM_API_BASE_URL=.*|LLM_API_BASE_URL=$LLM_BASE_URL|" .env
        sed -i 's/^LLM_API_KEY=.*/LLM_API_KEY=not-needed/' .env
        ok "LLM配置已写入: $LLM_BACKEND / $LLM_MODEL"
    else
        warn "LLM未配置，AI功能不可用"
    fi

    sed -i 's/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=\["\*"\]/' .env
    ok "ALLOWED_HOSTS已更新"
else
    warn ".env文件不存在，跳过"
fi

if [ -n "$LLM_BACKEND" ]; then
    fix "更新数据库LLM配置..."
    python3 << PYEOF
import sys, os, sqlite3
sys.path.insert(0, '.')
os.chdir('.')
try:
    from app.config import settings
    db_path = settings.SQLITE_DB_PATH
except:
    db_path = "./data/app.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS system_config (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('llm_backend', '$LLM_BACKEND')")
        conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('llm_model', '$LLM_MODEL')")
        conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('llm_api_base_url', '$LLM_BASE_URL')")
        conn.commit()
        print("OK")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
PYEOF
    ok "数据库LLM配置已更新"
fi

# ================================================================
section "步骤5/6: 重启后端"

if [ -f "$LOG_DIR/api.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/api.pid" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        fix "停止旧进程 (PID: $OLD_PID)..."
        kill -TERM "$OLD_PID" 2>/dev/null
        sleep 3
        kill -9 "$OLD_PID" 2>/dev/null
    fi
    rm -f "$LOG_DIR/api.pid"
fi

if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    PID_OCC=$(ss -tlnp 2>/dev/null | grep ":8000 " | grep -oP 'pid=\K[0-9]+' | head -1)
    [ -z "$PID_OCC" ] && PID_OCC=$(ss -tlnp 2>/dev/null | grep ":8000 " | awk '{print $NF}' | grep -oP '[0-9]+' | head -1)
    if [ -n "$PID_OCC" ]; then
        kill -9 "$PID_OCC" 2>/dev/null
        sleep 1
    fi
fi

API_LOG="$LOG_DIR/api.log"
echo "" > "$API_LOG"

nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$API_LOG" 2>&1 &
API_PID=$!
echo "$API_PID" > "$LOG_DIR/api.pid"

info "启动后端 (PID: $API_PID)..."

STARTUP_OK=false
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8000/health" --connect-timeout 1 >/dev/null 2>&1; then
        STARTUP_OK=true
        break
    fi
    if ! kill -0 "$API_PID" 2>/dev/null; then
        break
    fi
    sleep 1
done

if $STARTUP_OK; then
    ok "后端服务已就绪"
else
    if ! kill -0 "$API_PID" 2>/dev/null; then
        fail "后端启动失败！"
        tail -20 "$API_LOG" | while read line; do echo -e "    $line"; done
    else
        warn "启动超时"
    fi
fi

# ================================================================
section "步骤6/6: 验证"

echo -n "  后端健康: "
curl -sf http://localhost:8000/health >/dev/null 2>&1 && ok "正常" || fail "异常"

echo -n "  前端页面: "
curl -sf http://localhost/ -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null | grep -q "200" && ok "正常" || fail "异常"

if $LLM_RUNNING; then
    echo -n "  LLM服务: "
    curl -sf http://localhost:11435/v1/models --connect-timeout 5 >/dev/null 2>&1 && ok "llama.cpp正常" || fail "llama.cpp异常"

    echo -n "  AI问答: "
    TOKEN=$(python3 << 'PYEOF'
import sys, os, uuid, sqlite3
from datetime import datetime, timedelta, timezone
sys.path.insert(0, '.')
os.chdir('.')
try:
    from app.config import settings
    db_path = settings.SQLITE_DB_PATH
except:
    db_path = "./data/app.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id FROM users WHERE username = 'admin' AND is_active = 1").fetchone()
if row:
    token = uuid.uuid4().hex
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    now = datetime.now().isoformat()
    conn.execute("INSERT OR REPLACE INTO auth_tokens (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", (token, row['id'], expires_at, now))
    conn.commit()
    print(token)
conn.close()
PYEOF
)

    if [ -n "$TOKEN" ]; then
        RESP=$(curl -sf -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
            -d '{"message":"你好","stream":false}' http://localhost:8000/api/v1/chat/send --connect-timeout 60 2>/dev/null)
        ANSWER=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('answer',''))" 2>/dev/null)
        if [ -n "$ANSWER" ]; then
            ok "AI回答正常: ${ANSWER:0:80}..."
        else
            warn "AI未回答（模型可能还在加载中，请稍等1-2分钟再试）"
        fi
    else
        warn "Token生成失败"
    fi
else
    warn "LLM服务未运行，AI功能不可用"
fi

# ================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD} 配置完成！${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="10.221.100.33"

if [ -n "$LLM_BACKEND" ]; then
    echo -e "  ${BOLD}LLM配置:${NC}"
    echo -e "    后端:   ${GREEN}$LLM_BACKEND${NC}"
    echo -e "    模型:   ${GREEN}$LLM_MODEL${NC}"
    echo -e "    地址:   ${GREEN}$LLM_BASE_URL${NC}"
    echo ""
fi

echo -e "  ${BOLD}访问地址:${NC}"
echo -e "    前端:   ${GREEN}http://${LOCAL_IP}${NC}"
echo -e "    API:    ${GREEN}http://${LOCAL_IP}:8000/docs${NC}"
echo ""

if [ -f ".initial_passwords" ]; then
    echo -e "  ${BOLD}${YELLOW}初始账号:${NC}"
    while IFS=' / ' read -r uname upass; do
        echo -e "    ${GREEN}$uname${NC} / ${GREEN}$upass${NC}"
    done < .initial_passwords
    echo ""
fi

echo -e "  ${BOLD}常用命令:${NC}"
echo -e "    查看LLM日志:  tail -f $LOG_DIR/llama_cpp.log"
echo -e "    查看后端日志: tail -f $LOG_DIR/api.log"
echo -e "    重启LLM:      kill \$(cat $LOG_DIR/llama_cpp.pid); sleep 2; nohup llama-server -m $GGUF_MODEL --host 0.0.0.0 --port 11435 -c 4096 >> $LOG_DIR/llama_cpp.log 2>&1 &"
echo ""
