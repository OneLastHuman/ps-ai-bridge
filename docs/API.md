# API 手册 - ps_bridge.py

## PhotoshopAIBridge 统一入口
```python
from ps_bridge import PhotoshopAIBridge
bridge = PhotoshopAIBridge(host="127.0.0.1", port=49494, password="123456", use_com=False)
bridge.connect()
```

`use_com=True` 强制走 COM（适用于未开启远程连接时）。

---

### 看图 See
| 方法 | 说明 | 返回 |
|---|---|---|
| `get_app_info()` | `app.name/version/docCount` | `dict` |
| `list_documents()` | 所有打开文档 | `list[dict]` |
| `get_document_info()` | 当前文档宽高/分辨率/图层数 | `dict` |
| `list_layers()` | 扁平/递归图层列表 | `list[dict]` |
| `capture_jpeg(w,h,save_path)` | `sendDocumentThumbnailToNetworkClient` JPEG | `bytes` |
| `capture_layer_thumbnail(save_path,w,h,selected_only)` | `sendLayerThumbnailToNetworkClient` 图层级 | `bytes` |
| `capture_pixmap(w,h)` (TCP) | Pixmap raw RGB | `(w,h,bytes)` |

示例：
```python
jpg = bridge.capture_jpeg(1024,768, save_path="out/cap.jpg")
open("cap.jpg","wb").write(jpg)
```

### 画图 Draw
| 方法 | 说明 |
|---|---|
| `create_document(w,h,name,res,fill)` | 新建文档 |
| `draw_rect(x,y,w,h,color)` | 选区填充矩形 |
| `draw_ellipse(cx,cy,rx,ry,color)` | 32边多边形逼近（避 Elps 坑） |
| `draw_polygon(points,color)` | 任意多边形 |
| `paste_image(path_or_bytes)` | `place` 到当前文档 |
| `send_image_as_new_document(path)` | TCP `IMAGE_TYPE` 新建文档 |
| `generate_from_prompt(prompt)` | 占位：可接 SD/MJ 再 paste |

### 改图 Modify
| 方法 | 说明 |
|---|---|
| `adjust_brightness_contrast(b,c)` | `brightnessEvent` |
| `adjust_hue_saturation(h,s,l)` | `hueSaturation` |
| `apply_blur(radius)` | `gaussianBlur` |
| `transform_layer(sx,sy,angle)` | `transform` |
| `save_document(path, as_jpeg)` | `JPEGSaveOptions` |
| `undo()/redo()` | `undo` |

### 全工具 All Tools
| 方法 | 说明 |
|---|---|
| `select_tool(toolID)` | 任意工具，见 `list_tools()` |
| `execute_jsx(code)` | 任意 JSX DOM |
| `execute_action(stringID)` | 任意 ActionManager `stringIDToTypeID` |
| `list_tools()` | 60+ 工具 ID |

```python
bridge.select_tool("brushTool")
bridge.execute_jsx('app.activeDocument.activeLayer.opacity=50;')
bridge.execute_action("cut")
```

### 底层 TCP
`PhotoshopTCPClient` 直接对应 `PhotoshopProtocol.java:80`：
- `exec_jsx(code)` → `JAVASCRIPT_TYPE=2`
- `capture_jpeg()` → `sendDocumentThumbnailToNetworkClient`
- `send_image_jpeg(bytes)` → `IMAGE_TYPE=3`
- `subscribe_event("documentChanged")` → `networkEventSubscribe`

加密：`derive_key()` PBKDF2-HMAC-SHA1 salt=`Adobe Photoshop` iter=1000 key24 + 3DES/CBC/PKCS5 IV0，对应 `PSCryptor.cpp:379`。

### 事件
可订阅：`foregroundColorChanged/backgroundColorChanged/toolChanged/closedDocument/newDocumentViewCreated/currentDocumentChanged/documentChanged/activeViewChanged` 等（`howDoesItWork.html:133`）。

