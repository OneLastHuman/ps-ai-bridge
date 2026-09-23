---
name: ps-ai-bridge
description: Complete Photoshop CS6/CC bridge for AI Agents with see·draw·modify·all tools PLUS mandatory visual verification & one-layer-per-element discipline before delivery. Use when needing to (1) capture vision, (2) draw programmatically, (3) modify images, (4) drive any Photoshop tool, (5) handle CS6 COM/Remote, (6) build see→edit→verify loops, (7) maintain layer-per-material for editable delivery. Triggers on "PS看图/画图/改图/全工具/视觉检验/校验/分层", "控制PS", "Photoshop自动化", "让AI看图画图".
---

# PS AI Bridge

Control `Photoshop CS6 (13.0)` / `CC` for AI Agents with **see · draw · modify · all tools** in one bridge. Based on `connectionsdk` TCP:49494 + COM fallback, works with Photoshop CS6/CC (Remote Connections or COM).

## Workflow Decision Tree — 交付前必须走完 7 步

1. **Read intent** -> `see` / `draw` / `modify` / `tool` 四类
2. **Connect** -> `scripts/test_connection.py` (TCP 49494) 或 `--use-com`（COM 直连）；`0x80080005` → `scripts/fix_photoshop_com.ps1`
3. **See** -> `bridge.capture_jpeg()` / `list_layers()` -> 喂给视觉模型
4. **Draw/Modify/Tool (一素材一图层)** -> `ps_bridge.py` APIs 执行，**每个素材独立图层并命名**（见 `references/layers.md`），禁止单层扁平化
5. **Verify (强制·视觉+图层检验)** -> `capture_jpeg(save_path)` + `Read` 看图 + `list_layers()` 检分层 → 按 `references/verify_loop.md` 7项打分
6. **Optimize (按需循环)** -> 若遮挡/构图/色彩/文字/分层不达标，回到 Step 4 定向修复 → 再 capture → 直到 `PASS`
7. **Deliver** -> `save_document` (保留图层PSD) + 输出验证图路径，**不得跳过 Step 5-6**

> 反模式：`做完就算完成`。必须 `capture_jpeg` + `Read(filePath)` 用视觉确认，否则视为未交付。详见 `references/verify_loop.md`。

## Quick Start

```powershell
pip install -r scripts/requirements.txt  # pycryptodome + Pillow + pywin32
python scripts/test_connection.py --password 123456          # TCP
python scripts/test_connection.py --use-com                  # COM fallback
python scripts/demo_agent.py --use-com                       # full loop
python scripts/verify_all.py                                 # exhaustive check
```

TCP needs `Edit > Remote Connections > Enable + password` (see `references/protocol.md`).

## Core Capabilities

### 1. See - Vision for Agent
```python
from scripts.ps_bridge import PhotoshopAIBridge
b=PhotoshopAIBridge(use_com=True); b.connect()
b.get_app_info()              # app.name/version/docCount
b.get_document_info()         # width/height/mode/layers
b.list_layers()               # name/visible/opacity/bounds
jpg=b.capture_jpeg(800,600, save_path="out.jpg")  # sendDocumentThumbnailToNetworkClient
```
JPEG via `sendDocumentThumbnailToNetworkClient` (format 1) or `sendLayerThumbnailToNetworkClient` for layer-level. Pixmap also available. See `references/protocol.md`.

### 2. Draw - Create (一素材一图层)
```python
b.create_document(1024,768,"Canvas")
# 每个素材前新建并命名图层，后续可单独改该层而不动其他
b.execute_jsx('app.activeDocument.artLayers.add().name="BG_sky";')
b.draw_rect(50,50,400,200,(255,80,80))
b.execute_jsx('app.activeDocument.artLayers.add().name="MEI_branch";')
b.draw_ellipse(500,400,120,80,(80,160,255))  # 32-seg polygon, no Elps
b.execute_jsx('app.activeDocument.artLayers.add().name="MEI_bloom_01";')
b.draw_polygon([(700,100),(850,250),(750,400)],(80,220,120))
b.paste_image("tmp.jpg")  # open+copy fallback for CS6 → 自动成新层，需 execute_jsx 改名
b.save_document("out.jpg")
```
> **铁规：多素材必须一素材一图层**（`BG_远山`/`BG_雪地`/`MEI_主枝`/`MEI_花簇`/`TEXT_标题`/`TEXT_诗`/`SEAL_印`**分层**），否则后期无法单改某素材。详见 `references/layers.md`。Primitives 见 `assets/drawing_primitives.jsx`。

### 3. Modify - Edit Existing
```python
b.adjust_brightness_contrast(15,15)
b.adjust_hue_saturation(5,15,0)
b.apply_blur(3)
b.transform_layer(90,90,5)  # auto-unlocks background
b.undo(); b.redo()
```
Via `ActionDescriptor` (`brightnessEvent/gaussianBlur/transform`). See `references/api_reference.md`.

### 4. All Tools
```python
b.select_tool("brushTool")  # move/brush/eraser/gradient/pen/text/hand/zoom etc. 42 tools
b.execute_jsx('app.activeDocument.activeLayer.opacity=80; return app.activeDocument.name;')
b.execute_action("cut")     # any stringIDToTypeID
b.list_tools()
```
`assets/tools_map.jsx` maps 42 toolIDs. Any Photoshop Action *is* callable.

## Scripts

- `scripts/ps_bridge.py` - Core: `PhotoshopTCPClient` + `PhotoshopCOMBridge` + `PhotoshopAIBridge` (see/draw/modify/tool). Handles `PBKDF2+3DES` encryption, `__bridge_result` file回传, JSON polyfill, GBK->unicode.
- `scripts/test_connection.py` - Handshake + capture test
- `scripts/demo_agent.py` - 7-step see->draw->modify->tool loop (旧版，无强制校验)
- `scripts/verify_all.py` - Exhaustive 20-check 技术校验
- `scripts/verify_visual.py` - **视觉交付校验** (强制)：capture → vision checklist → PASS/FAIL + 自动重拍
- `scripts/agent_example.py` - Vision→decision→edit 单循环模板
- `scripts/enable_remote.ps1` - Check 49494 / hint
- `scripts/fix_photoshop_com.ps1` - HKCU CLSID fix + /Automation restart
- `scripts/run_jsx_com.ps1` - COM runner

## References

Load only when needed:
- `references/api_reference.md` - Full Python API (see/draw/modify/tool)
- `references/verify_loop.md` - **必读**：视觉检验 7项打分、修复→重拍循环
- `references/layers.md` - **必读**：一素材一图层命名/分组/可编辑交付规范
- `references/protocol.md` - TCP 49494 + PBKDF2+3DES + message format
- `references/com_direct.md` - COM diagnosis (`0x80080005`)
- `references/jsx_pitfalls.md` - No Chinese/Elps, selection, saveAs
- `references/drawing_patterns.md` - Prompt→primitives mapping + 分层绘制模板
- `references/plugin_extension.md` - C++ `PIFilter.h` FilterRecord for pixel-direct

## Assets

- `assets/bridge_core.jsx` - `bridgeGetDocumentInfo/listLayers/saveTempJpeg`
- `assets/drawing_primitives.jsx` - `rgb/fillRect/fillEllipse/fillPolygon/gradientBand/cloudCluster`
- `assets/tools_map.jsx` - 42 toolIDs + `bridgeSelectTool`
- `assets/example_scene.jsx` - Cyber-city 1920x1080 example

## Pitfalls

- **No Chinese in .jsx** - Use English, JSON polyfill escapes unicode to `\uXXXX`
- **No charID Elps** - Use polygon `fillEllipse` 32 segs
- **Background locked** - `transform` auto-unlocks `isBackgroundLayer=false`
- **Place not DOM** - Use `open+copy+paste` fallback for CS6
- **Save needs dir** - Python `Path.mkdir` before `saveAs`
- **COM needs 64-bit PowerShell** for HKCU, `cscript` for execution
- **跳过视觉检验** - 未 `capture_jpeg` + `Read` 即交付视为失败（踏雪寻梅压印）
- **单层扁平化** - 多素材挤在一层，后期无法单改；必须 `artLayers.add().name="TYPE_素材"`

## 强制交付标准 — 视觉+图层检验与迭代优化 (MANDATORY)

**每次 `draw`/`modify`/`tool`/`paste_image` 后必须：**

```python
from scripts.ps_bridge import PhotoshopAIBridge
b = PhotoshopAIBridge(use_com=True); b.connect()
# ... 每个素材前：b.execute_jsx('app.activeDocument.artLayers.add().name="MEI_bloom_01";')
# ... draw/modify ...
jpg = b.capture_jpeg(1200,900, save_path="out/cap.jpg")
layers = b.list_layers()  # 同步检分层
# 立刻 Read(cap) 看图 + 检查 layers 命名
```

检验清单（见 `references/verify_loop.md`）**7项**：

1. **遮挡** - 大字是否压住小字/印章（如 `踏雪寻梅` 压印，`PASS`需间距>40px）
2. **文字可读** - 书法/诗句完整、未截断
3. **构图** - 主体居中、留白合规
4. **色彩/水墨** - 雪地有层次、墨有浓淡
5. **完整性** - 梅花/枝干/亭篱完整在幅内
6. **分辨率** - 边缘清晰无锯齿
7. **分层** - **多素材一素材一图层**，`list_layers` 层数==素材数，命名为 `BG_/MEI_/TEXT_/SEAL_`

**循环：** `任一项 FAIL → 记录 → 定向修复 (仅动该层：改该层字号/平移该层/删重建该层) → 再 capture+list_layers → 再检验 → 直到 7项全 PASS`，3轮仍 FAIL 输出对比图请用户定夺。**禁止单层扁平交付。**

```powershell
# 技术校验（API通）
python scripts/verify_all.py        # expect 13 PASS
# 视觉交付校验（品质通）
python scripts/verify_visual.py --expect-title "踏雪寻梅"  # 自动 capture + checklist + 重拍
# 输出到系统临时目录 ps-ai-bridge/verify/ + cap.jpg
```

案例：见 `references/verify_loop.md` 末尾“踏雪寻梅压印”修复实录。
