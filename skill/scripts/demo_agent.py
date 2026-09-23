"""
demo_agent.py - AI Agent 完整演示：看图 → 画图 → 改图 → 全工具
用法:
  python demo_agent.py --host 127.0.0.1 --password 123456
  python demo_agent.py --use-com
"""
import argparse, os, sys, time
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent))
from ps_bridge import PhotoshopAIBridge

def main():
    ap = argparse.ArgumentParser(description="PS AI Bridge MVP Demo")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=49494)
    ap.add_argument("--password", default="123456")
    ap.add_argument("--use-com", action="store_true", help="强制 COM 模式（免远程连接）")
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "ps-ai-bridge"))
    args = ap.parse_args()

    Path(args.out).mkdir(parents=True, exist_ok=True)

    bridge = PhotoshopAIBridge(host=args.host, port=args.port, password=args.password, use_com=args.use_com, verbose=True)
    print(f"[1/7] Connect ({bridge.mode})...")
    print(bridge.connect())
    time.sleep(0.5)

    print("\n[2/7] 看图 - 文档信息")
    print(bridge.get_app_info())
    print(bridge.get_document_info())
    print("Documents:", bridge.list_documents())
    print("Layers:", bridge.list_layers()[:3])

    print("\n[3/7] 看图 - 捕获 JPEG")
    jpg = bridge.capture_jpeg(800,600, save_path=os.path.join(args.out, "capture_doc.jpg"))
    print(f"  captured {len(jpg)} bytes -> capture_doc.jpg")

    try:
        print("\n[4/7] 画图 - 新建文档 + 绘制图形")
        bridge.create_document(1024,768, name="AI_MVP_Canvas")
        bridge.draw_rect(50,50,400,200, fill_color=(255,80,80))
        bridge.draw_ellipse(500,400,180,120, fill_color=(80,160,255))
        bridge.draw_polygon([(700,100),(850,250),(750,400),(600,350)], fill_color=(80,220,120))
        bridge.save_document(os.path.join(args.out, "draw_result.jpg"))
        print("  draw done -> draw_result.jpg")
        time.sleep(0.5)
        jpg2 = bridge.capture_jpeg(800,600, save_path=os.path.join(args.out, "capture_after_draw.jpg"))
        print(f"  after draw capture {len(jpg2)} bytes")
    except Exception as e:
        print(f"  draw failed: {e}")

    print("\n[5/7] 改图 - 调整 + 滤镜")
    try:
        bridge.adjust_brightness_contrast(15,15)
        print("  brightness done")
        bridge.apply_blur(3)
        print("  blur done")
        bridge.transform_layer(scale_x=95, scale_y=95)
        print("  transform done")
        bridge.save_document(os.path.join(args.out, "after_modify.jpg"))
    except Exception as e:
        print(f"  modify failed: {e}")

    print("\n[6/7] 全工具 - 选择工具 + 执行任意 JSX/Action")
    print("  tools:", bridge.list_tools()[:5], "...")
    for tid in ["brushTool","eraserTool","gradientTool","moveTool"]:
        try:
            print(f"  select {tid}: {bridge.select_tool(tid)}")
            time.sleep(0.3)
        except Exception as e:
            print(f"  {tid} failed: {e}")
    # 任意 JSX
    print("  exec_jsx:", bridge.execute_jsx('return app.activeDocument.activeLayer.name;')[:200])
    # 任意 Action
    try: bridge.undo(); print("  undo sent")
    except: pass

    print("\n[7/7] 再次看图验证")
    final = bridge.capture_jpeg(800,600, save_path=os.path.join(args.out, "final.jpg"))
    print(f"  final {len(final)} bytes -> {args.out}/final.jpg")
    bridge.close()
    print("\nDone. Check output in", args.out)

if __name__ == "__main__":
    main()
