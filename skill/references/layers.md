# 一素材一图层 - Layer Discipline (必读)

> 后期要改某一个素材（如只改梅花颜色/只移印章），若所有素材在同一图层则需重画全图。**多素材必须一素材一图层**是可编辑交付的铁规。

## 命名规范

- `BG_远山` `BG_中景山` `BG_雪地` `BG_天空` `BG_宣纸` — 背景类
- `MEI_主枝` `MEI_分枝1` `MEI_花簇_右上` `MEI_花苞` `MEI_雪` — 梅相关
- `SCENE_亭` `SCENE_竹篱` `SCENE_奇石` `BIRD_喜鹊` `FX_落雪` — 场景/特效
- `TEXT_标题_踏雪寻梅` `TEXT_诗_墙角数枝` `TEXT_落款` — 文字（需为可编辑 TEXT 图层，而非栅格）
- `SEAL_踏雪` `SEAL_寻梅` `SEAL_暗香` — 印章
- 组：`MGT_梅枝组` `MGT_文字组`（可选 `LayerSet`）

## 创建模板（JSX）

```js
// 新建空白图层并命名，再绘制（CS6兼容）
function newLayer(name){
  var l = app.activeDocument.artLayers.add();
  l.name = name;
  l.kind = LayerKind.NORMAL;
  return l;
}
newLayer("MEI_主枝");
// 接着 draw_rect/ellipse/polygon 的 selection.fill 会落在此层
```

`paste_image` 后自动成新层，需立刻重命名：
```python
b.paste_image("branch.png")
b.execute_jsx('app.activeDocument.activeLayer.name="MEI_主枝";')
```

文字层必须是 `LayerKind.TEXT`：
```js
var l = app.activeDocument.artLayers.add();
l.kind = LayerKind.TEXT;
l.name = "TEXT_标题_踏雪寻梅";
l.textItem.contents = "踏雪寻梅";
l.textItem.font = "STXingkai";
```

## 检验

```python
layers = b.list_layers()  # [{name, visible, opacity, kind}, ...]
# 要求：
# - len(layers) == 素材数（本例冬梅约 12-15 层）
# - 无 "图层 1" 默认名，全部按规范命名
# - 无单层包含 >2 类素材（例：梅枝+花在一层 FAIL）
```

在 `verify_visual.py` 与 `verify_loop.md` 中，**分层** 为第7项，未达标不得交付 PSD。

## 分层实录 - 冬雪梅花重构

- **错误版：** `paste_image(single.jpg)` → 2层扁平化（`图层1` 含全部梅枝+花+雪+亭），改一朵花需重贴全图
- **正确版：** 拆素材分图层粘贴或分步绘制
  ```
  BG_宣纸 / BG_天空 / BG_远山 / BG_雪地
  SCENE_亭 / SCENE_竹篱 / SCENE_奇石
  MEI_主枝 / MEI_分枝_左 / MEI_花簇_右 / MEI_花簇_左 / MEI_花苞 / MEI_鸟 / FX_落雪
  TEXT_标题_踏雪寻梅 / TEXT_诗 / TEXT_落款
  SEAL_踏雪 / SEAL_寻梅 / SEAL_暗香
  ```
  → 15层，改 `MEI_花簇_右` 颜色只需选中该层 `adjust_hue_saturation`，其余不动。`capture_layer_thumbnail` 可单层验。

## 禁忌

- ❌ 一个 `execute_jsx` 里画完全部素材不换层
- ❌ `save_document(as_jpeg=True)` 交付 JPEG 代替 PSD（丢失分层）
- ❌ 层名 `图层 1` `副本` 未重命名（交付前必改）

最终交付必须同时给 `JPG(平面预览)` + `PSD(分层可编辑)`，并在 `list_layers()` 截图中证明层数与命名合格。
