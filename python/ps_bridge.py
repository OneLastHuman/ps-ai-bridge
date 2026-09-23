"""
PS AI Bridge MVP - python/ps_bridge.py
Python 实现 Adobe Photoshop Remote Connections 协议 + COM 备用通道
- 看图：capture / list_documents / get_layer_info
- 画图：create_document / draw_primitives / paste_image
- 改图：adjust / filter / transform
- 全工具：select_tool / execute_jsx / execute_action

协议参考（SDK 不随本仓库分发，请自行从 Adobe 获取 Photoshop Connection SDK 文档）：
  Remote Connections "how it works" / 消息帧格式 / PSCryptor 加密参数
"""

import hashlib
import socket
import struct
import time
import json
import os
import sys
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ─────────────────────────────────────────────
# 1. PSCryptor - PBKDF2 + 3DES/CBC/PKCS5 (IV=0)
# 对应 PSCryptor.cpp:379 DeriveKey + EncryptDecrypt
# salt="Adobe Photoshop", iterations=1000, keyLen=24, alg=DESede/CBC/PKCS5
# ─────────────────────────────────────────────

SALT = b"Adobe Photoshop"
ITERATIONS = 1000
KEY_LEN = 24
BLOCK_SIZE = 8  # 3DES block

def derive_key(password: str) -> bytes:
    """PBKDF2-HMAC-SHA1 对应 PBKeyDerive.cpp:276 pkcs5_pbkdf2"""
    # 特殊调试密钥 Swordfish（保留兼容）
    if password == "Swordfish":
        return bytes([0xe4,0x4a,0x93,0xc0,0x4d,0x79,0xbf,0x2e,0x93,0x71,0x91,0xa6,0x3d,0xbd,0xde,0x05,0xbb,0x15,0xc2,0x01,0x14,0x98,0xe1,0xfb])
    return hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'), SALT, ITERATIONS, dklen=KEY_LEN)


def _get_cipher(key: bytes, encrypt: bool):
    """自动探测 pycryptodome / cryptography"""
    # 尝试 pycryptodome
    try:
        from Crypto.Cipher import DES3
        from Crypto.Util.Padding import pad, unpad
        iv = b"\x00" * 8
        # 3DES 要求 key parity，可自动调整
        try:
            cipher = DES3.new(key, DES3.MODE_CBC, iv)
        except ValueError:
            # 调整 parity
            from Crypto.Cipher.DES3 import adjust_key_parity
            key = adjust_key_parity(key)
            cipher = DES3.new(key, DES3.MODE_CBC, iv)
        return ("pycryptodome", cipher, pad, unpad)
    except ImportError:
        pass
    # 尝试 cryptography
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        iv = b"\x00" * 8
        alg = algorithms.TripleDES(key)
        mode = modes.CBC(iv)
        cipher = Cipher(alg, mode, backend=default_backend())
        return ("cryptography", cipher, None, None)
    except ImportError:
        raise RuntimeError("Need pycryptodome or cryptography: pip install pycryptodome")

def encrypt_payload(plain: bytes, key: bytes) -> bytes:
    kind, cipher, pad, _ = _get_cipher(key, True)
    if kind == "pycryptodome":
        padded = pad(plain, BLOCK_SIZE)
        return cipher.encrypt(padded)
    else:
        from cryptography.hazmat.primitives import padding
        padder = padding.PKCS7(64).padder()
        padded = padder.update(plain) + padder.finalize()
        encryptor = cipher.encryptor()
        return encryptor.update(padded) + encryptor.finalize()

def decrypt_payload(cipher_bytes: bytes, key: bytes) -> bytes:
    kind, cipher, _, unpad = _get_cipher(key, False)
    if kind == "pycryptodome":
        plain_padded = cipher.decrypt(cipher_bytes)
        return unpad(plain_padded, BLOCK_SIZE)
    else:
        from cryptography.hazmat.primitives import padding
        decryptor = cipher.decryptor()
        padded = decryptor.update(cipher_bytes) + decryptor.finalize()
        unpadder = padding.PKCS7(64).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

def get_encrypted_length(plain_len: int) -> int:
    """PSCryptor.cpp:401 GetEncryptedLength"""
    rem = plain_len % BLOCK_SIZE
    return plain_len + (BLOCK_SIZE - rem)

# ─────────────────────────────────────────────
# 2. TCP 协议 - 对应 PhotoshopProtocol.java:30 & EchoClient.mm:290
# ─────────────────────────────────────────────
# Content Types howDoesItWork.html:99
ILLEGAL_TYPE = 0
ERRORSTRING_TYPE = 1
JAVASCRIPT_TYPE = 2
IMAGE_TYPE = 3
PROFILE_TYPE = 4
DATA_TYPE = 5
CANCEL_TYPE = 6
EVENT_STATUS_TYPE = 7

# Image format byte imagesandprofiles.html:53
JPEG_FORMAT = 1
PIXMAP_FORMAT = 2

PROTOCOL_VERSION = 1

class PhotoshopTCPClient:
    """TCP 直连 Photoshop Remote Connections (端口 49494)"""
    def __init__(self, host="127.0.0.1", port=49494, password="", timeout=5):
        self.host = host
        self.port = port
        self.password = password
        self.key = derive_key(password) if password else None
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.txn_id = 1  # IncrementTransactionID 对应 EchoClient.mm:98
        self.verbose = False

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)
        # 测试握手
        res = self.exec_jsx('"Connected";')
        if res.strip().strip('"').strip("'") != "Connected":
            # 尝试密码错误提示
            if "password" in res.lower() or "error" in res.lower():
                raise RuntimeError(f"Password error or not authorized: {res}")
        return res

    def close(self):
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock = None

    def _next_txn(self) -> int:
        # EchoClient.mm:98 odd/even 区分 test，这里简化递增
        tid = self.txn_id
        self.txn_id += 1
        if self.txn_id == 0:
            self.txn_id = 1
        return tid

    def _send_message(self, data: Optional[bytes], content_type: int) -> int:
        if not self.sock:
            raise RuntimeError("Not connected")
        prolog_len = 12  # version + txn + type
        plain_len = prolog_len + (len(data) if data else 0)
        # 构造明文
        plain = struct.pack("!III", PROTOCOL_VERSION, self._next_txn(), content_type)
        if data:
            plain += data
        txn_sent = struct.unpack("!I", plain[4:8])[0]
        # 加密 (com_status 不加密)
        if self.key:
            encrypted = encrypt_payload(plain, self.key)
        else:
            encrypted = plain
        msg_len = 4 + len(encrypted)  # 含 comm_status
        header = struct.pack("!ii", msg_len, 0)  # length + comm_status(0)
        self.sock.sendall(header + encrypted)
        return txn_sent

    def _recv_message(self) -> Tuple[int,int,int,bytes]:
        """返回 (com_status, version, txn, content_type, payload)"""
        # 读 4B length
        raw_len = self._recvall(4)
        if not raw_len: raise RuntimeError("Connection closed")
        msg_len = struct.unpack("!i", raw_len)[0]
        raw_status = self._recvall(4)
        com_status = struct.unpack("!i", raw_status)[0]
        body_len = msg_len - 4
        body = self._recvall(body_len)
        if com_status != 0:
            # 明文错误，body = version(4)+txn(4)+type(4)+text
            if len(body) < 12:
                return com_status, 0, 0, ERRORSTRING_TYPE, body
            ver, txn, ctype = struct.unpack("!III", body[:12])
            payload = body[12:]
            return com_status, ver, txn, ctype, payload
        else:
            # 解密
            if self.key:
                plain = decrypt_payload(body, self.key)
            else:
                plain = body
            if len(plain) < 12:
                raise RuntimeError(f"Decrypted too short: {len(plain)}")
            ver, txn, ctype = struct.unpack("!III", plain[:12])
            payload = plain[12:]
            return com_status, ver, txn, ctype, payload

    def _recvall(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                break
            buf += chunk
        return buf

    # ── 高层 ──
    def exec_jsx(self, jsx_code: str, timeout=10) -> str:
        """发送 JSX，返回执行结果字符串（对应 processJavaScript）"""
        # 确保以 \n 结尾
        if not jsx_code.endswith("\n"):
            jsx_code += "\n"
        data = jsx_code.encode("utf-8")
        self._send_message(data, JAVASCRIPT_TYPE)
        # 等待响应，带超时
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            com_status, ver, txn, ctype, payload = self._recv_message()
            if ctype == ERRORSTRING_TYPE:
                return f"ERROR: {payload.decode('utf-8', errors='ignore')}"
            elif ctype == JAVASCRIPT_TYPE:
                return payload.decode('utf-8', errors='ignore')
            elif ctype == IMAGE_TYPE:
                # 图片响应，返回特殊标记，由 capture 接口处理
                return f"__IMAGE__:{len(payload)}"
            else:
                return payload.decode('utf-8', errors='ignore') if payload else ""
        finally:
            self.sock.settimeout(old_timeout)

    def exec_jsx_raw(self, jsx_code: str, timeout=10):
        """返回原始 (ctype, payload)"""
        if not jsx_code.endswith("\n"):
            jsx_code += "\n"
        self._send_message(jsx_code.encode("utf-8"), JAVASCRIPT_TYPE)
        old = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            return self._recv_message()
        finally:
            self.sock.settimeout(old)

    def capture_jpeg(self, width=800, height=600) -> bytes:
        """请求文档缩略图 JPEG bytes - imagesandprofiles.html:53"""
        js = f'''
var idNS = stringIDToTypeID("sendDocumentThumbnailToNetworkClient");
var desc1 = new ActionDescriptor();
desc1.putInteger(stringIDToTypeID("width"), {int(width)});
desc1.putInteger(stringIDToTypeID("height"), {int(height)});
desc1.putInteger(stringIDToTypeID("format"), 1);
executeAction(idNS, desc1, DialogModes.NO);
'''
        if not js.endswith("\n"): js += "\n"
        self._send_message(js.encode("utf-8"), JAVASCRIPT_TYPE)
        com_status, ver, txn, ctype, payload = self._recv_message()
        if ctype == ERRORSTRING_TYPE:
            raise RuntimeError(f"Capture error: {payload.decode('utf-8', errors='ignore')}")
        if ctype != IMAGE_TYPE:
            raise RuntimeError(f"Expected IMAGE, got {ctype}: {payload[:200]}")
        # payload: 1 byte format + JPEG bytes
        fmt = payload[0]
        if fmt != JPEG_FORMAT:
            raise RuntimeError(f"Expected JPEG format 1, got {fmt}")
        return payload[1:]  # JPEG

    def capture_pixmap(self, width=800, height=600) -> Tuple[int,int,bytes]:
        """返回 (w,h, raw RGB bytes) Pixmap 模式"""
        js = f'''
var idNS = stringIDToTypeID("sendDocumentThumbnailToNetworkClient");
var desc1 = new ActionDescriptor();
desc1.putInteger(stringIDToTypeID("width"), {int(width)});
desc1.putInteger(stringIDToTypeID("height"), {int(height)});
desc1.putInteger(stringIDToTypeID("format"), 2);
executeAction(idNS, desc1, DialogModes.NO);
'''
        self._send_message(js.encode("utf-8"), JAVASCRIPT_TYPE)
        com_status, ver, txn, ctype, payload = self._recv_message()
        if ctype != IMAGE_TYPE:
            raise RuntimeError(f"Expected IMAGE, got {ctype}")
        fmt = payload[0]
        if fmt != PIXMAP_FORMAT:
            raise RuntimeError(f"Expected pixmap 2, got {fmt}")
        w = struct.unpack("!I", payload[1:5])[0]
        h = struct.unpack("!I", payload[5:9])[0]
        rowBytes = struct.unpack("!I", payload[9:13])[0]
        mode = payload[13]; channels = payload[14]; bits = payload[15]
        raw = payload[16:]
        return w, h, raw

    def send_image_jpeg(self, jpeg_bytes: bytes):
        """发送 JPEG 新建文档 - imagesandprofiles.html:64 content_type=3 + 1 byte format"""
        data = struct.pack("B", JPEG_FORMAT) + jpeg_bytes
        self._send_message(data, IMAGE_TYPE)
        com_status, ver, txn, ctype, payload = self._recv_message()
        if ctype == ERRORSTRING_TYPE:
            raise RuntimeError(payload.decode('utf-8', errors='ignore'))
        return payload.decode('utf-8', errors='ignore') if payload else "OK"

    def send_image_file(self, path: str):
        with open(path, "rb") as f:
            data = f.read()
        # 检测是否为 JPEG (简单)
        return self.send_image_jpeg(data)

    def subscribe_event(self, event_id: str) -> str:
        js = f'''
var idNS = stringIDToTypeID("networkEventSubscribe");
var desc1 = new ActionDescriptor();
desc1.putClass(stringIDToTypeID("eventIDAttr"), stringIDToTypeID("{event_id}"));
executeAction(idNS, desc1, DialogModes.NO);
"Subscribed:{event_id}";
'''
        return self.exec_jsx(js)

# ─────────────────────────────────────────────
# 3. COM Fallback - 对应 photoshop-jsx SKILL
# ─────────────────────────────────────────────
class PhotoshopCOMBridge:
    """未注册 COM 时的备用通道"""
    def __init__(self, ps_exe=None):
        self.ps_exe = ps_exe
        self._com = None

    def _get_com(self):
        if self._com:
            return self._com
        try:
            import win32com.client
            try:
                self._com = win32com.client.GetActiveObject("Photoshop.Application")
            except:
                self._com = win32com.client.Dispatch("Photoshop.Application")
            return self._com
        except Exception as e:
            raise RuntimeError(f"COM unavailable: {e}. Run scripts/enable_remote.ps1 or fix COM registration.")

    def exec_jsx(self, code: str) -> str:
        # 写临时 jsx，DoJavaScriptFile 调用（避免中文/Elps坑）
        # 通过 __bridge_result 文件回传返回值，解决 COM 无返回值问题
        result_path = tempfile.mktemp(suffix='.txt')
        result_path_js = result_path.replace("\\", "/")
        try:
            if os.path.exists(result_path):
                os.unlink(result_path)
        except: pass
        # 转换 code 使其在 COM 下能正确回传
        transformed = code
        stripped = transformed.strip()
        # IIFE 特殊处理：直接让整个 IIFE 赋值给 __bridge_result
        if stripped.startswith("(function()") and stripped.endswith(")();"):
            transformed = "__bridge_result = " + stripped
            use_outer_wrapper = False
        elif stripped.startswith("(function()") and ")();" in stripped:
            # 多行 IIFE，同样处理
            transformed = "__bridge_result = " + stripped
            use_outer_wrapper = False
        elif "return JSON.stringify" in transformed:
            # 非 IIFE 但包含 return JSON，替换所有 return 为赋值
            transformed = transformed.replace("return ", "__bridge_result = ")
            use_outer_wrapper = False
        elif "return \"" in transformed or "return '" in transformed or "return __bridge_result" in transformed or "return" in transformed:
            transformed = transformed.replace("return ", "__bridge_result = ")
            use_outer_wrapper = False
        else:
            import re
            m = re.search(r'"([^"]*)"\s*;\s*$', stripped)
            if m and "__bridge_result" not in stripped and "return" not in stripped:
                transformed = re.sub(r'"([^"]*)"\s*;\s*$', r'__bridge_result = "\1";', stripped)
                use_outer_wrapper = False
            else:
                use_outer_wrapper = True

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsx', delete=False, encoding='utf-8') as f:
            f.write('app.displayDialogs=DialogModes.NO; app.preferences.rulerUnits=Units.PIXELS;\n')
            f.write('if(typeof JSON==="undefined"){JSON={};JSON.stringify=function(o){if(o===null)return"null";if(typeof o==="string"){var s=o.replace(/\\\\/g,"\\\\\\\\").replace(/"/g,\'\\\\"\');s=s.replace(/[\\u0080-\\uFFFF]/g,function(c){return "\\\\u"+("0000"+c.charCodeAt(0).toString(16)).slice(-4);});return \'"\'+s+\'"\';}if(typeof o==="number"||typeof o==="boolean")return String(o);if(o instanceof Array){var s="[";for(var i=0;i<o.length;i++){if(i>0)s+=",";s+=JSON.stringify(o[i]);}return s+"]";}if(typeof o==="object"){var s="{";var f=true;for(var k in o){if(!f)s+=",";f=false;s+=\'"\'+k+\'":\'+JSON.stringify(o[k]);}return s+"}";}return \'"\'+String(o)+\'"\';};}\n')
            # helper to escape non-ASCII for fallback strings
            f.write('function __escUnicode(s){if(s==null)return "";return String(s).replace(/[\\u0080-\\uFFFF]/g,function(c){return "\\\\u"+("0000"+c.charCodeAt(0).toString(16)).slice(-4);});}\n')
            f.write('var __bridge_result = null;\n')
            f.write('try{\n')
            if use_outer_wrapper:
                # 普通代码用外层捕获返回值
                f.write('__bridge_result = (function(){\n')
                f.write(transformed)
                # 确保最后一行有 return 以捕获值
                if 'return' not in transformed and '__bridge_result' not in transformed:
                    # 尝试让最后一表达式成为返回值
                    f.write('\nreturn "OK";\n')
                f.write('\n})();\n')
            else:
                # 已转换为 __bridge_result 赋值，直接执行
                f.write(transformed)
                f.write('\n')
            f.write('}catch(e){ try{ __bridge_result = "ERROR:"+__escUnicode(e.toString()); }catch(ee){ __bridge_result="ERROR:unknown"; } }\n')
            f.write(f'var __resFile = new File("{result_path_js}");\n')
            f.write('__resFile.encoding = "UTF-8";\n')
            f.write('__resFile.open("w");\n')
            f.write('if(__bridge_result != null){ var _s=String(__bridge_result); try{ _s=__escUnicode(_s); }catch(e){} __resFile.write(_s); } else __resFile.write("OK");\n')
            f.write('__resFile.close();\n')
            jsx_path = f.name
        try:
            ps = self._get_com()
            ps.DoJavaScriptFile(jsx_path)
            # 等待文件生成（PS 同步，但加短轮询）
            for _ in range(20):
                if os.path.exists(result_path):
                    break
                time.sleep(0.05)
            if os.path.exists(result_path):
                # 优先 UTF-8（已设置 encoding），失败回落 cp936
                for enc in ("utf-8", "utf-8-sig", "cp936", "gbk", "latin1"):
                    try:
                        with open(result_path, 'r', encoding=enc) as rf:
                            content = rf.read()
                        if content and "�" not in content:
                            return content
                        # 若含替换字符，尝试下一编码
                        if content:
                            # 简单检测：若 utf-8 解出大量 � 则尝试 cp936
                            if content.count("�") > 2:
                                continue
                            return content
                    except: continue
                with open(result_path, 'rb') as rf:
                    return rf.read().decode('utf-8', errors='ignore')
            return "OK (COM no result)"
        finally:
            try: os.unlink(jsx_path)
            except: pass
            # 保留 result_path 供调试，调用方读取后可自行删除

    def capture_via_tempfile(self, width=800, height=600) -> bytes:
        """COM 下通过 JSX 保存临时 JPEG 再读取"""
        tmp_jpg = os.path.join(tempfile.gettempdir(), "ps_bridge_capture.jpg")
        tmp_jpg_js = tmp_jpg.replace("\\", "/")
        # 确保目录存在
        try: os.unlink(tmp_jpg)
        except: pass
        js = f'''
if(app.documents.length>0){{
  var tmp = new File("{tmp_jpg_js}");
  var doc=app.activeDocument;
  var opts=new JPEGSaveOptions(); opts.quality=8;
  try{{
    var dup=doc.duplicate("temp_capture");
    dup.resizeImage(UnitValue({width},"px"), UnitValue({height},"px"), null, ResampleMethod.BICUBIC);
    dup.saveAs(tmp, opts, true, Extension.LOWERCASE);
    dup.close(SaveOptions.DONOTSAVECHANGES);
  }}catch(e){{
    // fallback: 直接保存当前文档副本
    doc.saveAs(tmp, opts, true, Extension.LOWERCASE);
  }}
}}
"capture done";
'''
        self.exec_jsx(js)
        # 等待文件
        for _ in range(20):
            if os.path.exists(tmp_jpg) and os.path.getsize(tmp_jpg) > 0:
                break
            time.sleep(0.1)
        if os.path.exists(tmp_jpg):
            with open(tmp_jpg, 'rb') as f:
                return f.read()
        return b""

# ─────────────────────────────────────────────
# 4. 统一高层 API - AI Agent 直接调用
# ─────────────────────────────────────────────
class PhotoshopAIBridge:
    """
    统一入口：优先 TCP，失败回落 COM
    提供 看图 / 画图 / 改图 / 全工具 四类 API
    """
    def __init__(self, host="127.0.0.1", port=49494, password="", use_com=False, verbose=False):
        self.host = host
        self.port = port
        self.password = password
        self.use_com = use_com
        self.verbose = verbose
        self.tcp: Optional[PhotoshopTCPClient] = None
        self.com: Optional[PhotoshopCOMBridge] = None
        self.mode = "tcp" if not use_com else "com"

    def connect(self):
        if self.mode == "com":
            self.com = PhotoshopCOMBridge()
            # 静默测试，不弹框
            res = self.com.exec_jsx('return "COM connected "+app.name+" "+app.version;')
            return res
        else:
            self.tcp = PhotoshopTCPClient(self.host, self.port, self.password)
            try:
                res = self.tcp.connect()
                if self.verbose: print(f"[TCP] {res}")
                return res
            except Exception as e:
                print(f"[TCP] connect failed: {e}, fallback to COM...")
                self.mode = "com"
                self.com = PhotoshopCOMBridge()
                return self.com.exec_jsx('var x=1;')

    def close(self):
        if self.tcp: self.tcp.close()

    def _exec(self, jsx: str) -> str:
        if self.mode == "tcp" and self.tcp:
            return self.tcp.exec_jsx(jsx)
        else:
            if not self.com: self.com = PhotoshopCOMBridge()
            return self.com.exec_jsx(jsx)

    # ── 看图 ──
    def ping(self) -> str:
        return self._exec('alert("ping"); "pong";') if self.mode=="com" else self._exec('"pong";')

    def get_app_info(self) -> Dict:
        jsx = '''
(function(){
  var r={};
  r.name=app.name; r.version=app.version; r.docCount=app.documents.length;
  r.activeDoc = app.documents.length>0 ? app.activeDocument.name : "";
  r.build=app.build;
  return JSON.stringify(r);
})();
'''
        # TCP 可直接拿返回值，COM 需文件回传 - 这里统一用 TCP 风格，COM 下简化
        raw = self._exec(jsx + '\n')
        # 尝试解析 JSON
        try:
            # 提取 JSON 子串
            start = raw.find('{')
            end = raw.rfind('}')+1
            if start>=0:
                return json.loads(raw[start:end])
        except: pass
        return {"raw": raw}

    def list_documents(self) -> List[Dict]:
        jsx = '''
(function(){
  var arr=[];
  for(var i=0;i<app.documents.length;i++){
    var d=app.documents[i];
    arr.push({index:i, name:d.name, width:d.width.as("px"), height:d.height.as("px"), resolution:d.resolution, mode:d.mode.toString()});
  }
  return JSON.stringify(arr);
})();
'''
        raw = self._exec(jsx)
        try:
            s=raw[raw.find('['):raw.rfind(']')+1]
            return json.loads(s)
        except:
            return []

    def list_layers(self) -> List[Dict]:
        jsx = '''
(function(){
  if(app.documents.length==0) return "[]";
  var doc=app.activeDocument; var arr=[];
  for(var i=0;i<doc.layers.length;i++){
    var l=doc.layers[i];
    var kind="unknown";
    try{kind=l.kind.toString();}catch(e){}
    arr.push({index:i, name:l.name, visible:l.visible, opacity:l.opacity, kind:kind, bounds: l.bounds.toString()});
  }
  return JSON.stringify(arr);
})();
'''
        raw = self._exec(jsx)
        try:
            s=raw[raw.find('['):raw.rfind(']')+1]
            return json.loads(s)
        except:
            return [{"raw": raw}]

    def get_document_info(self) -> Dict:
        jsx = '''
(function(){
  if(app.documents.length==0) return JSON.stringify({error:"No document"});
  var d=app.activeDocument;
  var r={name:d.name, width:d.width.as("px"), height:d.height.as("px"), resolution:d.resolution, mode:d.mode.toString(), layers:d.layers.length, activeLayer:d.activeLayer.name};
  r.histogram = "ok";
  return JSON.stringify(r);
})();
'''
        raw=self._exec(jsx)
        try:
            return json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        except:
            return {"raw":raw}

    def capture_jpeg(self, width=1024, height=768, save_path: Optional[str]=None) -> bytes:
        """看图核心 - 返回 JPEG bytes"""
        if self.mode=="tcp" and self.tcp:
            data = self.tcp.capture_jpeg(width, height)
        else:
            if not self.com: self.com=PhotoshopCOMBridge()
            data = self.com.capture_via_tempfile(width, height)
        if save_path and data:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f: f.write(data)
        return data

    def capture_layer_thumbnail(self, save_path: Optional[str]=None, width=800, height=800, selected_only=True) -> bytes:
        """图层级缩略图 - sendLayerThumbnailToNetworkClient (LayerThumbnail.jsx)"""
        # 构造 JSX，TCP 下为请求图片响应
        js = f'''
var idNS = stringIDToTypeID("sendLayerThumbnailToNetworkClient");
var desc1 = new ActionDescriptor();
desc1.putInteger(stringIDToTypeID("width"), {width});
desc1.putInteger(stringIDToTypeID("height"), {height});
desc1.putInteger(stringIDToTypeID("format"), 1);
desc1.putBoolean(stringIDToTypeID("selectedLayers"), {str(selected_only).lower()});
desc1.putBoolean(stringIDToTypeID("sendThumbnailPixels"), true);
desc1.putBoolean(stringIDToTypeID("sendThumbnailBounds"), true);
executeAction(idNS, desc1, DialogModes.NO);
'''
        if self.mode=="tcp" and self.tcp:
            self.tcp._send_message((js+"\n").encode("utf-8"), JAVASCRIPT_TYPE)
            com_status, ver, txn, ctype, payload = self.tcp._recv_message()
            if ctype==IMAGE_TYPE:
                jpeg = payload[1:]
                if save_path: Path(save_path).parent.mkdir(parents=True, exist_ok=True); open(save_path,"wb").write(jpeg)
                return jpeg
            else:
                raise RuntimeError(payload.decode(errors="ignore"))
        else:
            # COM 回落用 document 捕获代替
            return self.capture_jpeg(width, height, save_path)

    # ── 画图 ──
    def create_document(self, width=1920, height=1080, name="AI_Canvas", resolution=72, fill="white") -> str:
        fill_map = {"white":"DocumentFill.WHITE","transparent":"DocumentFill.TRANSPARENT","background":"DocumentFill.BACKGROUNDCOLOR"}
        fill_val = fill_map.get(fill, "DocumentFill.WHITE")
        jsx = f'app.documents.add(UnitValue({width},"px"), UnitValue({height},"px"), {resolution}, "{name}", NewDocumentMode.RGB, {fill_val}); "{name} created";'
        return self._exec(jsx)

    def draw_rect(self, x, y, w, h, fill_color=(255,0,0), opacity=100) -> str:
        r,g,b=fill_color
        jsx = f'''
(function(){{
  if(app.documents.length==0) app.documents.add(800,600,72);
  var doc=app.activeDocument;
  var color=new SolidColor(); color.rgb.red={r}; color.rgb.green={g}; color.rgb.blue={b};
  doc.selection.select([[ {x},{y}],[ {x+w},{y}],[ {x+w},{y+h}],[ {x},{y+h}]]);
  doc.selection.fill(color, ColorBlendMode.NORMAL, {opacity}, false);
  doc.selection.deselect();
  "rect {x},{y} {w}x{h}";
}})();
'''
        return self._exec(jsx)

    def draw_ellipse(self, cx, cy, rx, ry, fill_color=(0,120,255)) -> str:
        # 多边形逼近 ellipse，避免 Elps 坑
        r,g,b=fill_color
        jsx = f'''
(function(){{
  if(app.documents.length==0) app.documents.add(800,600,72);
  var doc=app.activeDocument;
  var color=new SolidColor(); color.rgb.red={r}; color.rgb.green={g}; color.rgb.blue={b};
  var cx={cx}, cy={cy}, rx={rx}, ry={ry};
  var pts=[]; var segs=32;
  for(var i=0;i<segs;i++){{ var a=i*2*Math.PI/segs; pts.push([cx+rx*Math.cos(a), cy+ry*Math.sin(a)]); }}
  doc.selection.select(pts);
  doc.selection.fill(color);
  doc.selection.deselect();
  "ellipse";
}})();
'''
        return self._exec(jsx)

    def draw_polygon(self, points: List[Tuple[int,int]], fill_color=(0,255,0)) -> str:
        r,g,b=fill_color
        pts_str = ",".join([f"[{x},{y}]" for x,y in points])
        jsx = f'''
(function(){{
  var doc=app.activeDocument;
  var c=new SolidColor(); c.rgb.red={r}; c.rgb.green={g}; c.rgb.blue={b};
  doc.selection.select([{pts_str}]);
  doc.selection.fill(c); doc.selection.deselect();
  "polygon";
}})();
'''
        return self._exec(jsx)

    def paste_image(self, image_path_or_bytes) -> str:
        """画图：粘贴外部图像到当前文档，兼容 CS6（open+copy 回落）"""
        if isinstance(image_path_or_bytes, bytes):
            tmp = os.path.join(tempfile.gettempdir(), "ps_ai_paste.jpg")
            with open(tmp, "wb") as f: f.write(image_path_or_bytes)
            image_path_or_bytes = tmp
        p = image_path_or_bytes.replace("\\","/")
        jsx = f'''
(function(){{
  if(app.documents.length==0) app.documents.add(800,600,72);
  var f=new File("{p}");
  if(!f.exists) return "ERROR: file not found {p}";
  // 解锁背景以便粘贴
  try{{ var bg=app.activeDocument.activeLayer; if(bg.isBackgroundLayer) bg.isBackgroundLayer=false; }}catch(e){{}}
  try{{
    var docBefore=app.activeDocument;
    app.open(f);
    var docImg=app.activeDocument;
    docImg.selection.selectAll();
    docImg.selection.copy();
    docImg.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument=docBefore;
    docBefore.paste();
    return "placed {p} via open+copy";
  }}catch(e1){{
    try{{
      var desc=new ActionDescriptor();
      desc.putPath(stringIDToTypeID("null"), f);
      executeAction(stringIDToTypeID("place"), desc, DialogModes.NO);
      return "placed {p} via ActionManager";
    }}catch(e2){{
      return "ERROR: place failed "+e1+": "+e2;
    }}
  }}
}})();
'''
        return self._exec(jsx)

    def send_image_as_new_document(self, image_path: str) -> str:
        """TCP 特有：发送 JPEG 直接新建文档"""
        if self.mode=="tcp" and self.tcp:
            return self.tcp.send_image_file(image_path)
        else:
            return self.paste_image(image_path)

    # ── 改图 ──
    def select_tool(self, tool_id: str) -> str:
        """选择任意工具 - 对应 toolChanged 事件，兼容 CS6/CC"""
        # 尝试多种方式，优先 app.currentTool（最稳定），回落 ActionManager
        jsx = f'''
(function(){{
  var tool="{tool_id}";
  var ok=false;
  var err="";
  // 方式1: 直接设 currentTool
  try{{ app.currentTool=tool; ok=true; }}catch(e1){{ err=e1.toString(); }}
  // 方式2: ActionManager select
  if(!ok){{
    try{{
      var idselect = stringIDToTypeID("select");
      var desc = new ActionDescriptor();
      var ref = new ActionReference();
      ref.putClass(stringIDToTypeID(tool));
      desc.putReference(stringIDToTypeID("null"), ref);
      executeAction(idselect, desc, DialogModes.NO);
      ok=true;
    }}catch(e2){{ err+=\" | \"+e2.toString(); }}
  }}
  // 方式3: 尝试别名（如 brushTool -> paintbrushTool）
  if(!ok && tool==\"brushTool\"){{
    try{{ app.currentTool=\"paintbrushTool\"; ok=true; tool=\"paintbrushTool\"; }}catch(e3){{}}
  }}
  if(ok) return tool+\" selected via \"+app.currentTool;
  else return \"ERROR:\"+err;
}})();
'''
        return self._exec(jsx)

    def execute_jsx(self, code: str) -> str:
        """通用：执行任意 JSX，可调动 PS 所有 DOM"""
        return self._exec(code)

    def execute_action(self, action: str, from_set: Optional[str]=None) -> str:
        """执行 Action / 快捷操作"""
        if from_set:
            jsx = f'executeAction(stringIDToTypeID("{action}"), undefined, DialogModes.NO); "{action}";'
            # 实际播放动作需 app.doAction
            jsx = f'app.doAction("{action}","{from_set}"); "{action}";'
        else:
            # 常见 stringID 如 cut/copy/paste/undo/redo/mergeLayers
            jsx = f'executeAction(stringIDToTypeID("{action}"), new ActionDescriptor(), DialogModes.NO); "{action}";'
        return self._exec(jsx)

    def adjust_brightness_contrast(self, brightness=10, contrast=10) -> str:
        jsx = f'''
var desc=new ActionDescriptor();
desc.putInteger(stringIDToTypeID("brightness"), {brightness});
desc.putInteger(stringIDToTypeID("contrast"), {contrast});
executeAction(stringIDToTypeID("brightnessEvent"), desc, DialogModes.NO);
"brightness {brightness}";
'''
        return self._exec(jsx)

    def adjust_hue_saturation(self, hue=0, saturation=20, lightness=0) -> str:
        jsx = f'''
var desc=new ActionDescriptor();
desc.putInteger(stringIDToTypeID("hue"), {hue});
desc.putInteger(stringIDToTypeID("saturation"), {saturation});
desc.putInteger(stringIDToTypeID("lightness"), {lightness});
executeAction(stringIDToTypeID("hueSaturation"), desc, DialogModes.NO);
"hue";
'''
        return self._exec(jsx)

    def apply_blur(self, radius=5) -> str:
        jsx = f'''
var desc=new ActionDescriptor();
desc.putUnitDouble(stringIDToTypeID("radius"), stringIDToTypeID("pixelsUnit"), {radius});
executeAction(stringIDToTypeID("gaussianBlur"), desc, DialogModes.NO);
"blur {radius}";
'''
        return self._exec(jsx)

    def transform_layer(self, scale_x=100, scale_y=100, angle=0) -> str:
        # 兼容 CS6：解锁背景后用 DOM resize/rotate
        jsx = f'''
(function(){{
  try{{
    var doc=app.activeDocument;
    var layer=doc.activeLayer;
    if(layer.isBackgroundLayer) layer.isBackgroundLayer=false;
    if({scale_x}!=100 || {scale_y}!=100){{
      layer.resize({scale_x}, {scale_y}, AnchorPosition.MIDDLECENTER);
    }}
    if({angle}!=0){{
      layer.rotate({angle});
    }}
    return "transform via DOM";
  }}catch(e1){{
    return "ERROR transform:"+e1;
  }}
}})();
'''
        return self._exec(jsx)

    def list_tools(self) -> List[str]:
        # 静态表，见 jsx/tools_map.jsx
        return ["moveTool","brushTool","pencilTool","eraserTool","gradientTool","bucketTool","blurTool","dodgeTool","burnTool","spongeTool","cloneStampTool","healingBrushTool","patchTool","penTool","shapeTool","textTool","cropTool","eyedropperTool","handTool","zoomTool","sliceTool","historyBrushTool","artHistoryBrushTool","backgroundEraserTool","magicEraserTool","magicWandTool","lassoTool","polygonalLassoTool","magneticLassoTool","quickSelectTool","spotHealingBrushTool","redEyeTool","mixerBrushTool","sharpenTool","smudgeTool","pathSelectionTool","directSelectionTool","notesTool","audioAnnotationTool","measureTool","countTool","colorSamplerTool"]

    def save_document(self, path: str, as_jpeg=True, quality=12) -> str:
        # Python 侧先建目录，避免 PS saveAs 报“找不到文件”
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        except: pass
        p = path.replace("\\","/")
        if as_jpeg:
            jsx = f'''
var f=new File("{p}");
var opts=new JPEGSaveOptions(); opts.quality={quality};
app.activeDocument.saveAs(f, opts, true, Extension.LOWERCASE);
"saved {p}";
'''
        else:
            jsx = f'var f=new File("{p}"); app.activeDocument.saveAs(f); "saved";'
        return self._exec(jsx)

    def undo(self):
        # 历史记录回退，兼容 char/string ID
        jsx = '''
(function(){
  try{ executeAction(charIDToTypeID("undo"), undefined, DialogModes.NO); return "undo charID"; }catch(e1){
    try{ executeAction(stringIDToTypeID("undo"), undefined, DialogModes.NO); return "undo stringID"; }catch(e2){
      try{ app.activeDocument.activeHistoryState = app.activeDocument.historyStates[app.activeDocument.historyStates.length-2]; return "undo via history"; }catch(e3){ return "ERROR undo:"+e1+":"+e2+":"+e3; }
    }
  }
})();
'''
        return self._exec(jsx)
    def redo(self):
        jsx = '''
(function(){
  try{ executeAction(charIDToTypeID("redo"), undefined, DialogModes.NO); return "redo charID"; }catch(e1){
    try{ executeAction(stringIDToTypeID("redo"), undefined, DialogModes.NO); return "redo stringID"; }catch(e2){ return "ERROR redo:"+e1+":"+e2; }
  }
})();
'''
        return self._exec(jsx)
