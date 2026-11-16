#!/usr/bin/env python3
"""
PadSP — Xbox 手柄 → Pro Tools 原生环绕声像器（SurroundPanner 协议，同 Platane 摇杆原理）

Pro Tools 设置：Setup > Peripherals > MIDI Controllers：Type = SurroundPanner，收/发 = PadPan
             Setup > MIDI > MIDI Input Devices 勾选 PadPan
使用：打开某轨声像器窗口（右上角红色 Target 亮），手柄就控制它。

按键：
  A           开/关控制
  左摇杆      X（左右，CC16）/ Y（前后，CC17）
  RT / LT     LFE 增 / 减（CC18）
  RB 按住     Touch（按钮 06，写自动化时用；未完全验证）
  十字键 ←/→  上一条 / 下一条轨（按钮 02 / 03）
  Y           上一条轨的声像器（按钮 00）
  B           下一条轨的声像器（按钮 01）
协议（第 15 通道）：CC0=按下按钮, CC1=松开, CC16/17/18/20=相对编码器(二进制补码)
"""
import math, os, time, mido

PORT = "PadPan"
BTN = dict(A=0, B=1, X=2, Y=3, VIEW=4, MENU=6, LB=9, RB=10, UP=11, DOWN=12, LEFT=13, RIGHT=14)

out = mido.open_output(PORT, virtual=True)
inp = mido.open_input(PORT, virtual=True)

def cc(n, v): out.send(mido.Message("control_change", channel=14, control=n, value=v & 0x7F))
def rel(n, steps):
    while steps:
        s = max(-63, min(63, steps)); cc(n, s if s > 0 else 128 + s); steps -= s
def press(b): cc(0, b)
def release(b): cc(1, b)
def tap(b): press(b); time.sleep(0.03); release(b)

def dz(v, d=0.15): return 0.0 if abs(v) < d else (v - math.copysign(d, v)) / (1 - d)

import pygame
pygame.init(); pygame.joystick.init()
while pygame.joystick.get_count() == 0:
    print("等待手柄…"); time.sleep(1); pygame.joystick.quit(); pygame.joystick.init()
js = pygame.joystick.Joystick(0); js.init()
print("手柄:", js.get_name(), "| 端口:", PORT, "| 按 A 开始")
pygame.event.pump(); time.sleep(0.1); pygame.event.pump()
rest = [js.get_axis(i) for i in range(js.get_numaxes())]

def trig(i):
    r = rest[i]; t = (js.get_axis(i) - r) / ((1 - r) if r < 0.5 else 1.0)
    return t if t > 0.08 else 0.0

NEXT_BTN = 4      # B 键：下一条轨的声像器（若不对，改成 1 试试）
SPEED = 18.0      # 摇杆推满时每秒步数（25 步 = 一整边）
LFE_SPEED = 25.0
on, touch = False, False
acc = {16: 0.0, 17: 0.0, 18: 0.0}
last = time.time()
while not os.path.exists("pstop"):
    now = time.time(); dt = min(now - last, 0.05); last = now
    for e in pygame.event.get():
        if e.type == pygame.JOYBUTTONDOWN:
            b = e.button
            if b == BTN["A"]:
                on = not on; print("[控制]", "开" if on else "关")
                if not on and touch: release(6); touch = False
            elif b == BTN["Y"]: tap(0)
            elif b == BTN["B"]: tap(NEXT_BTN); print("[下一轨] 按钮", NEXT_BTN)
            elif b == BTN["LEFT"]: tap(2)
            elif b == BTN["RIGHT"]: tap(3)
    if on:
        rb = js.get_button(BTN["RB"])
        if rb and not touch: press(6); touch = True
        if not rb and touch: release(6); touch = False
        acc[16] += dz(js.get_axis(0)) * SPEED * dt
        acc[17] += -dz(js.get_axis(1)) * SPEED * dt
        acc[18] += (trig(5) - trig(4)) * LFE_SPEED * dt
        for n in acc:
            s = int(acc[n])
            if s: rel(n, s); acc[n] -= s
    time.sleep(1 / 120)
if touch: release(6)
print("exit")
