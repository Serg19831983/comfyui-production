@echo off
chcp 65001 > nul
title EMPIRE CONTROL HUB - RTX 3060 12GB
set PATH=C:\AI_Project\bin;%PATH%
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
start "COMFYUI CORE (8188)" /D "C:\AI_Project\ComfyUI" "C:\AI_Project\ComfyUI\venv_prod\Scripts\python.exe" main.py --listen 127.0.0.1 --port 8188 --fast --auto-launch
timeout /t 4 /nobreak > nul
start "STUDIO HUB (9000)" /D "C:\AI_Project\comfyui-production" "C:\AI_Project\ComfyUI\venv_prod\Scripts\python.exe" core\enterprise_studio_hub.py
exit