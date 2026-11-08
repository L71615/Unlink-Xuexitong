# 发布更新：把新打好的 dist_new 换成 dist，并生成「下载即用」的发布压缩包
#
# 用法：
#   1. 完全退出正在运行的「课业助手」（托盘里也要退）
#   2. 右键本脚本 → 使用 PowerShell 运行，或在终端里执行：
#        pwsh -File .\发布更新.ps1
#
# 做的事：
#   - dist → dist_old（旧包备份，确认没问题后可以删）
#   - dist_new → dist（新包，桌面快捷方式不用改）
#   - 生成 CourseHelper-<版本>-win64.zip 作为 Release 附件

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$running = Get-Process -Name 课业助手 -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "课业助手 还在运行（PID $($running.Id)），请先退出程序再运行本脚本。" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path 'dist_new\课业助手\课业助手.exe')) {
    Write-Host "没找到新包 dist_new\课业助手\课业助手.exe，请先执行：python build_exe.py" -ForegroundColor Yellow
    exit 1
}

$version = (python -c "import version; print(version.APP_VERSION)").Trim()
Write-Host "版本：$version" -ForegroundColor Cyan

if (Test-Path 'dist_old') { Remove-Item 'dist_old' -Recurse -Force }
if (Test-Path 'dist') { Rename-Item 'dist' 'dist_old' }
Rename-Item 'dist_new' 'dist'
Write-Host "已切换：dist 现在是新包，旧包保留在 dist_old" -ForegroundColor Green

$zip = "CourseHelper-$version-win64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Join-Path $root 'dist'),
    (Join-Path $root $zip),
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true)
$size = (Get-Item $zip).Length / 1MB
Write-Host ("已生成发布包：{0}（{1:N1} MB）" -f $zip, $size) -ForegroundColor Green
Write-Host "发布时上传这个 zip 到 Releases 即可（README 里写的名字和它一致）"
