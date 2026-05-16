#!/bin/bash
# 停止所有服务
echo "正在停止服务..."

stop_process() {
    local pid_file=$1
    local name=$2
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        kill -TERM "$PID" 2>/dev/null
        for i in $(seq 1 10); do
            kill -0 "$PID" 2>/dev/null || break
            sleep 1
        done
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$pid_file"
        echo "  $name 已停止 (PID: $PID)"
    else
        pkill -f "$3" 2>/dev/null && echo "  $name 已停止 (pkill)" || echo "  $name 未运行"
    fi
}

stop_process "data/logs/api.pid" "FastAPI后端" "uvicorn app.main:app"
stop_process "data/logs/ui.pid" "Streamlit前端" "streamlit run ui/app.py"

echo "服务已停止"
