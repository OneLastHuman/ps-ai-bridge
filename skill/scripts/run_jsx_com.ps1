param(
  [string]$JsxPath,
  [int]$TimeoutSec=30
)
# COM 执行器（COM 注册修复思路）
if(-not (Test-Path $JsxPath)){ Write-Error "JSX not found: $JsxPath"; exit 1 }
# 尝试 HKCU COM 修复提示
$clsid="{C4C3E2FB-D66C-44E5-96A0-349F951CB3D4}"
$hkcu="HKCU:\Software\Classes\CLSID\$clsid\LocalServer32"
if(-not (Test-Path $hkcu)){ Write-Host "Hint: Run scripts/fix_photoshop_com.ps1 if COM fails" -ForegroundColor Yellow }

$vbs = @"
Set ps = GetObject(, "Photoshop.Application")
If Err.Number <> 0 Then
  Set ps = CreateObject("Photoshop.Application")
End If
ps.DoJavaScriptFile "$($JsxPath.Replace('\','\\'))"
WScript.Echo "DONE"
"@
$tmpVbs = "$env:TEMP\ps_run.vbs"
Set-Content -Path $tmpVbs -Value $vbs -Encoding ASCII
Write-Host "Executing $JsxPath via COM..." -ForegroundColor Cyan
cscript //Nologo $tmpVbs
if($LASTEXITCODE -ne 0){ Write-Error "COM exec failed" }
Remove-Item $tmpVbs -Force -ErrorAction SilentlyContinue
