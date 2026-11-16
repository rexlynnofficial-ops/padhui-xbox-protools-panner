#!/usr/bin/env python3
# 嗅探 Pro Tools "SurroundPanner" 协议：创建虚拟端口 PadPan，记录 Pro Tools 发来的全部 MIDI
# 往 scmd 文件写十六进制（如 "B0 10 40"）即可发给 Pro Tools；写 "stop" 退出
import mido, os, time, threading
inp = mido.open_input("PadPan", virtual=True)
out = mido.open_output("PadPan", virtual=True)
t0 = time.time()
def rx():
    for m in inp:
        print(f"[RX {time.time()-t0:7.2f}] {m.hex()}", flush=True)
threading.Thread(target=rx, daemon=True).start()
print("PadPan 已创建", flush=True)
while True:
    if os.path.exists("scmd"):
        txt = open("scmd").read(); os.remove("scmd")
        for ln in txt.splitlines():
            ln = ln.strip()
            if not ln: continue
            if ln == "stop": raise SystemExit
            if ln.startswith("sleep"): time.sleep(float(ln.split()[1])); continue
            try:
                out.send(mido.Message.from_hex(ln)); print("[TX]", ln, flush=True)
            except Exception as e:
                print("[ERR]", ln, e, flush=True)
    time.sleep(0.01)
