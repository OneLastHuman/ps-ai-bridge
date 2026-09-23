"""
verify_visual.py - 视觉+图层交付校验（强制）
用途：任何 draw/modify 后，自动截图+列层，7项检验，支持循环重拍。

用法：
  python scripts/verify_visual.py --cap WxH --out "C:/Temp/cap.jpg"
  python scripts/verify_visual.py --expect-title "踏雪寻梅"
  python scripts/verify_visual.py --no-interactive  # 仅截图，留待 Read看图

流程：
  1. 连接 PS (COM 优先)
  2. capture_jpeg + list_layers
  3. 打印 7项清单（含分层），终端 y/n 打分或 Read看图
  4. FAIL 项定向修复后可一键重拍

输出：
  系统临时目录 ps-ai-bridge/verify_visual/
"""
import argparse, sys, os, time, json
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent))
from ps_bridge import PhotoshopAIBridge

OUT_DIR = Path(tempfile.gettempdir()) / "ps-ai-bridge" / "verify_visual"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHECKLIST = [
    ("遮挡", "大字是否压住小字/印章，间距>40px（例：踏雪寻梅压印）"),
    ("文字可读", "题字/诗句/印文完整、未截断、未糊"),
    ("构图", "主体居中、留白合规、天地不过压"),
    ("色彩/水墨", "雪地有层次、墨色有浓淡、不过曝"),
    ("完整性", "梅枝/花/亭篱/雀鸟完整在幅内"),
    ("清晰度", "边缘无锯齿、保存质量高"),
    ("分层", "一素材一图层：list_layers 层数==素材数，命名 BG_/MEI_/TEXT_/SEAL_ 合规，无单层扁平"),
]

def parse_args():
    p = argparse.ArgumentParser(description="视觉校验")
    p.add_argument("--cap", default="1200x900", help="截图尺寸 WxH")
    p.add_argument("--out", default=str(OUT_DIR / "verify_cap.jpg"), help="截图保存路径")
    p.add_argument("--expect-title", default="", help="期望标题（仅记录）")
    p.add_argument("--use-com", action="store_true", default=True, help="强制 COM")
    p.add_argument("--no-interactive", action="store_true", help="非交互，自动标记需人工看图")
    return p.parse_args()

def main():
    args = parse_args()
    w,h = map(int, args.cap.lower().split("x"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    bridge = PhotoshopAIBridge(use_com=True)
    print("[connect]", bridge.connect())
    info = bridge.get_document_info()
    print("[doc]", info)
    layers = bridge.list_layers()
    print(f"[layers] {len(layers)} layers:")
    for l in layers:
        print(f"  - {l.get('name')} ({l.get('kind')}) opacity={l.get('opacity')}")

    # capture
    print(f"[capture] {w}x{h} -> {out}")
    jpg = bridge.capture_jpeg(w, h, save_path=str(out))
    print(f"[captured] {len(jpg)} bytes")

    # 高清终验也拍一张
    full = OUT_DIR / "full_1800.jpg"
    try:
        bridge.capture_jpeg(1800, 1350, save_path=str(full))
        print(f"[full] {full} {full.stat().st_size} bytes")
    except Exception as e:
        print("[full fail]", e)

    # checklist 交互
    print("\n=== 视觉+图层检验 7项 (y=PASS, n=FAIL, 回车=待定) ===")
    if args.expect_title:
        print(f"期望标题: {args.expect_title}")
    print(f"请用 Read 工具打开 {out} 进行视觉检验，或在终端逐项输入：\n")

    results = {}
    if args.no_interactive:
        for name, desc in CHECKLIST:
            results[name] = "PENDING"
            print(f"[PENDING] {name}: {desc} -> 请用 Read({out}) 看图后补打分")
    else:
        for name, desc in CHECKLIST:
            try:
                ans = input(f"{name} - {desc} [y/n/enter]: ").strip().lower()
            except EOFError:
                ans = ""
            if ans == "y":
                results[name] = "PASS"
            elif ans == "n":
                results[name] = "FAIL"
            else:
                results[name] = "PENDING"
            print(f"  -> {name}: {results[name]}")

    # summary
    print("\n=== 汇总 ===")
    for k,v in results.items():
        print(f"  {k}: {v}")
    fails = [k for k,v in results.items() if v=="FAIL"]
    pending = [k for k,v in results.items() if v=="PENDING"]
    if fails:
        print(f"\n[FAIL] 需修复: {', '.join(fails)}")
        print("修复建议见 references/verify_loop.md -> 定向修复后重跑本脚本")
        # 可选：自动重拍提示
        try:
            if input("是否现在重拍一次对比? [y/N]: ").lower()=="y":
                out2 = OUT_DIR / "verify_cap_retry.jpg"
                jpg2 = bridge.capture_jpeg(w,h, save_path=str(out2))
                print(f"[retry] {out2} {len(jpg2)} bytes")
        except: pass
    elif pending:
        print("\n[PENDING] 存在待定项，请用 Read 看图 + list_layers 检查分层后补判定，禁止未看图/未查层交付")
    else:
        print("\n[PASS] 7项全 PASS，可 save_document(PSD保留分层 + JPG预览) 交付")
        # 提示保存
        save_path = OUT_DIR / "delivery.jpg"
        print(f"建议执行: bridge.save_document('{save_path}', quality=12)")

    # 记录 json
    log = OUT_DIR / "verify_log.json"
    with open(log, "w", encoding="utf-8") as f:
        json.dump({"doc": info, "layers": layers, "cap": str(out), "size": len(jpg), "results": results}, f, ensure_ascii=False, indent=2)
    print(f"[log] {log}")

    bridge.close()

if __name__ == "__main__":
    main()
