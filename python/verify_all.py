"""
verify_all.py - 完整功能验证：看图/画图/改图/全工具
要求：PS CS6 已启动，COM 可用
输出：系统临时目录 ps-ai-bridge/verify/
"""
import sys, os, time, json
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent))
from ps_bridge import PhotoshopAIBridge

OUT = Path(tempfile.gettempdir()) / "ps-ai-bridge" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

def check(name, fn):
    try:
        r=fn()
        print(f"[PASS] {name}: {str(r)[:120]}")
        return True, r
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        import traceback; traceback.print_exc()
        return False, str(e)

bridge = PhotoshopAIBridge(use_com=True, verbose=False)
print("=== Connect ===")
print(bridge.connect())
# 清理
bridge.execute_jsx('while(app.documents.length>0) app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); "cleaned";')
time.sleep(0.5)

results = {}

# 1 看图
print("\n=== 1 看图 ===")
check("get_app_info", lambda: bridge.get_app_info())
check("list_documents empty", lambda: bridge.list_documents())
# 创建一个文档供后续
check("create_document 800x600", lambda: bridge.create_document(800,600,"Verify_All"))
time.sleep(0.5)
check("get_document_info", lambda: bridge.get_document_info())
check("list_documents after", lambda: bridge.list_documents())
check("list_layers", lambda: bridge.list_layers())
# 捕获
def cap():
    data=bridge.capture_jpeg(600,400, save_path=str(OUT/"01_capture.jpg"))
    assert len(data)>1000, "capture too small"
    return f"{len(data)} bytes"
check("capture_jpeg", cap)
check("capture exists", lambda: os.path.exists(OUT/"01_capture.jpg"))

# 2 画图
print("\n=== 2 画图 ===")
check("draw_rect", lambda: bridge.draw_rect(20,20,150,80, (255,0,0)))
check("draw_ellipse", lambda: bridge.draw_ellipse(400,200,60,40, (0,255,0)))
check("draw_polygon", lambda: bridge.draw_polygon([(500,300),(600,350),(550,450),(480,380)], (0,120,255)))
# 保存画图结果
check("save draw", lambda: bridge.save_document(str(OUT/"02_draw.jpg")))
check("capture after draw", lambda: f"{len(bridge.capture_jpeg(600,400, save_path=str(OUT/'02_capture_after_draw.jpg')))} bytes")

# 测试 paste_image：先创建一个临时图片再粘贴
from PIL import Image
tmp_img = OUT/"tmp_paste.png"
img = Image.new("RGB",(100,100),(255,200,0))
# 在图片上画点
from PIL import ImageDraw
d=ImageDraw.Draw(img); d.ellipse([10,10,90,90], fill=(0,100,255))
img.save(tmp_img)
check("paste_image", lambda: bridge.paste_image(str(tmp_img)))
check("save after paste", lambda: bridge.save_document(str(OUT/"03_paste.jpg")))

# 3 改图
print("\n=== 3 改图 ===")
check("brightness", lambda: bridge.adjust_brightness_contrast(10,10))
check("hue", lambda: bridge.adjust_hue_saturation(5,10,0))
check("blur", lambda: bridge.apply_blur(2))
check("transform", lambda: bridge.transform_layer(90,90,5))
check("save after modify", lambda: bridge.save_document(str(OUT/"04_modify.jpg")))
check("capture after modify", lambda: f"{len(bridge.capture_jpeg(600,400, save_path=str(OUT/'04_capture_after_modify.jpg')))} bytes")

# 4 全工具
print("\n=== 4 全工具 ===")
check("list_tools", lambda: bridge.list_tools())
for tid in ["moveTool","brushTool","eraserTool","gradientTool","penTool","textTool","handTool","zoomTool"]:
    check(f"select_tool {tid}", lambda tid=tid: bridge.select_tool(tid))
    time.sleep(0.2)

check("execute_jsx return", lambda: bridge.execute_jsx('return app.activeDocument.name;'))
check("execute_jsx set opacity", lambda: bridge.execute_jsx('app.activeDocument.activeLayer.opacity=80; return app.activeDocument.activeLayer.opacity;'))
check("execute_action undo", lambda: bridge.undo())
time.sleep(0.5)
check("execute_action redo", lambda: bridge.redo())

# 5 综合：AI 风格生成 - 使用 drawing_primitives via JSX
print("\n=== 5 综合：任意图 ===")
# 用 bridge.execute_jsx 直接跑 example_scene 的部分
jsx_scene = '''
var doc=app.activeDocument;
var c=new SolidColor(); c.rgb.red=30; c.rgb.green=30; c.rgb.blue=60;
doc.selection.select([[0,0],[800,0],[800,200],[0,200]]);
doc.selection.fill(c); doc.selection.deselect();
"scene done";
'''
check("custom scene jsx", lambda: bridge.execute_jsx(jsx_scene))
check("final capture", lambda: f"{len(bridge.capture_jpeg(600,400, save_path=str(OUT/'05_final.jpg')))} bytes")
check("final save psd", lambda: bridge.save_document(str(OUT/"05_final.psd"), as_jpeg=False))

# 汇总
print("\n=== 汇总 ===")
files = list(OUT.glob("*"))
for f in sorted(files):
    print(f"  {f.name}: {f.stat().st_size} bytes")

# 清理：关闭但不保存？保留
# bridge.execute_jsx('while(app.documents.length>0) app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);')

bridge.close()
print("\nAll verify done. Check", OUT)
