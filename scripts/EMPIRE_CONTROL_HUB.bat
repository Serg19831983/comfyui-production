@echo off
chcp 65001 > nul
title EMPIRE CONTROL HUB - COMFYUI PRODUCTION
set PATH=C:\AI_Project\bin;%PATH%
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
start "COMFYUI ENGINE (8188)" cmd /k "cd /d C:\AI_Project\ComfyUI && venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188 --fast"
timeout /t 3 > nul
start "ENTERPRISE STUDIO HUB (9000)" cmd /k "cd /d C:\AI_Project\comfyui-production && C:\AI_Project\ComfyUI\venv\Scripts\python.exe core\enterprise_studio_hub.py"
echo [OK] ??? ?????????? ????????.
pause