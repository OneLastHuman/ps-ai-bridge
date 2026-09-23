# ps-ai-bridge

[English](README.md) | 中文

让 AI Agent 通过 Remote Connections（TCP）+ COM 备用通道，在 Adobe Photoshop CS6/CC 里**看图 · 画图 · 改图 · 驱动所有工具**的桥接器。

```
Agent  ──►  python/ps_bridge.py  ──►  Photoshop
              TCP :49494  (PBKDF2 + 3DES)
              或 COM      （未开启远程连接时备用）
```

![演示 — 用本桥接制作的夏日海报，一素材一图层](docs/images/demo.jpg)

## 功能

- **看图** — 应用/文档/图层信息、JPEG 缩略图、pixmap、图层缩略图
- **画图** — 新建文档、矩形/椭圆/多边形图元、粘贴外部图片
- **改图** — 亮度/对比度、色相/饱和度、模糊、变换、撤销/重做
- **全工具** — 任选 42 种工具、执行任意 JSX、调用任意 ActionManager 事件
- **校验循环** — 截图 → 视觉清单 → 图层检查 → 修复 → 重拍（交付前强制执行）
- **一素材一图层** — 命名图层（`BG_` / `MEI_` / `TEXT_` / `SEAL_`），交付可编辑 PSD

## 环境要求

- Adobe Photoshop CS6 或 CC（Windows）
- Python 3.8+
- 依赖：`pip install -r python/requirements.txt`
  - `pycryptodome`（或 `cryptography`）— 协议加密
  - `Pillow` — 图像处理（可选）
  - `pywin32` — Windows 下 COM 通道（可选）

## 快速开始

### 方案 A — 远程连接（TCP）

1. 在 Photoshop 中：**编辑 → 首选项 → 远程连接 → 勾选启用远程连接**，设置密码（下面示例用 `123456`，请换成你自己的），重启 Photoshop。
2. 连接：

```powershell
pip install -r python/requirements.txt
python python/test_connection.py --password 123456   # 换成你的密码
python python/demo_agent.py  --password 123456       # 完整 看→画→改 循环
python python/verify_all.py                          # 全面检查
```

### 方案 B — COM 备用通道（未开启远程连接时）

```powershell
python python/test_connection.py --use-com
python python/demo_agent.py --use-com
```

如果 COM 报错 `0x80080005`，执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/fix_photoshop_com.ps1 -PhotoshopPath "C:\Path\To\Photoshop.exe"
```

辅助脚本：

| 脚本 | 用途 |
|---|---|
| `scripts/enable_remote.ps1` | 检查 49494 端口 / 提示开启远程连接 |
| `scripts/fix_photoshop_com.ps1` | HKCU COM 注册修复（无需管理员） |
| `scripts/run_jsx_com.ps1` | 通过 COM 执行 `.jsx` 文件 |

## 仓库结构

```
ps-ai-bridge/
├── python/          # 核心桥接 + 演示 + 测试
│   ├── ps_bridge.py       # PhotoshopTCPClient + PhotoshopCOMBridge + PhotoshopAIBridge
│   ├── test_connection.py # 握手 + 截图测试
│   ├── demo_agent.py      # 7 步 看→画→改→工具 循环
│   ├── verify_all.py      # 全面技术检查
│   ├── agent_example.py   # 视觉→决策→编辑 模板
│   └── requirements.txt
├── jsx/             # ExtendScript 辅助脚本（桥接核心、绘图图元、工具映射）
├── scripts/         # PowerShell 辅助脚本（远程连接 / COM）
├── docs/
│   ├── API.md             # Python API 全参考
│   └── images/demo.jpg    # 演示截图
├── plugin/          # 可选 C++ 滤镜插件骨架（见 plugin/README.md）
└── skill/           # Agent skill 包（SKILL.md + references + assets + scripts）
    ├── SKILL.md
    ├── references/        # 协议、分层、校验循环、避坑、……
    ├── assets/            # skill 自带 JSX 片段
    └── scripts/           # skill 自包含镜像脚本
```

## 文档

- [`docs/API.md`](docs/API.md) — Python API（看 / 画 / 改 / 全工具）
- [`skill/SKILL.md`](skill/SKILL.md) — Agent 工作流、7 步交付清单
- [`skill/references/protocol.md`](skill/references/protocol.md) — TCP 帧格式 + 加密
- [`skill/references/layers.md`](skill/references/layers.md) — 一素材一图层规范
- [`skill/references/verify_loop.md`](skill/references/verify_loop.md) — 强制视觉校验
- [`skill/references/com_direct.md`](skill/references/com_direct.md) — COM 诊断
- [`skill/references/jsx_pitfalls.md`](skill/references/jsx_pitfalls.md) — ExtendScript 避坑
- [`plugin/README.md`](plugin/README.md) — 可选 C++ 像素级滤镜扩展

## 最小示例

```python
from python.ps_bridge import PhotoshopAIBridge

b = PhotoshopAIBridge(password="123456")  # 换成你的密码
b.connect()

jpg = b.capture_jpeg(1024, 768, save_path="out/cap.jpg")  # 看图
b.create_document(1024, 768, "Canvas")
b.execute_jsx('app.activeDocument.artLayers.add().name="BG_sky";')
b.draw_rect(50, 50, 400, 200, (255, 80, 80))              # 画图（独立图层）
b.adjust_brightness_contrast(15, 15)                       # 改图
b.select_tool("brushTool")                                 # 任选工具
layers = b.list_layers()                                   # 校验图层
b.save_document("out/result.psd")
```

## 校验（交付前强制执行）

```powershell
python python/verify_all.py                                # 技术校验：API 可达
python skill/scripts/verify_visual.py --expect-title "My Title"  # 视觉 + 图层清单
```

没有 `capture_jpeg` + 肉眼看图 + `list_layers` 检查，一律不算交付。

## 开源协议

MIT — 见 [LICENSE](LICENSE)。

## 免责声明

- 本项目是 Photoshop 远程连接协议的独立重实现，用于自动化，与 Adobe 无任何关联、无背书、无赞助。
- **Adobe Photoshop**、**Adobe** 及相关标志均为 Adobe 商标。本项目不包含 Adobe 软件、Adobe Photoshop SDK 或任何 Adobe 专有代码。
- Adobe Photoshop SDK / Connection SDK **不随本仓库分发**；如需（例如 `plugin/` 下可选 C++ 插件骨架），请自行从 Adobe 获取。
- 使用本软件需要你拥有正版 Adobe Photoshop 授权，遵守 Adobe 许可协议是你的责任。
- 文档和演示中的示例密码（如 `123456`）均为占位符，请在 Photoshop 远程连接中设置自己的密码，并通过 `--password` 传入。
