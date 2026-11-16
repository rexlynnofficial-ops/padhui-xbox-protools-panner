# Pro Tools SurroundPanner 协议（盲测记录，2026-11-09）

设置：Peripherals > MIDI Controllers > Type = SurroundPanner，收/发 = PadPan（虚拟端口）
所有控制消息走 MIDI 第 15 通道（状态字节 BE = CC, ch15）；Pro Tools 回传走第 1 通道（B0）。

| 消息 | 含义 | 状态 |
|---|---|---|
| Pro Tools → B0 01 07 | 连接时发送一次 | 已观察 |
| BE 00 nn | 按下按钮 nn | 已确认 |
| BE 01 nn | 松开按钮 nn | 已确认 |
| B0 00 nn / B0 01 nn（PT 回传） | 按钮 nn 的灯 开/关 | 推测 |
| 按钮 00 | 打开/关闭当前目标轨的输出（声像器）窗口 | 已确认 |
| 按钮 02 | 上一条轨（Aux 2 → Audio 39，只成功一次） | 部分确认 |
| BE 14 vv | 音量编码器，相对值，二进制补码（01=+1, 7F=-1），1 步 ≈ 1 dB | 已确认 |
| BE 12 vv | LFE 编码器，相对值（10=+16 步 → 约 -23 dB） | 已确认（Audio 38） |
| BE 10 / 11 / 13 | 对 Audio 38（立体声→5.1，Link 开）无可见效果 | 已测 |
| 摇杆 X / Y | 第 15 通道 CC2–119、其他通道 CC0–9、全部通道弯音，均无效果（含按下 06 号按钮后） | 未找到 |
| 按钮 02（按下+松开） | 切换目标轨：Audio 39 → Audio 38 | 已确认 |

注意：测试中 Audio 39 的音量曾被推到 +12 dB，已恢复为 0.0。

## 第二轮（同日）
- 鼠标拖动声像点时，Pro Tools 不回传任何位置消息。
- 按住 05 / 03 / 04 / 07 号按钮后，再对第 15 通道 CC2–19 发相对值（±16），Front/Rear/F-R/Divergence 均无变化。
- 第 15 通道以外（ch1–14、16）CC10–63 相对值，均无效果。
- 07 号按钮会点亮自己的灯（B0 00 07），是某种模式开关，作用未知；已关回。
- AudioSwift 手册（Logic 附录）说明 X/Y 是"相对值、二进制补码"，与 LFE/音量编码器格式一致，但具体 CC 号未写。

## HUI 结果（同日）
- HUI V-pot 在 Pan 模式下能推动原生声像器的 front 位置（X）：Audio 38（立体声→5.1）、PadTest（单声道→7.1.4）都已验证。
- Pan 键只在 Pan / PanR 之间切换；V-sel（strip 端口 5）、按住 Shift/Ctrl/Alt/Option、按住 V-sel 转动，都无法切到 F/R（Y）或高度。
- Platane 官网写明：Pro Tools 中"左右之间共有 25 个声像位置" → 与 SurroundPanner 相对步长 8（200/8=25）吻合，推测其在 Pro Tools 原生声像器用的是 SurroundPanner（Joystick 模式），不是 HUI；"两台控制 Atmos"在 Pro Tools 里应是通过 Dolby Atmos Panner 插件的 MIDI CC（CC10/11/16/17/25/26）。
