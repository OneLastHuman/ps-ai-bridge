# COM 直连诊断

If Photoshop does not register `Photoshop.Application`, COM calls fail.

**Symptoms**
- `New-Object -ComObject Photoshop.Application` -> `0x80080005 CO_E_SERVER_EXEC_FAILURE`
- `GetObject(,"Photoshop.Application")` -> 429
- `HKCR\CLSID\{C4C3E2FB...}\LocalServer32` points to wrong path

**Fix** `scripts/fix_photoshop_com.ps1` writes HKCU override (no admin) and restarts with `/Automation` for ROT.

**Verify** `cscript scripts/test_com.vbs` -> `PS 13.0.0 Docs:0`

**Fallback** COM fallback in `ps_bridge.py:332` auto-tries TCP then COM. Use `--use-com` to force.
