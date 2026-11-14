Set-Location 'C:\AI_Project\comfyui-production'
& 'C:\AI_Project\ComfyUI\venv_prod\Scripts\python.exe' -m pip freeze > 'C:\AI_Project\comfyui-production\requirements.txt'
Copy-Item 'C:\AI_Project\ComfyUI\user\default\workflows\*.json' 'C:\AI_Project\comfyui-production\workflows\' -Force -ErrorAction SilentlyContinue
git add .
if (git status --porcelain) { git commit -m 'chore: production sync'; git push -u origin main }