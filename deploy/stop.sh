#!/bin/bash
# 停止所有服务
echo "正在停止服务..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "streamlit run ui/app.py" 2>/dev/null
echo "服务已停止"
