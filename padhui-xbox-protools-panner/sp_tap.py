#!/usr/bin/env python3
# 旁听所有 MIDI 输入端口（含 AudioSwift），记录它发给 Pro Tools 的 SurroundPanner 消息
import mido, time, threading
t0 = time.time()
def listen(name):
    with mido.open_input(name) as p:
        for m in p:
            print(f"[{time.time()-t0:8.3f}] {name}: {m.hex()}", flush=True)
seen = set()
print("等待端口…", flush=True)
while True:
    for n in mido.get_input_names():
        if n not in seen:
            seen.add(n); print("监听:", n, flush=True)
            threading.Thread(target=listen, args=(n,), daemon=True).start()
    time.sleep(2)
