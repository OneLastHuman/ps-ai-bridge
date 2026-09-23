# ps-ai-bridge

English | [中文](README.zh-CN.md)

Bridge that lets AI agents **see · draw · modify · drive every tool** in Adobe Photoshop CS6/CC over Remote Connections (TCP) with a COM fallback.

```
Agent  ──►  python/ps_bridge.py  ──►  Photoshop
              TCP :49494  (PBKDF2 + 3DES)
              or COM      (no Remote Connections)
```

![Demo — Summer poster built by the bridge, one layer per element](docs/images/demo.jpg)

## Features

- **See** — app/document/layer info, JPEG thumbnails, pixmap, layer thumbnails
- **Draw** — create documents, rect/ellipse/polygon primitives, paste images
- **Modify** — brightness/contrast, hue/saturation, blur, transform, undo/redo
- **All tools** — select any of 42 tools, run arbitrary JSX, call any ActionManager event
- **Verify loop** — capture → vision checklist → layer check → fix → re-capture (mandatory before delivery)
- **One layer per element** — named layers (`BG_` / `MEI_` / `TEXT_` / `SEAL_`) for editable delivery

## Requirements

- Adobe Photoshop CS6 or CC (Windows)
- Python 3.8+
- Dependencies: `pip install -r python/requirements.txt`
  - `pycryptodome` (or `cryptography`) — protocol encryption
  - `Pillow` — image handling (optional)
  - `pywin32` — COM channel on Windows (optional)

## Quick Start

### Option A — Remote Connections (TCP)

1. In Photoshop: **Edit → Preferences → Remote Connections → Enable Remote Connections**, set a password (example below uses `123456` — replace with your own), restart Photoshop.
2. Connect:

```powershell
pip install -r python/requirements.txt
python python/test_connection.py --password 123456   # replace with your password
python python/demo_agent.py  --password 123456       # full see→draw→modify loop
python python/verify_all.py                          # exhaustive check
```

### Option B — COM fallback (no Remote Connections)

```powershell
python python/test_connection.py --use-com
python python/demo_agent.py --use-com
```

If COM fails with `0x80080005`, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fix_photoshop_com.ps1 -PhotoshopPath "C:\Path\To\Photoshop.exe"
```

Helper scripts:

| Script | Purpose |
|---|---|
| `scripts/enable_remote.ps1` | Check port 49494 / prompt to enable Remote Connections |
| `scripts/fix_photoshop_com.ps1` | HKCU COM registration fix (no admin) |
| `scripts/run_jsx_com.ps1` | Execute a `.jsx` file via COM |

## Repository layout

```
ps-ai-bridge/
├── python/          # Core bridge + demos + tests
│   ├── ps_bridge.py       # PhotoshopTCPClient + PhotoshopCOMBridge + PhotoshopAIBridge
│   ├── test_connection.py # Handshake + capture test
│   ├── demo_agent.py      # 7-step see→draw→modify→tool loop
│   ├── verify_all.py      # Exhaustive technical checks
│   ├── agent_example.py   # Vision→decision→edit template
│   └── requirements.txt
├── jsx/             # ExtendScript helpers (bridge core, drawing primitives, tools map)
├── scripts/         # PowerShell helpers (Remote Connections / COM)
├── docs/
│   ├── API.md             # Full Python API reference
│   └── images/demo.jpg    # Demo screenshot
├── plugin/          # Optional C++ filter-plugin skeleton (see plugin/README.md)
└── skill/           # Agent skill package (SKILL.md + references + assets + scripts)
    ├── SKILL.md
    ├── references/        # protocol, layers, verify loop, pitfalls, …
    ├── assets/            # JSX snippets bundled with the skill
    └── scripts/           # Mirrored copies for skill self-containment
```

## Documentation

- [`docs/API.md`](docs/API.md) — Python API (see / draw / modify / all tools)
- [`skill/SKILL.md`](skill/SKILL.md) — agent workflow, 7-step delivery checklist
- [`skill/references/protocol.md`](skill/references/protocol.md) — TCP frame format + encryption
- [`skill/references/layers.md`](skill/references/layers.md) — one-layer-per-element discipline
- [`skill/references/verify_loop.md`](skill/references/verify_loop.md) — mandatory visual verification
- [`skill/references/com_direct.md`](skill/references/com_direct.md) — COM diagnosis
- [`skill/references/jsx_pitfalls.md`](skill/references/jsx_pitfalls.md) — ExtendScript gotchas
- [`plugin/README.md`](plugin/README.md) — optional C++ pixel-level filter extension

## Minimal example

```python
from python.ps_bridge import PhotoshopAIBridge

b = PhotoshopAIBridge(password="123456")  # replace with your password
b.connect()

jpg = b.capture_jpeg(1024, 768, save_path="out/cap.jpg")  # see
b.create_document(1024, 768, "Canvas")
b.execute_jsx('app.activeDocument.artLayers.add().name="BG_sky";')
b.draw_rect(50, 50, 400, 200, (255, 80, 80))              # draw (own layer)
b.adjust_brightness_contrast(15, 15)                       # modify
b.select_tool("brushTool")                                 # any tool
layers = b.list_layers()                                   # verify layers
b.save_document("out/result.psd")
```

## Verification (mandatory before delivery)

```powershell
python python/verify_all.py                                # technical: API reachable
python skill/scripts/verify_visual.py --expect-title "My Title"  # visual + layer checklist
```

Never deliver without `capture_jpeg` + visual read + `list_layers` check.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

- This project is an independent reimplementation of the Photoshop Remote Connections protocol for automation. It is **not** affiliated with, endorsed by, or sponsored by Adobe.
- **Adobe Photoshop**, **Adobe**, and related marks are trademarks of Adobe. This project does not include Adobe software, the Adobe Photoshop SDK, or any Adobe proprietary code.
- The Adobe Photoshop SDK / Connection SDK is **not distributed** with this repository; obtain it directly from Adobe if you need it (e.g. for the optional C++ plugin skeleton under `plugin/`).
- You must own a licensed copy of Adobe Photoshop to use this software. Compliance with the Adobe license agreement is your responsibility.
- Example passwords (e.g. `123456`) in docs and demos are placeholders — set your own password in Photoshop Remote Connections and pass it via `--password`.
