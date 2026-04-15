import os
import sys

# 讓 Vercel 的 serverless function 能 import 根目錄的 app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
