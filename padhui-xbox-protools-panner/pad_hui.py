#!/usr/bin/env python3
"""
PadHUI — 把 Xbox 手柄模拟成一台 HUI 控制台，驱动 Pro Tools 原生声像器。

Pro Tools 设置：
  Setup > Peripherals > MIDI Controllers：Type = HUI，Receive From / Send To = "PadHUI"
  然后在混音窗口选中一轨（HUI 第 1 条 V-pot 对应 bank 第 1 轨）

依赖：pip3 install mido python-rtmidi pygame
运行：python3 pad_hui.py            # 真手柄
      python3 pad_hui.py --sim      # 无手柄：模拟摇杆画圆，用于测试

注：HUI 开关地址（zone/port）来自公开的 HUI 协议整理表，首次使用请用 --sim 对照
    Pro Tools 屏幕确认；V-pot 旋转（CC 0x40-0x47）是确定的。
"""
import argparse, math, threading, time
import mido

PORT = "PadHUI"
VPOT_CC = 0x40          # V-pot 1..8 = CC 0x40..0x47，相对值
ZONE_CC, PORT_CC = 0x0F, 0x2F

class HUI:
    def __init__(self):
        self.out = mido.open_output(PORT, virtual=True)
        self.inp = mido.open_input(PORT, virtual=True)
        self.online = False
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        for msg in self.inp:
            # Pro Tools 每秒发 ping（Note On 0 vel 0），必须回 vel 127 否则掉线
            if msg.type == "sysex":
                d = list(msg.data)
                if len(d) > 6 and d[:5] == [0, 0, 0x66, 5, 0] and d[5] == 0x10:   # 4 字符小屏：轨名
                    print(f"[HUI] strip {d[6]} = {bytes(d[7:11]).decode('ascii','replace')}")
                continue
            if msg.type == "control_change" and 0x10 <= msg.control <= 0x17:
                print(f"[HUI] vpot{msg.control-0x10} ring={msg.value}")
                continue
            if msg.type in ("note_on", "note_off") and msg.note == 0 and msg.channel == 0:
                pass
            else:
                print("[RX]", msg.hex() if hasattr(msg, "hex") else msg)
                continue
            if msg.type in ("note_on", "note_off") and msg.note == 0:
                self.out.send(mido.Message("note_on", note=0, velocity=127))
                if not self.online:
                    self.online = True
                    print("[HUI] Pro Tools 已连接")

    def vpot(self, strip, steps):
        """steps>0 顺时针。HUI：bit6=方向，低 6 位=步数"""
        while steps:
            n = max(-15, min(15, steps))
            val = (0x40 | n) if n > 0 else (-n)
            self.out.send(mido.Message("control_change", control=VPOT_CC + strip, value=val))
            steps -= n

    def switch(self, zone, port, down=True):
        self.out.send(mido.Message("control_change", control=ZONE_CC, value=zone))
        self.out.send(mido.Message("control_change", control=PORT_CC, value=(0x40 | port) if down else port))

    def tap(self, zone, port):
        self.switch(zone, port, True); time.sleep(0.03); self.switch(zone, port, False)


def pad_source(sim):
    """返回 (lx, ly, ry, a, x_btn) 的生成器"""
    if sim:
        t0 = time.time()
        while True:
            t = time.time() - t0
            yield math.cos(t), math.sin(t), 0.0, True, False   # 一直“握 A”画圆
    import pygame
    pygame.init(); pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        raise SystemExit("没找到手柄，可用 --sim 测试")
    js = pygame.joystick.Joystick(0); js.init()
    print("手柄:", js.get_name())
    while True:
        pygame.event.pump()
        yield js.get_axis(0), -js.get_axis(1), -js.get_axis(3), js.get_button(0), js.get_button(2)


def dz(v, d=0.15):
    return 0.0 if abs(v) < d else (v - math.copysign(d, v)) / (1 - d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--strip", type=int, default=0, help="HUI 条 0-7")
    ap.add_argument("--speed", type=float, default=6.0, help="每帧最大步数")
    a = ap.parse_args()

    hui = HUI()
    print(f"虚拟 MIDI 端口 '{PORT}' 已创建，等待 Pro Tools…")
    # 环绕声像器在 HUI 里：V-pot 控制当前选中的声像参数；
    # 手柄 X 键 = 按下 V-pot（在 X / Y(Front-Rear) 等参数间切换）
    acc = [0.0, 0.0]
    prev_x = False
    import os
    sent = 0
    paused = True   # 默认暂停，写 "sim on" 开始
    for lx, ly, ry, hold, xbtn in pad_source(a.sim):
        if os.path.exists("stop"):
            print("stop file -> exit"); break
        # 调试通道：往 cmd 文件写命令，如 "tap 11 3" / "vpot 0 5" / "sim on" / "sim off"
        if os.path.exists("cmd"):
            try:
                lines = open("cmd").read().split("\n"); os.remove("cmd")
            except Exception:
                lines = []
            for ln in lines:
                w = ln.split()
                if not w: continue
                print("[CMD]", ln)
                if w[0] == "tap": hui.tap(int(w[1], 0), int(w[2], 0))
                elif w[0] == "vpot": hui.vpot(int(w[1]), int(w[2]))
                elif w[0] == "down": hui.switch(int(w[1], 0), int(w[2], 0), True)
                elif w[0] == "up": hui.switch(int(w[1], 0), int(w[2], 0), False)
                elif w[0] == "sim": paused = (w[1] == "off")
                elif w[0] == "strip": a.strip = int(w[1])
                elif w[0] == "cc": hui.out.send(mido.Message("control_change", channel=int(w[1]), control=int(w[2], 0), value=int(w[3])))
                elif w[0] == "pb": hui.out.send(mido.Message("pitchwheel", channel=int(w[1]), pitch=int(w[2])))
        if globals().get("paused_flag") is None: pass
        if xbtn and not prev_x:
            hui.tap(0x08 + a.strip // 8, 0x00)   # V-pot 按下（zone 视版本可能需调整）
        prev_x = xbtn
        if hold and hui.online and not paused:
            acc[0] += dz(lx) * a.speed
            acc[1] += dz(ly) * a.speed
            sx, sy = int(acc[0]), int(acc[1])
            if sx:
                hui.vpot(a.strip, sx); acc[0] -= sx; sent += 1
                if sent % 60 == 1: print(f"[TX] vpot{a.strip} {sx:+d} (total {sent})")
            # HUI 每条只有一个 V-pot：左右推当前参数，上下也推同一个（按 X 键切到 Front/Rear 再推）
            if sy and not sx: hui.vpot(a.strip, sy); acc[1] -= sy
        time.sleep(1 / 60)


if __name__ == "__main__":
    main()
