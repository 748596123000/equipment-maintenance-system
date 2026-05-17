#!/bin/bash
# ============================================================
# 设备检修知识检索与作业系统 - 启动脚本
# 支持：Nginx(React前端) + FastAPI(后端)
# ============================================================

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 创建日志目录
mkdir -p data/logs

# 启动FastAPI后端
echo "启动FastAPI后端 (端口8000)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee data/logs/api.log &
API_PID=$!
echo $API_PID > data/logs/api.pid
echo "  后端PID: $API_PID"

# 等待后端启动（健康检查替代固定等待）
echo "等待后端就绪..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "  后端已就绪"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  警告: 后端未在30秒内就绪"
    fi
    sleep 1
done

# 检测前端模式：Nginx(React) 或 Streamlit
if command -v nginx &> /dev/null && [ -d "/usr/share/nginx/html/assets" ]; then
    echo "启动Nginx前端 (端口80)..."
    nginx 2>&1 | tee data/logs/ui.log &
    UI_PID=$!
    echo $UI_PID > data/logs/ui.pid
    echo "  Nginx PID: $UI_PID"
    FRONTEND_URL="http://localhost:80"
elif [ -d "frontend/dist" ] && command -v nginx &> /dev/null; then
    echo "检测到React前端构建产物，配置Nginx..."
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null
    cp frontend/nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null
    cp -r frontend/dist/* /usr/share/nginx/html/ 2>/dev/null
    nginx 2>&1 | tee data/logs/ui.log &
    UI_PID=$!
    echo $UI_PID > data/logs/ui.pid
    echo "  Nginx PID: $UI_PID"
    FRONTEND_URL="http://localhost:80"
else
    echo "启动Streamlit前端 (端口8501)..."
    streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true 2>&1 | tee data/logs/ui.log &
    UI_PID=$!
    echo $UI_PID > data/logs/ui.pid
    echo "  前端PID: $UI_PID"
    FRONTEND_URL="http://localhost:8501"
fi

echo ""
echo "=========================================="
echo "  系统已启动"
echo "  前端: $FRONTEND_URL"
echo "  API:  http://localhost:8000/docs"
echo "=========================================="
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号，清理子进程
cleanup() {
    echo ""
    echo "正在停止服务..."
    kill -TERM $API_PID 2>/dev/null
    kill -TERM $UI_PID 2>/dev/null
    nginx -s stop 2>/dev/null
    # 等待最多5秒
    for i in $(seq 1 5); do
        kill -0 $API_PID 2>/dev/null || kill -0 $UI_PID 2>/dev/null || break
        sleep 1
    done
    kill -9 $API_PID 2>/dev/null
    kill -9 $UI_PID 2>/dev/null
    rm -f data/logs/api.pid data/logs/ui.pid
    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 等待子进程
wait
