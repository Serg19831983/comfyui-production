@echo off
chcp 65001 > nul
title EMPIRE CONTROL HUB - RTX 3060 12GB (2026 STANDARD)
set PATH=C:\AI_Project\bin;%PATH%
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:512
start "COMFYUI CORE (8188)" /D "C:\AI_Project\ComfyUI" "C:\AI_Project\ComfyUI\venv_prod\Scripts\python.exe" main.py --listen 127.0.0.1 --port 8188 --use-sage-attention --reserve-vram 1.5 --fast
timeout /t 8 /nobreak > nul
start "STUDIO HUB (9000)" /D "C:\AI_Project\comfyui-production" "C:\AI_Project\ComfyUI\venv_prod\Scripts\python.exe" core\hub.py
exit