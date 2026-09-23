"""
agent_example.py - AI Agent 集成范例
展示：多模态 Agent 如何“看图”后决策，再“画图/改图”

场景：Agent 收到用户说“把画面调得更温暖，加个光斑”
1. 看图 capture_jpeg -> 给视觉模型
2. 画图 draw_ellipse 光斑
3. 改图 adjust_hue_saturation 暖色
"""
import sys
from pathlib import Path
import tempfile
sys.path.insert(0, str(Path(__file__).parent))
from ps_bridge import PhotoshopAIBridge
import os, tempfile

# 初始化（自动选 TCP 或 COM）
bridge = PhotoshopAIBridge(password="123456", verbose=True)
bridge.connect()

# 1. 看图 - 供 Agent 视觉输入
print("=== 看图 ===")
info = bridge.get_document_info()
print(info)
jpg_bytes = bridge.capture_jpeg(1024,768)
# 这里 jpg_bytes 可直接喂给 GPT-4V / Qwen-VL 等
# vision_model.describe(jpg_bytes) -> "画面偏冷，主体在中央..."
out_dir = Path(tempfile.gettempdir()) / "ps-ai-bridge"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "agent_see.jpg").write_bytes(jpg_bytes)
print(f"已保存视野 {len(jpg_bytes)} bytes")

# 2. Agent 决策后：画图 - 加光斑（暖光）
print("\n=== 画图：加光斑 ===")
# 模拟 Agent 输出：{"action":"draw_ellipse","cx":800,"cy":300,"rx":120,"ry":120,"color":[255,200,80]}
bridge.draw_ellipse(800,300,120,120, fill_color=(255,200,80))
bridge.draw_ellipse(800,300,80,80, fill_color=(255,240,180))
print("光斑已绘制")

# 3. 改图 - 调暖色
print("\n=== 改图：暖色滤镜 ===")
bridge.adjust_hue_saturation(hue=5, saturation=15, lightness=5)
bridge.apply_blur(1)  # 轻微柔化
print("暖色调整完成")

# 4. 全工具 - 切换画笔再微调
print("\n=== 全工具 ===")
bridge.select_tool("brushTool")
# 任意 JSX：把当前图层不透明度设为 90%
bridge.execute_jsx('app.activeDocument.activeLayer.opacity=90; "opacity 90";')

# 5. 再看图验证闭环
print("\n=== 验证 ===")
final = bridge.capture_jpeg(1024,768, save_path=str(out_dir / "agent_final.jpg"))
print(f"最终画面 {len(final)} bytes")
bridge.save_document(str(out_dir / "agent_final.psd"), as_jpeg=False)
bridge.close()
print("Agent 闭环完成")
