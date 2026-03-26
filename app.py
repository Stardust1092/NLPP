"""
Hugging Face Spaces 入口
HF Spaces 要求 app.py 在根目录，此文件将 demo 从 ui/app.py 导出。
"""
import sys
import os

# 确保项目根目录在 import 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import demo  # noqa: E402

if __name__ == "__main__":
    demo.launch()
