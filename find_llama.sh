#!/bin/bash

echo "查找 llama.cpp 安装位置..."
echo ""

# 方法1: 查找可执行文件
echo "[方法1] 查找 llama-cli 或 llama-server..."
find /usr -name "llama-cli" -o -name "llama-server" -o -name "main" 2>/dev/null

echo ""
echo "[方法2] 查看安装文件列表..."
rpm -ql llama.cpp 2>/dev/null | head -30

echo ""
echo "[方法3] 查找包含 llama 的可执行文件..."
find /usr/bin /usr/local/bin /opt -name "*llama*" -type f 2>/dev/null

echo ""
echo "[方法4] 查看 rpm 包信息..."
rpm -qi llama.cpp 2>/dev/null

echo ""
echo "[方法5] 查找示例程序或文档..."
find /usr/share -name "*llama*" -type f 2>/dev/null | head -10