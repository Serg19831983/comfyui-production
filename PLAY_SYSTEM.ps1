$ErrorActionPreference = "Continue"
$ComfyDir   = "C:\AI_Project\ComfyUI"
$ProdDir    = "C:\AI_Project\comfyui-production"
$VenvPython = "C:\AI_Project\ComfyUI\venv\Scripts\python.exe"
$KitchenDir = "C:\AI_Project\ComfyUI\venv\Lib\site-packages\comfy_kitchen"
$HubPath    = "C:\AI_Project\ComfyUI\server.py"
Get-NetTCPConnection -LocalPort 8188, 9000 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
if (-not (Get-Process -Name "ollama*" -ErrorAction SilentlyContinue)) {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
}
if (Test-Path $KitchenDir) {
    Get-ChildItem -Path $KitchenDir -Filter "*.py" -Recurse | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "list\[(int|bool|float)\]") {
            $patched = $content -replace "list\[(int|bool|float)\]", 'Sequence[$1]'
            if ($patched -notmatch "from typing import.*Sequence") {
                $patched = "from typing import Sequence
" + $patched
            }
            Set-Content -Path $_.FullName -Value $patched -Encoding UTF8
        }
    }
}
Start-Job -ScriptBlock {
    param($dir)
    if (Test-Path $dir) {
        Set-Location $dir
        if (-not (Test-Path ".git")) {
            git init
            git branch -M main
        }
        git config user.name "Serg19831983"
        git config user.email "Serg19831983@users.noreply.github.com"
        git remote remove origin 2>$null
        git remote add origin "https://github.com/Serg19831983/comfyui-production.git"
        git add .
        git commit -m "AutoSync 2026-11-14 02:48" 2>$null
        git push -u origin main --force 2>$null
    }
} -ArgumentList $ProdDir | Out-Null
if (Test-Path $VenvPython) {
    if (Test-Path "$ComfyDir\main.py") {
        Start-Process -FilePath $VenvPython -ArgumentList ""$ComfyDir\main.py" --listen 0.0.0.0 --port 8188" -WorkingDirectory $ComfyDir
    }
    if (Test-Path $HubPath) {
        Start-Process -FilePath $VenvPython -ArgumentList ""$HubPath" --port 9000" -WorkingDirectory $ProdDir
    }
}
$timeout = 90
$elapsed = 0
while ($elapsed -lt $timeout) {
    $p8188 = Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -InformationLevel Quiet -WarningAction SilentlyContinue
    $p9000 = Test-NetConnection -ComputerName 127.0.0.1 -Port 9000 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($p8188 -and $p9000) {
        Start-Process "http://127.0.0.1:9000"
        break
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
}
