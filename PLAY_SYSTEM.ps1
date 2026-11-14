$ErrorActionPreference = "Continue"
$GitUser    = "Serg19831983"
$RepoUrl    = "https://github.com"
$ComfyDir   = "C:\AI_Project\ComfyUI"
$ProdDir    = "C:\AI_Project\comfyui-production"
$VenvPython = "C:\AI_Project\ComfyUI\venv\Scripts\python.exe"
$KitchenDir = "C:\AI_Project\ComfyUI\venv\Lib\site-packages\comfy_kitchen"
# Очистка старых зависших процессов Python на портах 8188 и 9000
Get-NetTCPConnection -LocalPort 8188, 9000 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
# 1. Авто-патч comfy_kitchen
if (Test-Path $KitchenDir) {
    Get-ChildItem -Path $KitchenDir -Filter "*.py" -Recurse | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "list\[(int|bool|float)\]") {
            $patched = $content -replace "list\[(int|bool|float)\]", 'Sequence[$1]'
            if ($patched -notmatch "from typing import.*Sequence") {
                $patched = "from typing import Sequence`r`n" + $patched
            }
            Set-Content -Path $_.FullName -Value $patched -Encoding UTF8
        }
    }
}
# 2. Фоновая синхронизация GitHub (не тормозит запуск)
Start-Job -ScriptBlock {
    param($dir, $url, $user)
    if (Test-Path $dir) {
        Set-Location $dir
        if (-not (Test-Path ".git")) {
            git init
            git branch -M main
        }
        git config user.name $user
        git config user.email "$user@://github.com"
        git remote remove origin 2>$null
        git remote add origin $url
        git add .
        git commit -m "AutoSync $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>$null
        git push -u origin main --force 2>$null
    }
} -ArgumentList $ProdDir, $RepoUrl, $GitUser | Out-Null
# 3. Запуск ядра ComfyUI (8188) и Studio Hub (9000)
if (Test-Path $VenvPython) {
    if (Test-Path "$ComfyDir\main.py") {
        Start-Process -FilePath $VenvPython -ArgumentList "`"$ComfyDir\main.py`" --listen 0.0.0.0 --port 8188" -WorkingDirectory $ComfyDir
    }
    $HubEntry = Get-ChildItem -Path $ProdDir -Filter "*.py" -Recurse | Where-Object { $_.Name -match "^(app|hub|server|main)\.py$" } | Select-Object -First 1
    if ($HubEntry) {
        Start-Process -FilePath $VenvPython -ArgumentList "`"$($HubEntry.FullName)`" --port 9000" -WorkingDirectory $ProdDir
    }
}
# 4. Ожидание готовности серверов и авто-открытие браузера (Play)
$timeout = 90
$elapsed = 0
$opened8188 = $false
$opened9000 = $false
while ($elapsed -lt $timeout) {
    if (-not $opened9000) {
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port 9000 -InformationLevel Quiet -WarningAction SilentlyContinue) {
            Start-Process "http://127.0.0.1:9000"
            $opened9000 = $true
        }
    }
    if (-not $opened8188) {
        if (Test-NetConnection -ComputerName 127.0.0.1 -Port 8188 -InformationLevel Quiet -WarningAction SilentlyContinue) {
            Start-Process "http://127.0.0.1:8188"
            $opened8188 = $true
        }
    }
    if ($opened8188 -and $opened9000) { break }
    Start-Sleep -Seconds 2
    $elapsed += 2
}
