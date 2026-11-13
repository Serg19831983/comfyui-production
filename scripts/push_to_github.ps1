param([string]$Msg = "chore: sync workflows, configs and production scripts")
$ErrorActionPreference = "Stop"
Set-Location "C:\AI_Project\comfyui-production"
& "C:\AI_Project\ComfyUI\venv\Scripts\pip.exe" freeze > "C:\AI_Project\comfyui-production\requirements.txt"
Copy-Item "C:\AI_Project\ComfyUI\user\default\workflows\*.json" "C:\AI_Project\comfyui-production\workflows\" -Force -ErrorAction SilentlyContinue
git add .
$status = git status --porcelain
if ($status) {
    git commit -m $Msg
    git push -u origin main
    Write-Output "[GITHUB SYNC OK] Изменения отправлены в репозиторий."
} else {
    Write-Output "[SKIP] Нет новых изменений для отправки."
}