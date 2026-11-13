@echo off
chcp 65001 > nul
title COMFYUI PRODUCTION - RTX 3060 12GB
cd /d C:\AI_Project\ComfyUI
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --fast --auto-launch
pause