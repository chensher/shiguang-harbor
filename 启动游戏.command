#!/bin/bash
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 server.py
else
  echo "没有找到 python3。请在终端运行：xcode-select --install  安装后再双击本文件。"
  read -n 1
fi
