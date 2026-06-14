# PowerShell 安装脚本 - 解决 Windows GBK/UTF-8 编码冲突
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

Write-Host "Installing akshare..." -ForegroundColor Cyan
D:\python\python.exe -m pip install akshare --no-cache-dir

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  akshare installed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now run:" -ForegroundColor Yellow
    Write-Host "  python -m src.cli.main fetch all" -ForegroundColor White
} else {
    Write-Host "Installation failed. Trying alternative method..." -ForegroundColor Red
    D:\python\python.exe -m pip install akshare --no-cache-dir --force-reinstall --user
}
pause
