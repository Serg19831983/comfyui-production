@echo off
chcp 65001 > nul
title COMFYUI PRODUCTION ENGINE - RTX 3060 12GB
set PATH=C:\AI_Project\bin;%PATH%
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /d C:\AI_Project\ComfyUI
venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --reserve-vram 1.5 --preview-method auto --auto-launch
pause