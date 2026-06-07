#!/bin/bash

echo "编译 llama.cpp (LoongArch)..."
cd ~/llama.cpp

# 清理旧编译
rm -rf build
mkdir build
cd build

echo "[1/3] 配置 CMake..."
cmake .. \
    -DLLAMA_NATIVE=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=ON

echo ""
echo "[2/3] 编译..."
cmake --build . --config Release -j$(nproc)

echo ""
echo "[3/3] 检查编译结果..."
ls -la llama-cli llama-server 2>/dev/null || echo "编译文件不在当前目录"
find . -name "llama-cli" -o -name "llama-server" 2>/dev/null

echo ""
echo "编译完成!"
echo ""
echo "使用方式:"
echo "  cd ~/llama.cpp/build"
echo "  ./llama-cli -m ~/models/qwen2.5-7b-instruct-q4_k_m.gguf -p \"你好\" -n 100"
echo ""
echo "启动API服务:"
echo "  ./llama-server -m ~/models/qwen2.5-7b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 11434"