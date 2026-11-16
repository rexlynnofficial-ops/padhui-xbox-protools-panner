#!/usr/bin/env python3
"""
PadMouse v2 — Xbox 手柄控制 Pro Tools 原生声像器（5.1 / 7.1 / 7.1.4 / Atmos 对象）

按键：
  A（按一下）      进入/退出控制（进入后鼠标按住声像点，左摇杆拖动 X/Y）
  左摇杆           X / Y（前后左右）
  右摇杆上下       高度 Z（7.1.4 / Atmos 声像器的高度控件）
  LT / RT（按住）  LFE 音量 减小 / 增大
  RB（按住）       该轨自动化切到 Touch 写入；松开回到 Read
  Menu（☰）        标定：按提示把鼠标放到对应位置后按 Menu，B 跳过当前项
  View（⧉）        重新开始标定

依赖：pip3 install pygame pyobjc-framework-Quartz pyobjc-framework-Cocoa
需要：系统设置 > 隐私与安全性 > 辅助功能 允许"终端"
"""
import argparse, math, os, time, json
import Quartz as Q

HERE = os.path.dirname(os.path.abspath(__file__))
CAL = os.path.join(HERE, "pad_mouse_cal.json")
OVER = 0.12   # 鼠标可超出方格边缘的比例，确保声像能到 ±100

# pygame 下 Xbox 手柄的编号（首次运行看终端 [BTN]/[AXIS] 输出，不对就改这里）
BTN = dict(A=0, B=1, X=2, Y=3, VIEW=4, GUIDE=5, MENU=6, LB=9, RB=10)  # SDL GameController 顺序
AX = dict(LX=0, LY=1, RX=2, RY=3, LT=4, RT=5)

# 标定顺序：(键, 提示)
CAL_STEPS = [
    ("tl",      "鼠标放到 XY 方格【左上角】"),
    ("br",      "鼠标放到 XY 方格【右下角】"),
    ("lfe_cap", "鼠标放到 LFE 推子【当前推子帽】上"),
    ("lfe_top", "鼠标放到 LFE 推子【最上端】(0 dB 以上的顶)"),
    ("lfe_bot", "鼠标放到 LFE 推子【最下端】(-∞)"),
    ("z_knob",  "鼠标放到【高度 Z】旋钮/推子上（5.1 轨没有就按 B 跳过）"),
    ("auto",    "鼠标放到声像器窗口里的【自动化模式】下拉框(auto read)上"),
]

# ---------------------------------------------------------------- 鼠标/键盘
_last = [None]
def mouse_pos():
    p = Q.CGEventGetLocation(Q.CGEventCreate(None)); return (p.x, p.y)

def post(kind, x, y):
    ev = Q.CGEventCreateMouseEvent(None, kind, (x, y), Q.kCGMouseButtonLeft)
    Q.CGEventSetIntegerValueField(ev, Q.kCGMouseEventClickState, 1)
    if _last[0] is not None:
        Q.CGEventSetIntegerValueField(ev, Q.kCGMouseEventDeltaX, int(round(x - _last[0][0])))
        Q.CGEventSetIntegerValueField(ev, Q.kCGMouseEventDeltaY, int(round(y - _last[0][1])))
    _last[0] = (x, y)
    Q.CGEventPost(Q.kCGHIDEventTap, ev)

def key(code):
    for down in (True, False):
        Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateKeyboardEvent(None, code, down)); time.sleep(0.02)

KC = {"t": 17, "o": 31, "r": 15, "e": 14, "return": 36, "escape": 53}

def front_protools():
    try:
        from AppKit import NSRunningApplication
        for a in NSRunningApplication.runningApplicationsWithBundleIdentifier_("com.avid.ProTools"):
            a.activateWithOptions_(3)
        time.sleep(0.2)
    except Exception as e:
        print("activate failed", e)

def click(x, y):
    post(Q.kCGEventLeftMouseDown, x, y); time.sleep(0.03); post(Q.kCGEventLeftMouseUp, x, y)

def drag_relative(x, y, dy, steps=4):
    """在 (x,y) 按下，垂直拖 dy 像素后松开（Pro Tools 旋钮/推子都是相对拖动）"""
    post(Q.kCGEventLeftMouseDown, x, y)
    for i in range(1, steps + 1):
        time.sleep(0.008); post(Q.kCGEventLeftMouseDragged, x, y + dy * i / steps)
    post(Q.kCGEventLeftMouseUp, x, y + dy)

def dz(v, d=0.12):
    return 0.0 if abs(v) < d else (v - math.copysign(d, v)) / (1 - d)

# ---------------------------------------------------------------- 控制器
class Pad:
    def __init__(self):
        import pygame
        self.pg = pygame
        pygame.init(); pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            raise SystemExit("没找到手柄：确认 Xbox 键常亮（蓝牙已连接）")
        self.js = pygame.joystick.Joystick(0); self.js.init()
        print("手柄:", self.js.get_name(), "| 轴", self.js.get_numaxes(), "| 键", self.js.get_numbuttons())
        self.pressed = set()
        pygame.event.pump(); time.sleep(0.1); pygame.event.pump()
        self.rest = [self.js.get_axis(i) for i in range(self.js.get_numaxes())]
        print("轴静止值:", [round(x, 2) for x in self.rest])
        self.prev_ax = list(self.rest)

    def read(self):
        pg, js = self.pg, self.js
        self.pressed = set()
        for e in pg.event.get():
            if e.type == pg.JOYBUTTONDOWN:
                print("[BTN]", e.button); self.pressed.add(e.button)
        ax = lambda i: js.get_axis(i) if i < js.get_numaxes() else 0.0
        for i in range(js.get_numaxes()):          # 打印明显变化的轴，方便核对编号
            if abs(js.get_axis(i) - self.prev_ax[i]) > 0.5:
                print(f"[AXIS] {i} = {js.get_axis(i):+.2f}"); self.prev_ax[i] = js.get_axis(i)
        def trig(i):
            r, val = self.rest[i] if i < len(self.rest) else 0.0, ax(i)
            span = 1 - r if r < 0.5 else 1.0
            t = (val - r) / span
            return t if t > 0.08 else 0.0
        return dict(
            lx=ax(AX["LX"]), ly=-ax(AX["LY"]), ry=-ax(AX["RY"]),
            lt=trig(AX["LT"]), rt=trig(AX["RT"]),
            rb=bool(js.get_button(BTN["RB"])),
            press=lambda name: BTN[name] in self.pressed)

# ---------------------------------------------------------------- 主循环
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=1.2, help="XY 每秒移动方格比例")
    ap.add_argument("--lfe-speed", type=float, default=120, help="LFE 每秒像素")
    ap.add_argument("--z-speed", type=float, default=90, help="Z 每秒像素")
    a = ap.parse_args()

    cal = json.load(open(CAL)) if os.path.exists(CAL) else {}
    cal = {k: tuple(v) for k, v in cal.items()}
    step = 0 if not all(k in cal for k in ("tl", "br")) else None
    if step is not None: print(">> 标定 1/%d：%s，然后按 Menu" % (len(CAL_STEPS), CAL_STEPS[0][1]))
    else: print("已加载标定:", ", ".join(cal), "（按 View 重新标定）")

    pad = Pad()
    u, v = 0.5, 0.5           # XY 归一化（v=0 顶部=前）
    controlling = False       # A 切换
    xy_down = False
    touch = False
    lfe_acc = z_acc = 0.0

    def save(): json.dump(cal, open(CAL, "w"), indent=1)

    def xy_point():
        (x0, y0), (x1, y1) = cal["tl"], cal["br"]
        return x0 + u * (x1 - x0), y0 + v * (y1 - y0)

    def xy_press():
        nonlocal xy_down
        if not xy_down: post(Q.kCGEventLeftMouseDown, *xy_point()); xy_down = True

    def xy_release():
        nonlocal xy_down
        if xy_down: post(Q.kCGEventLeftMouseUp, *xy_point()); xy_down = False

    def set_auto(mode):
        if "auto" not in cal: print("未标定自动化下拉框"); return
        was = xy_down; xy_release()
        click(*cal["auto"]); time.sleep(0.15)
        for ch in mode: key(KC[ch])          # 菜单键入首字母跳转
        key(KC["return"]); time.sleep(0.1)
        print("[AUTO]", "touch" if mode == "to" else "read")
        if was: xy_press()

    last = time.time()
    while True:
        if os.path.exists("mstop"): break
        now = time.time(); dt = min(now - last, 0.05); last = now
        g = pad.read()

        # ---- 标定
        if g["press"]("VIEW"):
            xy_release(); controlling = False; step = 0
            print(">> 标定 1/%d：%s，然后按 Menu" % (len(CAL_STEPS), CAL_STEPS[0][1]))
        if step is not None:
            k, tip = CAL_STEPS[step]
            if g["press"]("MENU") or g["press"]("B"):
                if g["press"]("MENU"): cal[k] = mouse_pos(); print("  ", k, "=", cal[k])
                else: cal.pop(k, None); print("   跳过", k)
                step += 1; save()
                if step >= len(CAL_STEPS): step = None; print(">> 标定完成。按 A 开始控制")
                else: print(">> 标定 %d/%d：%s，然后按 Menu" % (step + 1, len(CAL_STEPS), CAL_STEPS[step][1]))
            time.sleep(1 / 60); continue

        # ---- A 切换控制
        if g["press"]("A"):
            controlling = not controlling
            print("[CTRL]", "开始" if controlling else "退出")
            if controlling: front_protools(); xy_press()
            else:
                xy_release()
                if touch: set_auto("re"); touch = False

        if not controlling:
            time.sleep(1 / 60); continue

        # ---- RB 按住 = Touch
        if g["rb"] and not touch: set_auto("to"); touch = True
        if not g["rb"] and touch: set_auto("re"); touch = False

        # ---- XY
        u += dz(g["lx"]) * a.speed / 60; v -= dz(g["ly"]) * a.speed / 60
        u = min(max(u, -OVER), 1 + OVER); v = min(max(v, -OVER), 1 + OVER)
        if xy_down: post(Q.kCGEventLeftMouseDragged, *xy_point())

        # ---- LFE（扳机），累积到 ≥2 像素再拖一次
        lfe_acc += (g["lt"] - g["rt"]) * a.lfe_speed * dt     # 屏幕 y 向下=减小
        if abs(lfe_acc) >= 2 and all(k in cal for k in ("lfe_cap", "lfe_top", "lfe_bot")):
            cx, cy = cal["lfe_cap"]
            top, bot = cal["lfe_top"][1], cal["lfe_bot"][1]
            ny = min(max(cy + lfe_acc, top), bot); d = ny - cy
            if d:
                xy_release(); drag_relative(cx, cy, d)
                cal["lfe_cap"] = (cx, ny); xy_press()
            lfe_acc = 0.0
        elif abs(lfe_acc) >= 2: lfe_acc = 0.0

        # ---- Z（右摇杆上下），旋钮相对拖动
        z_acc += -dz(g["ry"]) * a.z_speed * dt               # 向上推 = 鼠标往上拖
        if abs(z_acc) >= 2 and "z_knob" in cal:
            xy_release(); drag_relative(*cal["z_knob"], z_acc); xy_press(); z_acc = 0.0
        elif abs(z_acc) >= 2: z_acc = 0.0

        time.sleep(1 / 60)

    xy_release()
    if touch: set_auto("re")
    save(); print("exit")

if __name__ == "__main__":
    main()
