# PadHUI — Xbox controller → Pro Tools surround panner

Emulates a HUI control surface over a virtual MIDI port so an Xbox controller can move Pro Tools' native 5.1 / 7.1.4 / Atmos panner.

- `pad_hui.py` — main tool (virtual HUI over MIDI). `python3 pad_hui.py --sim` runs without a controller for testing.
- `pad_mouse.py` — alternative approach mapping the stick to mouse movement on the panner (calibration in `pad_mouse_cal.json`).
- `pad_sp.py`, `sp_sniff.py`, `sp_tap.py` — experiments / protocol sniffing for the Surround Panner.
- `SurroundPanner协议笔记.md` — protocol notes.
- `run_*.command` — double-click launchers on macOS.

Setup in Pro Tools: Setup > Peripherals > MIDI Controllers → Type = HUI, Receive From / Send To = "PadHUI".
Dependencies: `pip3 install mido python-rtmidi pygame`
Status: work in progress.
