# scripts/enable_remote.ps1 - 检查并提示开启远程连接
param([string]$PhotoshopPath="")
Write-Host "=== PS Remote Connections Check ===" -ForegroundColor Cyan
$proc = Get-Process Photoshop -ErrorAction SilentlyContinue
if(-not $proc){
  Write-Host "Photoshop 未运行。" -ForegroundColor Yellow
  if($PhotoshopPath){ Write-Host "正在启动: $PhotoshopPath" -ForegroundColor Yellow; Start-Process $PhotoshopPath -ArgumentList "/Automation"; Start-Sleep 3 }
  else { Write-Host "请传入 -PhotoshopPath \"C:\Path\To\Photoshop.exe\" 或手动启动 Photoshop" -ForegroundColor Yellow }
}
else { Write-Host "Photoshop 运行中 PID $($proc.Id)" -ForegroundColor Green }

# 检查端口 49494
$listener = Get-NetTCPConnection -LocalPort 49494 -ErrorAction SilentlyContinue
if($listener){ Write-Host "端口 49494 已监听（远程连接已启用）" -ForegroundColor Green; $listener | Format-Table }
else {
  Write-Host "端口 49494 未监听！" -ForegroundColor Red
  Write-Host "请手动： 编辑 > 远程连接 > 勾选 启用远程连接 > 输入密码 123456 > 确定" -ForegroundColor Yellow
  Write-Host "然后重启 Photoshop" -ForegroundColor Yellow
}

# 测试 TCP
try {
  $c = New-Object System.Net.Sockets.TcpClient("127.0.0.1",49494)
  if($c.Connected){ Write-Host "TCP 连接测试成功" -ForegroundColor Green; $c.Close() }
} catch { Write-Host "TCP 连接失败: $_" -ForegroundColor Red }

Write-Host "`n备用：若不便开启远程，可用 COM 模式： python python/demo_agent.py --use-com" -ForegroundColor Cyan
