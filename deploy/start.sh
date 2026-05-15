#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 启动脚本
# ============================================================

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 创建日志目录
mkdir -p data/logs

# 启动FastAPI后端
echo "启动FastAPI后端 (端口8000)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > data/logs/api.log 2>&1 &
API_PID=$!
echo "  后端PID: $API_PID"

# 等待后端启动
sleep 3

# 启动Streamlit前端
echo "启动Streamlit前端 (端口8501)..."
streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 > data/logs/ui.log 2>&1 &
UI_PID=$!
echo "  前端PID: $UI_PID"

echo ""
echo "=========================================="
echo "  系统已启动"
echo "  前端: http://localhost:8501"
echo "  API:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号，清理子进程
cleanup() {
    echo ""
    echo "正在停止服务..."
    kill $API_PID 2>/dev/null
    kill $UI_PID 2>/dev/null
    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 等待子进程
wait
