#!/bin/bash

echo "设置 llama.cpp 快捷命令..."

# 创建软链接
sudo ln -sf /usr/bin/llama_cpp_main /usr/local/bin/llama-cli

echo "测试 llama.cpp..."
llama-cli --help 2>&1 | head -20

echo ""
echo "llama.cpp 已配置完成!"
echo ""
echo "使用方式:"
echo "  1. 下载模型:"
echo "     mkdir -p ~/models && cd ~/models"
echo "     wget https://modelscope.cn/models/qwen/Qwen2.5-7B-Instruct-GGUF/resolve/master/qwen2.5-7b-instruct-q4_k_m.gguf"
echo ""
echo "  2. 运行对话:"
echo "     llama-cli -m ~/models/qwen2.5-7b-instruct-q4_k_m.gguf -p \"你好\" -n 100"
echo ""
echo "  3. 启动API服务(后台运行):"
echo "     nohup llama_cpp_main -m ~/models/qwen2.5-7b-instruct-q4_k_m.gguf \" > /dev/null 2>&1 &"
echo "     或查看 llama_cpp_main --help 了解参数"
echo ""
echo "注意: 旧版本可能没有 llama-server，只有 llama_cpp_main"
echo "      可以用 llama_cpp_main --help 查看支持的参数"