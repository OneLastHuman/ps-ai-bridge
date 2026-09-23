# 视觉检验与迭代优化 - Verify Loop (必读)

> 目标：任何在 PS 中生成/修改的内容，**做完不等于完成**。必须经视觉检验打分并迭代至交付标准。

## 何时触发
- `draw`/`paste_image`/`create_document` 后
- `modify`/`adjust_*`/`transform` 后
- `tool`/`execute_jsx` 改变画面后
- 每次准备向用户交付前

## 标准流程 7 步（含分层检验）

```python
from scripts.ps_bridge import PhotoshopAIBridge
b = PhotoshopAIBridge(use_com=True); b.connect()

# 1. 执行绘制/修改（每个素材前先 newLayer 命名）
b.execute_jsx('app.activeDocument.artLayers.add().name="MEI_主枝";')
b.paste_image(r"C:\path\branch.png")

# 2. 强制截图 + 列层
cap = "out/cap_verify.jpg"
jpg = b.capture_jpeg(1200, 900, save_path=cap)
layers = b.list_layers()  # 同步检分层

# 3. 立刻 Read(cap) 看图 + 检查 layers 命名
# 4. 按下表 7项打分 → PASS/FAIL
# 5. 若 FAIL → 定向修复（只动 FAIL 层）→ 回到 2 重拍
# 6. 全 PASS → save_document(PSD保留分层 + JPG预览) + 交付
# 7. 附 layers 清单供用户复验
```

## 检验清单 7 项（每项 PASS/FAIL）

| # | 项 | 检查方法 | FAIL 典型 | 修复 |
|---|---|---|---|---|
| 1 | **遮挡** | 大字/大图形是否压住小字/印章/落款。量间距>40px | `踏雪寻梅` 压住 `踏雪` 印；诗句被山压 | 减小字号 92→78，印章下移 580→620，或换列 |
| 2 | **文字可读** | 诗句/题字/印文完整、未截断、未糊边 | 边缘截断、缺字、糊 | 调 `position`、换字体 `STXINGKA`→`STKAITI`、改 `size` |
| 3 | **构图** | 主体居中、留白合章法、天地留空 | 梅枝出框、雪地过满 | `translate`/`resize` 枝干起点 |
| 4 | **色彩/水墨** | 雪不过曝、墨有浓淡、雪地蓝灰阴影 | 雪地纯白无层次 | 加 `SNOW_SHADOW`、`brightness` 微调 |
| 5 | **完整性** | 梅花/亭篱/雀鸟完整在幅内 | 右枝出画布 | 重算 `sc` 或起点内移 |
| 6 | **清晰度** | 无锯齿、文字不发虚、quality 12 | `quality 8` 发虚 | `save quality=12` + 1800终验 |
| 7 | **分层** | `list_layers()` 层数==素材数，命名 `BG_/MEI_/TEXT_/SEAL_` 合规，无扁平 | 15素材仅2层、含 `图层 1` 默认名 | 拆 `paste_image` 为多图层或 `artLayers.add().name` 重建（见 `references/layers.md`） |

**判定：** 7项全 PASS 才能交付；任一 FAIL 必须 Optimize。

## Optimize 循环（最多 3 轮）

```
轮1: 捕获 → 视觉打分 → 标记 FAIL 项 + 原因
  ↓
  定向修复：仅改关联参数（例：遮挡→只动字号/印章位，不动全图）
  ↓
轮2: 重 capture → 再打分 → 仍 FAIL？
  ↓
轮3: 换策略（例：字号已最小则移印章列）
  ↓
仍 FAIL → 输出 前/后对比图 + 差异说明，请用户定夺，不强行交付
```

- 每轮必须 `capture_jpeg(save_path)` 并 `Read` 新图，不可用旧图推测。
- 每次修复后写日志：`原因 → 动作 → 新 capture 路径`。

## 常用修复映射

- **标题压印** → `title font 92→78, spacing 105→92, seal y 580→620`（本 skill 实录，见下）
- **诗句被截** → `xl 95→110` 或字号 42→36
- **梅枝出框** → `trunk_pts` 起点 `W-90→W-120` 或 `layer.resize(sc*0.92)`
- **雪地过曝** → 雪地多边形 alpha 70→45，或叠 `SNOW_SHADOW`

## 反模式

- ❌ `save_document` 后直接交付，不做 `capture_jpeg` + `Read` + `list_layers`
- ❌ 用 `get_document_info()` 数值推断画面正确
- ❌ 一次改多个无关层（难以追溯）
- ❌ 低分 600px 冒充 1200px 终验
- ❌ 单层扁平交付 PSD（实为 JPEG 换扩展名）

## 实录 1：踏雪寻梅压印修复（视觉）

- **现象：** `winter_capture2.jpg` 矢量 `踏雪寻梅` `1593,20-1771,976` 压住 `寒梅` 印
- **检验：** 7项 → 遮挡 FAIL、分层 FAIL（多余矢量层命名混乱）
- **修复：** 删脏层，重生成 `title 踏雪寻梅 font78 spacing92 seal620`，重建
- **重验：** `winter_fixed_capture.jpg` 视觉 6项 PASS，分层仍 2层扁平 → 触发实录2

## 实录 2：扁平化分层修复

- **现象：** `winter_fixed_capture.jpg` 虽视觉 PASS，但 `list_layers()` 仅2层（`图层1` 含全部梅枝+花+雪），违反一素材一图层
- **检验：** 分层 FAIL
- **修复：** 按 `references/layers.md` 将 `winter_meihua.py` 拆为 15层分素材贴图：`BG_宣纸/.../MEI_主枝/.../TEXT_标题/.../SEAL_踏雪`，每素材前 `artLayers.add().name`
- **重验：** `list_layers()` 15层命名合规，单改 `MEI_花簇_右` 颜色验证不影响他层，最终交付 PSD 保留分层 + JPG 预览

## 工具

- `scripts/verify_visual.py` 提供自动 capture + 交互式 checklist（命令行回车打分），见该文件头注释。

