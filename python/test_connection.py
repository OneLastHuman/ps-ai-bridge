"""test_connection.py - 连通性自检"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ps_bridge import PhotoshopTCPClient, PhotoshopAIBridge

def test_tcp(host, port, password):
    print(f"Testing TCP {host}:{port} password='{password}'")
    c = PhotoshopTCPClient(host, port, password, timeout=5)
    try:
        c.connect()
        print("  [OK] TCP handshake")
        r = c.exec_jsx('app.name + " " + app.version;')
        print(f"  [OK] exec_jsx -> {r.strip()}")
        jpg = c.capture_jpeg(400,300)
        print(f"  [OK] capture_jpeg {len(jpg)} bytes")
        # 事件订阅
        r2 = c.subscribe_event("documentChanged")
        print(f"  [OK] subscribe documentChanged -> {r2.strip()[:80]}")
        c.close()
        print("TCP all passed")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback; traceback.print_exc()
        try: c.close()
        except: pass
        return False

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=49494)
    ap.add_argument("--password", default="123456")
    ap.add_argument("--use-com", action="store_true")
    args=ap.parse_args()
    if args.use_com:
        b=PhotoshopAIBridge(use_com=True)
        print(b.connect())
        print(b.get_app_info())
        print("COM OK")
    else:
        ok=test_tcp(args.host, args.port, args.password)
        if not ok:
            print("\nHint: 编辑 > 远程连接 > 启用远程连接 > 设密码，或用 --use-com 回落")
            print("Also check firewall and Photoshop is running.")
