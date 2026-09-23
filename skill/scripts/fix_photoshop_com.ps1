param(
  [string]$PhotoshopPath = ""
)
# Fix Photoshop COM registration (HKCU override, no admin)
if (-not $PhotoshopPath) {
  Write-Host "Usage: .\fix_photoshop_com.ps1 -PhotoshopPath \"C:\Path\To\Photoshop.exe\"" -ForegroundColor Yellow
  exit 1
}
$clsid = "{C4C3E2FB-D66C-44E5-96A0-349F951CB3D4}"
$hkcu = "HKCU:\Software\Classes\CLSID\$clsid\LocalServer32"
New-Item -Path $hkcu -Force | Out-Null
Set-ItemProperty -Path $hkcu -Name "(default)" -Value "$PhotoshopPath /Automation" | Out-Null
New-Item -Path "HKCU:\Software\Classes\Photoshop.Application\CLSID" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\Photoshop.Application\CLSID" -Name "(default)" -Value $clsid | Out-Null
Write-Host "Fixed HKCU COM to $PhotoshopPath"

$proc = Get-Process Photoshop -ErrorAction SilentlyContinue
$needRestart = $false
if ($proc) {
  $cmd = (Get-CimInstance Win32_Process -Filter "Name='Photoshop.exe'" | Where-Object { $_.ProcessId -eq $proc.Id }).CommandLine
  if ($cmd -notlike "*/Automation*") {
    Write-Host "Photoshop running without /Automation, restarting..."
    $needRestart = $true
    Stop-Process -Id $proc.Id -Force
    Start-Sleep 3
  } else {
    Write-Host "Photoshop already with /Automation PID $($proc.Id)"
  }
}
if (-not (Get-Process Photoshop -ErrorAction SilentlyContinue) -or $needRestart) {
  Start-Process -FilePath $PhotoshopPath -ArgumentList "/Automation" -WindowStyle Normal
  Write-Host "Started Photoshop with /Automation, waiting 8s..."
  Start-Sleep 8
}
Get-Process Photoshop | Select-Object Id, ProcessName, MainWindowTitle | Format-List | Out-String | Write-Host
