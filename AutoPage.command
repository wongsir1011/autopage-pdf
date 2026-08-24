#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d "myenv" ]; then
    echo "正在初始化 AutoPage PDF v1.3.0（首次執行需等待數分鐘）..."
    python3 -m venv myenv
fi

source myenv/bin/activate
if [ ! -f "myenv/.autopage_v1_3_0_ready" ]; then
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    touch "myenv/.autopage_v1_3_0_ready"
fi
python3 autopage_gui.py
