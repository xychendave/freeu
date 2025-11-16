#!/bin/bash

# FreeU启动脚本

echo "🚀 启动 FreeU - AI文件整理助手"
echo "=================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装Python 3"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ 错误: 需要Python $REQUIRED_VERSION 或更高版本"
    echo "当前版本: Python $PYTHON_VERSION"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 找不到requirements.txt"
    exit 1
fi

# 安装依赖
echo "安装Python依赖..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

# 启动应用
echo "✅ 依赖检查完成"
echo "🚀 启动应用..."
echo ""

python3 src/main.py