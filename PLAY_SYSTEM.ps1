$ComfyDir   = "C:\AI_Project\ComfyUI"
$RepoDir    = "C:\AI_Project\comfyui-production"
$VenvPython = "$ComfyDir\venv\Scripts\python.exe"
$HubPath    = "$RepoDir\core\enterprise_studio_hub.py"
$env:PATH = "C:\AI_Project\bin;" + $env:PATH
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"
function Test-PortOpen([int]$Port) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $c.Connect("127.0.0.1", $Port); $c.Close(); return $true } catch { return $false }
}
if (-not (Test-PortOpen 8188) -and (Test-Path "$ComfyDir\main.py")) {
    Start-Process -FilePath $VenvPython -ArgumentList @("$ComfyDir\main.py", "--listen", "127.0.0.1", "--port", "8188", "--fast") -WorkingDirectory $ComfyDir
}
if (-not (Test-PortOpen 9000) -and (Test-Path $HubPath)) {
    Start-Process -FilePath $VenvPython -ArgumentList @($HubPath) -WorkingDirectory $RepoDir
}
for ($i = 0; $i -lt 15; $i++) {
    if (Test-PortOpen 8188) {
        Start-Process ([string]::Format("http://{0}:{1}", "127.0.0.1", 8188))
        if (Test-PortOpen 9000) {
            Start-Process ([string]::Format("http://{0}:{1}/docs", "127.0.0.1", 9000))
        }
        break
    }
    Start-Sleep -Seconds 2
}
